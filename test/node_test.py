import sys

sys.path.append("../")
from app.models import Blockchain

# This should put blockchain on a usable state (participant list and chain OK)
chain = Blockchain()
chain.add_transaction_to_pool("12345")
chain.add_transaction_to_pool("12345")
chain.create_and_add_block()
chain.show_blockchain()