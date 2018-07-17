import sys
import logging

from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from base64 import b64encode, b64decode
from collections import OrderedDict

# Log configuration
logging.basicConfig(format = "%(asctime)-15s %(message)s", stream=sys.stdout)
logger = logging.getLogger("blockchain_logger")
logger.setLevel(logging.DEBUG)

class Transaction():
    def __init__(self, addr_from, addr_to):
        """
        Inicialização da transação.
        TODO: dados os endereços de origem e destino, apenas armazena os valores.
        """
        pass

    def sign(self, key):
        """
        Assina o JSON da transação com a chave passada como argumento.
        TODO: Criar procedimento de assinatura e armazenar em variável interna.
        O resultado da assinatura deve passar por uma codificação em base64 (b64encode) e
        posteriormente ser decodificado em UTF-8 (decode) para ser compatível com o resto do código.
        """
        signer = PKCS1_v1_5.new(key)
        digest = SHA256.new()
        digest.update(str(self.get_json()).encode())
        self.signature = b64encode(signer.sign(digest)).decode()

    def get_json(self):
        """
        TODO: Retornar dicionário (OrderedDict) com os seguintes campos:
        * addr_from: endereço do peer que originou a transação
        * addr_to: endereço do candidato que receberá o voto
        """
        pass

    def get_signed_json(self, key):
        """
        TODO: Retornar dicionário (OrderedDict) contendo:
          * addr_from
          * addr_to
          * signature: assinatura gerada pelo método sign
          * pubkey: chave pública que verificará a validade da assinatura

        A chave pública deve passar pelo mesma codificação que a assinatura.
        Uma dica para evitar problemas de padding com a chave pública é adicionar um bytearray (b"==") ao final
        do que será codificado com base64.
        """
        pass