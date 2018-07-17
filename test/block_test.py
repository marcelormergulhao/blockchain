import unittest
import sys
sys.path.append("../")

from app.models.transaction import Transaction
from app.models.block import Block

from Crypto.PublicKey import RSA

class BlockTest(unittest.TestCase):
    def test_block_creation(self):
        # Create genesis transaction
        transaction = Transaction("Genesis Addr", "Genesis Block")
        key = RSA.generate(1024)
        miner_id = "1234"
        # Create genesis block with genesis transaction, signing it
        genesis = Block("Genesis Block", 0, [transaction.get_signed_json(key)], miner_id)

        self.assertDictEqual(genesis.get_json(), {"miner": miner_id,
            "hash": "",
            "prevHash": "Genesis Block",
            "height": 0,
            "nonce": 0,
            "data": [transaction.get_signed_json(key)]})

    def test_block_mining(self):
        # Create example block
        h = "some hash"
        data = "some random data"
        block = Block(h, 0, [data], "1234")
        block.mine()
        self.assertEqual(block.block["hash"], "00015080dc53b9ab05840ec3cbebe26bb4c13059b9b8c828404a730fa32e134c")

if __name__ == "__main__":
    unittest.main()