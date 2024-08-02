import datetime
import logging
import urllib.parse
import mimetypes
import json
import logging
import socket
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from http.server import BaseHTTPRequestHandler
from threading import Thread

from jinja2 import Environment, FileSystemLoader

from datetime import datetime

BASE_DIR = Path()

BUFFER_SIZE = 1024
HTTP_PORT = 3000
HTTP_HOST = '0.0.0.0'
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000

jinja = Environment(loader=FileSystemLoader('templates'))


class MyFramework(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlparse(self.path)

        match route.path:
            case '/':
                self.send_html('index.html')
            case '/message':
                self.send_html('templates/message.html')
            case _:
                file = BASE_DIR.joinpath(route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html('error.html')

    def do_POST(self):
        size = self.headers.get('Content-Length')
        data = self.rfile.read(int(size))
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))
        client_socket.close()

        self.send_response(302)
        self.send_header("Location", "/message")
        self.end_headers()

    def send_html(self, filename, status_code=200):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

        with open(filename, 'rb') as f:
            self.wfile.write(f.read())

    def send_static(self, filename, status_code=200):
        self.send_response(200)
        mimetype, *_ = mimetypes.guess_type(filename)

        if mimetype:
            self.send_header('Content-Type', mimetype)
        else:
            self.send_header("Content-type", mimetype)

        self.end_headers()

        with open(filename, "rb") as f:
            self.wfile.write(f.read())

    def render_template(self, filename, status_code=200):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        with open('storage/db.json', "r", encoding='utf-8') as file:
            data = json.load(file)

        template = jinja.get_template(filename)
        message = "Hello World!"
        html = template.render(blogs=data, message=message)
        self.wfile.write(html.encode())


def save_data_from_form(data):
    parse_data = urllib.parse.unquote_plus(data.decode())
    try:
        parse_dict = {key: value for key, value in [el.split('=') for el in parse_data.split('&')]}
        now_time = str(datetime.now())

        ### нагуглив, як додати до json новий допис =)
        try:
            with open('storage/data.json', 'r', encoding='utf-8') as file:
                entry_data = json.load(file)
        except FileNotFoundError:
            entry_data = {}

        entry_data[now_time] = parse_dict
        ###

        with open('storage/data.json', 'w', encoding='utf-8') as file:
            json.dump(entry_data, file, ensure_ascii=False, indent=4)

    except ValueError as err:
        logging.error(err)
    except OSError as err:
        logging.error(err)


def run_socket_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    logging.info("Starting socket server")
    try:
        while True:
            msg, address = server_socket.recvfrom(BUFFER_SIZE)
            logging.info(f"Socket received {address}: {msg}")
            save_data_from_form(msg)
    except KeyboardInterrupt:
        pass
    finally:
        server_socket.close()


def run_http_server(host, port):
    address = (host, port)
    http_server = HTTPServer(address, MyFramework)  # Instantiate MyFramework
    logging.info('Starting http server')

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http_server.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(threadName)s %(message)s')

    server = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    server.start()

    server_socket = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    server_socket.start()
