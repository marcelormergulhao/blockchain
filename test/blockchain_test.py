import unittest
import sys
sys.path.append("../")

from app.models.blockchain import Blockchain
from app.models.block import Block
from app.models.transaction import Transaction

from Crypto.PublicKey import RSA

class BlockchainTest(unittest.TestCase):
    def test_blockchain_creation(self):
        chain = Blockchain()
        self.assertTrue(chain.empty())
        
    def test_genesis_block_creation(self):
        chain = Blockchain()
        private_key = RSA.generate(1024)
        miner_id = "1234"
        chain.create_genesis_block(private_key, miner_id)
        self.assertEqual(len(chain.storage), 1)
        genesis = chain.storage[0]
        # Check if the block is valid and the correct value is on the data field
        self.assertEqual(genesis["hash"][0:3], "000")
        self.assertEqual(genesis["prevHash"], "Genesis Block")


    def test_block_validation(self):
        chain = Blockchain()
        private_key = RSA.generate(1024)
        miner_id = "1234"
        chain.create_genesis_block(private_key, miner_id)
        prevBlock = chain.storage[0]
        t = Transaction("1234", "4567")
        # Create Block with dummy transaction
        block = Block(prevBlock["hash"], prevBlock["height"] + 1, [t.get_signed_json(private_key)], miner_id)
        block.mine()

        # Check block validation is ok
        self.assertTrue(chain.validate_block(block.get_json(), prevBlock))

        # Mess with blockchain structure
        block.block["prevHash"] = "00012345"
        self.assertFalse(chain.validate_block(block.get_json(), prevBlock))

        # Mess with height
        block.block["prevHash"] = prevBlock["hash"]
        block.block["height"] = 5
        self.assertFalse(chain.validate_block(block.get_json(), prevBlock))

        # Mess with PoW
        block.block["height"] = 2
        block.block["hash"] = "0111111111"
        self.assertFalse(chain.validate_block(block.get_json(), prevBlock))

        # Mess with hash but keep PoW
        block.block["hash"] = "0001111111"
        self.assertFalse(chain.validate_block(block.get_json(), prevBlock))

        # Mess with transaction integrity
        t.signature = "L7TBH0ahox4GOAdF8om2ijbNVPcO3Ys6+KdvfFhvfX/SysetaJw+0rlU6VMuzwB0rQ/X2+ioAdtXcstutSeRAfZTYP+utaNFL1nP48as/C6mca4sp+ya39AWWLIUuZeGMit9kSUavx6uX5cSAuqXB4tcK/bUSVghtMC9vG4JyC8="
        block = Block(prevBlock["prevHash"], prevBlock["height"] + 1, [t.get_signed_json(private_key)], miner_id)
        block.mine()
        self.assertFalse(chain.validate_block(block.get_json(), prevBlock))

    def test_double_spending(self):
        chain = Blockchain()
        # Setup chain with known values
        chain.setup_new_chain([{"data":[{"addr_from":"Genesis Addr","addr_to":"Genesis Block","pubkey":"LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlHZk1BMEdDU3FHU0liM0RRRUJBUVVBQTRHTkFEQ0JpUUtCZ1FEbUk0U1BjSTI0eVpqY0o0eHZjcHY1aHBXMgpQYVdkYWpYUm84VGU3VktBcnB5Skh2N0VMSUQ1dEZXKzNwRk8rcVBYYk1TKzk4bnl6Zk1ockY3Rk5zcVlwdlBRCmxCekxYZXZJWDQvdXlPa0p0UHFBM1VTdExXL3ZjRTR2NnNTcVNQMndRaVhsazV5TkVGaGVaNGxNYXVrNzUyemIKekhic2xpc1A5SlJYNCtiQS93SURBUUFCCi0tLS0tRU5EIFBVQkxJQyBLRVktLS0tLT09","signature":"G+jAyLxJ1xQIPP3vzrX80sYzZ+JX78OSOxc9kGWqxQ9nRTrfNhnXPA4xu6fZeuidjD1chPuYTJyu77J0M5lRFAF4NbT1QemKAon9wBGtjklX4FpEZAmDK/ex58Etj2TY3fgFqByKzKO/eMOnjBqBfO0HQkxO+cob58S8gLWEt3I="}],"hash":"000fc4a7168fd501a2576da8841d62f781061cb14abb8aac7300a8641477773b","height":0,"miner":"5106","nonce":2923,"prevHash":"Genesis Block","timestamp":"1531853048.28545"},{"data":[{"addr_from":"5106","addr_to":"12345","pubkey":"LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlHZk1BMEdDU3FHU0liM0RRRUJBUVVBQTRHTkFEQ0JpUUtCZ1FEbUk0U1BjSTI0eVpqY0o0eHZjcHY1aHBXMgpQYVdkYWpYUm84VGU3VktBcnB5Skh2N0VMSUQ1dEZXKzNwRk8rcVBYYk1TKzk4bnl6Zk1ockY3Rk5zcVlwdlBRCmxCekxYZXZJWDQvdXlPa0p0UHFBM1VTdExXL3ZjRTR2NnNTcVNQMndRaVhsazV5TkVGaGVaNGxNYXVrNzUyemIKekhic2xpc1A5SlJYNCtiQS93SURBUUFCCi0tLS0tRU5EIFBVQkxJQyBLRVktLS0tLT09","signature":"cQ7WZNVP9J8LD1WMB1H6KGBCHkXw+NVgISFbWcWsvgsBFgl5FqIA0SrT0fLYjoxGzw+kIMBlF1dOZ/G49jIJfqclqbQQiwMnsor3XgJb4Inqt6Q6CR/zxMWeFN1m1VAvnX8PgZxOuja+WSV2Lp8cLzsIsZBHWpCtOSeChJ2zV0w="}],"hash":"00057d09370bcd45fa37ef5e5085e7923658d03633b2d444497dd72a18a33baa","height":1,"miner":"5106","nonce":1046,"prevHash":"000fc4a7168fd501a2576da8841d62f781061cb14abb8aac7300a8641477773b","timestamp":"1531853066.532551"}])
        self.assertTrue(chain.check_double_spending("5106"))
        self.assertFalse(chain.check_double_spending("1234"))
        

if __name__ == "__main__":
    unittest.main()