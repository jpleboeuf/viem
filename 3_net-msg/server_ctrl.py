"""a demo control client for a simple client-server protocol"""

#
#   Client in Python:
#   - connects "reg/ctrl" REQ socket to tcp://localhost:8000
#   - sends "STOP" to server through "reg/ctrl",
#      expects nothing in return :'( ...
#      ... No, expecting STOP:ACK.
#

from collections import namedtuple
import zmq
from zmq.utils.win32 import allow_interrupt
from utils import count_calls

# pylint:disable=inconsistent-quotes
ClientProp = namedtuple('ClientProp',
    ['context', 'socket_reg'])
# pylint:enable=inconsistent-quotes

def start_client():
    context: zmq.Context
    socket_reg: zmq.Socket
    def start_zmq():
        nonlocal context
        nonlocal socket_reg
        # Prepare our context and sockets:
        context = zmq.Context()
        # + socket to smanage the server
        print(" Connecting to the server for management...")
        socket_reg = context.socket(zmq.REQ)
        socket_reg.connect("tcp://localhost:8000")
        print("  Connected to the server for management.")
    print("Starting client...")
    start_zmq()
    print("Client started.")
    return ClientProp(context, socket_reg)

@count_calls
def stop_client(client_prop:ClientProp):
    def stop_zmq():
        print(" ZMQ: cleanly exiting...")
        client_prop.socket_reg.close()
        client_prop.context.term()
        print(" ZMQ: clean exit.")
    if stop_client.__calls__ == 0:
        print("Stopping client...")
        stop_zmq()
        print("Client stopped.")
    else:
        print("Stopping client: client already stopped.")

def run_client(client_prop:ClientProp):
    # Send the registration request:
    stop_req:str = "STOP"
    print(f"Sending stop request: \"{stop_req}\"...")
    client_prop.socket_reg.send_string(stop_req)
    # Get the reply to the stop request:
    stop_req_rep = client_prop.socket_reg.recv_string()
    print(f" Received reply to: \"{stop_req}\" << \"{stop_req_rep}\"")

def main():
    client_prop:ClientProp
    def keyb_int():
        # See "Ctrl-C doesn't kill python on windows"
        #  <https://github.com/zeromq/pyzmq/issues/100>
        nonlocal client_prop
        stop_client(client_prop)
    try:
        with allow_interrupt(keyb_int):
            client_prop = start_client()
            run_client(client_prop)
    except KeyboardInterrupt:
        print("Interrupt received, stopping...")
    finally:
        # Clean up:
        stop_client(client_prop)

if __name__ == '__main__':  # pylint:disable=inconsistent-quotes
    main()
