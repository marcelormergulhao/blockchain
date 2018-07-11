from flask import request, jsonify, render_template, redirect
from app import app
from app.models import Blockchain,Block

blockchain = Blockchain()

@app.route("/")
@app.route("/status")
def index():
    return render_template("status.html", blockchain=blockchain)

@app.route("/cast_vote", methods=["POST"])
def cast_vote():
    if request.form is not None:
        print("Cast vote to {}".format(request.form["vote_addr"]))
        blockchain.add_transaction_to_pool(request.form["vote_addr"])
    return redirect("/status")

@app.route("/list")
def get_miner_list():
    """Return list of miners advertised to this node"""
    return jsonify(blockchain.participant_list)

@app.route("/advertise", methods=["POST"])
def advertise():
    """Receive node advertisement and store on miner list"""
    received_data = request.get_json()
    if received_data is not None:
        blockchain.add_participant_to_list(received_data)
    return jsonify({"status": "ok"})

@app.route("/blockchain")
def get_blockchain():
    """Return current blockchain"""
    return jsonify(blockchain.blockchain)

@app.route("/update_pool", methods=["POST"])
def add_transaction():
    """Update transaction pool"""
    pass
    # received_data = request.get_json()
    # if received_data is not None:
    #     print("Received Pool {}".format(received_data))
    #     blockchain.update_pool(received_data)
    # return redirect("/status")

@app.route("/add_new_block", methods=["POST"])
def add_block():
    """Add block to chain"""
    received_data = request.get_json()
    if request.json is not None:
        print("Received Block {}".format(received_data))
        blockchain.validate_and_add_block(received_data)
    return jsonify({"status": "ok"})
