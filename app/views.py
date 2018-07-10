from flask import request, jsonify
from app import app
from app.models import Blockchain,Block

@app.route("/")
def index():
    return "Welcome to the blockchain APP"

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
