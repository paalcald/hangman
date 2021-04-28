#! /usr/bin/python3
import multiprocessing as mp
import multiprocessing.connection as cn
import threading as th
import sys
import socket
import time

def handle_conn_error(error_code, local_info):
    if error_code == -1:
        new_username = input("username taken, please try a different one: ")
        change_username(new_username, local_info)

def change_username(new_username, local_info):
    local_info['name'] = new_username
    print(f"new username is {local_info['name']}")

def handle_connection(conn):
    while True:
        (user, msg) = conn.recv()
        handle_inc(user, msg)

def handle_inc(user, msg):
    print(f"[{user}]: ", msg)

def cl_listener(info, ready, found):
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
    p = mp.Process(target = handle_connection, args =(conn,))
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
    server_info = {
        'address': server_address,
        'port': server_port,
        'authkey': b"secret server pass"
    }
    local_info = {
        'name': 'pab',
        'address': local_address,
        'port': mp.Value('i',local_port),
        'authkey': b"secret client pass"
    }
    #find opponent

    print(f"attempting to connect to {server_info['address']}"
          f" at port {server_info['port']}\n"
          f"from {local_info['address']}"
          f" at port {local_info['port']}\n")

    with cn.Client(address=(server_info['address'], server_info['port']) ,
                      authkey= server_info['authkey']) as sv_conn:
        listener_ready = mp.Semaphore(value=0)
        opponent_found = mp.Semaphore(value=0)
        #lanzar el proceso que escucha del juego
        sv = mp.Process(target = cl_listener, args = (local_info,
                                                   listener_ready,
                                                   opponent_found))
        sv.start()
        listener_ready.acquire()
        local_info['port'] = local_info['port'].value
        #attemp connection to enemy
        #opponent_found.acquire()
        status = 0;  
        """ 
        status = { 0 => being added to playerbase  ,
                   1 => in lobby                   ,
                   2 => playing                    }
        """
        while True:
            if status == 0: # being added to playerbase
                sv_conn.send(local_info)
                (code, msg) = sv_conn.recv()
                if code == 0: # 0 for connection success
                    status = 1
                elif code == -1: # -1 for connection error
                    handle_conn_error(msg, local_info)

            elif status == 1: # player in lobby
                msg_out = input("> ")
                sv_conn.send(msg_out)
                (code, msg) = sv_conn.recv()
                if code == 0:
                    for item in msg:
                        print(item)
                elif code == 1:
                    op_conn = cn.Client(address=(msg['address'],
                                                   msg['port']),
                                          authkey= msg['authkey'])
                    status = 2 
                    print("playing")

            elif status == 2: # playing
                msg_out = input("")
                if len(msg_out) == 1:
                    sv_conn.send(msg_out)
                    game_state = sv_conn.recv()
                    if game_state[0] == 'ongoing':
                        print(game_state[1])
                    elif game_state[0] == 'over':
                        print(game_state[1])
                        game_conn.close()
                        playing = False
                else:
                    op_conn.send((local_info['name'], msg_out))


#conectar con el servidor
if __name__ == '__main__':
    main(sys.argv[1:])
