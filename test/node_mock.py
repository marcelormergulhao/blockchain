import hashlib
import json
from flask import Flask, jsonify, request

app = Flask(__name__)
blockchain = None

class Block():
    def __init__(self, hash, prevHash, height, data, miner):
        self.block = {
            "miner": miner,
            "hash": hash,
            "prevHash": prevHash,
            "height": height,
            "nonce": 0, # Nonce will be used to "mine" node
            "data": [] # Empty transaction list initially
        }

    def add_transaction(self, transaction):
        pass

    def mine(self):
        """Calculate valid hash from current transaction list"""
        while True:
            # Get hash from complete block, discarding own hash
            sha256 = hashlib.sha256(json.dumps(self.block).encode())
            hexdigest = sha256.hexdigest()
            # print("Current hash: {}".format(hexdigest))
            if hexdigest[0:3] == "000":
                # print("Mined node")
                self.block["hash"] = hexdigest
                print(self.block)
                break
            self.block["nonce"] = self.block["nonce"] + 1

@app.route("/list")
def get_participant_list():
    # Participant list contains just a single item for now
    participants = [{"miner_id": "1", "address": "localhost"}]
    return jsonify(participants)

@app.route("/blockchain")
def get_genesis_blockchain():
    global blockchain
    if blockchain is None:
        blockchain = [Block("","Genesis Block",0,"Genesis Block Data", 1)]
        blockchain[0].mine()
    json_list = [b.block for b in blockchain]
    return jsonify(json_list)

@app.route("/update_pool", methods=["POST"])
def update_transaction_pool():
    received_data = request.get_json()
    if received_data is not None:
        print("Received Pool {}".format(received_data))
        return json.dumps(received_data)
    return jsonify({"error": "true"})

@app.route("/add_new_block", methods=["POST"])
def update_blocks():
    received_data = request.get_json()
    if request.json is not None:
        print("Received Block {}".format(received_data))
        return json.dumps(received_data)
    return jsonify({"error": "true"})


app.run(port=13131)