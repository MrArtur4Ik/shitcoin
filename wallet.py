from cryptography.hazmat.primitives.asymmetric import rsa
from decimal import Decimal as D
import os, time
import core.constants as constants
import core.utils as utils
import core.blockchain as blockchain
import queries, node

def show_account():
    balance, transactions = queries.get_wallet_balance_and_transactions(address)
    print("Your wallet address:", utils.public_key_to_address(private_key.public_key()))
    print(f"Balance: {utils.nano_to_decimal(balance)}")
    print(f"Transactions: {transactions}")

def main():
    global private_key, address
    if not os.path.exists("wallet/private_key"):
        os.mkdir("wallet")
        print("Creating your wallet...")
        private_key = rsa.generate_private_key(65537, constants.bits)
        with open("wallet/private_key", "wb") as file:
            file.write(utils.serialize_private_key(private_key))
    else:
        with open("wallet/private_key", "rb") as file:
            private_key = utils.deserialize_private_key(file.read())
    address = utils.serialize_public_key(private_key.public_key())
    print("Synchronizing blocks... Press Ctrl+C to skip.")
    if not os.path.exists("blocks"):
        os.mkdir("blocks")
    node.load_nodes_from_config()
    try:
        node.synchronize_blocks()
        print("Blocks synchronizing completed!")
    except KeyboardInterrupt:
        print("Block synchronizing was skipped. Wait for cancelling from another nodes.")
    show_account()
    while True:
        command = input("What do you want to do? (a - check account, t - transaction): ")
        if command.lower() == "a":
            node.synchronize_blocks()
            show_account()
        elif command.lower() == "t":
            address_str = input("Type address you want to transfer for: ")
            try:
                address_bytes = utils.address_to_public_key_bytes(address_str)
            except:
                print("Wrong address format.")
                continue
            try:
                amount = int(D(input("Type amount: "))*(10**constants.digits))
                fee = int(D(input("Type fee: "))*(10**constants.digits))
            except:
                print("Wrong format.")
            agree = input(f"Are you sure for this transaction: {utils.nano_to_decimal(amount)} with fee {utils.nano_to_decimal(fee)}? (y - agree): ")
            if agree == "y":
                tx = blockchain.Transaction(utils.serialize_public_key(private_key.public_key()), address_bytes, amount, fee, int(time.time()*1000))
                tx.sign(private_key)
                node.broadcast_cell(tx)
                print(f"Transaction {tx.hash().hex()} was sended. Wait for confirmation.")
        '''elif command.lower() == "s":
            try:
                node.synchronize_blocks()
                print("Blocks synchronizing completed!")
            except KeyboardInterrupt:
                print("Block synchronizing was skipped. Wait for cancelling from another nodes.")'''

if __name__ == "__main__":
    main()