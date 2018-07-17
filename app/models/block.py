import sys
import logging
import json
from datetime import datetime

from collections import OrderedDict
from Crypto.Hash import SHA256

# Log configuration
logging.basicConfig(format = "%(asctime)-15s %(message)s", stream=sys.stdout)
logger = logging.getLogger("blockchain_logger")
logger.setLevel(logging.DEBUG)

class Block():
    def __init__(self, prevHash, height, data, miner):
        """
        TODO: Criar variável interna chamada "block" como um dicionário, contendo as seguintes chaves:
         * hash: inicialmente vazia, vai armazenar a hash do bloco após mineirar
         * prevHash: hash do bloco imediatamente anterior na cadeia
         * height: indica a ordem do bloco na cadeia
         * nonce: inteiro usado na mineiração
         * data: lista de transações assinadas
        """
        self.block = OrderedDict()
        pass

    def mine(self):
        """
        Executa o processo de Proof of Work, manipulando o nonce para que a hash tenha o formato esperado.
        TODO: Encontrar hash que mostre a computação realizada, contendo "000" no início.
        Após encontrar o hash, colocar no campo esperado e adicionar um campo chamado "timestamp" para validar o momento da criação.
        """
        pass

    def get_json(self):
        """
        Return block as OrderedDict
        """
        return self.block