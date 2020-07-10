from State import *
from socket import socket
import pickle
from time import sleep

class Transition:
    def passive_open(self):
        print ("Error!")
        return False
    def syn(self):
        print ("Error!")
        return False
    def ack(self):
        print ("Error!")
        return False
    def rst(self):
        print ("Error!")
        return False
    def syn_ack(self):
        print ("Error!")
        return False
    def close(self):
        print ("Error!")
        return False
    def fin(self):
        print ("Error!")
        return False
    def timeout(self):
        print ("Error!")
        return False
    def active_open(self):
        print ("Error!")
        return 

class Closed(State, Transition): 
    def __init__(self, Context):
        State.__init__(self, Context)   

    def passive_open(self):
        #transition to listen state
        print("[Server] Transitioning to listen state..." + "\n")
        sleep(self.CurrentContext.sleep_time)
        self.CurrentContext.setState("LISTEN")
        return True

    def trigger(self):
        try:
            print("[Server] Current state = " + self.CurrentContext.state + "\n")
            self.CurrentContext.socket.close()  # attempt to terminate socket
            sleep(self.CurrentContext.sleep_time)
            return True
        except:  # no current connection
            return False

class Listen(State, Transition):
    def __init__(self, Context):
        State.__init__(self, Context)
    def syn(self):
        print("[Server] Acknowledging...")
        #generate and sent acknowledgement packet
        self.CurrentContext.data["flg"] = "SYN+ACK"
        #set sequence number expected from client
        self.CurrentContext.data["ackSeq"] += 1
        #serialise dictionary(packet) using pickle then send
        msg = pickle.dumps(self.CurrentContext.data)
        self.CurrentContext.connection.send(msg)
        print("[Server] Packet sent: " + str(self.CurrentContext.data))
        sleep(self.CurrentContext.sleep_time)
        #transition to syn received
        print("[Server] Transitioning to syn received state..." + "\n")
        self.CurrentContext.setState("SYN_RECVD")
        return True

    def trigger(self):
        print("[Server] Current state = " + self.CurrentContext.state + "\n")
        #listen for incoming packets
        self.CurrentContext.listen()
        #capture packet and deserialise
        msg = self.CurrentContext.connection.recv(1024)
        data = pickle.loads(msg)
        print("[Server] Packet received: " + str(data))
        sleep(self.CurrentContext.sleep_time)
        #reply if sequence number and flag are as expected
        if data["seq"] == self.CurrentContext.data["ackSeq"] and data["flg"] == "SYN":
            return self.CurrentContext.syn()
        else:
            print("invalid cmd")
            return False


class Syn_Recvd(State, Transition):
    def __init__(self, Context):
        State.__init__(self, Context)

    def ack(self):
        print("[Server] Connection established")
        #transition to syn established state
        print("[Server] Transitioning to established state..." + "\n")
        self.CurrentContext.setState("ESTABLISHED")
        return True

    def trigger(self):
        print("[Server] Current state = " + self.CurrentContext.state + "\n")
        msg = self.CurrentContext.connection.recv(1024)
        data = pickle.loads(msg)
        print("[Server] Packet received: " + str(data))
        sleep(self.CurrentContext.sleep_time)
        #if packet receive contains ack flag then connection has been succesfully established
        if data["seq"] == self.CurrentContext.data["ackSeq"] and data["flg"] == "ACK":
            return self.CurrentContext.ack()
        #if flag is rst then that means somethong went wrong on client side
        elif data["flg"] == "RST":
            print("connection timed out...")
            #reset packet dictionary
            self.CurrentContext.data = {"seq": 0, "ackSeq": 0, "flg": ""}
            #transition to listen
            return self.CurrentContext.setState("LISTEN")

        else:
            print("invalid cmd")
            return False

