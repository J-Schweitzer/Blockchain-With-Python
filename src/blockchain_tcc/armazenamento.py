"""Persistência dos blocos em SQLite (o ledger sobrevive a reinícios)."""
import json
import sqlite3

from blockchain_tcc.formato import canonico, sha256_hex, hash_governanca


class Armazenamento:
    def __init__(self, caminho="ledger.db"):
        self._con = sqlite3.connect(caminho)
        try:
            self._preparar_tabelas()
        except Exception:
            self._con.close()
            raise

    def _preparar_tabelas(self):
        tabelas = {linha[0] for linha in self._con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self._legado = "blocos" in tabelas and "configuracao" not in tabelas
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS blocos (indice INTEGER PRIMARY KEY, dados TEXT NOT NULL)"
        )
        if not self._legado:
            self._con.execute(
                "CREATE TABLE IF NOT EXISTS configuracao (id INTEGER PRIMARY KEY CHECK(id = 1), dados TEXT NOT NULL)"
            )
        self._con.commit()

    def carregar_configuracao(self):
        if self._legado:
            return None
        linha = self._con.execute("SELECT dados FROM configuracao WHERE id = 1").fetchone()
        return json.loads(linha[0]) if linha else None

    def inicializar(self, configuracao, genesis):
        with self._con:
            if self._con.execute("SELECT COUNT(*) FROM blocos").fetchone()[0]:
                raise ValueError("o banco já contém blocos")
            self._con.execute(
                "INSERT INTO configuracao (id, dados) VALUES (1, ?)",
                (canonico(configuracao).decode("utf-8"),),
            )
            self._inserir_bloco(genesis)

    def atualizar_registro(self, versoes, esperado, altura):
        with self._con:
            # Impede sobrescrever mudanças feitas por uma instância desatualizada.
            self._con.execute("BEGIN IMMEDIATE")
            config = self.carregar_configuracao()
            topo = self._con.execute("SELECT MAX(indice) FROM blocos").fetchone()[0]
            if config is None or config["registro"] != esperado or topo is None or topo + 1 != altura:
                raise ValueError("estado desatualizado; reabra o sistema")
            config["registro"] = versoes
            self._con.execute(
                "UPDATE configuracao SET dados = ? WHERE id = 1",
                (canonico(config).decode("utf-8"),),
            )

    def _inserir_bloco(self, bloco_dict):
        self._con.execute(
            "INSERT INTO blocos (indice, dados) VALUES (?, ?)",
            (bloco_dict["indice"], canonico(bloco_dict).decode("utf-8")),
        )

    def salvar_bloco(self, bloco_dict):
        # Reverte a transação se ocorrer falha antes do commit.
        with self._con:
            self._con.execute("BEGIN IMMEDIATE")
            if bloco_dict["indice"] > 0:
                config = self.carregar_configuracao()
                if config is None or bloco_dict.get("registro_hash") != sha256_hex(canonico(config["registro"][-1])):
                    raise ValueError("cadastro desatualizado; reabra o sistema")
                if bloco_dict.get("governanca_hash") != hash_governanca(config["rede_id"], config["validadores"]):
                    raise ValueError("governança desatualizada; reabra o sistema")
            self._inserir_bloco(bloco_dict)

    def carregar_blocos(self):
        cur = self._con.execute("SELECT indice, dados FROM blocos ORDER BY indice")
        blocos = []
        for indice, dados in cur:
            bloco = json.loads(dados)
            if not isinstance(bloco, dict) or type(bloco.get("indice")) is not int:
                raise ValueError("estrutura de bloco inválida no SQLite")
            if bloco["indice"] != indice:
                raise ValueError("índice da tabela diverge do bloco persistido")
            blocos.append(bloco)
        return blocos

    def fechar(self):
        self._con.close()
