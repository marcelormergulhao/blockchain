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
    pass

@app.route("/advertise")
def advertise():
    """Receive node advertisement and store on miner list"""
    pass

@app.route("/blockchain")
def get_blockchain():
    """Return current blockchain"""
    pass

@app.route("/update_pool", methods=["POST"])
def add_transaction():
    """Update transaction pool"""
    pass

@app.route("/add_new_block", methods=["POST"])
def add_block():
    """Add block to chain"""
    pass
