#!/usr/bin/env python3

import sys, threading, time, os
from stem.control import Controller
from stem import SocketError, UnsatisfiableRequest
import stem.process
from stem.util import term
from flask import Flask
from flask import send_from_directory

import socks

# Stem for hidden services: source: https://stem.torproject.org/tutorials/over_the_river.html
# Serving static files with flask: source: https://www.techcoil.com/blog/serve-static-files-python-3-flask/
# Using flask with tor: source: https://gist.github.com/PaulSec/ec8f1689bfde3ce9a920

# Set tor_cmd: source: https://stackoverflow.com/a/25069013
WEB_PORT = 8080
CONTROL_PORT = 7001
SOCKS_PORT = 7000
HIDDEN_SERVICE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'hidden_service')
static_file_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'public')
TOR_CMD = "/Applications/TorBrowser.app/Tor/tor.real"

app = Flask(__name__)

def start_web_app():
    print ('Starting web app')
    app.run(port=WEB_PORT, threaded=True)

def print_bootstrap_lines(line):
    if "Bootstrapped " in line:
        print(term.format(line, term.Color.BLUE))

@app.route('/', methods=['GET'])
def serve_dir_directory_index():
    return send_from_directory(static_file_dir, 'index.html')


@app.route('/<path:path>', methods=['GET'])
def serve_file_in_dir(path):

    if not os.path.isfile(os.path.join(static_file_dir, path)):
        path = os.path.join(path, 'index.html')

    return send_from_directory(static_file_dir, path)


def main():
    print(term.format("Starting Tor:\n", term.Attr.BOLD))

    tor_process = stem.process.launch_tor_with_config(
      config = {
        'tor_cmd': TOR_CMD,
        'SocksPort': str(SOCKS_PORT),
        'ControlPort': str(CONTROL_PORT),
        'ExitNodes': '{ru}',
      },
      init_msg_handler = print_bootstrap_lines,
    )

    # Start the flask web app in a separate thread
    t = threading.Thread(target=start_web_app)
    t.daemon = True
    t.start()

    # Connect to the Tor control port
    try:
        c = Controller.from_port(port=CONTROL_PORT)
        c.authenticate()
    except SocketError:
        print ('Cannot connect to Tor control port')
        sys.exit()

    # Create an ephemeral hidden service
    try:
        print ('Creating hidden service')
        result = c.create_hidden_service(HIDDEN_SERVICE_DIR, 80, target_port=WEB_PORT)
        print (" * Created host: %s" % result.hostname)
        onion = result.hostname
    except UnsatisfiableRequest:
        print ('Cannot create ephemeral hidden service, Tor version is too old')
        sys.exit()
    except Exception, e:
        print e
        sys.exit()

    t.join()
if __name__ == '__main__':
main()
