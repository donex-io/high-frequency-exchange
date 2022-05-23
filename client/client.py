import grpc
from intercom_pb2 import PayRequest
from intercom_pb2_grpc import InvoiceStub

import os
import codecs

import invoices_pb2 as lninvoices
import invoices_pb2_grpc as lninvoices_grpc
import router_pb2 as lnrouter
import router_pb2_grpc as lnrouter_grpc
import lightning_pb2 as ln
import lightning_pb2_grpc as lngrpc

host = os.getenv("APP_HOST", "localhost")
os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'

import time
def start():
    while True:
        time.sleep(1)
        intercomStub = stub()
        my_pubkey = intercomStub[0].GetInfo(ln.GetInfoRequest(), metadata=[('macaroon', macaroon())]).identity_pubkey
        invoice = ln.Invoice(
            value=100,
            payment_addr=bytes.fromhex(my_pubkey)
        )
        own_payment_request = intercomStub[0].AddInvoice(invoice, metadata=[('macaroon', macaroon())]).payment_request

        host = os.getenv("CLIENT_HOST", "localhost")
        with open("client.key", "rb") as fp:
            client_key = fp.read()
        with open("client.pem", "rb") as fp:
            client_cert = fp.read()
        with open("ca.pem", "rb") as fp:
            ca_cert = fp.read()
        creds = grpc.ssl_channel_credentials(ca_cert, client_key, client_cert)
        gRPCChannel = grpc.secure_channel(
            f"{host}:50051", creds
        )

        gRPCClient = InvoiceStub(gRPCChannel)
        gRPCRequest = PayRequest(invoice_in=own_payment_request.encode('UTF-8'))
        gRPCResponse = gRPCClient.Pay(gRPCRequest)
        print(gRPCResponse)

def stub():
    # TODO Paths to cert should be in a config file
    cert = open(os.path.expanduser('~/bitcoin-regtest/.lnd2/tls.cert'), 'rb').read()
    creds = grpc.ssl_channel_credentials(cert)
    # TODO Port of LND should be in config file
    channel = grpc.secure_channel('localhost:10002', creds)
    stub = lngrpc.LightningStub(channel)
    router_stub = lnrouter_grpc.RouterStub(channel)
    return stub, router_stub

def macaroon():
    # TODO Path to macaroon should be in a config file
    with open(os.path.expanduser('~/bitcoin-regtest/.lnd2/data/chain/bitcoin/regtest/admin.macaroon'), 'rb') as f:
        macaroon_bytes = f.read()
    return codecs.encode(macaroon_bytes, 'hex')

if __name__ == "__main__":
    start()