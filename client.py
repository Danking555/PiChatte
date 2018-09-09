import socket
import server
import sys

def get_client_ip():
    if server.server_ip == '0.0.0.0':
        return '127.0.0.1'
    return server.server_ip

def connect_open_to_port():
    for add_port in range(server.max_client_size):
        try:
            client = socket.socket()
            client.connect((get_client_ip(),server.initial_port + add_port))
            return client
        except Exception as e:
            print e
            del client
            continue

import select, Queue

class ServerAborted(Exception):
    pass


def recieveNewData(server,first_time_bool):
    # Get new data
    data = server.recv(1024)
    if not data:
        # server forcibly closed
        raise ServerAborted
    else:
        print data
        if not first_time_bool:
            print "type what you want to be echoed..."


def chatClient():
    '''
    A simple chat client enabling init/destroy connection with server, excepting data from/to server
    :return:
    '''
    try:
        conn = connect_open_to_port()
        conn.setblocking(0)
        inputs = [sys.stdin, conn]
        outputs = []
        messages = {}
        first_time_bool = True

        while inputs:
            reading, writing, exceptional = select.select(inputs, outputs,inputs) # That's blocking

            # Socket to conn sends data, check if it's from someone -> print data
            for s in reading:
                if s == conn:
                    recieveNewData(conn,first_time_bool)
                if s == sys.stdin:
                    data = raw_input()

                    # set the messages
                    if first_time_bool:
                        messages[conn] = Queue.Queue() # init new message queue
                        first_time_bool = False

                    messages[conn].put(data)
                    outputs.append(conn)

            for s2 in writing:
                try:
                    to_send = messages[s2].get_nowait()

                except Queue.Empty:
                    outputs.remove(conn)
                else:
                    conn.send(to_send)

            for s3 in exceptional:
                pass

        conn.close()
    except KeyboardInterrupt:
        conn.close()
    except ServerAborted:
        conn.close()
        print "Server aborted"


if __name__ == '__main__':
    chatClient()