import os, time, queries
from core.blockchain import Block, deserialize_block, Transaction, Cell
import core.utils as utils
import core.constants as constants
from cryptography.hazmat.primitives.asymmetric import rsa
import email.utils, json, node, threading
from socketserver import ThreadingTCPServer
from decimal import Decimal as D
import tools, threading

transactions = []
lock = threading.Lock()


class CryptoNodeServerHandler(node.NodeServerHandler):
    def cell_handler(self, cell: Cell):
        global transactions, last_block, private_key, address, mining_block, difficult
        if isinstance(cell, Transaction):
            if not tools.is_transaction_valid(cell): return
            if cell.hash() in [tx.hash() for tx in transactions]: return
            if queries.transaction_exists(cell): return
            node.broadcast_cell(cell)
            transactions.append(cell)
            print(f"{email.utils.formatdate(cell.ctime/1000)} [TRANSACTION] " + \
                    f"{utils.public_key_bytes_to_address(cell.source)} -> {utils.public_key_bytes_to_address(cell.destination)} " + \
                    f"Amount: {D(cell.amount)/D(10**constants.digits)}")
        elif isinstance(cell, Block):
            #if cell.id <= queries.get_last_block_id(): return
            #print(cell.id, cell.hash())
            if not tools.is_block_valid(cell):
                return
            with lock:
                if cell.id != queries.get_last_block_id()+1:
                    return
                node.broadcast_cell(cell)
                cell_bytes = cell.to_cell()
                for connection in node.listening_connections:
                    connection.send(len(cell_bytes).to_bytes(4, "big") + cell_bytes)
                node.store_block(cell)
                transactions = [Transaction(None, utils.serialize_public_key(private_key.public_key()), utils.mining_gift_from_block_id(cell.id+1), 0)]
                last_block = cell
                mining_block = Block(cell.id+1, cell.hash(), transactions)
                difficult = queries.calculate_difficult()
                mined_block_message(cell)
                print("Difficult for mining:", difficult)
                time.sleep(0.1)

def server_loop():
    global server
    print("Starting server...")
    server = ThreadingTCPServer(address, CryptoNodeServerHandler)
    with server:
        server.serve_forever()

def mined_block_message(block: Block):
    print(f"[{email.utils.formatdate(block.ctime/1000)} {block.ctime}] [BLOCK]\n{block.id} {block.hash().hex()}\n" + \
        f"[Nonce:{block.nonce}] [Miner:{utils.public_key_bytes_to_address(block.transactions[0].destination)}]\n [Transactions:{len(block.transactions)-1}]")

def main():
    global last_block, private_key, address, mining_block, transactions, difficult

    #Create/Import wallet

    if not os.path.exists("wallet/private_key"):
        os.mkdir("wallet")
        print("Creating your wallet...")
        private_key = rsa.generate_private_key(65537, constants.bits)
        with open("wallet/private_key", "wb") as file:
            file.write(utils.serialize_private_key(private_key))
    else:
        with open("wallet/private_key", "rb") as file:
            private_key = utils.deserialize_private_key(file.read())
    print("Your wallet address:", utils.public_key_to_address(private_key.public_key()))

    #Initialising ode server

    with open("config.json", "r") as file:
        config = json.loads(file.read())
        address = (config["ip"], config["port"])
    node.load_nodes_from_config()
    threading.Thread(target=server_loop).start()

    #Synchronizing blocks...

    print("Synchronizing blocks... Press Ctrl+C for immediately start node.")
    if not os.path.exists("blocks"):
        os.mkdir("blocks")
    try:
        node.synchronize_blocks()
        print("Blocks synchronizing completed!")
    except:
        print("Block synchronizing was skipped. Wait for cancelling from another nodes.")

    #Blocks

    own_last_block_id = queries.get_last_block_id()
    if own_last_block_id < 0:
        print("No blocks were created.")
        last_block = Block(-1, b'\x00'*64, [], 0)
    else:
        last_block = queries.get_block(own_last_block_id)
        print(f"Last block: {last_block.id} {last_block.hash().hex()}")
    
    print("Mining...")
    transactions = [Transaction(None, utils.serialize_public_key(private_key.public_key()), utils.mining_gift_from_block_id(last_block.id+1), 0)]
    mining_block = Block(last_block.id+1, last_block.hash(), transactions)
    difficult = queries.calculate_difficult()
    try:
        while True:
            print("Difficult for mining:", difficult)
            while True:
                with lock:
                    mining_block.ctime = int(time.time()*1000)
                    if utils.zeros_count(int.from_bytes(mining_block.hash(), "little")) >= difficult:
                        if tools.is_block_valid(mining_block):
                            node.broadcast_cell(mining_block)
                            mined_block_message(mining_block)
                            print("+ Mined", utils.nano_to_decimal(utils.mining_gift_from_block_id(mining_block.id)))
                            node.store_block(mining_block)
                            transactions = [Transaction(None, utils.serialize_public_key(private_key.public_key()), utils.mining_gift_from_block_id(last_block.id+1), 0)]
                            last_block = mining_block
                            mining_block = Block(mining_block.id+1, mining_block.hash(), transactions)
                            difficult = queries.calculate_difficult()
                            break
                    mining_block.nonce += 1
    except KeyboardInterrupt:
        server.shutdown()
    '''zeros = []
    while True:
        while time.time() - last_block_time < constants.time_before_blocks:
            block.nonce = nonce
            block.time = int(time.time())'''

if __name__ == "__main__":
    main()