#! /usr/bin/python3
import multiprocessing as mp
import multiprocessing.connection as cn
import sys
import socket
import time
import ctypes
import string

class Hangman_Interface():
    def __init__(self, name1, manager, ready):
        w1 = "Welcome to the Hangman game interface, a game developed by UCM"
        w2 = "students to learn to code using parallel programming tecniques."
        w3 = "To start playing type a command, 'help' to see available ones."
        w4 = " "
        w5 = " "
        w6 = "You are now connected to the server. Enjoy your time!!"
        self.chat_log      = manager.list((w1,w2,w3,w4,w5,w6))
        self.known_letters = manager.list(("","","","","","","","","","","",""))
        self.player_name   = name1
        self.op_name       = manager.Value(ctypes.c_wchar_p, "--")
        self.player_score  = mp.Value('i', 0)
        self.op_score      = mp.Value('i', 0)
        self.word_length   = mp.Value('i', 0)
        self.mistakes      = mp.Value('i', 7)
        self.op_mistakes   = mp.Value('i', 7)
        self.mutex         = mp.Lock()
        self.refresh_cond  = mp.Condition(self.mutex)
        self.printing      = mp.Process(target = self.show_intf)
        self.ready         = ready

    def set_op(self, op):
        self.mutex.acquire()
        self.op_name.value = op
        self.refresh_cond.notify_all()
        self.mutex.release()
    
    def set_len(self, leng):
        self.mutex.acquire()
        self.word_length.value = leng
        self.refresh_cond.notify_all()
        self.mutex.release()
        
    def update_log(self, msg):
        self.mutex.acquire()
        if len(self.chat_log) < 6:
            for entry in msg:
                self.chat_log.append(entry)
        else:
            for entry in msg:
                self.chat_log.pop(0)
                self.chat_log.append(entry)
        self.refresh_cond.notify_all()
        self.mutex.release()

    def update_game_state(self, msg):
        self.mutex.acquire()
        self.player_score.value = msg['score']
        self.mistakes.value = msg['mistakes']
        self.op_mistakes.value = msg['op_mistakes']
        self.refresh_cond.notify_all()
        self.mutex.release()

    def show_intf(self):
        self.ready.release()
        print(self.artf())
        while True:
            self.refresh()

    def refresh(self):
        self.mutex.acquire()
        self.refresh_cond.wait(30)
        print(self.artf())
        self.mutex.release()

    def artf(self):
        play1 = self.player_name.value
        pla2  = self.op_name.value
        length = self.word_length.value
        s1 = self.player_score.value
        s2 = self.op_score.value
        l = list(self.known_letters)
        r = list(map(lambda i: "▔▔▔" if (i < length) else ' ', range(12)))
        chat = list(self.chat_log)
        art = [[0]*8]*8
        for i in range(8):
            for j in range(8):
                art[i][j] = f"{play1}: {i}, {pla2}: {j}, chat: {self.chat_log}"
        art[7][7]=f"""
╔═══════════════════════════════════════════════════════════════════╗
║ {play1:10} {s1:^3}              🅷🅰🅽🅶🅼🅰🅽                {s2:^3} {pla2:>10} ║
╠═══════════════════════════════════════════════════════════════════╣
║                      ▛▀▀▀▀▀▀▀▀▀██▀▀▀▀▀▀▀▀▜                        ║
║                      ┊         ██        ┊                        ║
║                      O         ██        O                        ║
║                     /|\        ██       /|\                       ║
║                      |         ██        |                        ║
║                     / \        ██       / \                       ║
║                                ██                                 ║
║                ▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂██▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂                 ║
║                ▐▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▌                 ║
║                ▐▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▌                 ║
║                ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀                 ║
║                                                                   ║
║          {l[0]:^3} {l[1]:^3} {l[2]:^3} {l[3]:^3} {l[4]:^3} {l[5]:^3} {l[6]:^3} {l[7]:^3} {l[8]:^3} {l[9]:^3} {l[10]:^3} {l[11]:^3}          ║
║          {r[0]:3} {r[1]:3} {r[2]:^3} {r[3]:3} {r[4]:3} {r[5]:3} {r[6]:3} {r[7]:3} {r[8]:3} {r[9]:3} {r[10]:3} {r[11]:3}          ║
╠═══════════════════════════════════════════════════════════════════╣
║ {chat[0]:66}║
║ {chat[1]:66}║
║ {chat[2]:66}║
║ {chat[3]:66}║
║ {chat[4]:66}║
║ {chat[5]:66}║
╚═══════════════════════════════════════════════════════════════════╝"""      
        return art[self.mistakes.value][self.op_mistakes.value]

