"""Minimal local Chromium DevTools client for document preview checks."""
import base64
import json
import os
import socket
import struct
from urllib.parse import urlparse


class CDP:
    def __init__(self, url):
        p=urlparse(url)
        self.sock=socket.create_connection((p.hostname,p.port),timeout=15)
        key=base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f'GET {p.path} HTTP/1.1\r\nHost: {p.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        header=b''
        while not header.endswith(b'\r\n\r\n'):
            header+=self.sock.recv(1)
        if b' 101 ' not in header: raise RuntimeError(header.decode())
        self.index=0

    def read(self,n):
        data=b''
        while len(data)<n:
            part=self.sock.recv(n-len(data))
            if not part: raise EOFError('DevTools connection closed')
            data+=part
        return data

    def send(self, payload):
        data=json.dumps(payload).encode()
        mask=os.urandom(4)
        n=len(data)
        header=bytes([0x81,0x80 | n]) if n<126 else bytes([0x81,0x80 | 126])+struct.pack('!H',n) if n<65536 else bytes([0x81,0x80 | 127])+struct.pack('!Q',n)
        self.sock.sendall(header+mask+bytes(b^mask[i%4] for i,b in enumerate(data)))

    def receive(self):
        fragments=b''
        while True:
            a,b=self.read(2)
            n=b&127
            if n==126: n=struct.unpack('!H',self.read(2))[0]
            if n==127: n=struct.unpack('!Q',self.read(8))[0]
            mask=self.read(4) if b&128 else None
            data=self.read(n)
            if mask: data=bytes(v^mask[i%4] for i,v in enumerate(data))
            if (a&15)==8: raise EOFError('WebSocket closed')
            if (a&15) not in (0,1): continue
            fragments+=data
            if a&128: return json.loads(fragments)

    def call(self,method,params=None):
        self.index+=1
        self.send({'id':self.index,'method':method,'params':params or {}})
        while True:
            message=self.receive()
            if message.get('id')==self.index:
                if 'error' in message: raise RuntimeError(message['error'])
                return message.get('result',{})

    def evaluate(self,expression):
        r=self.call('Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True})
        if 'exceptionDetails' in r: raise RuntimeError(r['exceptionDetails'])
        return r.get('result',{}).get('value')

    def close(self):
        self.sock.close()
