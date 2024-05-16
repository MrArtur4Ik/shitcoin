from core.blockchain import Block, Transaction, verify_transaction
import core.utils as utils
import time, queries

def is_block_valid(block: Block):
    if block.id < 0: return False
    current_timestamp = time.time()
    last_block_id = block.id-1
    if last_block_id >= 0:
        if time.time() < queries.get_block(last_block_id).ctime/1000: return False
    if not current_timestamp-10 < block.ctime/1000 < current_timestamp+10: return False
    difficult = queries.calculate_difficult(last_block_id)
    if block.get_difficult() < difficult:
        print(block.get_difficult(), difficult)
        print('invalid1')
        return False
    if last_block_id > 0:
        if not block.previous_block == queries.get_block(block.id-1).hash():
            print('invalid2')
            return False
    for id, transaction in enumerate(block.transactions):
        if not is_transaction_valid(transaction, id != 0, id != 0):
            print('invalid3')
            return False
    return True

def is_transaction_valid(tx: Transaction, check_sign: bool = True, check_fee: bool = True):
    if check_sign:
        if not verify_transaction(tx): return False
    if check_fee:
        if tx.fee == 0: return False
    return True