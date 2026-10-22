"""Identidades Ed25519 e versões do cadastro por altura de confirmação."""
from copy import deepcopy

from blockchain_tcc.formato import canonico, sha256_hex
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
        """Exportação bruta para interoperabilidade/testes; não usar para guardar em disco."""
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
    except (InvalidSignature, ValueError, TypeError):
        return False


class Registro:
    """Cadastro versionado. Alterações passam a valer no próximo bloco.

    A autoridade administrativa é o processo local, não o relógio do sensor.
    Cada bloco assina o hash da versão de cadastro usada na confirmação.
    """

    def __init__(self):
        self._membros = {}
        self._versoes = [{"versao": 1, "inicio_bloco": 1, "membros": {}}]
        self._altura = lambda: 1
        self._persistir = None

    @staticmethod
    def _conferir_membro(nome, pub_hex, papel):
        if not isinstance(nome, str) or not nome.strip():
            raise ValueError("nome de membro inválido")
        if papel not in (DISPOSITIVO, VALIDADOR):
            raise ValueError(f"papel inválido: {papel}")
        if not isinstance(pub_hex, str) or len(pub_hex) != 64 or pub_hex != pub_hex.lower():
            raise ValueError("chave pública inválida")
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex))

    def vincular(self, altura, persistir):
        self._altura = altura
        self._persistir = persistir

    def _alterar(self, membros):
        versoes = self.exportar_estado()
        versoes.append({
            "versao": len(versoes) + 1,
            "inicio_bloco": self._altura(),
            "membros": deepcopy(membros),
        })
        # O callback pode rejeitar a mudança; a memória só muda após o commit.
        if self._persistir:
            self._persistir(versoes)
        self._versoes = versoes
        self._membros = deepcopy(membros)

    def autorizar(self, nome, pub_hex, papel):
        self._conferir_membro(nome, pub_hex, papel)
        novo = {"papel": papel, "pub": pub_hex, "ativo": True}
        if self._membros.get(nome) == novo:
            return
        membros = deepcopy(self._membros)
        membros[nome] = novo
        self._alterar(membros)

    def revogar(self, nome):
        if nome not in self._membros or not self._membros[nome]["ativo"]:
            return
        membros = deepcopy(self._membros)
        membros[nome]["ativo"] = False
        self._alterar(membros)

    def versao_para_bloco(self, indice):
        for versao in reversed(self._versoes):
            if versao["inicio_bloco"] <= indice:
                return deepcopy(versao)
        raise ValueError("cadastro histórico ausente")

    def hash_para_bloco(self, indice):
        return sha256_hex(canonico(self.versao_para_bloco(indice)))

    def membros_para_bloco(self, indice):
        return self.versao_para_bloco(indice)["membros"]

    def assinatura_valida(self, nome, papel, dados: bytes, assinatura_hex: str,
                         indice=None, registro_hash=None) -> bool:
        membros = self._membros
        if indice is not None:
            if registro_hash != self.hash_para_bloco(indice):
                return False
            membros = self.membros_para_bloco(indice)
        m = membros.get(nome)
        if not m or not m["ativo"] or m["papel"] != papel:
            return False
        return verificar(m["pub"], dados, assinatura_hex)

    def to_dict(self):
        return deepcopy(self._membros)

    def exportar_estado(self):
        return deepcopy(self._versoes)

    @classmethod
    def from_estado(cls, dados):
        if not isinstance(dados, list) or not dados:
            raise ValueError("histórico do cadastro ausente")
        anterior = 1
        for numero, versao in enumerate(dados, 1):
            if set(versao) != {"versao", "inicio_bloco", "membros"}:
                raise ValueError("formato de cadastro inválido")
            if type(versao["versao"]) is not int or versao["versao"] != numero:
                raise ValueError("sequência de cadastro inválida")
            inicio = versao["inicio_bloco"]
            if type(inicio) is not int or inicio < anterior:
                raise ValueError("altura de cadastro inválida")
            anterior = inicio
            if not isinstance(versao["membros"], dict):
                raise ValueError("membros inválidos")
            for nome, membro in versao["membros"].items():
                if set(membro) != {"pub", "papel", "ativo"} or type(membro["ativo"]) is not bool:
                    raise ValueError("membro inválido")
                cls._conferir_membro(nome, membro["pub"], membro["papel"])
        r = cls()
        r._versoes = deepcopy(dados)
        r._membros = deepcopy(dados[-1]["membros"])
        return r

    @classmethod
    def from_dict(cls, dados):
        r = cls()
        for nome, membro in dados.items():
            r.autorizar(nome, membro["pub"], membro["papel"])
            if not membro.get("ativo", True):
                r.revogar(nome)
        return r
