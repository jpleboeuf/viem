"""a demo server for a simple client-server protocol"""

#
#   Server in Python:
#   - binds "reg" REP socket to tcp://*:8000;
#   - binds "txt" REP socket to tcp://*:8001;
#   - expects UUID from client through "reg",
#      replies with token;
#   - expects text from client through "txt" (with UUID and token),
#      replies with ACK if client recognized and registered, errors if not.
#

from typing import Tuple, Dict
from collections import namedtuple
import uuid
import zmq
from zmq.utils.win32 import allow_interrupt
from utils import count_calls

SOCKET_REG_ADDR:str = "tcp://*:8000"
SOCKET_TXT_ADDR:str = "tcp://*:8001"

# pylint:disable=inconsistent-quotes
ServerProp = namedtuple('ServerProp',
    ['uuid', 'context', 'socket_reg', 'socket_txt', 'poller'])
# pylint:enable=inconsistent-quotes

def gen_server_uuid() -> uuid.UUID:
    # Make a random UUID:
    uniq_id:uuid.UUID = uuid.uuid4()
    print(" Server id:", uniq_id)
    return uniq_id

def start_server():
    context: zmq.Context
    socket_reg: zmq.Socket
    socket_txt: zmq.Socket
    poller: zmq.Poller
    def start_zmq():
        nonlocal context
        nonlocal socket_reg
        nonlocal socket_txt
        nonlocal poller
        # Prepare our context and sockets:
        context = zmq.Context()
        # + socket to register the client on the server
        print(" Creating a socket",
            f"listening on {SOCKET_REG_ADDR} for registrations...")
        try:
            socket_reg = context.socket(zmq.REP)
            socket_reg.bind(SOCKET_REG_ADDR)
            print(f"  Listening for registrations on {SOCKET_REG_ADDR}.")
        except zmq.error.ZMQError:
            print(f"  Error: address {SOCKET_REG_ADDR} already in use!")
            print("Exiting.")
            context.term()
            exit(8)
        # + socket to send text to the server
        print(f" Creating a socket listening on {SOCKET_TXT_ADDR} for texts...")
        try:
            socket_txt = context.socket(zmq.REP)
            socket_txt.bind(SOCKET_TXT_ADDR)
            print(f"  Listening for texts on {SOCKET_TXT_ADDR}.")
        except zmq.error.ZMQError:
            print(f"  Error: address {SOCKET_TXT_ADDR} already in use!")
            print("Exiting.")
            context.term()
            exit(8)
        # Initialize poll set:
        poller = zmq.Poller()
        poller.register(socket_reg, zmq.POLLIN)
        poller.register(socket_txt, zmq.POLLIN)
    print("Starting server...")
    uniq_id:uuid.UUID = gen_server_uuid()
    start_zmq()
    print("Server started.")
    return ServerProp(uniq_id, context, socket_reg, socket_txt, poller)

@count_calls
def stop_server(server_prop:ServerProp):
    def stop_zmq():
        print(" ZMQ: cleanly exiting...")
        server_prop.socket_txt.close()
        server_prop.socket_reg.close()
        server_prop.context.term()
        print(" ZMQ: clean exit.")
    if stop_server.__calls__ == 0:
        print("Stopping server...")
        stop_zmq()
        print("Server stopped.")
    else:
        print("Stopping server: server already stopped.")

def run_server(server_prop:ServerProp, text_file:str):
    # Open text log file, line-buffered:
    txt_log_file = open(text_file, 'a', encoding='utf-8', buffering=1)  # pylint:disable=inconsistent-quotes
    client:Dict[uuid.UUID,str] = {}
    # Process messages from both sockets:
    while True:
        socks = dict(server_prop.poller.poll())
        if server_prop.socket_reg in socks:
            reg_req:str = server_prop.socket_reg.recv_string()
            if reg_req == "STOP":
                print("Received request to STOP, sending back STOP:ACK.")
                server_prop.socket_reg.send_string("STOP:ACK")
                break
            # Receive the registration request:
            print(f"Received registration request: \"{reg_req}\".")
            # Generate a token for this client:
            client_token:str = uuid.uuid4().hex
            client[uuid.UUID(reg_req)] = client_token
            # Set the reply to the registration request:
            reg_req_rep:str = client_token
            print(f" Sending reply to: \"{reg_req}\" >> \"{reg_req_rep}\"")
            server_prop.socket_reg.send_string(reg_req_rep)
        if server_prop.socket_txt in socks:
            # Receive the request with the text:
            txt_req:Tuple[bytes,bytes,bytes] = (
                server_prop.socket_txt.recv_multipart())
            print(f"Received request with text: \"{txt_req}\".")
            (client_txt, client_uuid_hex, client_token) = tuple(
                str(b, 'utf-8') for b in txt_req)  # pylint:disable=inconsistent-quotes
            txt_req_rep:str = ""
            if (client_uuid := uuid.UUID(client_uuid_hex)) not in client.keys():
                print(f" ERROR: Unknown client {client_uuid_hex}!")
                txt_req_rep = "ERR:unknown-client"
            else:
                if client[client_uuid] != client_token:
                    print(f" ERROR: Wrong token {client_token}",
                        f"sent by client {client_uuid_hex}",
                        "the token does not match the one in the server DB!")
                    txt_req_rep = "ERR:wrong-token"
                else:
                    print(" All good :)")
                    print(f" Storing \"{client_txt}\" for later use.")
                    txt_log_file.write(client_txt + "\n")
                    txt_req_rep = "ACK"
            print(f" Sending reply to: \"{txt_req}\" >> \"{txt_req_rep}\"")
            server_prop.socket_txt.send_string(txt_req_rep)

def main():
    server_prop:ServerProp
    def keyb_int():
        # See "Ctrl-C doesn't kill python on windows"
        #  <https://github.com/zeromq/pyzmq/issues/100>
        nonlocal server_prop
        stop_server(server_prop)
    try:
        with allow_interrupt(keyb_int):
            server_prop = start_server()
            run_server(server_prop, "messages.txt")
    except KeyboardInterrupt:
        print("Interrupt received, stopping...")
    finally:
        # Clean up:
        stop_server(server_prop)

if __name__ == '__main__':  # pylint:disable=inconsistent-quotes
    main()
