import configparser
import os
import inspect
import sys


# HFX CONFIG FILE

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
settings_file_name = currentdir + '/settings.conf'

def write_default_hfx_config(init_with_current_price):
    config = configparser.ConfigParser()
    if os.path.exists(settings_file_name):
        config.read(settings_file_name) # SATs per absolute underlying price change
    config['HFX'] = {'last_agreed_price': '31404',
                'long_position': 'False',
                'factor': '100', 
                'max_diff_sats': '5', 
                'channel_partner' : '0123456789',
                'ip': 'localhost',
                'port_server': '50052',
                'port_client': '50051',
                'url': 'https://api.coinbase.com/v2/prices/btc-usd/spot'}
    with open(settings_file_name, 'w') as configfile:
        config.write(configfile)
    if init_with_current_price:
        set_hfx_config({'last_agreed_price': str(get_current_price())})
    return config

def get_full_config():
    config = configparser.ConfigParser()
    if os.path.exists(settings_file_name):
        config.read(settings_file_name)
    return config

def set_hfx_config(config_parameters):
    config = configparser.ConfigParser()
    if os.path.exists(settings_file_name):
        config.read(settings_file_name)
    for para in config_parameters:
        config.set('HFX', para, config_parameters[para])
    with open(settings_file_name, 'w') as configfile:
        config.write(configfile)
    return config

def get_hfx_config(parameter):
    config = get_full_config()
    return config['HFX'][parameter]


# PRICE AND TRANSFER VALUE

import requests
def get_current_price():
    url = get_hfx_config('url')
    price_float = float((requests.get(url)).json()['data']['amount'])
    return int(price_float)

def get_target_transfer_value():
    current_price = get_current_price()
    print('>> APP: Current price: ', current_price)
    last_price = int(get_hfx_config('last_agreed_price'))
    print('>> APP: Last agreed price: ', last_price)
    factor = int(get_hfx_config('factor'))
    long_position = (get_hfx_config('long_position') == "True")
    if long_position:
        target_transfer_value = (current_price - last_price) * factor
    else:
        target_transfer_value = (last_price - current_price) * factor
    return int(target_transfer_value), current_price

def get_hfx_parter_id():
    return str(get_hfx_config('channel_partner'))

def diff_calc_price_cur_price(calc_price, cur_price):
    print('>> APP: calc_price:', calc_price, 'cur_price:', cur_price)
    diff = cur_price - calc_price
    return diff

def check_before_payment(remote_pay_req):
    pay_req = lnd.get_decoded_pay_req(remote_pay_req)
    amount_to_pay = pay_req.num_satoshis
    long_position = (get_hfx_config('long_position') == "True")
    factor = int(get_hfx_config('factor'))
    last_agreed_price = int(get_hfx_config('last_agreed_price'))
    i_payed = True
    if long_position ^ i_payed:
        new_value_calculated = int(last_agreed_price + (amount_to_pay / factor))
    else:
        new_value_calculated = int(last_agreed_price - (amount_to_pay / factor))
    target_transfer_value, current_price = get_target_transfer_value()
    diff = diff_calc_price_cur_price(new_value_calculated, current_price)
    if (abs(diff) > 2):
        print('>> APP: WARNING: PRICE DIFFERNCE!! Checking transfer value...')
        acutual_amount_to_pay = -target_transfer_value
        max_diff_sats = int(get_hfx_config('max_diff_sats'))
        if (amount_to_pay - acutual_amount_to_pay > max_diff_sats):
            print('>> APP: ACTUAL AMOUNT:', acutual_amount_to_pay, 'BUT ASKED FOR: ', amount_to_pay)
            return False 
    return True


# UPDATING LAST AGREED PRICE

def update_agreed_price(amount_to_pay, i_payed):
    long_position = (get_hfx_config('long_position') == "True")
    factor = int(get_hfx_config('factor'))
    last_agreed_price = int(get_hfx_config('last_agreed_price'))
    if long_position ^ i_payed:
        new_value_calculated = int(last_agreed_price + (amount_to_pay / factor))
    else:
        new_value_calculated = int(last_agreed_price - (amount_to_pay / factor))
    print('>> APP: I am long: ', long_position, '. Updating agreed price by ', int(amount_to_pay/factor), ' from ', last_agreed_price, ' to ', new_value_calculated)
    current_price = get_current_price()
    diff = diff_calc_price_cur_price(new_value_calculated, current_price)
    set_hfx_config({'last_agreed_price': str(current_price)})

def update_agreed_price_server(remote_pay_req):
    print('>> APP: I payed.')
    pay_req = lnd.get_decoded_pay_req(remote_pay_req)
    difference = pay_req.num_satoshis
    update_agreed_price(difference, i_payed=True)

def update_agreed_price_client():
    print('>> APP: They payed.')
    pay_req = get_last_invoice()
    if pay_req:
        difference = pay_req.amt_paid_sat
        update_agreed_price(difference, i_payed=False)


# --------------------
# LND functionalities:
# --------------------

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir) 
sys.path.insert(0, parentdir + '/lnd') 
import lnd_helper as lnd


# CREATE OUTGOING PAYMENT REQUESTS

import json
def get_new_memo(input_dict):
    input_dict['channel_partner'] = get_hfx_parter_id()
    return json.dumps(input_dict)

def get_payment_request():
    target_transfer_value, current_price = get_target_transfer_value()
    print('>> APP: target_transfer_value ', target_transfer_value, ' SATs')
    payment_request = None
    if (target_transfer_value > 0):
        print('>> APP: Creating payment request')
        payment_request = lnd.get_payment_request(target_transfer_value, get_new_memo({'offered_price':str(current_price)}))
    return target_transfer_value, payment_request


# GETTING INVOICES FROM LND

def pending_invoices():
    return lnd.pending_invoices({'channel_partner': get_hfx_parter_id()})

def get_last_invoice():
    return lnd.get_last_invoice({'channel_partner': get_hfx_parter_id()})


# PAYING INCOMING INVOICE

def pay_payment_request(remote_payment_request):
    lnd.pay_payment_request(remote_payment_request)
    print( '>> APP: PAYMENT SUCCESSFUL')


# BASIC LND FUNCTIONS

def get_local_balance():
    return lnd.get_balance()[0]

def get_remote_balance():
    return lnd.get_balance()[1]
