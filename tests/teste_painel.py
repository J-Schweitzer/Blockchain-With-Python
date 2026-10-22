"""Painel e laboratório: autorização, dados reais e preservação do ledger."""
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from blockchain_tcc.api import create_app
from blockchain_tcc.iniciar_api import main
from blockchain_tcc.preparar_demo_api import preparar
from blockchain_tcc.sistema import Sistema

SENHA = "senha-painel-testes-2026"
TOKEN = "token-administrativo-painel-testes-2026"
AUTH = {"Authorization": "Bearer " + TOKEN}


class TestPainel(unittest.TestCase):
    def setUp(self):
        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)
        self.pasta = preparar(Path(temporario.name) / "dados", SENHA)
        self.app = create_app(self.pasta, SENHA, TOKEN, modo_apresentacao=True, limite_requisicoes=10000)
        self.cliente = self.app.test_client()

    def simular(self):
        return self.cliente.post("/apresentacao/leituras", json={}, headers=AUTH)

    def gravar(self):
        self.assertEqual(self.simular().status_code, 202)
        resposta = self.cliente.post("/blocos", json={}, headers=AUTH)
        self.assertEqual(resposta.status_code, 201)
        return resposta.get_json()

    def executar_copia(self, bloco=1, valor="99.9", recalcular=False):
        return self.cliente.post("/apresentacao/integridade", json={
            "bloco": bloco, "valor": valor, "recalcular_hash": recalcular}, headers=AUTH)

    def test_shell_publico_nao_expoe_dados_ou_credenciais(self):
        resposta = self.cliente.get("/painel")
        self.assertEqual(resposta.status_code, 200)
        texto = resposta.get_data(as_text=True)
        self.assertIn("Token administrativo", texto)
        self.assertIn("/painel/static/painel.js", texto)
        for segredo in (TOKEN, SENHA, "sensor-temp-01\":", "BEGIN ENCRYPTED PRIVATE KEY"):
            self.assertNotIn(segredo, texto)
        self.assertEqual(self.cliente.get("/").headers["Location"], "/painel")
        for recurso in ("painel.css", "painel.js"):
            with self.cliente.get("/painel/static/" + recurso) as asset:
                self.assertEqual(asset.status_code, 200)
        self.assertIn("script-src 'self'", resposta.headers["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", resposta.headers["Content-Security-Policy"])
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")

    def test_dados_e_laboratorio_exigem_token(self):
        for rota in ("/painel/dados", "/transacoes"):
            self.assertEqual(self.cliente.get(rota).status_code, 401)
        for rota in ("/apresentacao/leituras", "/apresentacao/integridade"):
            self.assertEqual(self.cliente.post(rota, json={}).status_code, 401)

    def test_modo_de_apresentacao_exige_ativacao_explicita(self):
        cliente = create_app(self.pasta, SENHA, TOKEN).test_client()
        self.assertFalse(cliente.get("/painel/dados", headers=AUTH).get_json()["apresentacao"])
        self.assertEqual(cliente.post("/apresentacao/leituras", json={}, headers=AUTH).status_code, 403)
        self.assertEqual(cliente.post("/apresentacao/integridade", json={"bloco": 1, "valor": "99", "recalcular_hash": False}, headers=AUTH).status_code, 403)

    def test_resumo_consistente_reflete_cadastro_fila_e_blocos(self):
        self.gravar()
        self.simular()
        resumo = self.cliente.get("/painel/dados", headers=AUTH).get_json()
        self.assertEqual(resumo["blocos"], 2)
        self.assertEqual(resumo["transacoes_confirmadas"], 2)
        self.assertEqual(resumo["pendentes"], 2)
        self.assertEqual(resumo["proximo_validador"], "V2")
        self.assertEqual(len(resumo["membros"]), 5)
        self.assertEqual([s["leituras"] for s in resumo["sensores"]], [1, 1])
        self.assertEqual(resumo["ultimos_blocos"][0]["indice"], 1)
        self.assertTrue(resumo["validacao"]["valida"])
        self.assertTrue(resumo["simulacao_disponivel"])

    def test_listagem_de_transacoes_pagina_as_mais_recentes(self):
        self.gravar()
        self.gravar()
        pagina = self.cliente.get("/transacoes?inicio=0&limite=1", headers=AUTH).get_json()
        self.assertEqual(pagina["total"], 4)
        self.assertEqual(pagina["itens"][0]["bloco"], 2)
        self.assertEqual(len(pagina["itens"]), 1)
        outra = self.cliente.get("/transacoes?inicio=3&limite=1", headers=AUTH).get_json()
        self.assertEqual(outra["itens"][0]["bloco"], 1)

    def test_simulacao_assina_e_apenas_enfileira(self):
        resposta = self.simular()
        self.assertEqual(resposta.status_code, 202)
        dados = resposta.get_json()
        self.assertTrue(dados["simuladas"])
        self.assertEqual(len(dados["leituras"]), 2)
        self.assertTrue(all(t["versao"] == 3 and len(t["assinatura"]) == 128 for t in dados["leituras"]))
        with Sistema.abrir(self.pasta) as s:
            self.assertEqual(len(s.cadeia.blocos), 1)
        self.assertEqual(self.cliente.post("/blocos", json={}, headers=AUTH).status_code, 201)
        with Sistema.abrir(self.pasta) as s:
            self.assertEqual(s.cadeia.validar(), (True, None))

    def test_simulacao_respeita_revogacao_de_sensor(self):
        self.cliente.post("/membros/sensor-temp-01/revogar", json={}, headers=AUTH)
        resposta = self.simular().get_json()
        self.assertEqual(resposta["sensores_ignorados"], ["sensor-temp-01"])
        self.assertEqual([t["dispositivo"] for t in resposta["leituras"]], ["sensor-umid-01"])
        self.cliente.post("/membros/sensor-umid-01/revogar", json={}, headers=AUTH)
        self.assertEqual(self.simular().status_code, 409)

    def test_simulacao_nao_usa_chave_antiga_apos_rotacao(self):
        from blockchain_tcc.identidade import Identidade
        nova = Identidade("sensor-temp-01")
        self.cliente.put("/membros/sensor-temp-01", json={"pub_hex": nova.pub_hex}, headers=AUTH)
        resposta = self.simular().get_json()
        self.assertEqual(resposta["sensores_ignorados"], ["sensor-temp-01"])

    def test_fila_cheia_nao_publica_lote_parcial(self):
        cliente = create_app(self.pasta, SENHA, TOKEN, modo_apresentacao=True, max_pendentes=1).test_client()
        self.assertEqual(cliente.post("/apresentacao/leituras", json={}, headers=AUTH).status_code, 429)
        self.assertEqual(cliente.get("/estado", headers=AUTH).get_json()["pendentes"], 0)

    def test_pacote_ausente_nao_cria_arquivos(self):
        from blockchain_tcc.identidade import Identidade
        pasta = self.pasta.parent / "sem-pacote"
        with Sistema.criar(pasta, [Identidade("V1")], [], SENHA):
            pass
        cliente = create_app(pasta, SENHA, TOKEN, modo_apresentacao=True).test_client()
        self.assertFalse(cliente.get("/painel/dados", headers=AUTH).get_json()["simulacao_disponivel"])
        self.assertEqual(cliente.post("/apresentacao/leituras", json={}, headers=AUTH).status_code, 409)
        self.assertFalse((pasta / "simulador").exists())

    def test_demonstracao_detecta_alteracao_sem_gravar(self):
        bloco = self.gravar()
        self.simular()
        antes = (self.pasta / "ledger.db").read_bytes()
        resposta = self.executar_copia()
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.get_json()
        self.assertTrue(dados["original_valida"])
        self.assertFalse(dados["copia_valida"])
        self.assertFalse(dados["persistido"])
        self.assertIn("hash", dados["motivo"])
        self.assertEqual(antes, (self.pasta / "ledger.db").read_bytes())
        self.assertEqual(self.cliente.get("/blocos/1", headers=AUTH).get_json(), bloco)
        self.assertEqual(self.cliente.get("/estado", headers=AUTH).get_json()["pendentes"], 2)

    def test_recalculo_do_hash_continua_detectado_pela_assinatura(self):
        self.gravar()
        antes = (self.pasta / "ledger.db").read_bytes()
        dados = self.executar_copia(recalcular=True).get_json()
        self.assertIn("assinatura", dados["motivo"])
        self.assertNotEqual(dados["hash_registrado"], dados["hash_recalculado"])
        self.assertFalse(dados["copia_valida"])
        self.assertEqual(antes, (self.pasta / "ledger.db").read_bytes())

    def test_laboratorio_recusa_indices_e_valores_invalidos(self):
        bloco = self.gravar()
        for indice, valor, recalc in ((0, "99", False), (True, "99", False), (-1, "99", False),
                                     (1, "", False), (1, "99", "sim"), (1, "x" * 4097, False)):
            self.assertEqual(self.executar_copia(indice, valor, recalc).status_code, 400)
        self.assertEqual(self.executar_copia(99).status_code, 404)
        self.assertEqual(self.executar_copia(valor=bloco["transacoes"][0]["valor"]).status_code, 409)
        self.assertEqual(self.cliente.post("/apresentacao/integridade", json={}, headers=AUTH).status_code, 400)

    def test_pacote_de_outra_rede_nao_enfileira(self):
        arquivo = self.pasta / "simulador" / "sensores.json"
        config = json.loads(arquivo.read_text(encoding="utf-8"))
        config["rede_id"] = "0" * 32
        arquivo.write_text(json.dumps(config), encoding="utf-8")
        self.assertEqual(self.simular().status_code, 409)
        self.assertEqual(self.cliente.get("/estado", headers=AUTH).get_json()["pendentes"], 0)

    def test_opcao_de_linha_de_comando_ativa_apresentacao(self):
        with patch("blockchain_tcc.iniciar_api.getpass.getpass", side_effect=[SENHA, TOKEN]), \
                patch("blockchain_tcc.iniciar_api.serve") as servir, redirect_stdout(StringIO()):
            self.assertEqual(main([str(self.pasta), "--apresentacao"]), 0)
        app = servir.call_args.args[0]
        self.assertTrue(app.extensions["blockchain"].modo_apresentacao)


if __name__ == "__main__":
    unittest.main()