class Established(State, Transition):
    def __init__(self, Context):
        State.__init__(self, Context)

    def fin(self):
        #send ack to client
        print("[Server] Acknowledging...")
        self.CurrentContext.data["flg"] = "ACK"
        self.CurrentContext.data["ackSeq"] += 1
        msg = pickle.dumps(self.CurrentContext.data)
        self.CurrentContext.connection.send(msg)
        print("[Server] Packet sent: " + str(self.CurrentContext.data))
        sleep(self.CurrentContext.sleep_time)
        #transition to close wait
        print("[Server] Transitioning to close wait state...\n")
        self.CurrentContext.setState("CLOSE_WAIT")

    def trigger(self):
        print("[Server] Current state = " + self.CurrentContext.state + "\n")
        msg = self.CurrentContext.connection.recv(1024)
        data = pickle.loads(msg)
        print("[Server] Packet received: " + str(data))
        sleep(self.CurrentContext.sleep_time)
        #begin closing connection when fin flag is receieved
        if data["seq"] == self.CurrentContext.data["ackSeq"] and data["flg"] == "FIN":
            self.CurrentContext.data["seq"] = data["ackSeq"]
            return self.CurrentContext.fin()

class Close_wait(State, Transition):
    def __init__(self, Context):
        State.__init__(self, Context)
    def close(self):
        #send fin to client
        print("[Server] Sending fin request...")
        self.CurrentContext.data["flg"] = "FIN"
        self.CurrentContext.data["ackSeq"] += 1
        msg = pickle.dumps(self.CurrentContext.data)
        self.CurrentContext.connection.send(msg)
        sleep(self.CurrentContext.sleep_time)
        print("[Server] Packet sent: " + str(self.CurrentContext.data))
        #transition to last ack
        print("[Server] Transitioning to last ack state...\n")
        self.CurrentContext.setState("LAST_ACK")

    def trigger(self):
        print("[Server] Current state = " + self.CurrentContext.state + "\n")
        return self.CurrentContext.close()
    
class Last_ack(State, Transition):
    def __init__(self, Context):
        State.__init__(self, Context)
    def ack(self):
        print("[Server] Fin request acknowledged")
        print("[Server] Connection timing out...")
        self.CurrentContext.timeout()
        return True

    def timeout(self):
        # transition to closed
        print("[Server] Transitioning to closed state...\n")
        self.CurrentContext.setState("CLOSED")
        return True

    def trigger(self):
        print("[Server] Current state = " + self.CurrentContext.state + "\n")
        msg = self.CurrentContext.connection.recv(1024)
        data = pickle.loads(msg)
        print("[Server] Packet received: " + str(data))
        sleep(self.CurrentContext.sleep_time)
        if data["seq"] == self.CurrentContext.data["ackSeq"] and data["flg"] == "ACK":
            self.CurrentContext.data["seq"] = data["ackSeq"]
            return self.CurrentContext.ack()

class TCP_Server(StateContext, Transition):
    def __init__(self):
        self.sleep_time = 2 #places pauses in script for demo purposes
        self.host = "127.0.0.1"
        self.port = 5000
        self.socket = None
        self.seq = 0 #initial sequence number
        self.ackSeq = 0 #initial ack number
        self.data = {"seq": self.seq, "ackSeq": self.ackSeq, "flg": ""} #dictionary to hold packet data
        self.availableStates["CLOSED"] = Closed(self)
        self.availableStates["LISTEN"] = Listen(self)
        self.availableStates["SYN_RECVD"] = Syn_Recvd(self)
        self.availableStates["ESTABLISHED"] = Established(self)
        self.availableStates["CLOSE_WAIT"] = Close_wait(self)
        self.availableStates["LAST_ACK"] = Last_ack(self)
        self.setState("CLOSED")

    def passive_open(self):
        return self.CurrentState.passive_open()
    def syn(self):
        return self.CurrentState.syn()
    def ack(self):
        return self.CurrentState.ack()
    def syn_ack(self):
        return self.CurrentState.syn_ack()
    def close(self):
        return self.CurrentState.close()
    def fin(self):
        return self.CurrentState.fin()
    def timeout(self):
        return self.CurrentState.timeout()
    def active_open(self):
        return self.CurrentState.active_open()

    def listen(self):
        '''initiates a listen socket'''
        self.socket = socket()
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            self.connection, self.connection_address = self.socket.accept()
            return True
        except Exception as err:
            print(err)
            exit()

if __name__ == '__main__':
    activeServer = TCP_Server()
    activeServer.passive_open()
    var = input("...")