from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.hashes import Hash, SHA512
from typing import List
import io, time, random
import core.constants as constants
import core.utils as utils

pad = padding.PSS(padding.MGF1(SHA512()), padding.PSS.MAX_LENGTH)
algorithm = SHA512()

class Cell:
    cell_type = b'\x00'
    def to_cell(self) -> bytes: return b''

class Transaction(Cell):
    cell_type = b'\x02'
    type: int
    source: bytes
    destination: bytes
    amount: int
    fee: int
    nonce: int
    ctime: int
    data: bytes
    signature: bytes
    def __init__(self, source: bytes, destination: bytes, amount: int, fee: int, ctime: int = None, data: bytes = bytes(), type: int = 0, signature = bytes(), nonce: int = random.randint(0, 2**32-1)) -> None:
        self.type = type
        self.source = source if source else (b'\x00'*(constants.bits//8))
        self.destination = destination if destination else (b'\x00'*(constants.bits//8))
        self.amount = amount
        self.fee = fee
        self.nonce = nonce
        self.ctime = ctime if ctime else int(time.time()*1000)
        self.data = data
        self.signature = signature
    def serialize_without_sign(self) -> bytes:
        return self.type.to_bytes(1, "big") + self.source + self.destination + self.amount.to_bytes(8, "big") + self.fee.to_bytes(8, "big") + self.nonce.to_bytes(4, "big") + self.ctime.to_bytes(8, "big") + len(self.data).to_bytes(2, "big") + self.data
    def hash(self) -> bytes:
        h = Hash(SHA512())
        h.update(self.serialize_without_sign())
        return h.finalize()
    def sign(self, private_key: rsa.RSAPrivateKey):
        self.signature = private_key.sign(self.hash(), pad, algorithm)
    def to_cell(self) -> bytes:
        return (self.signature if self.signature else (b'\x00'*(constants.bits//8))) + self.serialize_without_sign()

class Block(Cell):
    cell_type = b'\x04'
    id: int
    previous_block: bytes
    nonce: int
    ctime: int
    transactions: List[Transaction]
    def __init__(self, id: int, previous_block: bytes, transactions: List[Transaction], nonce = 0, ctime = None):
        self.id = id
        self.previous_block = previous_block
        self.transactions = transactions
        self.nonce = nonce
        self.ctime = ctime if ctime else int(time.time()*1000)
    def to_cell(self) -> bytes:
        txs = bytes()
        for tx in self.transactions:
            b = tx.to_cell()
            txs += len(b).to_bytes(4, "big") + b
        return self.id.to_bytes(16, "big", signed=True) + self.previous_block + self.nonce.to_bytes(16, "big") + self.ctime.to_bytes(8, "big") + len(self.transactions).to_bytes(4, "big") + txs
    def hash(self) -> bytes:
        h = Hash(SHA512())
        h.update(self.to_cell())
        return h.finalize()
    def get_difficult(self) -> int:
        return utils.zeros_count(int.from_bytes(self.hash(), "little"))

def deserialize_transaction(b: bytes):
    stream = io.BytesIO(b)
    signature = stream.read(constants.bits//8)
    type = int.from_bytes(stream.read(1), "big")
    source = stream.read(constants.bits//8)
    destination = stream.read(constants.bits//8)
    amount = int.from_bytes(stream.read(8), "big")
    fee = int.from_bytes(stream.read(8), "big")
    nonce = int.from_bytes(stream.read(4), "big")
    ctime = int.from_bytes(stream.read(8), "big")
    data = stream.read(int.from_bytes(stream.read(2), "big"))
    return Transaction(source, destination, amount, fee, ctime, data, type, signature, nonce)

def deserialize_block(b: bytes):
    stream = io.BytesIO(b)
    id = int.from_bytes(stream.read(16), "big")
    previous_block = stream.read(64)
    nonce = int.from_bytes(stream.read(16), "big")
    ctime = int.from_bytes(stream.read(8), "big")
    transactions = []
    for i in range(int.from_bytes(stream.read(4), "big")):
        l = int.from_bytes(stream.read(4), "big")
        tx = stream.read( l )
        transactions.append(deserialize_transaction(tx))
    return Block(id, previous_block, transactions, nonce, ctime)

def verify_transaction(tx: Transaction):
    try:
        utils.deserialize_public_key(tx.source).verify(tx.signature, tx.hash(), pad, algorithm)
        return True
    except:
        return False