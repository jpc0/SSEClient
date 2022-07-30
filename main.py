import ssl
from dataclasses import dataclass
import time
import socket
import re


@dataclass(slots=True)
class Event:
    data: str = ''
    event: str = 'message'
    id: str | None = None 
    retry: int | None = None


def parse_chunks(data: bytes) -> list[str]:
    split_data = data.split(str.encode("\r\n"))
    messages = []
    for i in range(len(split_data)):
        if i % 2 == 0:
            continue
        messages.append(split_data[i].decode())
    return messages


def decode_message(message: str) -> Event:
    sse_line_pattern = re.compile('(?P<name>[^:]*):?( ?(?P<value>.*))?')
    msg = Event()
    for line in message.splitlines():
        m = sse_line_pattern.match(line)
        if m is None:
            continue

        name = m.group('name')
        if name == '':
            # line began with a ":", so is a comment.  Ignore
            continue
        value = m.group('value')

        if name == 'data':
            # If we already have some data, then join to it with a newline.
            # Else this is it.
            if msg.data:
                msg.data = '%s\n%s' % (msg.data, value)
            else:
                msg.data = value
        elif name == 'event':
            msg.event = value
        elif name == 'id':
            msg.id = value
        elif name == 'retry':
            msg.retry = int(value)
    return msg


def open_encryped(hostname, port, path):
    BUFSIZE = 8192
    context = ssl.create_default_context()
    with socket.create_connection((hostname, port)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            ssock.send(str.encode(f"GET {path} HTTP/1.1\n\n"))
            ssock.setblocking(False)
            running = True
            data: bytes = b''
            first_iter = True
            messages: list[Event] = []

            while running:
                try:
                    while True:
                        data += ssock.recv(BUFSIZE)
                        if len(data) == 0:
                            running = False
                            break
                        if first_iter:
                            first_iter = False
                            first_message = data.split(str.encode("\r\n\r\n"))
                            if len(first_message) > 1:
                                data = first_message[1]
                        messages = list(map(decode_message, parse_chunks(data)))
                        yield messages
                        data = b''
                        messages = []
                except BlockingIOError:
                    yield None


def open_unencrypted(hostname, port, path):
    BUFSIZE = 8192
    with socket.create_connection((hostname, port)) as s:
        s.send(str.encode(f"GET {path} HTTP/1.1\n\n"))
        s.setblocking(False)
        running = True
        data: bytes = b''
        first_iter = True
        messages: list[Event] = []

        while running:
            try:
                while True:
                    data += s.recv(BUFSIZE)
                    if len(data) == 0:
                        running = False
                        break
                    if first_iter:
                        first_iter = False
                        first_message = data.split(str.encode("\r\n\r\n"))
                        if len(first_message) > 1:
                            data = first_message[1]
                    messages = list(map(decode_message, parse_chunks(data)))
                    yield messages
                    data = b''
                    messages = []
            except BlockingIOError:
                yield messages
    raise StopIteration()

