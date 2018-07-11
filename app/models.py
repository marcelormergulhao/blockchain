import hashlib
import random
import json
import requests
import logging
import sys

# Log configuration
logging.basicConfig(format = "%(asctime)-15s %(message)s", stream=sys.stdout)
logger = logging.getLogger("blockchain_logger")
logger.setLevel(logging.DEBUG)

class Transaction():
    def __init__(self, addr_from, addr_to):
        self.addr_from = addr_from
        self.addr_to = addr_to

    def get_json(self):
        return {"addr_from": self.addr_from, "addr_to": self.addr_to}
        

class Block():
    def __init__(self, prevHash, height, data, miner):
        self.block = {
            "miner": miner,
            "hash": "",
            "prevHash": prevHash,
            "height": height,
            "nonce": 0, # Nonce will be used to "mine" node
            "data": data
        }

    def mine(self):
        """Calculate valid hash from current transaction list"""
        logger.info("Mining node")
        while True:
            # Get hash from complete block, discarding own hash
            sha256 = hashlib.sha256(json.dumps(self.block).encode())
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
        random.seed()
        self.miner_id = self.generate_miner_id()
        self.participant_list = None
        self.get_current_participant_list()
        self.blockchain = None
        self.get_current_blockchain()
        # Valid addresses you can issue a vote to
        self.valid_addresses = [{"name": "Candidate 1", "address": "12345"},
                                {"name": "Candidate 2", "address": "5678"},
                                {"name": "Candidate 3", "address": "9999"}]
        self.transaction_pool = []

    def get_current_participant_list(self):
        """
        Get current participant list from other peers
        """
        logger.info("Get Current Participant List")
        if self.participant_list is None:
            logger.info("Use master node as source")
            # Treat as the first list insertion
            r = requests.get("http://localhost:13131/list")
            logger.debug("Request return: {}".format(r.status_code))
            if r.status_code == 200:
                self.participant_list = r.json()
        else:
            logger.info("Use current participants as source")
            done = False
            while not done:
                random_participant = random.randint(0,len(self.participant_list)-1)
                r = requests.get("http://" + self.participant_list[random_participant]["address"] + ":13131/list")
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
            random_participant = random.randint(0,len(self.participant_list)-1)
            r = requests.get("http://" + self.participant_list[random_participant]["address"] + ":13131/blockchain")
            logger.debug("Request result: {}".format(r.status_code))
            if r.status_code == 200:
                self.blockchain = r.json()
                logger.debug("Current Blockchain {}".format(self.blockchain))
        else:
            # There should never be an empty participant list
            logger.error("Empty participant list, won't get blockchain for now")
        

    def get_current_transaction_pool(self):
        logger.info("Get current transaction pool")
        if self.participant_list is not None:
            random_participant = random.randint(0,len(self.participant_list)-1)
            r = requests.get("http://" + self.participant_list[random_participant]["address"] + ":13131/pool")
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
                self.transaction_pool.append(transaction.get_json())
                self.propagate_pool()
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
        genesis = Block("Genesis Block",0,"Genesis Block Data", self.miner_id)
        genesis.mine()
        self.blockchain = [genesis]

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
            self.transaction_pool = []
            self.blockchain.append(block.get_json())
            self.propagate_block(block.get_json())
        return block

    def show_blockchain(self):
        for block in self.blockchain:
            print(block)

    def generate_miner_id(self):
        return str(random.randint(0, 10000))

    def propagate_pool(self):
        logger.info("Propagate transaction pool")
        for peer in self.participant_list:
            r = requests.post("http://" + peer["address"] + ":13131/update_pool", json = self.transaction_pool)
            if r.status_code == 200:
                logger.info("Sent pool to {}".format(peer["address"]))
            else:
                print("Status Code: {}".format(r.status_code))

    def propagate_block(self, block):
        logger.info("Propagate block")
        for peer in self.participant_list:
            r = requests.post("http://" + peer["address"] + ":13131/add_new_block", json = block)
            if r.status_code == 200:
                logger.info("Sent block to {}".format(peer["address"]))
            else:
                print("Status Code: {}".format(r.status_code))