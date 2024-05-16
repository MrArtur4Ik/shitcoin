from cryptography.hazmat.primitives.asymmetric import rsa
import base64, io
import core.utils as utils
import core.constants as constants
from decimal import Decimal as D

def serialize_public_key(public_key: rsa.RSAPublicKey):
    return public_key.public_numbers().n.to_bytes(constants.bits//8, "little")

def serialize_private_key(private_key: rsa.RSAPrivateKey):
    return serialize_public_key(private_key.public_key()) + \
        private_key.private_numbers().d.to_bytes(constants.bits//8, "little") + \
        private_key.private_numbers().p.to_bytes(constants.bits//16, "little") + \
        private_key.private_numbers().q.to_bytes(constants.bits//16, "little")

def deserialize_public_key(b: bytes):
    return rsa.RSAPublicNumbers(65537, int.from_bytes(b, "little")).public_key()

def deserialize_private_key(b: bytes):
    stream = io.BytesIO(b)
    n = int.from_bytes(stream.read(constants.bits//8), "little")
    d = int.from_bytes(stream.read(constants.bits//8), "little")
    p = int.from_bytes(stream.read(constants.bits//16), "little")
    q = int.from_bytes(stream.read(constants.bits//16), "little")
    return rsa.RSAPrivateNumbers(p, q, d, rsa.rsa_crt_dmp1(d, p), rsa.rsa_crt_dmq1(d, q), rsa.rsa_crt_iqmp(p, q), rsa.RSAPublicNumbers(65537, n)).private_key()

def public_key_to_address(public_key: rsa.RSAPublicKey):
    return base64.urlsafe_b64encode(serialize_public_key(public_key)).decode()

def public_key_bytes_to_address(public_key: bytes):
    return public_key_to_address(deserialize_public_key(public_key))

def address_to_public_key_bytes(s: str):
    return base64.urlsafe_b64decode(s.encode())

def address_to_public_key(s: str):
    return deserialize_public_key(address_to_public_key_bytes(s))

def mining_gift_from_block_id(id: int):
    return (100//(id//constants.blocks_between_halfing+1))*(10**constants.digits)

def nano_to_decimal(i: int):
    return D(i)/D(10**(constants.digits))

def zeros_count(i: int):
    if i == 0: return -1
    zeros = 0
    while True:
        if (i >> zeros) & 0b1 == 1:
            return zeros
        zeros += 1