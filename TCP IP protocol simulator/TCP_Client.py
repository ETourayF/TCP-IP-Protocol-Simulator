from State import *
from socket import socket
import pickle
from time import *
import time

#transitions
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

    def active_open(self):
        print("[Client] Initiating connection...")
        self.CurrentContext.make_connection()
        print("[Client] Sending syn request...")

        #initiating 3 way handshake with syn packet
        self.CurrentContext.data["flg"] = "SYN"
        #packet is in dictionary form. pickle serialises the dictionary
        #so that it can be sent
        msg = pickle.dumps(self.CurrentContext.data)
        self.CurrentContext.socket.send(msg)
        print("[Client] Packet sent: " + str(self.CurrentContext.data))
        sleep(self.CurrentContext.sleep_time)#for debugging

        #transition to syn sent
        print("[Client] Transitioning to syn sent state...\n")
        self.CurrentContext.setState("SYN_SENT")
        return True

    def trigger(self):
        try:
            print("[Client] Current state = " + self.CurrentContext.state + "\n")
            #attempt to close socket
            self.CurrentContext.socket.close()
            return True
        except:  # no current connection
            return False

class Syn_sent(State, Transition):
    def __init__(self, Context):
        State.__init__(self, Context)

    def rst(self):
        print("[Client] resetting...")
        print("[Client] Transitioning to closed state...")
        #generate and send packet with rst flag
        self.CurrentContext.data["flg"] = "RST"
        msg = pickle.dumps(self.CurrentContext.data)
        self.CurrentContext.socket.send(msg)
        #delay closing the connection to give the server a chance to receive the packet
        sleep(self.CurrentContext.sleep_time + 3)
        self.CurrentContext.setState("CLOSED")
        return True

    def timeout(self):
        print("[Client] Connection timed out...")
        #generate and send packet with rst flag
        self.CurrentContext.data["flg"] = "RST"
        msg = pickle.dumps(self.CurrentContext.data)
        self.CurrentContext.socket.send(msg)
        #delay closing the connection to give the server a chance to receive the packet
        sleep(self.CurrentContext.sleep_time + 3)
        print("[Client] Transitioning to closed state...")
        self.CurrentContext.setState("CLOSED")
        return True

    def syn_ack(self):
        #generate and send ack to server
        print("[Client] acknowledging...")
        self.CurrentContext.data["flg"] = "ACK"
        #increment ack sequence (sequence number expected in next packet from server)
        self.CurrentContext.data["ackSeq"] += 1
        msg = pickle.dumps(self.CurrentContext.data)
        self.CurrentContext.socket.send(msg)
        print("[Client] Packet sent: " + str(self.CurrentContext.data))
        sleep(self.CurrentContext.sleep_time)
        #transition to established
        print("[Client] Transitioning to established state...\n")
        self.CurrentContext.setState("ESTABLISHED")
        return True

    def trigger(self):
        print("[Client] Current state = " + self.CurrentContext.state + "\n")
        counter = time.perf_counter() #current cpu time
        timeoutAt = 5 #time before timing out

        #if it takes more than specified amout of time then time out
        while True:
            timer = time.perf_counter()
            if timer < counter + timeoutAt:
                msg = self.CurrentContext.socket.recv(1024)
                #packet de serialise packet
                data = pickle.loads(msg)
                print("[Client] Packet received: " + str(data))
                sleep(self.CurrentContext.sleep_time)
                #make sure the sequence number rec1ieved is whats expected
                if data["seq"] == self.CurrentContext.data["ackSeq"] and data["flg"] == "SYN+ACK":
                    #set sequence number to the number being expected by the server
                    self.CurrentContext.data["seq"] = data["ackSeq"]
                    return self.CurrentContext.syn_ack()
                else:
                    print("invalid cmd")
                    return False
            else:
                return self.CurrentContext.timeout()

class Established(State, Transition):
    def __init__(self, Context):
        State.__init__(self, Context)

    def close(self):
        # send fin to server
        print("[Client] Sending fin request...")
        self.CurrentContext.data["flg"] = "FIN"
        self.CurrentContext.data["ackSeq"] += 1
        msg = pickle.dumps(self.CurrentContext.data)
        self.CurrentContext.socket.send(msg)
        print("[Client] Packet sent: " + str(self.CurrentContext.data))
        sleep(self.CurrentContext.sleep_time)
        # transition to fin wait 1
        print ("[Client] Transitioning to fin wait 1...\n")
        self.CurrentContext.setState("FIN_WAIT_1")
        return True

    def trigger(self):
        print("[Client] Connection established...")
        print("[Client] Current state = " + self.CurrentContext.state + "\n")
        return self.CurrentContext.close()

