# Blockchain PoC

The code in this repo contain a simple voting app that uses Blockchain to store the data and
Flask to provide an API to access it.

The app uses Proof of Work similar to Bitcoin, where blocks are "mined" and makes simplifications
to the aspects that resolve ties on blocks.

Additionally, parts of the code where removed and the instructions on how to complete it were
given to use the code as a introductory workshop.

## Environment Setup

The app is built on Python 3 and is managed with pip, so create an virtual environment and install
all the dependencies:

```
virtualenv env --python=/usr/bin/python3.5
pip install -r requirements.txt
source env/bin/activate
```

When you want to run the app, use the "run.sh" script, that sets the Flask environment variables
and calls the development server.

## Usage

When complete, the app has a simple index page that allows the user to choose between three candidates
and cast his vote.
Go to `http://localhost:5000/` to see it.

The interface is simple and the functionality of the app is hidden, but the votes are stored in a blockchain
structure (in memory) and has mechanisms to sign transactions, validate blocks and check for double spending.

There are other routes that help in development:

* /list: contains the participant list of the P2P network
* /blockchain: contains the list of votes in the chain

## Workshop Development and Testing

The instructions on how to implement each of the methods are provided as "TODO" at the beggining of
each method.
The best path to follow is to start with the Transaction class, then Block and finally Blockchain.

There are unit tests provided for each of the parts of the model: transaction, block and blockchain.
Simply run them from the tests folder to check if the implementation matches the expected:

```
cd tests
python transaction_test.py
python block_test.py
python blockchain_test.py
```

Finally, one example of solution is in the models_solution folder, that is used by the current app
views.

