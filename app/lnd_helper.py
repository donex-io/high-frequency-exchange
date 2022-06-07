import os
import grpc
import codecs
import lightning_pb2 as ln
import lightning_pb2_grpc as lngrpc
import router_pb2 as lnrouter
import router_pb2_grpc as lnrouter_grpc


# LND CONFIG FILE

import configparser

import inspect
import sys
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
settings_file_name = currentdir + '/settings.conf'

def write_default_lnd_config():
    config = configparser.ConfigParser()
    if os.path.exists(settings_file_name):
        config.read(settings_file_name)
    with open(settings_file_name, 'w') as configfile:
            config['LND'] = {'lnd_dir': '~/bitcoin-regtest/.lnd1',
                'cert_path': '~/bitcoin-regtest/.lnd1/tls.cert',
                'macaroon_path': '~/bitcoin-regtest/.lnd1/data/chain/bitcoin/regtest/admin.macaroon',
                'ip': 'localhost',
                'port': '10001'}
            config.write(configfile)
    return config

write_default_lnd_config()

def get_config():
    config = configparser.ConfigParser()
    if os.path.exists(settings_file_name):
        config.read(settings_file_name)
    return config


# LND CONNECTION

TIMEOUT_SEC = 3
def check_grpc_server_on(channel, ip, port) -> bool:
    try:
        grpc.channel_ready_future(channel).result(timeout=TIMEOUT_SEC)
        return True
    except grpc.FutureTimeoutError:
        connection = ip + ':' + port
        print('>> LND: WARNING! LND AT "', connection, '" IS NOT CONNECTED!')
        return False


# STUB & MACAROON

def stub():
    config = get_config()
    if('LND' in config):
        cert_path = config['LND']['cert_path']
        ip = config['LND']['ip']
        port = config['LND']['port']
        cert = open(os.path.expanduser(cert_path), 'rb').read()
        creds = grpc.ssl_channel_credentials(cert)
        channel = grpc.secure_channel(ip+':'+port, creds)
        check_grpc_server_on(channel, ip, port)
        stub = lngrpc.LightningStub(channel)
        router_stub = lnrouter_grpc.RouterStub(channel)
        return stub, router_stub

def macaroon():
    config = get_config()
    with open(os.path.expanduser((config['LND']['macaroon_path'])), 'rb') as f:
        macaroon_bytes = f.read()
    return codecs.encode(macaroon_bytes, 'hex')


# BASICS

def get_local_pubkey():
    lnStub = stub()
    return lnStub[0].GetInfo(ln.GetInfoRequest(), metadata=[('macaroon', macaroon())]).identity_pubkey

def get_balance():
    lnStub = stub()
    channels = lnStub[0].ChannelBalance(ln.ChannelBalanceRequest(), metadata=[('macaroon', macaroon())]) 
    return channels.local_balance.sat, channels.remote_balance.sat


# OUTGOING PAYMENT REQUESTS

def get_payment_request(target_transfer_value, memo_for_payment):
    lnStub = stub()
    invoice = ln.Invoice(
        memo=str(memo_for_payment),
        value=int(target_transfer_value),
        expiry=10,
        payment_addr=bytes.fromhex(get_local_pubkey())
    )
    print('>> LND: Creating payment request...')
    pay_req = lnStub[0].AddInvoice(invoice, metadata=[('macaroon', macaroon())]).payment_request
    print('>> LND: Payment request successfuly created.')
    return pay_req

import json
def filter_invoices(invoices, memo_to_filter_json_string):
    filtered = []
    for invoice in invoices:
        for key in memo_to_filter_json_string:
            if key in invoice.memo:
                invoice_memo = json.loads(invoice.memo)
                if invoice_memo[key] == memo_to_filter_json_string[key]:
                    import time
                    expiry_time = int(invoice.creation_date) + int(invoice.expiry)
                    current_time = int(time.time()) 
                    if (current_time < expiry_time):
                        print('>> LND: expiry_time: ', expiry_time, ' current_time: ', current_time)
                        filtered.append(invoice)
    return filtered

def pending_invoices(memo_to_filter):
    lnStub = stub()
    request = ln.ListInvoiceRequest(
        pending_only=True,
        reversed=False
    )
    response = lnStub[0].ListInvoices(request, metadata=[('macaroon', macaroon())])
    filtered_invoices = filter_invoices(response.invoices, memo_to_filter)
    if len(filtered_invoices) > 0:
        from datetime import datetime
        print('>> LND: Pending invoices from ', datetime.utcfromtimestamp(filtered_invoices[0].creation_date).strftime('%Y-%m-%d %H:%M:%S'))
        return True
    else:
        return False

def get_last_invoice(memo_to_filter):
    lnStub = stub()
    request = ln.ListInvoiceRequest(
        reversed=True
    )
    response = lnStub[0].ListInvoices(request, metadata=[('macaroon', macaroon())])
    filtered_invoices = filter_invoices(response.invoices, memo_to_filter)
    number_of_invoices = len(filtered_invoices)
    if number_of_invoices > 0:
        return filtered_invoices[0]
    else:
        print('>> LND: Problem? No last invoice.')
        return {}


# INCOMING PAYMENT REQUESTS

def pay_payment_request(remote_payment_request):
    lnStub = stub()
    request = lnrouter.SendPaymentRequest(
        payment_request=remote_payment_request,
        timeout_seconds= 5
    )
    print('>> LND: Payment sending:')
    for response in stub()[1].SendPaymentV2(request, metadata=[('macaroon', macaroon())]):
        print(response)

def get_decoded_pay_req(pay_req_str):
    request = ln.PayReqString(
        pay_req=pay_req_str,
    )
    return stub()[0].DecodePayReq(request, metadata=[('macaroon', macaroon())])