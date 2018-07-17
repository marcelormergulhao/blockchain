import sys
import logging
import json

from threading import Lock
from collections import OrderedDict
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from base64 import b64encode, b64decode

from app.models.block import Block
from app.models.transaction import Transaction

# Log configuration
logging.basicConfig(format = "%(asctime)-15s %(message)s", stream=sys.stdout)
logger = logging.getLogger("blockchain_logger")
logger.setLevel(logging.DEBUG)

class Blockchain():
    def __init__(self):
        """
        Initialize blockchain storage and possibly populate
        """
        self.lock = Lock()
        self.t_lock = Lock()
        self.storage = []
        self.transaction_pool = []

    def empty(self):
        return len(self.storage) == 0

    def setup_new_chain(self, json_list):
        self.storage = list(json_list)
    
    def create_genesis_block(self, private_key, miner_id):
        logger.info("Creating genesis block")
        transaction = Transaction("Genesis Addr", "Genesis Block")
        genesis = Block("Genesis Block", 0, [transaction.get_signed_json(private_key)], miner_id)
        genesis.mine()
        self.storage = [genesis.get_json()]

    def check_transaction(self, miner_id):
        for block in self.storage:
            logger.info("Block {}".format(block))
            transactions = block["data"]
            for transaction in transactions:
                logger.info("Checking transaction {}".format(transaction))
                if transaction["addr_from"] == miner_id:
                    logger.error("User has already issued his vote")
                    return True
        # Also check for soon to be completed transactions
        for transaction in self.transaction_pool:
            if transaction["addr_from"] == miner_id:
                logger.error("User has vote on transaction pool")
        return False

    def remove_transactions_from_pool(self, block):
        """
        After receiveing a new block, check if the transactions were in the pool and remove them
        """
        logger.info("Current pool {}".format(self.transaction_pool))
        for transaction in block["data"]:
            if transaction in self.transaction_pool:
                self.transaction_pool.remove(transaction)
        logger.info("New pool {}".format(self.transaction_pool))
        return

    def validate_block(self, block, prevBlock):
        logger.info("Validate block")
        if prevBlock is not None:
            # Validate consistence with blockchain
            if block["prevHash"] == prevBlock["hash"]:
                logger.info("Block is consistent with blockchain")
                # Validate PoW
                if block["hash"][0:3] == "000":
                    logger.info("Block has PoW")
                    # Validate the block hash is from itself, create same block structure
                    transactions = []
                    for t in block["data"]:
                        new_t = OrderedDict({"addr_from": t["addr_from"]})
                        new_t["addr_to"] = t["addr_to"]
                        new_t["signature"] = t["signature"]
                        new_t["pubkey"] = t["pubkey"]
                        transactions.append(new_t)
                        
                    striped_block = Block(block["prevHash"], block["height"], transactions, block["miner"])
                    striped_block.block["nonce"] = block["nonce"]
                    striped_block.block["hash"] = ""
                    logger.info("Striped {}".format(striped_block.get_json()))
                    sha256 = SHA256.new()
                    sha256.update(json.dumps(striped_block.get_json()).encode())
                    hexdigest = sha256.hexdigest()
                    if hexdigest == block["hash"]:
                        logger.info("Block generates the hash provided")
                        for transaction in block["data"]:
                            if not self.validate_transaction(transaction):
                                return False
                        logger.info("Block has all transactions valid")
                        logger.info("Accept block")
                        return True
                    else:
                        logger.info("Invalid block hash")
        return False

    def create_and_add_block(self, miner_id):
        block = None
        if not self.empty():
            # Get last block
            prevBlock = self.storage[-1]
            # Use it to create new block with the current transactions in pool
            block = Block(prevBlock["hash"], prevBlock["height"] + 1, self.transaction_pool, miner_id)
            block.mine()
            logger.info("Block created: {}".format(block.get_json()))
            self.validate_and_add_block(block.get_json())
        return block

    def validate_transaction(self, transaction):
        t_sig = b64decode(transaction["signature"].encode())
        pubkey = b64decode(transaction["pubkey"].encode())
        verifier = PKCS1_v1_5.new(RSA.importKey(pubkey))
        digest = SHA256.new()
        t = Transaction(transaction["addr_from"], transaction["addr_to"])
        digest.update(str(t.get_json()).encode())
        verified = verifier.verify(digest,t_sig)
        if verified:
            return True
        else:
            logger.info("Signature is invalid")
        return False

    def add_transaction_to_pool(self, transaction):
        self.t_lock.acquire()
        self.transaction_pool.append(transaction)
        self.t_lock.release()
        return

    def validate_and_add_block(self, block):
        logger.info("Validate and add block")
        if len(self.storage) > 0:
            # logger.info("Block received: {}".format(block))
            self.lock.acquire()
            current_head = self.storage[-1]
            # Check if node has the same height as the current head and untie the conflict with the timestamp
            if current_head["height"] == block["height"]:
                logger.info("Validate conflicting block")
                prevBlock = self.storage[-2]
                if current_head["timestamp"] > block["timestamp"]:
                    if self.validate_block(block, prevBlock):
                        # Recover transactions that do not match
                        for transaction in current_head["data"]:
                            if transaction not in block["data"]:
                                self.add_transaction_to_pool(transaction)
                        self.storage[-1] = block
                elif current_head["timestamp"] == block["timestamp"]:
                    # Untie timestamp conflict with miner id
                    if current_head["miner"] > block["miner"]:
                        if self.validate_block(block, prevBlock):
                            # Recover transactions that do not match
                            for transaction in current_head["data"]:
                                if transaction not in block["data"]:
                                    self.add_transaction_to_pool(transaction)
                            self.storage[-1] = block
            # Otherwise, the node just must be valid
            elif current_head["height"] == block["height"] - 1:
                logger.info("Validate next block")
                if self.validate_block(block, current_head):
                    self.storage.append(block)
                    self.remove_transactions_from_pool(block)
            self.lock.release()
        return False

    def get_chain(self):
        return self.storage