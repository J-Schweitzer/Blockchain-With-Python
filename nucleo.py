"""Núcleo da blockchain privada: transações, blocos, cadeia e consenso PoA.

Consenso Proof of Authority em rodízio: o bloco de índice i só é aceito se
produzido e assinado pelo validador da vez. Não há mineração nem gas, e a
finalidade é determinística: bloco aceito é bloco definitivo.
"""
import hashlib
import json
import time
from dataclasses import asdict, dataclass

from identidade import DISPOSITIVO, VALIDADOR

HASH_ZERO = "0" * 64


class ErroBlockchain(Exception):
    pass


def canonico(obj) -> bytes:
    """Serialização determinística, base de todo hash e assinatura."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_hex(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


@dataclass
class Transacao:
    dispositivo: str
    valor: str
    ts: float
    assinatura: str = ""

    def conteudo(self) -> bytes:
        return canonico({"dispositivo": self.dispositivo, "valor": self.valor, "ts": self.ts})

    @classmethod
    def criar(cls, identidade, valor):
        tx = cls(identidade.nome, str(valor), time.time())
        tx.assinatura = identidade.assinar(tx.conteudo())
        return tx

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class Bloco:
    indice: int
    ts: float
    transacoes: list
    hash_anterior: str
    validador: str
    assinatura: str = ""
    hash: str = ""

    def cabecalho(self) -> bytes:
        return canonico({
            "indice": self.indice,
            "ts": self.ts,
            "transacoes": self.transacoes,
            "hash_anterior": self.hash_anterior,
            "validador": self.validador,
        })

    def calcular_hash(self) -> str:
        return sha256_hex(self.cabecalho())

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


class Cadeia:
    def __init__(self, registro, validadores, armazenamento=None):
        if not validadores:
            raise ErroBlockchain("é preciso ao menos um validador")
        self.registro = registro
        self.validadores = list(validadores)  # nomes, na ordem do rodízio
        self.armazenamento = armazenamento
        self.pendentes = []
        self.blocos = []

        salvos = armazenamento.carregar_blocos() if armazenamento else []
        if salvos:
            self.blocos = [Bloco.from_dict(b) for b in salvos]
            ok, erro = self.validar()
            if not ok:
                raise ErroBlockchain(f"ledger persistido está corrompido: {erro}")
        else:
            self._criar_genesis()

    def _criar_genesis(self):
        g = Bloco(0, 0.0, [], HASH_ZERO, "genesis")
        g.hash = g.calcular_hash()
        self._anexar(g)

    def _anexar(self, bloco):
        self.blocos.append(bloco)
        if self.armazenamento:
            self.armazenamento.salvar_bloco(bloco.to_dict())

    def validador_da_vez(self, indice: int) -> str:
        return self.validadores[(indice - 1) % len(self.validadores)]

    def adicionar_transacao(self, tx: Transacao):
        if not self.registro.assinatura_valida(tx.dispositivo, DISPOSITIVO, tx.conteudo(), tx.assinatura):
            raise ErroBlockchain(f"transação rejeitada: '{tx.dispositivo}' não autorizado ou assinatura inválida")
        self.pendentes.append(tx.to_dict())

    def produzir_bloco(self, validador, ts=None) -> Bloco:
        if not self.pendentes:
            raise ErroBlockchain("não há transações pendentes")
        indice = len(self.blocos)
        esperado = self.validador_da_vez(indice)
        if validador.nome != esperado:
            raise ErroBlockchain(f"não é a vez de '{validador.nome}' (vez de '{esperado}')")
        bloco = Bloco(
            indice=indice,
            ts=time.time() if ts is None else ts,
            transacoes=list(self.pendentes),
            hash_anterior=self.blocos[-1].hash,
            validador=validador.nome,
        )
        bloco.hash = bloco.calcular_hash()
        bloco.assinatura = validador.assinar(bloco.hash.encode())
        self.pendentes.clear()
        self._anexar(bloco)
        return bloco

    def validar(self):
        """Verifica a cadeia inteira. Retorna (True, None) ou (False, motivo)."""
        for i, b in enumerate(self.blocos):
            if b.indice != i:
                return False, f"bloco {i}: índice incorreto"
            if b.calcular_hash() != b.hash:
                return False, f"bloco {i}: conteúdo não corresponde ao hash"
            if i == 0:
                continue
            if b.hash_anterior != self.blocos[i - 1].hash:
                return False, f"bloco {i}: elo quebrado (hash anterior diferente)"
            if b.validador != self.validador_da_vez(i):
                return False, f"bloco {i}: produzido fora da vez"
            if not self.registro.assinatura_valida(b.validador, VALIDADOR, b.hash.encode(), b.assinatura):
                return False, f"bloco {i}: assinatura do validador inválida"
            for tx in b.transacoes:
                t = Transacao.from_dict(tx)
                if not self.registro.assinatura_valida(t.dispositivo, DISPOSITIVO, t.conteudo(), t.assinatura):
                    return False, f"bloco {i}: transação com assinatura inválida"
        return True, None

    def historico(self, dispositivo):
        """Rastreabilidade: todas as leituras de um dispositivo, com o bloco de origem."""
        return [
            {"bloco": b.indice, "valor": tx["valor"], "ts": tx["ts"]}
            for b in self.blocos
            for tx in b.transacoes
            if tx["dispositivo"] == dispositivo
        ]
