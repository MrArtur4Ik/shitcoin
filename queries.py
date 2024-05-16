from core.blockchain import Block, deserialize_block, Transaction
import os
import core.constants as constants
import core.utils as utils

def get_wallet_balance(address: bytes):
    blocks = sorted([int(s) for s in os.listdir("blocks")])
    balance = 0
    for id in blocks:
        with open("blocks/" + str(id), "rb") as file:
            block = deserialize_block(file.read())
            validated = block.transactions[0].destination == address
            for tx in block.transactions:
                if validated: balance += tx.fee #Add fee if wallet is validator of this block
                if tx.destination == address: #Receive
                    balance += tx.amount
                if tx.source == address: #Send
                    balance -= tx.amount+tx.fee
    return balance

def get_wallet_balance_and_transactions(address: bytes):
    blocks = sorted([int(s) for s in os.listdir("blocks")])
    balance = 0
    transactions = 0
    for id in blocks:
        with open("blocks/" + str(id), "rb") as file:
            block = deserialize_block(file.read())
            validated = block.transactions[0].destination == address
            for tx in block.transactions:
                if validated: balance += tx.fee #Add fee if wallet is validator of this block
                if tx.destination == address: #Receive
                    balance += tx.amount
                if tx.source == address: #Send
                    balance -= tx.amount+tx.fee
                    transactions += 1
    return balance, transactions

def transaction_exists(transaction: Transaction):
    blocks = sorted([int(s) for s in os.listdir("blocks")])
    b = transaction.to_cell()
    for id in blocks:
        with open("blocks/" + str(id), "rb") as file:
            block = deserialize_block(file.read())
            for tx in block.transactions:
                if tx.to_cell() == b: return True
    return False


def get_block(id: int):
    with open("blocks/" + str(id), "rb") as file:
        return deserialize_block(file.read())

def get_last_block_id():
    try:
        return sorted([int(s) for s in os.listdir("blocks")])[-1]
    except:
        return -1

def calculate_difficult(last_block: int = None):
    if last_block == None: last_block = get_last_block_id()
    if last_block < 1: return constants.start_difficult
    blocks_count = 100
    checking_blocks = range(max(last_block-blocks_count+1, 0), last_block+1)
    average_time, average_difficult = None, None
    blocks = [get_block(id) for id in checking_blocks]
    for i, block in enumerate(blocks):
        block_difficult = utils.zeros_count(int.from_bytes(block.hash(), "little"))
        if average_difficult == None: average_difficult = block_difficult
        else: average_difficult = (average_difficult + block_difficult) / 2
        if average_time == None:
            average_time = (blocks[i+1].ctime-block.ctime)
        else:
            if block.id < last_block:
                average_time = (average_time+(blocks[i+1].ctime-block.ctime))/2
    #Average time and difficult is between last 'blocks_count' blocks.
    #(TimeBeforeBlocks/AverageTime)**SomeNumber*SomeNumber*LastBlockDifficult
    #return round((constants.time_between_blocks/average_time)**0.05*utils.zeros_count(int.from_bytes(blocks[-1].hash(), "little")))
    try:
        a = constants.time_between_blocks/average_time
    except ZeroDivisionError:
        a = 1.0
    return int(round((a**0.05)*0.96*average_difficult))