class Fin_wait_1(State, Transition):
    def __init__(self, Context):
        State.__init__(self, Context)

    def ack(self):
        #transition to fin wait 2
        print("[Client] Transitioning to fin wait 2 state...\n")
        self.CurrentContext.setState("FIN_WAIT_2")
        return True

    def trigger(self):
        print("[Client] Current state = " + self.CurrentContext.state + "\n")
        msg = self.CurrentContext.socket.recv(1024)
        data = pickle.loads(msg)
        print("[Client] Packet received: " + str(data))
        sleep(self.CurrentContext.sleep_time)
        if data["seq"] == self.CurrentContext.data["ackSeq"] and data["flg"] == "ACK":
            self.CurrentContext.data["seq"] = data["ackSeq"]
            return self.CurrentContext.ack()
        else:
            print("invalid cmd")
            return False
    
class Fin_wait_2(State, Transition):
    def __init__(self, Context):
        State.__init__(self, Context)

    def fin(self):
        #send ack to server
        print("[Client] Sending final acknowledgement...")
        self.CurrentContext.data["flg"] = "ACK"
        self.CurrentContext.data["ackSeq"] += 1
        msg = pickle.dumps(self.CurrentContext.data)
        self.CurrentContext.socket.send(msg)
        print("[Client] Packet sent: " + str(self.CurrentContext.data))
        sleep(self.CurrentContext.sleep_time)
        print("[Client] Transitioning to timed wait state...\n")
        #transition to timed wait
        self.CurrentContext.setState("TIMED_WAIT")
        return True

    def trigger(self):
        print("[Client] Current state = " + self.CurrentContext.state + "\n")
        msg = self.CurrentContext.socket.recv(1024)
        data = pickle.loads(msg)
        print("[Client] Packet received: " + str(data))
        sleep(self.CurrentContext.sleep_time)
        if data["seq"] == self.CurrentContext.data["ackSeq"] and data["flg"] == "FIN":
            self.CurrentContext.data["seq"] = data["ackSeq"]
            return self.CurrentContext.fin()
        else:
            print("invalid cmd")
            return False

class Timed_wait(State, Transition):
    def __init__(self, Context):
        State.__init__(self, Context)

    def timeout(self):
        #transition to closed
        print("[Client] Transitioning to closed state...\n")
        self.CurrentContext.setState("CLOSED")
        return True

    def trigger(self):
        print("[Client] Current state = " + self.CurrentContext.state + "\n")
        print("[Client] Timing out...")

        counter = time.perf_counter()  # current cpu time

        timeoutAt = 5  # time before timing out
        # if it takes more than specified amount of time then time out
        while True:
            timer = time.perf_counter()
            if timer < counter + timeoutAt:
                return self.CurrentContext.timeout()


class TCP_Client(StateContext, Transition):
    def __init__(self):
        self.sleep_time = 2 #places pauses in script for demo purposes
        self.host = "127.0.0.1"
        self.port = 5000
        self.socket = None
        self.seq = 0 #initial sequence number
        self.ackSeq = 0 #initial ack number
        self.data = {"seq": self.seq, "ackSeq": self.ackSeq, "flg": ""} #dictionary to hold packet data
        self.availableStates["CLOSED"] = Closed(self)
        self.availableStates["SYN_SENT"] = Syn_sent(self)
        self.availableStates["ESTABLISHED"] = Established(self)
        self.availableStates["FIN_WAIT_1"] = Fin_wait_1(self)
        self.availableStates["FIN_WAIT_2"] = Fin_wait_2(self)
        self.availableStates["TIMED_WAIT"] = Timed_wait(self)
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

    def make_connection(self):
        '''initiates an outbound connection'''
        self.socket = socket()
        try:
            self.socket.connect((self.host, self.port))
            self.connection_address = self.host
        except Exception as err:
            print(err)
            exit()

    def encrypt(self):
        return True
    def decrypt(self):
        return True


if __name__ == '__main__':
    activeClient = TCP_Client()
    activeClient.active_open()
    var = input("...")