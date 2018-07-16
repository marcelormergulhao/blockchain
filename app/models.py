import hashlib
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
        return {"addr_from": self.addr_from, "addr_to": self.addr_to}

    def get_signed_json(self, key):
        if self.signature is None:
            self.sign(key)

        # Use this append "==" trick to avoid incorrect padding
        pubkey = b64encode(key.publickey().exportKey("PEM") + b"==").decode()
        return {"addr_from": self.addr_from, "addr_to": self.addr_to,
                "signature": self.signature, "pubkey": pubkey}
        

class Block():
    def __init__(self, prevHash, height, data, miner):
        self.block = {
            "miner": miner,
            "hash": "",
            "prevHash": prevHash,
            "height": height,
            "nonce": 0, # Nonce will be used to "mine" node
            "data": list(data)
        }

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
                break
            self.block["nonce"] = self.block["nonce"] + 1

    def get_json(self):
        return self.block



class Blockchain():
    def __init__(self):
        """
        Blockchain initialization routine, generates miner ID and synchronizes blockchain (blocks and participants)
        """
        self.master_node = "localhost:5000"
        random.seed()
        self.generate_miner_id()
        self.address = self.get_current_address()
        self.participant_list = []
        self.get_current_participant_list()
        self.advertise()
        self.blockchain = None

        while self.blockchain is None:
            self.get_current_blockchain()
        # Valid addresses you can issue a vote to
        self.valid_addresses = [{"name": "Candidate 1", "address": "12345"},
                                {"name": "Candidate 2", "address": "5678"},
                                {"name": "Candidate 3", "address": "9999"}]
        self.transaction_pool = []
        # Control the token for "current block creator"
        self.update_block_creator()
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
                    self.blockchain = r.json()
                    logger.debug("Current Blockchain {}".format(self.blockchain))
            else:
                logger.info("Current node is the only one in the participant list")
                if self.blockchain is None:
                    self.create_genesis_block()
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

    def add_transaction_to_pool(self, addr_to):
        """
        Used to make a transaction from current node to another
        """
        logger.info("Add transaction to pool")
        if self.has_to_vote():
            if self.check_valid_address(addr_to):
                transaction = Transaction(self.miner_id, addr_to)
                self.transaction_pool.append(transaction.get_signed_json(self.private_key))
                self.propagate_transaction(transaction.get_signed_json(self.private_key))
                if self.block_creator:
                    if not self.sched.get_jobs():
                        logger.info("Start block schedule")
                        self.sched.add_job(self.create_and_add_block, 'date',run_date=datetime.now()+timedelta(seconds=10))
            else:
                logger.error("Cannot vote for this ledger, check the address")

    def has_to_vote(self):
        """
        Check if node still hasn't voted
        """
        logger.info("Checking blockchain for node votes")
        if self.blockchain is not None:
            for block in self.blockchain:
                logger.info("Block {}".format(block))
                transactions = block["data"]
                for transaction in transactions:
                    logger.info("Checking transaction {}".format(transaction))
                    if transaction["addr_from"] == self.miner_id:
                        logger.error("User has already issued his vote")
                        return False
        # Also check for soon to be completed transactions
        for transaction in self.transaction_pool:
            if transaction["addr_from"] == self.miner_id:
                logger.error("User has vote on transaction pool")
                return False
        return True


    def check_valid_address(self, address):
        logger.info("Check destination address")
        for valid_candidate in self.valid_addresses:
            if address in valid_candidate["address"]:
                return True
        return False

    def create_genesis_block(self):
        logger.info("Creating genesis block")
        transaction = Transaction("Genesis Addr", "Genesis Block")
        genesis = Block("Genesis Block", 0, [transaction.get_signed_json(self.private_key)], self.miner_id)
        genesis.mine()
        self.blockchain = [genesis.get_json()]

    def create_and_add_block(self):
        """
        Create block using current transaction pool as data
        """
        block = None
        if self.blockchain is not None:
            prevBlock = self.blockchain[-1]
            block = Block(prevBlock["hash"], prevBlock["height"] + 1, self.transaction_pool, self.miner_id)
            block.mine()
            logger.info("Block created: {}".format(block.get_json()))
            # After adding current transaction to block, remove transactions from pool
            self.blockchain.append(block.get_json())
            self.remove_transactions_from_pool(block.get_json())
            self.propagate_block(block.get_json())
        return block

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

    def show_blockchain(self):
        for block in self.blockchain:
            print(block)

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

    def update_block_creator(self):
        """
        Check if it is this node time to generate blocks
        """
        self.block_creator = True

    def validate_and_add_block(self, block):
        # Check if received block fits the position of new block
        if self.blockchain is not None:
            logger.info("Block received: {}".format(block))
            prevBlock = self.blockchain[-1]
            if block["prevHash"] == prevBlock["hash"]:
                if block["hash"][0:3] == "000":
                    logger.info("Valid block")
                    self.blockchain.append(block)
                    self.remove_transactions_from_pool(block)
                    self.propagate_block(block)
        return

    def validate_and_add_transaction(self, transaction):
        logger.info("Transaction received: {}".format(transaction))
        # First check if the signature is ok
        t_sig = b64decode(transaction["signature"].encode())
        pubkey = b64decode(transaction["pubkey"].encode())
        verifier = PKCS1_v1_5.new(RSA.importKey(pubkey))
        digest = SHA256.new()
        t = Transaction(transaction["addr_from"], transaction["addr_to"])
        digest.update(str(t.get_json()).encode())
        verified = verifier.verify(digest,t_sig)
        if verified:
            logger.info("Verified signature")
            for valid_addr in self.valid_addresses:
                if transaction["addr_to"] == valid_addr["address"]:
                    self.transaction_pool.append(transaction)
                    break
        else:
            logger.info("Signature is invalid")
        return


    def get_current_address(self):
        return "localhost:5000"

    def add_participant_to_list(self, peer):
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
            

