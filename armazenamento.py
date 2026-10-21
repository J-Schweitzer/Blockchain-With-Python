"""Persistência dos blocos em SQLite (o ledger sobrevive a reinícios)."""
import json
import sqlite3


class Armazenamento:
    def __init__(self, caminho="ledger.db"):
        self._con = sqlite3.connect(caminho)
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS blocos (indice INTEGER PRIMARY KEY, dados TEXT NOT NULL)"
        )
        self._con.commit()

    def salvar_bloco(self, bloco_dict):
        self._con.execute(
            "INSERT INTO blocos (indice, dados) VALUES (?, ?)",
            (bloco_dict["indice"], json.dumps(bloco_dict, sort_keys=True)),
        )
        self._con.commit()

    def carregar_blocos(self):
        cur = self._con.execute("SELECT dados FROM blocos ORDER BY indice")
        return [json.loads(linha[0]) for linha in cur]

    def fechar(self):
        self._con.close()
