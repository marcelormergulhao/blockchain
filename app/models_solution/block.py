import sys
import logging
import json
from datetime import datetime

from collections import OrderedDict
from Crypto.Hash import SHA256

# Log configuration
logging.basicConfig(format = "%(asctime)-15s %(message)s", stream=sys.stdout)
logger = logging.getLogger("blockchain_logger")
logger.setLevel(logging.DEBUG)

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
        """
        Calculate valid hash from current transaction list
        """
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
        """
        Return block as OrderedDict
        """
        return self.block