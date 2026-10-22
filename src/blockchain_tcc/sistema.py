"""Entrada da aplicação persistente da etapa 2; administração local confiável."""
import sqlite3
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from blockchain_tcc.armazenamento import Armazenamento
from blockchain_tcc.cofre import CofreChaves, senha_bytes
from blockchain_tcc.identidade import DISPOSITIVO, VALIDADOR, Registro
from blockchain_tcc.nucleo import Cadeia, ErroBlockchain, Transacao


def publicar_pasta(preparada, destino):
    for tentativa in range(5):
        try:
            preparada.rename(destino)
            return
        except PermissionError:
            # Antivírus e sincronização no Windows podem segurar arquivos recém-fechados.
            if tentativa == 4 or destino.exists():
                raise
            time.sleep(0.05 * (tentativa + 1))


class Sistema:
    def __init__(self, pasta, armazenamento, cadeia):
        self.pasta = Path(pasta)
        self.armazenamento = armazenamento
        self.cadeia = cadeia
        self.registro = cadeia.registro
        self.cofre = CofreChaves(self.pasta / "chaves")

    @classmethod
    def criar(cls, pasta, validadores, dispositivos, senha):
        senha_bytes(senha)
        validadores, dispositivos = list(validadores), list(dispositivos)
        identidades = validadores + dispositivos
        nomes = [i.nome for i in identidades]
        if not validadores or len(set(nomes)) != len(nomes):
            raise ValueError("informe validadores e nomes únicos para todos os membros")
        destino = Path(pasta).resolve()
        if destino.exists():
            raise FileExistsError("a pasta de destino já existe; use Sistema.abrir")
        destino.parent.mkdir(parents=True, exist_ok=True)
        # Publica a pasta somente após concluir cadastro, gênese e chaves cifradas.
        with tempfile.TemporaryDirectory(prefix=".inicializacao-", dir=destino.parent) as tmp:
            preparada = Path(tmp) / "sistema"
            preparada.mkdir()
            registro = Registro()
            cofre = CofreChaves(preparada / "chaves")
            for membros, papel in ((validadores, VALIDADOR), (dispositivos, DISPOSITIVO)):
                for identidade in membros:
                    registro.autorizar(identidade.nome, identidade.pub_hex, papel)
                    cofre.salvar(identidade, senha)
            armazenamento = Armazenamento(preparada / "ledger.db")
            try:
                Cadeia(registro, [i.nome for i in validadores], armazenamento, rede_id=uuid4().hex)
            finally:
                armazenamento.fechar()
            publicar_pasta(preparada, destino)
        return cls.abrir(destino)

    @classmethod
    def abrir(cls, pasta):
        pasta = Path(pasta).resolve()
        if not (pasta / "ledger.db").is_file():
            raise FileNotFoundError("ledger ausente; crie um novo sistema explicitamente")
        try:
            armazenamento = Armazenamento(pasta / "ledger.db")
        except (sqlite3.Error, OSError) as exc:
            raise ErroBlockchain("não foi possível abrir o banco de dados") from exc
        try:
            config = armazenamento.carregar_configuracao()
            if config is None:
                raise ErroBlockchain("ledger legado sem cadastro: exige migração explícita")
            if not isinstance(config, dict) or set(config) != {"versao", "rede_id", "validadores", "registro"}:
                raise ValueError("configuração inválida")
            if type(config["versao"]) is not int or config["versao"] != 2:
                raise ValueError("versão de sistema incompatível")
            registro = Registro.from_estado(config["registro"])
            cadeia = Cadeia(registro, config["validadores"], armazenamento, config["rede_id"])
            return cls(pasta, armazenamento, cadeia)
        except (ValueError, TypeError, KeyError, AttributeError, sqlite3.Error) as exc:
            armazenamento.fechar()
            raise ErroBlockchain("configuração ou ledger inválido") from exc
        except Exception:
            armazenamento.fechar()
            raise

    def carregar_identidade(self, nome, senha):
        membro = self.registro.to_dict().get(nome)
        if not membro or not membro["ativo"]:
            raise ErroBlockchain("identidade ausente ou revogada")
        return self.cofre.carregar(nome, membro["pub"], senha)

    def criar_transacao(self, nome, valor, senha):
        identidade = self.carregar_identidade(nome, senha)
        return Transacao.criar(identidade, valor, rede_id=self.cadeia.rede_id)

    def produzir_bloco(self, senha):
        nome = self.cadeia.validador_da_vez(len(self.cadeia.blocos))
        return self.cadeia.produzir_bloco(self.carregar_identidade(nome, senha))

    def autorizar(self, identidade, papel, senha):
        Registro._conferir_membro(identidade.nome, identidade.pub_hex, papel)
        # Gravar a chave primeiro evita publicar uma identidade sem chave recuperável.
        try:
            self.cofre.salvar(identidade, senha)
        except FileExistsError:
            self.cofre.carregar(identidade.nome, identidade.pub_hex, senha)
        self.registro.autorizar(identidade.nome, identidade.pub_hex, papel)

    def revogar(self, nome):
        self.registro.revogar(nome)

    def fechar(self):
        self.armazenamento.fechar()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.fechar()
