"""Verifica o arquivo local de credenciais e a inicialização sem prompts."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from blockchain_tcc.credenciais import ler_credenciais
from blockchain_tcc.iniciar_api import main as iniciar_api
from blockchain_tcc.preparar_demo_api import main as preparar_demo


SENHA = "senha-local-de-teste-123"
TOKEN = "token-local-de-teste-2026-com-mais-de-32-caracteres"


class TesteCredenciais(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pasta = Path(self.temp.name)
        self.arquivo = self.pasta / "credenciais.local.txt"
        self.arquivo.write_text(
            f"# valores locais\nSENHA_CHAVES={SENHA}\nTOKEN_ADMIN={TOKEN}\n",
            encoding="utf-8",
        )

    def test_ler_sem_executar_conteudo(self):
        self.assertEqual(ler_credenciais(self.arquivo), (SENHA, TOKEN))
        literal = "$(comando_inexistente)123"
        self.arquivo.write_text(
            "SENHA_CHAVES=" + literal + "\nTOKEN_ADMIN=" + TOKEN + "\n",
            encoding="utf-8",
        )
        self.assertEqual(ler_credenciais(self.arquivo), (literal, TOKEN))

    def test_rejeitar_arquivo_incompleto(self):
        self.arquivo.write_text("SENHA_CHAVES=\nTOKEN_ADMIN=\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "preencha"):
            ler_credenciais(self.arquivo)

    def test_preparar_e_iniciar_sem_getpass(self):
        dados = self.pasta / "dados"
        with patch("getpass.getpass", side_effect=AssertionError("prompt inesperado")):
            self.assertEqual(preparar_demo([str(dados), "--credenciais", str(self.arquivo)]), 0)
            with patch("blockchain_tcc.iniciar_api.serve") as servir:
                self.assertEqual(iniciar_api([
                    str(dados), "--porta", "5101", "--apresentacao",
                    "--credenciais", str(self.arquivo),
                ]), 0)
        app = servir.call_args.args[0]
        self.assertEqual(app.test_client().get("/saude").status_code, 200)
        self.assertEqual(app.test_client().get("/painel").status_code, 200)


if __name__ == "__main__":
    unittest.main()
