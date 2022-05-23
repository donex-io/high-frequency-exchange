from concurrent import futures
import grpc
from intercom_pb2 import PayResponse
import intercom_pb2_grpc

import os
import codecs

os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'

import invoices_pb2 as lninvoices
import invoices_pb2_grpc as lninvoices_grpc
import router_pb2 as lnrouter
import router_pb2_grpc as lnrouter_grpc
import lightning_pb2 as ln
import lightning_pb2_grpc as lngrpc

class Service(intercom_pb2_grpc.InvoiceServicer):
    
    def Pay(self, request, context):
        
        # CHECK INCOMING REQUEST
        print(request)
        requested_price = 900
        remote_payment_request = request.invoice_in

        # TODO CHECK PRICE
        actual_price = 1000
        if (requested_price > actual_price):
            context.abort(grpc.StatusCode.ABORTED, "Value too low")

        # PAY INCOMING REQUEST
        print("Pay incoming request...")
        request = lnrouter.SendPaymentRequest(
            payment_request=remote_payment_request,
            timeout_seconds= 5
        )
        print("gRPC request prepared.")
        for response in stub()[1].SendPaymentV2(request, metadata=[('macaroon', macaroon())]):
            print(response)
        print("Payment successful.")

        return PayResponse(accepted=True)

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
    server.add_secure_port("[::]:50051", creds)

    server.start()
    server.wait_for_termination()

def stub():
    # TODO Paths to cert should be in a config file
    cert = open(os.path.expanduser('~/bitcoin-regtest/.lnd1/tls.cert'), 'rb').read()
    creds = grpc.ssl_channel_credentials(cert)
    # TODO Port of LND should be in config file
    channel = grpc.secure_channel('localhost:10001', creds)
    stub = lngrpc.LightningStub(channel)
    router_stub = lnrouter_grpc.RouterStub(channel)
    return stub, router_stub

def macaroon():
    # TODO Path to macaroon should be in a config file
    with open(os.path.expanduser('~/bitcoin-regtest/.lnd1/data/chain/bitcoin/regtest/admin.macaroon'), 'rb') as f:
        macaroon_bytes = f.read()
    return codecs.encode(macaroon_bytes, 'hex')

if __name__ == "__main__":
    serve()