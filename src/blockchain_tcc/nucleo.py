"""Ledger local com transações assinadas e rodízio de autoridades.

O rodízio verifica a autoridade prevista para cada bloco em um único processo.
Não implementa consenso distribuído, replicação nem tolerância a falhas de nós.
"""
import math
import sqlite3
import time
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from uuid import uuid4

from blockchain_tcc.identidade import DISPOSITIVO, VALIDADOR, Registro
from blockchain_tcc.formato import canonico, sha256_hex, hash_governanca

HASH_ZERO = "0" * 64


class ErroBlockchain(Exception):
    pass


@dataclass
class Transacao:
    dispositivo: str
    valor: str
    ts: float
    assinatura: str = ""
    versao: int = 2
    id_transacao: str = field(default_factory=lambda: uuid4().hex)
    rede_id: str = "local"
    medicao: dict | None = None

    def conteudo(self) -> bytes:
        dados = {
            "versao": self.versao, "id_transacao": self.id_transacao,
            "rede_id": self.rede_id, "dispositivo": self.dispositivo,
            "valor": self.valor, "ts": self.ts,
        }
        if self.versao == 3:
            dados["medicao"] = self.medicao
        return canonico(dados)

    @classmethod
    def criar(cls, identidade, valor, rede_id="local", medicao=None):
        tx = cls(identidade.nome, str(valor), time.time(), rede_id=rede_id,
                 versao=3 if medicao is not None else 2, medicao=deepcopy(medicao))
        tx.assinatura = identidade.assinar(tx.conteudo())
        return tx

    def to_dict(self):
        dados = asdict(self)
        if self.versao == 2:
            dados.pop("medicao")
        return dados

    @classmethod
    def from_dict(cls, d):
        campos = {"dispositivo", "valor", "ts", "assinatura", "versao", "id_transacao", "rede_id"}
        if isinstance(d, dict) and d.get("versao") == 3:
            campos.add("medicao")
        if not isinstance(d, dict) or set(d) != campos:
            raise ValueError("schema de transação incompatível; esperado formato 2 ou 3")
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
    versao: int = 2
    registro_hash: str = ""
    rede_id: str = "local"
    governanca_hash: str = ""

    def cabecalho(self) -> bytes:
        dados = {
            "indice": self.indice,
            "ts": self.ts,
            "transacoes": self.transacoes,
            "hash_anterior": self.hash_anterior,
            "validador": self.validador,
        }
        if self.versao == 2:
            dados.update(versao=2, registro_hash=self.registro_hash, rede_id=self.rede_id,
                         governanca_hash=self.governanca_hash)
        return canonico(dados)

    def calcular_hash(self) -> str:
        return sha256_hex(self.cabecalho())

    def to_dict(self):
        dados = asdict(self)
        if self.versao == 1:
            for campo in ("versao", "registro_hash", "rede_id", "governanca_hash"):
                dados.pop(campo)
        return dados

    @classmethod
    def from_dict(cls, d):
        return cls(**dict(d, versao=d.get("versao", 1)))


