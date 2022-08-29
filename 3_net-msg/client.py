"""a demo client for a simple client-server protocol"""

#
#   Client in Python:
#   - connects "reg" REQ socket to tcp://localhost:8000;
#   - connects "txt" REQ socket to tcp://localhost:8001;
#   - sends UUID to server through "reg",
#      expects token back;
#   - sends text to server through "txt" (with UUID and token),
#      expects ACK.
#

from typing import Tuple
from collections import namedtuple
import uuid
import zmq
from zmq.utils.win32 import allow_interrupt
from utils import count_calls

# pylint:disable=inconsistent-quotes
ClientProp = namedtuple('ClientProp',
    ['uuid', 'context', 'socket_reg', 'socket_txt'])
# pylint:enable=inconsistent-quotes

def gen_client_uuid() -> uuid.UUID:
    # Make a random UUID:
    uniq_id:uuid.UUID = uuid.uuid4()
    print(" Client id:", uniq_id)
    return uniq_id

def start_client():
    context: zmq.Context
    socket_reg: zmq.Socket
    socket_txt: zmq.Socket
    def start_zmq():
        nonlocal context
        nonlocal socket_reg
        nonlocal socket_txt
        # Prepare our context and sockets:
        context = zmq.Context()
        # + socket to register the client on the server
        print(" Connecting to the server for registration...")
        socket_reg = context.socket(zmq.REQ)
        socket_reg.connect("tcp://localhost:8000")
        print("  Connected to the server for registration.")
        # + socket to send text to the server
        print(" Connecting to the server for texting...")
        socket_txt = context.socket(zmq.REQ)
        socket_txt.connect("tcp://localhost:8001")
        print("  Connected to the server for texting.")
    print("Starting client...")
    uniq_id:uuid.UUID = gen_client_uuid()
    start_zmq()
    print("Client started.")
    return ClientProp(uniq_id, context, socket_reg, socket_txt)

@count_calls
def stop_client(client_prop:ClientProp):
    def stop_zmq():
        print(" ZMQ: cleanly exiting...")
        client_prop.socket_txt.close()
        client_prop.socket_reg.close()
        client_prop.context.term()
        print(" ZMQ: clean exit.")
    if stop_client.__calls__ == 0:
        print("Stopping client...")
        stop_zmq()
        print("Client stopped.")
    else:
        print("Stopping client: client already stopped.")

def run_client(client_prop:ClientProp, text:str):
    # Send the registration request:
    reg_req:str = client_prop.uuid.hex
    print(f"Sending registration request: \"{reg_req}\"...")
    client_prop.socket_reg.send_string(reg_req)
    # Get the reply to the registration request:
    reg_req_rep = client_prop.socket_reg.recv_string()
    print(f" Received reply to: \"{reg_req}\" << \"{reg_req_rep}\"")
    # Send the request with the text:
    token:str = reg_req_rep
    txt_req:Tuple[bytes,bytes,bytes] = tuple([str.encode(p)
        for p in [text, client_prop.uuid.hex, token]])
    print(f"Sending request with text: {txt_req}...")
    client_prop.socket_txt.send_multipart(txt_req)
    # Get the reply to the request with the text:
    txt_req_rep = client_prop.socket_txt.recv_string()
    print(f" Received reply to: {txt_req} << \"{txt_req_rep}\"")

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
            run_client(client_prop, "Hello, Server!")
    except KeyboardInterrupt:
        print("Interrupt received, stopping...")
    finally:
        # Clean up:
        stop_client(client_prop)

if __name__ == '__main__':  # pylint:disable=inconsistent-quotes
    main()
