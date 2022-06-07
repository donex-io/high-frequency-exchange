from threading import Lock
from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit
import requests

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

import os
import sys
import inspect
#url = 'https://api.coinbase.com/v2/prices/btc-usd/spot'
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir) 
sys.path.insert(0, parentdir + '/app') 
import app
""" import configparser
def update_app_config(config_parameters):
    app_settings_path = os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))) + '/app/settings.conf'
    config = configparser.ConfigParser()
    config.read(app_settings_path)
    for para in config_parameters:
        config.set('HFX', para, config_parameters[para])
    with open(app_settings_path, 'w') as configfile:
        config.write(configfile)
    return config """


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(3)
        count += 1
        price = ((requests.get(app.get_hfx_config('url'))).json())['data']['amount']
        socketio.emit('my_response',
                      {'data': 'Bitcoin current price (USD): ' + price, 'count': count}) 
        socketio.emit('node_info_response', {'data': {'local_balance': app.get_local_balance(), 'remote_balance' : app.get_remote_balance()}})


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@socketio.event
def my_event(message):
    emit('set_api_underlying_response', {'url': url})
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})

# Receive the test request from client and send back a test response
@socketio.on('test_message')
def handle_message(data):
    print('received message: ' + str(data))
    emit('test_response', {'data': 'Test response sent'})

# Broadcast a message to all clients
@socketio.on('broadcast_message')
def handle_broadcast(data):
    print('received: ' + str(data))
    emit('broadcast_response', {'data': 'Broadcast sent'}, broadcast=True)

# ROBIN
# Broadcast a message to all clients
@socketio.on('getNodeInfo_message')
def handle_broadcast(data):
    print('received: ' + str(data))
    if(str(data) != "Robin"):
        print('Wrong identification code!')
    emit('node_info_response', {'data': {'local_balance': app.get_local_balance(), 'remote_balance' : app.get_remote_balance()}})

#
@socketio.on('set_api_underlying_message')
def handle_broadcast(data):
    # HANDLE USER AUTHENTICATION
    print('received url: ' + str(data))
    url = data['url']
    app.set_hfx_config({'url': url})
    emit('set_api_underlying_response', {'url': url})


@socketio.event
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0')