class Cadeia:
    def __init__(self, registro, validadores, armazenamento=None, rede_id="local"):
        if (not isinstance(validadores, (list, tuple)) or not validadores
                or any(not isinstance(v, str) or not v.strip() for v in validadores)
                or len(set(validadores)) != len(validadores)):
            raise ErroBlockchain("lista de validadores inválida ou vazia")
        if not isinstance(rede_id, str) or not rede_id.strip():
            raise ErroBlockchain("identificador de rede inválido")
        self.registro = registro
        self.validadores = list(validadores)  # nomes, na ordem do rodízio
        self.armazenamento = armazenamento
        self.rede_id = rede_id
        self.pendentes = []
        self.blocos = []

        try:
            salvos = armazenamento.carregar_blocos() if armazenamento else []
            if not isinstance(salvos, list):
                raise ValueError("lista de blocos esperada")
            self.blocos = [Bloco.from_dict(b) for b in salvos]
            config = armazenamento.carregar_configuracao() if armazenamento else None
            Registro.from_estado(registro.exportar_estado())
            if armazenamento and config is None and salvos:
                raise ErroBlockchain("ledger legado sem cadastro: exige migração explícita")
            if config is not None and config != self._configuracao():
                raise ErroBlockchain("configuração divergente ou inválida; abra pelo Sistema.abrir")
            if config is not None and not salvos:
                raise ErroBlockchain("ledger persistido sem bloco gênese")
            if registro.exportar_estado()[-1]["inicio_bloco"] > max(1, len(self.blocos)):
                raise ErroBlockchain("cadastro com altura futura inválida")
            self._conferir_validadores(registro.to_dict())
        except (TypeError, ValueError, KeyError, AttributeError, sqlite3.Error) as exc:
            raise ErroBlockchain("não foi possível carregar o ledger persistido") from exc
        if self.blocos:
            ok, erro = self.validar()
            if not ok:
                raise ErroBlockchain(f"ledger persistido está corrompido: {erro}")
        else:
            self._criar_genesis()
        registro.vincular(lambda: len(self.blocos), self._persistir_registro)

    def _configuracao(self):
        return {"versao": 2, "rede_id": self.rede_id,
                "validadores": self.validadores, "registro": self.registro.exportar_estado()}

    def _conferir_validadores(self, membros):
        ativos = [n for n, m in membros.items() if m["ativo"] and m["papel"] == VALIDADOR]
        if not ativos or any(n not in self.validadores for n in ativos):
            raise ErroBlockchain("é preciso manter autoridade ativa na lista fixa de validadores")

    def _persistir_registro(self, versoes):
        self._conferir_validadores(versoes[-1]["membros"])
        if self.armazenamento:
            try:
                self.armazenamento.atualizar_registro(
                    versoes, self.registro.exportar_estado(), len(self.blocos)
                )
            except (sqlite3.Error, ValueError, OSError) as exc:
                raise ErroBlockchain("não foi possível persistir o cadastro") from exc

    def _criar_genesis(self):
        g = Bloco(0, 0.0, [], HASH_ZERO, "genesis", versao=1)
        g.hash = g.calcular_hash()
        if self.armazenamento:
            try:
                self.armazenamento.inicializar(self._configuracao(), g.to_dict())
            except (sqlite3.Error, ValueError, OSError) as exc:
                raise ErroBlockchain("não foi possível inicializar o ledger") from exc
        self.blocos.append(g)

    def _anexar(self, bloco):
        # O commit no SQLite precede qualquer alteração do estado em memória.
        if self.armazenamento:
            try:
                self.armazenamento.salvar_bloco(bloco.to_dict())
            except (sqlite3.Error, ValueError, OSError) as exc:
                raise ErroBlockchain("não foi possível persistir o bloco") from exc
        self.blocos.append(bloco)

    def validador_da_vez(self, indice: int) -> str:
        membros = self.registro.membros_para_bloco(indice)
        ativos = [v for v in self.validadores if membros.get(v, {}).get("ativo")
                  and membros[v]["papel"] == VALIDADOR]
        if not ativos:
            raise ErroBlockchain("não há autoridade ativa para produzir o bloco")
        return ativos[(indice - 1) % len(ativos)]

    def _ids_confirmados(self):
        return {t.get("id_transacao") for b in self.blocos for t in b.transacoes
                if isinstance(t, dict) and isinstance(t.get("id_transacao"), str)}

    def adicionar_transacao(self, tx: Transacao):
        if not self._transacao_valida(tx):
            raise ErroBlockchain("transação rejeitada: estrutura, autorização ou assinatura inválida")
        if tx.id_transacao in self._ids_confirmados() or any(
            t.get("id_transacao") == tx.id_transacao for t in self.pendentes
        ):
            raise ErroBlockchain("transação repetida (replay)")
        self.pendentes.append(tx.to_dict())

    def descartar_pendente(self, id_transacao):
        self.pendentes[:] = [t for t in self.pendentes if t.get("id_transacao") != id_transacao]

    def produzir_bloco(self, validador, ts=None) -> Bloco:
        if not self.pendentes:
            raise ErroBlockchain("não há transações pendentes")
        ok, erro = self.validar()
        if not ok:
            raise ErroBlockchain(f"cadeia inválida: {erro}")
        indice = len(self.blocos)
        esperado = self.validador_da_vez(indice)
        if validador.nome != esperado:
            raise ErroBlockchain(f"não é a vez de '{validador.nome}' (vez de '{esperado}')")
        bloco = Bloco(
            indice=indice,
            ts=time.time() if ts is None else ts,
            transacoes=deepcopy(self.pendentes),
            hash_anterior=self.blocos[-1].hash,
            validador=validador.nome,
            registro_hash=self.registro.hash_para_bloco(indice),
            rede_id=self.rede_id,
            governanca_hash=hash_governanca(self.rede_id, self.validadores),
        )
        try:
            bloco.hash = bloco.calcular_hash()
        except (TypeError, ValueError) as exc:
            raise ErroBlockchain("bloco com estrutura inválida") from exc
        bloco.assinatura = validador.assinar(bloco.hash.encode())
        # Revalida as pendências e a chave do produtor antes de gravar o bloco.
        ok, erro = self._validar_bloco(bloco, indice, self._ids_confirmados())
        if not ok:
            raise ErroBlockchain(erro)
        self._anexar(bloco)
        self.pendentes.clear()
        return bloco

    @staticmethod
    def _timestamp_valido(ts):
        return type(ts) in (int, float) and math.isfinite(ts) and ts >= 0

    def _transacao_valida(self, tx, indice=None, registro_hash=None):
        try:
            if not isinstance(tx, Transacao):
                return False
            if type(tx.versao) is not int or tx.versao not in (2, 3) or tx.rede_id != self.rede_id:
                return False
            if tx.versao == 2 and tx.medicao is not None:
                return False
            if tx.versao == 3:
                if not isinstance(tx.medicao, dict) or set(tx.medicao) != {"grandeza", "unidade"}:
                    return False
                if any(not isinstance(v, str) or not v.strip() or len(v) > 64 for v in tx.medicao.values()):
                    return False
            if (not isinstance(tx.id_transacao, str) or len(tx.id_transacao) != 32
                    or any(c not in "0123456789abcdef" for c in tx.id_transacao)):
                return False
            if not isinstance(tx.dispositivo, str) or not tx.dispositivo.strip():
                return False
            if not isinstance(tx.valor, str) or not self._timestamp_valido(tx.ts):
                return False
            if not isinstance(tx.assinatura, str):
                return False
            return self.registro.assinatura_valida(
                tx.dispositivo, DISPOSITIVO, tx.conteudo(), tx.assinatura,
                indice=indice, registro_hash=registro_hash,
            )
        except (TypeError, ValueError, OverflowError):
            return False

    def _validar_bloco(self, b, i, ids_anteriores=None):
        try:
            if not isinstance(b, Bloco) or type(b.indice) is not int or b.indice != i:
                return False, f"bloco {i}: índice incorreto"
            if not self._timestamp_valido(b.ts) or not isinstance(b.transacoes, list):
                return False, f"bloco {i}: estrutura inválida"
            if b.calcular_hash() != b.hash:
                return False, f"bloco {i}: conteúdo não corresponde ao hash"
            if i == 0:
                esperado = Bloco(0, 0.0, [], HASH_ZERO, "genesis", versao=1)
                esperado.hash = esperado.calcular_hash()
                if b.versao != 1 or b.to_dict() != esperado.to_dict():
                    return False, "bloco 0: gênese diferente do modelo fixo"
                return True, None
            if not b.transacoes:
                return False, f"bloco {i}: não há transações"
            if type(b.versao) is not int or b.versao != 2 or b.rede_id != self.rede_id:
                return False, f"bloco {i}: versão ou rede inválida"
            if b.registro_hash != self.registro.hash_para_bloco(i):
                return False, f"bloco {i}: versão histórica do cadastro inválida"
            if b.governanca_hash != hash_governanca(self.rede_id, self.validadores):
                return False, f"bloco {i}: configuração de governança divergente"
            if b.hash_anterior != self.blocos[i - 1].hash:
                return False, f"bloco {i}: elo quebrado (hash anterior diferente)"
            if b.validador != self.validador_da_vez(i):
                return False, f"bloco {i}: produzido fora da vez"
            if not isinstance(b.assinatura, str) or not self.registro.assinatura_valida(
                b.validador, VALIDADOR, b.hash.encode(), b.assinatura,
                indice=i, registro_hash=b.registro_hash,
            ):
                return False, f"bloco {i}: assinatura do validador inválida"
            vistos = set(ids_anteriores or ())
            for dados in b.transacoes:
                tx = Transacao.from_dict(dados)
                if not self._transacao_valida(tx, i, b.registro_hash):
                    return False, f"bloco {i}: transação inválida"
                if tx.id_transacao in vistos:
                    return False, f"bloco {i}: transação repetida (replay)"
                vistos.add(tx.id_transacao)
        except (TypeError, ValueError, KeyError, AttributeError, OverflowError, ErroBlockchain):
            return False, f"bloco {i}: estrutura inválida"
        return True, None

    def validar(self):
        """Verifica a cadeia inteira. Retorna (True, None) ou (False, motivo)."""
        if not self.blocos:
            return False, "cadeia vazia: bloco gênese ausente"
        vistos = set()
        for i, b in enumerate(self.blocos):
            ok, erro = self._validar_bloco(b, i, vistos)
            if not ok:
                return False, erro
            vistos.update(t["id_transacao"] for t in b.transacoes)
        return True, None

    def historico(self, dispositivo):
        """Rastreabilidade: todas as leituras de um dispositivo, com o bloco de origem."""
        return [
            {"bloco": b.indice, "valor": tx["valor"], "ts": tx["ts"]}
            for b in self.blocos
            for tx in b.transacoes
            if tx["dispositivo"] == dispositivo
        ]
