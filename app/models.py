import random
import json
import requests
import logging
import sys
import os
from datetime import datetime,timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from base64 import b64encode, b64decode
from collections import OrderedDict
from threading import Lock

# Log configuration
logging.basicConfig(format = "%(asctime)-15s %(message)s", stream=sys.stdout)
logger = logging.getLogger("blockchain_logger")
logger.setLevel(logging.DEBUG)

class Transaction():
    def __init__(self, addr_from, addr_to):
        self.addr_from = addr_from
        self.addr_to = addr_to
        self.signature = None

    def sign(self, key):
        signer = PKCS1_v1_5.new(key)
        digest = SHA256.new()
        digest.update(str(self.get_json()).encode())
        self.signature = b64encode(signer.sign(digest)).decode()

    def get_json(self):
        ordered_json = OrderedDict({"addr_from": self.addr_from})
        ordered_json["addr_to"] = self.addr_to
        return ordered_json

    def get_signed_json(self, key):
        if self.signature is None:
            self.sign(key)

        # Use this append "==" trick to avoid incorrect padding
        pubkey = b64encode(key.publickey().exportKey("PEM") + b"==").decode()
        ordered_json = self.get_json()
        ordered_json["signature"] = self.signature
        ordered_json["pubkey"] = pubkey
        return ordered_json
        

class Block():
    def __init__(self, prevHash, height, data, miner):
        self.block = OrderedDict({"miner": miner})
        self.block["hash"] = ""
        self.block["prevHash"] = prevHash
        self.block["height"] = height
        # Nonce will be used to "mine" node
        self.block["nonce"] = 0
        self.block["data"] = list(data)

    def mine(self):
        """Calculate valid hash from current transaction list"""
        logger.info("Mining node")
        while True:
            # Get hash from complete block, discarding own hash
            sha256 = SHA256.new()
            sha256.update(json.dumps(self.block).encode())
            hexdigest = sha256.hexdigest()
            if hexdigest[0:3] == "000":
                self.block["hash"] = hexdigest
                self.block["timestamp"] = str(datetime.now().timestamp())
                break
            self.block["nonce"] = self.block["nonce"] + 1

    def get_json(self):
        return self.block

class Blockchain():
    def __init__(self):
        """
        Initialize blockchain storage and possibly populate
        """
        self.lock = Lock()
        self.t_lock = Lock()
        # self.conflicting_block = None
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

