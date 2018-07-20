import sys
import logging
import json
import random
import requests
import os

from datetime import datetime,timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from Crypto.PublicKey import RSA

from app.models.blockchain import Blockchain
from app.models.transaction import Transaction

# Log configuration
logging.basicConfig(format = "%(asctime)-15s %(message)s", stream=sys.stdout)
logger = logging.getLogger("blockchain_logger")
logger.setLevel(logging.DEBUG)

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
        """
        Request current blockchain from another peer and save it.
        """
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
        """
        Request transaction pool from other peer and save it.
        """
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
            if self.blockchain.check_double_spending(self.miner_id):
                return False
            if self.blockchain.has_transaction_in_pool(self.miner_id):
                return False
        return True

    def check_valid_address(self, address):
        """
        Check if the value inserted is a valid candidate in the list
        """
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
        """
        Post generated transaction to all the peers in the list
        """
        logger.info("Propagate transaction")
        for peer in self.participant_list:
            if peer["address"] != self.address:
                r = requests.post("http://" + peer["address"] + "/update_pool", json = transaction)
                if r.status_code == 200:
                    logger.info("Sent transaction to {}".format(peer["address"]))

    def propagate_block(self, block):
        """
        Post generated block to all the peers in the list
        """
        logger.info("Propagate block")
        for peer in self.participant_list:
            if peer["address"] != self.address:
                r = requests.post("http://" + peer["address"] + "/add_new_block", json = block)
                if r.status_code == 200:
                    logger.info("Sent block to {}".format(peer["address"]))


    def validate_and_add_block(self, block):
        """
        Validate received block and add it to local chain
        """
        self.blockchain.validate_and_add_block(block)
        return

    def validate_and_add_transaction(self, transaction):
        """
        Validate received transaction and add it to transaction pool
        """
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
        """
        Receive peer advertisement and add him to the list
        """
        if peer not in self.participant_list:
            self.participant_list.append(peer)

    def advertise(self):
        """
        Post registration message to the current peers of the network
        """
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