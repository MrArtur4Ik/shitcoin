from socketserver import StreamRequestHandler
import core.blockchain as blockchain
import socket, queries, random, json, psutil, traceback, os

addresses = []

def send_packet(address: tuple, b: bytes, timeout: float = 2):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(address)
        sock.send(b)
        sock.close()
    except:
        pass

def load_nodes_from_config():
    global addresses
    with open("nodes.json", "rb") as file:
        config = json.loads(file.read())
        addresses = [(n["ip"], n["port"]) for n in config]

def broadcast_cell(cell: blockchain.Cell):
    a = psutil.net_if_addrs()
    own_addresses = [a[n][0].address for n in a]
    for address in addresses:
        #if address in own_addresses: continue
        b = cell.to_cell()
        try:
            send_packet(address, b'CRYPTO' + b'\x01' + cell.cell_type + len(b).to_bytes(4, "big") + b)
        except socket.timeout:
            pass

def get_last_block_id(address: tuple):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(address)
    sock.send(b'CRYPTO\x02\x00')
    last_block_id = int.from_bytes(sock.recv(16), "big", signed=True)
    sock.close()
    return last_block_id

def store_block(block: blockchain.Block):
    with open("blocks/" + str(block.id), "wb") as file:
        file.write(block.to_cell())

def synchronize_blocks():
    if len(addresses) <= 0: return
    highest_block = -1
    address = None
    for addr in addresses:
        try:
            lbi = get_last_block_id(addr)
            if lbi > highest_block:
                highest_block = lbi
                address = addr
        except:
            pass
    if not address: return
    keep = True
    while keep:
        own_last_block_id = queries.get_last_block_id()
        #address = random.choice(addresses)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(address)
            sock.send(b'CRYPTO\x02\x00')
            last_block_id = int.from_bytes(sock.recv(16), "big", signed=True)
            if own_last_block_id >= 0:
                sock.send(b'CRYPTO\x02\x01' + (own_last_block_id).to_bytes(16, "big", signed=True) + (own_last_block_id).to_bytes(16, "big", signed=True))
                try:
                    length = int.from_bytes(sock.recv(4), "big")
                    block = blockchain.deserialize_block(sock.recv(length))
                    assert sock.recv(4) == b'\x00'*4
                except:
                    continue
                if queries.get_block(own_last_block_id).hash() != block.hash():
                    start_block_id = 0
                else:
                    start_block_id = own_last_block_id+1
            else:
                start_block_id = 0
            if last_block_id == own_last_block_id: break
            end_block_id = last_block_id
            sock.send(b'CRYPTO\x02\x01' + start_block_id.to_bytes(16, "big", signed=True) + end_block_id.to_bytes(16, "big", signed=True))
            while True:
                length = int.from_bytes(sock.recv(4), "big")
                if length <= 0:
                    keep = False
                    break
                block = blockchain.deserialize_block(sock.recv(length))
                store_block(block)
        except socket.timeout:
            print(f"Node {address[0]}:{address[1]} doesn't response. Trying another...")
        except ConnectionRefusedError:
            pass
        
listening_connections = []

class NodeServerHandler(StreamRequestHandler):
    def handle(self):
        global listening_connections
        assert self.rfile.read(6) == b'CRYPTO'
        while True:
            command_type = self.rfile.read(1)
            if command_type == b'': break
            if command_type == b'\x01': #broadcast
                type = self.rfile.read(1)
                length = int.from_bytes(self.rfile.read(4), "big")
                if type == b'\x02':
                    cell = blockchain.deserialize_transaction(self.rfile.read(length))
                    self.cell_handler(cell)
                elif type == b'\x04':
                    cell = blockchain.deserialize_block(self.rfile.read(length))
                    self.cell_handler(cell)
            elif command_type == b'\x02': #get commands
                subcommand = self.rfile.read(1)
                if subcommand == b'\x00': #get last block id
                    self.wfile.write(queries.get_last_block_id().to_bytes(16, "big", signed=True))
                elif subcommand == b'\x01': #get block/blocks
                    start_block_id = int.from_bytes(self.rfile.read(16), "big", signed=True)
                    end_block_id = int.from_bytes(self.rfile.read(16), "big", signed=True)
                    for block_id in range(start_block_id, end_block_id+1):
                        try:
                            block = queries.get_block(block_id)
                        except:
                            continue
                        cell = block.to_cell()
                        self.wfile.write(len(cell).to_bytes(4, "big") + cell)
                    self.wfile.write((0).to_bytes(4, "big"))
            elif command_type == b'\x03': #listening to blocks and transactions
                if not self.connection in listening_connections: listening_connections.append(self.connection)
                try:
                    self.rfile.read(1)
                except:
                    pass
                listening_connections.remove(self.connection)
    def cell_handler(self, cell: blockchain.Cell): pass