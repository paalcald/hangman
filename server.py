#! /usr/bin/python3 
import multiprocessing as mp
import multiprocessing.connection as cn
import sys
import ctypes
    
class UsernameTaken(Exception):
    """the username is taken """
    pass

class RequestDenied(Exception):
    """the oponent didnt accept the request on time """
    pass
class PlayerInfo:
    def __init__(self, conn, info, manager):
        self.info = info
        self.conn = conn

    def get_info(self):
        return self.info
    
    def get_conn(self):
        return self.conn

class Playerbase:
    def __init__(self, manager):
        self.username = '' 
        self.manager = manager
        self.players = manager.dict()
        self.mutex = mp.Lock()
        self.requests = manager.dict()
        self.accepted = manager.dict()
        self.cond = mp.Condition(self.mutex)

    def add(self, player, player_info, player_conn):
        self.mutex.acquire()
        try:
            self.players[player]
            username_taken = True
        except:
            self.players[player] = PlayerInfo(player_conn,
                                              player_info,
                                              self.manager)
            self.requests[player] = []
            self.accepted[player] = 0
            username_taken = False
        self.mutex.release()
        if username_taken:
            raise UsernameTaken

    def listRequests(self):
        return list(self.requests)

    def setUsername(self, name):
        self.username = name

    def getInfo(self,player):
        return self.players[player].get_info()

    def getPlayers(self):
        return self.players.keys()

    def acceptRequest(self, opponent):
        self.mutex.acquire()
        out = False
        print(f"{self.requests[self.username]}")
        if opponent in self.requests[self.username]:
            self.accepted[opponent] = 1
            out = True
        print(f"after if {out}")
        self.cond.notify_all()
        self.mutex.release()
        return out

    def makeRequest(self, opponent):
        self.mutex.acquire()
        player = self.username
        self.requests[opponent] = self.requests[opponent] + [self.username]
        notification = (2, [f"You received a game request from {self.username}!"])
        self.players[opponent].get_conn().send(notification)
        out = self.cond.wait_for(lambda: self.accepted[self.username] == 1,
                                 timeout = 10)
        self.requests[opponent] = list(filter(lambda x: x!=player,
                                              self.requests[opponent]))
        print(self.requests[opponent])
        self.accepted[self.username] = 0
        self.mutex.release()
        return out

    def remove(self, player_id):
        self.mutex.acquire()
        try:
            self.players.pop(player_id)
        except:
            pass
        self.mutex.release()

def process_input(msg, new_player, pb, status):
    try:
        [command, args] = msg.split()
    except:
        command = msg

    if command == 'help':
        to_print = ["Please type an available command for server interaction",
                " - ls : display current playerbase",
                " - play <player> : request to play against <player>",
                " - accept <player> : accept to play against <player>"]
        msg_out = (0, to_print)

    elif command == 'ls':
        to_print = pb.getPlayers()
        to_print.remove(pb.username)
        to_print =list(map(lambda string: " -" + string, to_print))
        to_print.insert(0, "jugadores: ")
        msg_out = (0, to_print) 

    elif command == 'request':
        to_print = pb.listRequests()
        msg_out = (0, to_print)

    elif command == 'accept':
        try:
            op = args
            if pb.acceptRequest(op):
                msg_out = (1, pb.getInfo(op))
                print(msg_out)
                status = 2
                new_player.send((2, ["Game request accepted"]))
            else:
                to_print = [f"you didn't receive any request from {op}"]
        except KeyError:
            to_print = ["couldn't find opponent, type 'ls' for list"]
            msg_out = (0, to_print)

    elif command == 'play':
        try:
            op = args
            if pb.makeRequest(op):
                opponent_info = pb.getInfo(op)
                msg_out = (1, opponent_info)
                status = 2
                new_player.send((2, ["Game request accepted!"]))
            else:
                raise RequestDenied
        except RequestDenied:
            to_print = [f"{op} did not accept your request"]
            msg_out = (0, to_print)
        except KeyError:
            to_print = ["couldn't find opponent, type 'ls' for list"]
            msg_out = (0, to_print)

    else:
        to_print = ["unknown command, type 'help' to see available ones"] 
        msg_out = (0, to_print)
    new_player.send(msg_out)
    print(msg_out)
    return (1 if status==1 else 2)
        

def handle_connection(new_player, tmp_id, playerbase, ready):
    status = 0 # adding to db
    try:
        while True:
            if status == 0: # adding player to playerbase
                player_info = new_player.recv()
                try:
                    username = player_info.pop('name')
                    playerbase.setUsername(username)
                    playerbase.add(username, player_info, new_player)
                    status = 1
                    print(f"{tmp_id} added to playerbase as {username}")
                    ready.release()
                    msg = (0, 1)
                except UsernameTaken:
                    msg = (-1 , -1) # ( -1, 1) for (error, username_taken)
                new_player.send(msg)
            elif status == 1: # player in lobby
                msg = new_player.recv()
                status = process_input(msg, new_player, playerbase, status)
            elif status == 2: # playing
                print(f"{playerbase.username} is playing" )
                new_player.send(('pepe', 4))
                msg = new_player.recv()
                new_player.send("lol")
    except:
        playerbase.remove(playerbase.username)

def main(argv):
    if (len(argv) < 2):
        server_address = '127.0.0.1'
        server_port = 8080
    else:
        server_address = argv[0]
        server_port = int(argv[1])
    server_info = {
        'address': server_address,
        'port': server_port,
        'authkey': b"secret server pass"
    }
    with cn.Listener(address=(server_info['address'], server_info['port']) ,
                     authkey= server_info['authkey']) as public_port:
        print(f"Game server starting at ip {server_info['address']}"
              f" in port {server_info['port']} ...")

        m = mp.Manager()
        playerbase = Playerbase(m)

        while True:
            print("accepting connections...")
            new_player = public_port.accept()
            tmp_id = public_port.last_accepted
            print("new connection from ", tmp_id)
            player_added = mp.Semaphore(value=0)
            p = mp.Process(target = handle_connection, args =(new_player,
                                                              tmp_id,
                                                              playerbase,
                                                              player_added))
            p.start()
            player_added.acquire()

if __name__ == '__main__':
    main(sys.argv[1:])
