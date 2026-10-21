"""Identidades Ed25519 e registro de membros autorizados.

O Registro cumpre aqui o papel que a Certificate Authority (CA) cumpre no
Hyperledger Fabric: só quem estiver cadastrado, com o papel correto, pode
gravar transações ou produzir blocos.
"""
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

DISPOSITIVO = "dispositivo"
VALIDADOR = "validador"


class Identidade:
    """Par de chaves de um membro (dispositivo IoT ou validador)."""

    def __init__(self, nome, chave_privada=None):
        self.nome = nome
        self._priv = chave_privada or Ed25519PrivateKey.generate()
        self.pub_hex = self._priv.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        ).hex()

    def assinar(self, dados: bytes) -> str:
        return self._priv.sign(dados).hex()

    def exportar_privada(self) -> str:
        return self._priv.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        ).hex()

    @classmethod
    def importar(cls, nome, privada_hex):
        return cls(nome, Ed25519PrivateKey.from_private_bytes(bytes.fromhex(privada_hex)))


def verificar(pub_hex: str, dados: bytes, assinatura_hex: str) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(
            bytes.fromhex(assinatura_hex), dados
        )
        return True
    except (InvalidSignature, ValueError):
        return False


class Registro:
    """Lista de membros autorizados: nome -> (papel, chave pública)."""

    def __init__(self):
        self._membros = {}

    def autorizar(self, nome, pub_hex, papel):
        if papel not in (DISPOSITIVO, VALIDADOR):
            raise ValueError(f"papel inválido: {papel}")
        self._membros[nome] = {"papel": papel, "pub": pub_hex}

    def revogar(self, nome):
        self._membros.pop(nome, None)

    def assinatura_valida(self, nome, papel, dados: bytes, assinatura_hex: str) -> bool:
        """True só se o membro existe, tem o papel exigido e a assinatura confere."""
        m = self._membros.get(nome)
        if not m or m["papel"] != papel:
            return False
        return verificar(m["pub"], dados, assinatura_hex)

    def to_dict(self):
        return dict(self._membros)

    @classmethod
    def from_dict(cls, dados):
        r = cls()
        r._membros = dict(dados)
        return r