def send_fmt(local_info):
    fmtd_info            = {}
    fmtd_info['name']    = local_info['name'].value
    fmtd_info['address'] = local_info['address']
    fmtd_info['port']    = local_info['port'].value
    fmtd_info['authkey'] = local_info['authkey']
    return fmtd_info


def handle_conn_error(error_code, local_info):
    if error_code == -1:
        new_username = input("username taken, please try a different one: ")
        change_username(new_username, local_info)

def change_username(new_username, local_info):
    local_info['name'].value = new_username
    print(f"new username is {local_info['name'].value}")

def handle_connection(conn, intf):
    while True:
        (user, msg) = conn.recv()
        msg_f = f"[{user}]: {msg}"
        intf.update_log(msg_f)

def cl_listener(info, ready, intf):
    print(f"Opening listener")
    attemps = 10
    while attemps > 0:
        try:
            cl = cn.Listener(address=(info['address'], info['port'].value),
                             authkey= info['authkey'])
            print("accepting connections ...")
            ready.release()
        except OSError:
            attemps -= 1
            info['port'].value += 1
            time.sleep(.1)
            continue
        break
    conn = cl.accept()
    p = mp.Process(target = handle_connection, args =(conn,intf))
    p.start()

def main(argv):
    if (len(argv) < 5):
        server_address = '127.0.0.1'
        server_port = 8080
        local_name = 'test_name'
        local_address = '127.0.0.1'
        local_port = 8090
    else:
        server_address = argv[0]
        server_port = int(argv[1])
        local_name = argv[2]
        local_address = argv[3]
        local_port = int(argv[4])
    m = mp.Manager()
    server_info = {
        'address' : server_address,
        'port'    : server_port,
        'authkey' : b"secret server pass"
    }
    local_info ={
        'name'    : m.Value(ctypes.c_wchar_p, "pab"),
        'address' : local_address,
        'port'    : mp.Value('i',local_port),
        'authkey' : b"secret client pass"
    }
    print(f"attempting to connect to {server_info['address']}"
          f" at port {server_info['port']}\n"
          f"from {local_info['address']}"
          f" at port {local_info['port'].value}\n")

    with cn.Client(address=(server_info['address'], server_info['port']) ,
                      authkey= server_info['authkey']) as sv_conn:
        #lanzar la interfaz del juego
        intf_ready = mp.Semaphore(value=0)
        intf = Hangman_Interface(local_info['name'],
                                 m,
                                 intf_ready)
        intf.printing.start()
        intf_ready.acquire()
        #lanzar el proceso que escucha del juego
        listener_ready = mp.Semaphore(value=0)
        sv = mp.Process(target = cl_listener, args = (local_info,
                                                   listener_ready,
                                                   intf))
        sv.start()
        listener_ready.acquire()
        status = 0;  
        """ 
        status = { 0 => being added to playerbase  ,
                   1 => in lobby                   ,
                   2 => playing                    }
        """
        while True:
            # CONNECTING
            if status == 0: 
                sv_conn.send(send_fmt(local_info))
                (code, msg) = sv_conn.recv()
                if code == 0: # 0 for connection success
                    status = 1
                elif code == -1: # -1 for connection error
                    handle_conn_error(msg, local_info)
            # IN LOBBY
            elif status == 1:
                msg_out = input("> ")
                sv_conn.send(msg_out)
                (code, msg) = sv_conn.recv()
                if code == 0:
                    intf.update_log(msg)
                elif code == 1:
                    print(msg)
                    op_conn = cn.Client(address=(msg['address'],
                                                   msg['port']),
                                          authkey= msg['authkey'])
                    status = 2  
                    (op_name, word_length) = sv_conn.recv()
                    intf.set_op(op_name)
                    intf.set_len(word_length)
            # PLAYING
            elif status == 2:
                msg_out = input("")
                if len(msg_out) == 1:
                    sv_conn.send(msg_out)
                    (code, game_state) = sv_conn.recv()
                    if code == 1: #game ongoing
                        update_game_state(game_state)
                    elif code == 0: #game over
                        print(game_state)
                        status = 1 #in lobby
                        op_conn.close()
                else:
                    fmtd_msg_out = (local_info['name'].value, msg_out)
                    op_conn.send(fmtd_msg_out)
                    intf.update_log(f"[{fmtd_msg_out[0]}]: {fmtd_msg_out[1]}")

#conectar con el servidor
if __name__ == '__main__':
    main(sys.argv[1:])
