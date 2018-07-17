import unittest
import sys
sys.path.append("../")

from app.models.transaction import Transaction

from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from base64 import b64encode, b64decode
from collections import OrderedDict

class TransactionTest(unittest.TestCase):
    def test_transaction_creation(self):
        # Create transaction and check if used ordered dict
        t = Transaction("1234","4567")
        o_dict = OrderedDict({"addr_from" : "1234"})
        o_dict["addr_to"] = "4567"
        self.assertTrue(type(t.get_json()) == type(o_dict))
        self.assertDictEqual(t.get_json(), o_dict)

    def test_transaction_signature(self):
        # Create transaction
        t = Transaction("1234","4567")
        # Create Private Key
        key = RSA.generate(1024)
        # Sign transaction and recover complete transaction JSON
        signed_json = t.get_signed_json(key)

        # Verify signature and public key match
        t_sig = b64decode(signed_json["signature"].encode())
        pubkey = b64decode(signed_json["pubkey"].encode())
        verifier = PKCS1_v1_5.new(RSA.importKey(pubkey))
        digest = SHA256.new()
        t = Transaction(signed_json["addr_from"], signed_json["addr_to"])
        digest.update(str(t.get_json()).encode())

        self.assertTrue(verifier.verify(digest,t_sig))

if __name__ == "__main__":
    unittest.main()