#! /usr/bin/python3 
import multiprocessing as mp
import multiprocessing.connection as cn
import sys
    
class UsernameTaken(Exception):
    """the username is taken """
    pass

class RequestDenied(Exception):
    """the oponent didnt accept the request on time """
    pass
class Playerbase:
    def __init__(self, manager):
        self.username = '' 
        self.players = manager.dict()
        self.mutex = mp.Lock()
        self.requests = manager.list()
        self.c_mutex = mp.Lock()
        self.cond = mp.Condition(self.mutex)

    def add(self, player, player_info):
        self.mutex.acquire()
        try:
            self.players[player]
            username_taken = True
        except:
            self.players[player] = player_info
            username_taken = False
        self.mutex.release()
        if username_taken:
            raise UsernameTaken

    def listRequests(self):
        return list(self.requests)

    def setUsername(self, name):
        self.username = name

    def getInfo(self,player):
        return self.players[player]

    def getPlayers(self):
        return self.players.keys()

    def acceptRequest(self, opponent):
        self.mutex.acquire()
        self.requests.append((opponent, self.username))
        print(self.requests)
        self.cond.notify_all()
        self.mutex.release()

    def makeRequest(self, opponent):
        self.mutex.acquire()
        out = self.cond.wait_for(lambda: 
                (self.username, opponent) in self.listRequests(),
                timeout = 30)
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
                "- ls : display current playerbase",
                "- play <player> : request to play against <player>",
                "- accept <player> : accept to play against <player>",
                "- info <player>"]
        msg_out = (0, to_print)

    elif command == 'ls':
        to_print = pb.getPlayers()
        msg_out = (0, to_print) 

    elif command == 'accept':
        try:
            op = args
            pb.acceptRequest(op)
            msg_out = (1, pb.getInfo(op))
            print(msg_out)
        except KeyError:
            to_print = "couldn't find opponent, type 'ls' for list"
            msg_out = (0, to_print)

    elif command == 'play':
        try:
            op = args
            if pb.makeRequest(op):
                opponent_info = pb.getInfo(op)
                msg_out = (1, opponent_info)
                status = 2
            else:
                raise RequestDenied
        except RequestDenied:
            to_print = f"{op} did not accept your request"
            msg_out = (0, to_print)
        except KeyError:
            to_print = "couldn't find opponent, type 'ls' for list"
            msg_out = (0, to_print)

    elif command == 'info':
        try:
            tar = args
            tar_info = pb.getInfo(tar).items()
            msg_out = (0, tar_info)
        except:
            pass

    else:
        to_print = ["unknown command, type 'help' to see available ones"] 
        msg_out = ('print', to_print)
    new_player.send(msg_out)
        

def handle_connection(new_player, tmp_id, playerbase):
    status = 0 # adding to db
    while True:
        if status == 0: # adding player to playerbase
            player_info = new_player.recv()
            try:
                username = player_info.pop('name')
                playerbase.setUsername(username)
                playerbase.add(username, player_info)
                status = 1
                print(f"{tmp_id} added to playerbase as {username}")
                msg = (0, 1)
            except UsernameTaken:
                msg = (-1 , -1) # ( -1, 1) for (error, username_taken)
            new_player.send(msg)
        elif status == 1: # player in lobby
            msg = new_player.recv()
            process_input(msg, new_player, playerbase, status)
        elif status == 2: # playing
            msg = new_player.recv()
            new_player.send("lol")

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
            p = mp.Process(target = handle_connection, args =(new_player,
                                                              tmp_id,
                                                              playerbase))
            p.start()

if __name__ == '__main__':
    main(sys.argv[1:])
