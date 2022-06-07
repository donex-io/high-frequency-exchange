from concurrent import futures
import grpc
from intercom_pb2 import PayResponse
import intercom_pb2_grpc

import os
import codecs

os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'

import inspect
import sys
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir) 
sys.path.insert(0, parentdir + '/app') 
import app

class Service(intercom_pb2_grpc.InvoiceServicer):
    
    def Pay(self, request, context):
        remote_payment_request = request.invoice_in
        print("Incoming request...")
        if app.check_before_payment(remote_payment_request):
            app.pay_payment_request(remote_payment_request)
            app.update_agreed_price_server(remote_payment_request)
            return PayResponse(accepted=True)
        else:
            return PayResponse(accepted=False)
            #context.abort(grpc.StatusCode.ABORTED, "Channel partner asks for too much!")


def serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )
    intercom_pb2_grpc.add_InvoiceServicer_to_server(
        Service(), server
    )

    with open("server.key", "rb") as fp:
        server_key = fp.read()
    with open("server.pem", "rb") as fp:
        server_cert = fp.read()
    with open("ca.pem", "rb") as fp:
        ca_cert = fp.read()
    creds = grpc.ssl_server_credentials(
        [(server_key, server_cert)],
        root_certificates=ca_cert,
        require_client_auth=True,
    )
    port = app.get_hfx_config('port_server')
    server.add_secure_port(f"[::]:{port}", creds)

    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()