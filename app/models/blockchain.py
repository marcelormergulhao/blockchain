import sys
import logging
import json

from threading import Lock
from collections import OrderedDict
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from base64 import b64encode, b64decode

from app.models.block import Block
from app.models.transaction import Transaction

# Log configuration
logging.basicConfig(format = "%(asctime)-15s %(message)s", stream=sys.stdout)
logger = logging.getLogger("blockchain_logger")
logger.setLevel(logging.DEBUG)

class Blockchain():
    def __init__(self):
        self.lock = Lock()
        self.t_lock = Lock()
        self.storage = []
        self.transaction_pool = []

    def empty(self):
        """
        Checks if the blockchain is empty
        """
        return len(self.storage) == 0

    def setup_new_chain(self, json_list):
        """
        Start new chain (block list) from current result
        """
        self.storage = list(json_list)
    
    def create_genesis_block(self, private_key, miner_id):
        """
        Cria o primeiro bloco da cadeia.
        TODO: Criar bloco com os seguintes campos:
            * prevHash: Usar a string "Genesis Block"
            * height: 0
            * data: lista contendo uma transação de "Genesis Addr" para "Genesis Block" devidamente assinada
            * miner_id: identificação do nó que está criando o bloco
        Após criado, mineirar o bloco e então adicionar o resultado à lista storage
        """
        pass

    def check_double_spending(self, miner_id):
        """
        Verificação de transações do endereço passado como argumento na cadeia.
        TODO: Varrer a cadeia (lista storage) e as transações pendentes (lista transaction_pool)
        para ver se o participante está tentando votar novamente.
        Retornar True caso encontre um voto do participante e False caso contrário
        """
        pass

    def has_transaction_in_pool(self, miner_id):
        """
        Check if miner has transaction on pool to avoid multiple instances
        """
        for transaction in self.transaction_pool:
            if transaction["addr_from"] == miner_id:
                logger.error("User has vote on transaction pool")
                return True
        return False

    def remove_transactions_from_pool(self, block):
        """
        After receiveing a new block, check if the transactions were in the pool and remove them
        """
        logger.info("Current pool {}".format(self.transaction_pool))
        for transaction in block["data"]:
            if transaction in self.transaction_pool:
                self.transaction_pool.remove(transaction)
        logger.info("New pool {}".format(self.transaction_pool))
        return

    def get_transactions_from_data(self, data):
        transactions = []
        for t in data:
            new_t = OrderedDict({"addr_from": t["addr_from"]})
            new_t["addr_to"] = t["addr_to"]
            new_t["signature"] = t["signature"]
            new_t["pubkey"] = t["pubkey"]
            transactions.append(new_t)
        return transactions

    def validate_block(self, block, prevBlock):
        """
        Valida integridade do bloco e se ele é compatível com o anterior na cadeia.
        TODO: Dado o bloco e o anterior como dicionários, validar:
            * Se a hash do bloco anterior está referenciada no candidato
            * Se há "Proof of Work"
            * Se a hash no bloco corresponde de fato ao SHA256 do conteúdo do bloco
              * Uma sugestão é criar um bloco novo, referenciando os campos do que foi recebido
               e alterar na mão o nonce. Para manter a ordem das transações e seus campos, a sugestão é
               usar a função "get_transactions_from_data(data)", já fornecida 
            * Se as transações contidas no bloco são válidas (assinadas e sem duplicação)
              * Há as função "validate_transaction(t)" para validar a assinatura e "check_double_spend()" para duplicação
            Retornar True se o bloco for válido e False caso contrário
        """
        pass

    def create_and_add_block(self, miner_id):
        """
        Using miner_id and current transaction_pool, create block and add to chain.
        """
        block = None
        if not self.empty():
            # Get last block
            prevBlock = self.storage[-1]
            # Use it to create new block with the current transactions in pool
            block = Block(prevBlock["hash"], prevBlock["height"] + 1, self.transaction_pool, miner_id)
            block.mine()
            logger.info("Block created: {}".format(block.get_json()))
            self.validate_and_add_block(block.get_json())
        return block

    def validate_transaction(self, transaction):
        """
        Validate that a transaction signature corresponds to the provided data
        """
        t_sig = b64decode(transaction["signature"].encode())
        pubkey = b64decode(transaction["pubkey"].encode())
        verifier = PKCS1_v1_5.new(RSA.importKey(pubkey))
        digest = SHA256.new()
        t = Transaction(transaction["addr_from"], transaction["addr_to"])
        digest.update(str(t.get_json()).encode())
        verified = verifier.verify(digest,t_sig)
        if verified:
            return True
        else:
            logger.info("Signature is invalid")
        return False

    def add_transaction_to_pool(self, transaction):
        """
        Add transaction to pool with concurrency protection
        """
        self.t_lock.acquire()
        self.transaction_pool.append(transaction)
        self.t_lock.release()
        return

    def validate_and_add_block(self, block):
        """
        Validate block in JSON format and add to chain.
        Change transaction pool accordingly.
        """
        logger.info("Validate and add block")
        if len(self.storage) > 0:
            self.lock.acquire()
            current_head = self.storage[-1]
            # Check if node has the same height as the current head and untie the conflict with the timestamp
            if current_head["height"] == block["height"]:
                logger.info("Validate conflicting block")
                prevBlock = self.storage[-2]
                if current_head["timestamp"] > block["timestamp"]:
                    if self.validate_block(block, prevBlock):
                        # Recover transactions that do not match
                        for transaction in current_head["data"]:
                            if transaction not in block["data"]:
                                self.add_transaction_to_pool(transaction)
                        self.storage[-1] = block
                elif current_head["timestamp"] == block["timestamp"]:
                    # Untie timestamp conflict with miner id
                    if current_head["miner"] > block["miner"]:
                        if self.validate_block(block, prevBlock):
                            # Recover transactions that do not match
                            for transaction in current_head["data"]:
                                if transaction not in block["data"]:
                                    self.add_transaction_to_pool(transaction)
                            self.storage[-1] = block
            # Otherwise, the node just must be valid
            elif current_head["height"] == block["height"] - 1:
                logger.info("Validate next block")
                if self.validate_block(block, current_head):
                    self.storage.append(block)
                    self.remove_transactions_from_pool(block)
            self.lock.release()
        return False

    def get_chain(self):
        """
        Return list representing the blockchain
        """
        return self.storage