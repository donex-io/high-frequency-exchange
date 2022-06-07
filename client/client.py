import grpc
from intercom_pb2 import PayRequest
from intercom_pb2_grpc import InvoiceStub

import os
import codecs

import inspect
import sys
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir) 
sys.path.insert(0, parentdir + '/app') 
import app


# GRPC CONNECTION TO SERVER

host = os.getenv("APP_HOST", "localhost")
os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'

def get_gRPCChannel ():
    host = os.getenv("CLIENT_HOST", "localhost")
    with open("client.key", "rb") as fp:
        client_key = fp.read()
    with open("client.pem", "rb") as fp:
        client_cert = fp.read()
    with open("ca.pem", "rb") as fp:
        ca_cert = fp.read()
    creds = grpc.ssl_channel_credentials(ca_cert, client_key, client_cert)
    port = app.get_hfx_config('port_client')
    gRPCChannel = grpc.secure_channel(
        f"{host}:{port}", creds
    )
    return gRPCChannel, host, port


# CHANNEL PARTNER CONNECTION

def check_grpc_server_on(channel, ip, port) -> bool:
    print('>> CLIENT: Checking connection to server...')
    try:
        TIMEOUT_SEC = 3
        print('>> CLIENT: Starting test')
        result = grpc.channel_ready_future(channel).result(timeout=TIMEOUT_SEC)
        print('>> CLIENT: Connection to server status:', result)
        return True
    except grpc.FutureTimeoutError:
        connection = ip + ':' + port
        print('>> CLIENT: WARNING! SERVER AT "', connection, '" IS NOT CONNECTED!')
        return False


# STARTING PROGRAMM

import time
def start():
    while True:
        if(app.pending_invoices()):
            print('>> CLIENT: Pending invoices! No update!')
        else:
            app.update_agreed_price_client()
            target_transfer_value, own_payment_request = app.get_payment_request()
            print('>> CLIENT: target_transfer_value: ', target_transfer_value)
            if own_payment_request:
                gRPCChannel, host, port = get_gRPCChannel()
                if check_grpc_server_on(gRPCChannel, host, port):
                    print('>> CLIENT: Connection to server ok')
                    gRPCClient = InvoiceStub(gRPCChannel)
                    gRPCRequest = PayRequest(invoice_in=own_payment_request.encode('UTF-8'))
                    print('>> CLIENT: Sending Pay request to server...')
                    gRPCResponse = gRPCClient.Pay(gRPCRequest)
                    print('>> CLIENT: gRPCResponse: ', gRPCResponse)
                else:
                    print('>> CLIENT: Server not available. Skip sending invoice.')
            else:
                print('>> CLIENT: Development not in your favour!')
        time.sleep(5)

if __name__ == "__main__":
    app.write_default_hfx_config(True)
    start()