class PeerToPeer():
    def __init__(self, addr):
        """
        PeerToPeer network initialization routine, generates miner ID and synchronizes blockchain (blocks and participants)
        """
        self.master_node = "localhost:5000"
        random.seed()
        self.generate_miner_id()
        self.address = addr
        self.participant_list = []
        self.get_current_participant_list()
        self.advertise()
        self.blockchain = Blockchain()

        while self.blockchain.empty():
            self.get_current_blockchain()
        # Valid addresses you can issue a vote to
        self.valid_addresses = [{"name": "Candidate 1", "address": "12345"},
                                {"name": "Candidate 2", "address": "5678"},
                                {"name": "Candidate 3", "address": "9999"}]
        self.sched = BackgroundScheduler(daemon=True)
        self.sched.start()

    def get_current_participant_list(self):
        """
        Get current participant list from other peers
        """
        logger.info("Get Current Participant List")
        if self.address == self.master_node:
            logger.info("Assuming this node as Master")
            return

        if len(self.participant_list) == 0:
            logger.info("Use master node as source")
            # Treat as the first list insertion
            try:
                r = requests.get("http://" + self.master_node + "/list")
                logger.debug("Request return: {}".format(r.status_code))
                if r.status_code == 200:
                    self.participant_list = r.json()
            except:
                logger.error("Could not get data from master node")

        else:
            logger.info("Use current participants as source")
            done = False
            while not done:
                random_participant = random.randint(0,len(self.participant_list)-1)
                r = requests.get("http://" + self.participant_list[random_participant]["address"] + "/list")
                if r.status_code == 200:
                    self.participant_list = r.json()
                    done = True
                elif r.status_code == 408:
                    # Client timeout, remove participant from list and try another
                    self.participant_list.pop(random_participant)
                    if len(self.participant_list) == 0:
                        logger.error("Participant list is empty now, will keep trying on master node for now")
                        done = True
                else:
                    logger.error("Invalid return code, finish operation")
                    done = True

    def get_current_blockchain(self):
        logger.info("Get current blockchain")
        if self.participant_list is not None:
            if len(self.participant_list) > 1:
                random_participant = random.randint(0,len(self.participant_list)-1)
                # Check if the participant is not himself. If it is just abort with error
                if self.participant_list[random_participant]["address"] == self.address:
                    return
                r = requests.get("http://" + self.participant_list[random_participant]["address"] + "/blockchain")
                logger.debug("Request result: {}".format(r.status_code))
                if r.status_code == 200:
                    self.blockchain.setup_new_chain(r.json())
            else:
                logger.info("Current node is the only one in the participant list")
                if self.blockchain.empty():
                    self.blockchain.create_genesis_block(self.private_key, self.miner_id)
        else:
            # There should never be an empty participant list
            logger.error("Empty participant list, won't get blockchain for now")        

    def get_current_transaction_pool(self):
        logger.info("Get current transaction pool")
        if self.participant_list is not None:
            random_participant = random.randint(0,len(self.participant_list)-1)
            r = requests.get("http://" + self.participant_list[random_participant]["address"] + "/pool")
            logger.debug("Request result: {}".format(r.status_code))
            if r.status_code == 200:
                self.transaction_pool = r.json()
                logger.debug("Current Transaction Pool {}".format(self.transaction_pool))
        else:
            # There should never be an empty participant list
            logger.error("Empty participant list, won't get transaction pool for now")

    def create_and_add_transaction(self, addr_to):
        """
        Used to make a transaction from current node to another
        """
        logger.info("Add transaction to pool")
        if self.has_to_vote():
            if self.check_valid_address(addr_to):
                transaction = Transaction(self.miner_id, addr_to)
                self.blockchain.add_transaction_to_pool(transaction.get_signed_json(self.private_key))
                self.propagate_transaction(transaction.get_signed_json(self.private_key))
                if len(self.sched.get_jobs()) == 0:
                    logger.info("Start block schedule")
                    self.sched.add_job(self.create_and_add_block, 'date',run_date=datetime.now()+timedelta(seconds=5))
            else:
                logger.error("Cannot vote for this ledger, check the address")

    def has_to_vote(self):
        """
        Check if node still hasn't voted
        """
        logger.info("Checking blockchain for node votes")
        if not self.blockchain.empty():
            if self.blockchain.check_transaction(self.miner_id):
                return False
        return True

    def check_valid_address(self, address):
        logger.info("Check destination address")
        for valid_candidate in self.valid_addresses:
            if address in valid_candidate["address"]:
                return True
        return False

    def create_and_add_block(self):
        """
        Create block using current transaction pool as data
        """
        block = self.blockchain.create_and_add_block(self.miner_id)
        self.propagate_block(block.get_json())
        return

    def generate_miner_id(self):
        """
        Check if there is already an ID for this node and load it, otherwise create.
        Also, keep a private key to use when signing transactions
        """
        if os.path.isfile("private_key.pem") :
            logger.info("Loading private key")
            with open("private_key.pem") as fr:
                self.private_key = RSA.importKey(fr.read())
            
            with open("miner_id.txt") as fr:
                self.miner_id = fr.read()

        else:
            logger.info("Create new miner ID")
            self.miner_id = str(random.randint(0, 10000))
            logger.info("Saving miner ID")
            with open("miner_id.txt", "w") as fw:
                fw.write(self.miner_id)

            logger.info("Create private key")
            self.private_key = RSA.generate(1024)
            with open("private_key.pem", "w") as fw:
                fw.write(self.private_key.exportKey("PEM").decode())
            
        return 

    def propagate_transaction(self, transaction):
        logger.info("Propagate transaction")
        for peer in self.participant_list:
            if peer["address"] != self.address:
                r = requests.post("http://" + peer["address"] + "/update_pool", json = transaction)
                if r.status_code == 200:
                    logger.info("Sent transaction to {}".format(peer["address"]))

    def propagate_block(self, block):
        logger.info("Propagate block")
        for peer in self.participant_list:
            if peer["address"] != self.address:
                r = requests.post("http://" + peer["address"] + "/add_new_block", json = block)
                if r.status_code == 200:
                    logger.info("Sent block to {}".format(peer["address"]))


    def validate_and_add_block(self, block):
        self.blockchain.validate_and_add_block(block)
        return

    def validate_and_add_transaction(self, transaction):
        logger.info("Transaction received: {}".format(transaction))
        # First check if the signature is ok
        if self.blockchain.validate_transaction(transaction):
            # Then check the destination address
            logger.info("Verified signature")
            for valid_addr in self.valid_addresses:
                if transaction["addr_to"] == valid_addr["address"]:
                    self.blockchain.add_transaction_to_pool(transaction)
                    if len(self.sched.get_jobs()) == 0:
                        logger.info("Start block schedule")
                        self.sched.add_job(self.create_and_add_block, 'date',run_date=datetime.now()+timedelta(seconds=5))
        return

    def add_participant_to_list(self, peer):
        if peer not in self.participant_list:
            self.participant_list.append(peer)

    def advertise(self):
        logger.info("Advertise node to other peers")
        if len(self.participant_list) > 0:
            advertisement = {"miner_id":self.miner_id, "address": self.address}
            for peer in self.participant_list:
                if peer["address"] != self.address:
                    try:
                        requests.post("http://" + peer["address"] + "/advertise", json = advertisement)
                    except:
                        logger.error("Error advertising for {}".format(peer["address"]))
        # Add current node to its own list
        self.participant_list.append({"miner_id":self.miner_id, "address": self.address})
            
        