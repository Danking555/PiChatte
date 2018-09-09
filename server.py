
import select, Queue, sys, socket

initial_port = 8200
max_client_size = 4
server_ip = '0.0.0.0'


class ServerError(Exception):
    pass

class CloseServer(Exception):
    pass

class ClientData:
    def __init__(self):
        self.messages = Queue.Queue() # Init new messages queue for client
        self.name = 'Uknown'

class Communication():


    def __init__(self):
        self.initListeningServer()
        self.inputs = [sys.stdin, self.server]
        self.outputs = []
        self.clients_data = {}
        print 'listening for new connections on port', initial_port


    def initListeningServer(self):
        '''
        Inits new tcp listening on the local machine
        :return:
        '''
        global initial_port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                self.server.bind(('0.0.0.0', initial_port))
                break
            except Exception:
                initial_port += 1
                continue
        self.server.listen(max_client_size)
        self.server.setblocking(0)


    def closeServer(self):
        '''
        Sends 'closing message' to clients and stops connection
        Closes the server
        :return:
        '''
        for client in self.inputs[2:]:
            client.send('server is stopped! Closing connection')
            if client in self.outputs: self.outputs.remove(client)
            if client in self.inputs: self.inputs.remove(client)
        self.server.close()
        self.inputs.remove(self.server)

    def acceptNewConnection(self):
        '''
        Accepts a connection and sends a 'what is your name?' message
        :return:
        '''
        client_socket, peername = self.server.accept()
        port = peername[1]
        print 'Accepted new connection on port', port

        self.inputs.append(client_socket)  # Add to list for listening
        self.clients_data[client_socket] = ClientData()
        self.clients_data[client_socket].messages.put("what is your name?")
        self.outputs.append(client_socket)  # Add to list for sending

    def acceptClientName(self,client, data):
        '''
        Send hello (name) message to client
        :param client:
        :param data:
        :return:
        '''
        self.clients_data[client].name = data  # Update the name of the client
        if client not in self.outputs:
            self.outputs.append(client)
        self.clients_data[client].messages.put("Server says: Hello " + data)
        self.sendall(self.server, data + ' joined the room', client)

    def sendall(self,from_sender, data, to_change = None):
        '''
        Sets a speicific message to all connected clients, if any, except of the sender.
        Sets a message to the sender regarding what clients the message will be sent to
        :param from_sender: the sender socket (client)
        :param data: message to send
        :return:
        '''
        name = self.clients_data[from_sender].name if from_sender != self.server else "\nServer"
        to_send = name + ': ' + data
        special = None # used to replace name. i.e you left the room
        if to_change:
            special = '\nyou ' + ' '.join(data.split()[1:])
        clients = []

        for client in self.inputs[1:]:  # send the message
            self.outputs.append(client)


            if client != from_sender:
                if client not in self.clients_data: continue # Some error
                clients.append(self.clients_data[client].name)
                if special and client == to_change: # send you instead of the name for this message
                    self.clients_data[client].messages.put(special)
                else:
                    self.clients_data[client].messages.put(to_send)
            elif self.server != from_sender:
                self.clients_data[from_sender].messages.put(
                    "Server: message sent to " + "server only" if len(
                        clients) == 0 else "the users: " + str(clients))

    def handleLostConnection(self,client,port):
        '''
        Removes client from clients list and sends update to all clients
        :param client:
        :param port:
        :return:
        '''
        print 'connection with', port, 'named', self.clients_data[client].name, 'lost'
        self.sendall(self.server, self.clients_data[client].name + ' left the room', client)
        del self.clients_data[client]  # Can't send messages to this socket anymore

        if client in self.outputs:
            self.outputs.remove(client)  # in case a message had to be sent to this client -> remove socket

        self.inputs.remove(client)  # remove socket

    def handleServerCommands(self):
        command = raw_input()
        if command == 'stop':
            self.closeServer()
            raise CloseServer

    def handleRecieveDataFromClient(self, client):
        '''
        Accepts new name from client or Accepts a message from client and sends to all connected clients
        :param client: Recieve on this socket
        :return:
        '''
        data = client.recv(1024)
        port = client.getpeername()[1]
        if data:
            print 'from port', port, '--', data

            if self.clients_data[client].name == 'Uknown': # Client answered to 'What is your name?'
                self.acceptClientName(client, data)
            else:
                self.sendall(client, data)  # Send message to all other clients

        else:
            self.handleLostConnection(client, port)  # THE READ OF SOCKET IN NONE BECAUSE IT HAS BEEN CLOSED

    def sendToSocket(self, client):
        '''
        Sends the first message available for a client from his messages queue
        :param client: socket to send message (client)
        :return:
        '''
        try:
            to_send = self.clients_data[client].messages.get_nowait()  # Get last message to be sent
        except Queue.Empty:
            # There are no messages to send the client (Error while setting output to socket ?)
            self.outputs.remove(client)
        else:
            client.send(to_send)  # send the message on the socket
            print 'sent:', to_send, ',to:', self.clients_data[client].name

    def mainProccess(self):
        '''
        Does all the job of establishing new connections closing connections, sending messages and recieving messages
        :return:
        '''
        try:
            while self.inputs:
                # in case of a change in input socket, output socket don't block and operate else it blocks all other operations such as input
                reading, writing, exceptional = select.select(self.inputs, self.outputs, self.inputs)

                for s1 in reading:

                    if s1 is sys.stdin:
                        self.handleServerCommands()
                    elif s1 is self.server:
                        self.acceptNewConnection()
                    else: # ACCEPT DATA FROM CONNECTION
                        self.handleRecieveDataFromClient(s1)

                if len(self.inputs) == 1:
                    raise CloseServer

                # Send of data is required for socket (only once, so remove socket)
                for s2 in writing:
                    if s2 not in self.outputs: continue
                    self.sendToSocket(s2)

                # Error -> if server -> send error to all sockets, else if some client-> remove from list of inputs, or outputs
                for s3 in exceptional:

                    if self.server is s3:
                        raise ServerError
        except CloseServer:
            print 'closing server'
            self.closeServer()


def chatServer():
    connection = Communication()
    try:
        connection.mainProccess()
    except KeyboardInterrupt:
        print "Keyboard interrupt closing the connections"
        connection.closeServer()
    except ServerError:
        print "Error ocoured in server"
        connection.closeServer()

    except Exception as e:
        print 'error establishing server:'
        print e

if __name__ == '__main__':
    chatServer()