import sys
import logging

from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from base64 import b64encode, b64decode
from collections import OrderedDict

# Log configuration
logging.basicConfig(format = "%(asctime)-15s %(message)s", stream=sys.stdout)
logger = logging.getLogger("blockchain_logger")
logger.setLevel(logging.DEBUG)

class Transaction():
    """
    This class contains the definition of what is stored in blocks and
    implements the signing scheme.
    """
    def __init__(self, addr_from, addr_to):
        """
        Transaction initialization, just populate source and destination
        """
        self.addr_from = addr_from
        self.addr_to = addr_to
        self.signature = None

    def sign(self, key):
        """
        Sign JSON from current transaction with provided key.
        """
        signer = PKCS1_v1_5.new(key)
        digest = SHA256.new()
        digest.update(str(self.get_json()).encode())
        self.signature = b64encode(signer.sign(digest)).decode()

    def get_json(self):
        """
        Return OrderedDict with "addr_from" and "addr_to" fields.
        """
        ordered_json = OrderedDict({"addr_from": self.addr_from})
        ordered_json["addr_to"] = self.addr_to
        return ordered_json

    def get_signed_json(self, key):
        """
        Return OrderedDict containing "addr_from", "addr_to", "signature" and "pubkey".
        """
        if self.signature is None:
            self.sign(key)

        # Use this append "==" trick to avoid incorrect padding
        pubkey = b64encode(key.publickey().exportKey("PEM") + b"==").decode()
        ordered_json = self.get_json()
        ordered_json["signature"] = self.signature
        ordered_json["pubkey"] = pubkey
        return ordered_json