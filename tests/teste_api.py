"""API: assinaturas, autorização, concorrência, estado e limites HTTP."""
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from blockchain_tcc.api import create_app
from blockchain_tcc.identidade import Identidade
from blockchain_tcc.nucleo import Transacao
from blockchain_tcc.sistema import Sistema

SENHA = "senha-dos-testes-http-2026"
TOKEN = "token-administrativo-dos-testes-http-2026"
AUTH = {"Authorization": "Bearer " + TOKEN}
MEDICAO = {"grandeza": "temperatura", "unidade": "°C"}


class TestAPI(unittest.TestCase):
    def setUp(self):
        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)
        self.pasta = Path(temporario.name) / "sistema"
        self.sensor = Identidade("sensor-temp-01")
        with Sistema.criar(self.pasta, [Identidade("V1"), Identidade("V2")], [self.sensor], SENHA) as s:
            self.rede = s.cadeia.rede_id
        self.app = create_app(self.pasta, SENHA, TOKEN, limite_requisicoes=10000)
        self.client = self.app.test_client()

    def tx(self, sensor=None, medicao=MEDICAO):
        return Transacao.criar(sensor or self.sensor, 23.5, self.rede, medicao=medicao)

    def enviar(self, tx=None):
        return self.client.post("/transacao", json=(tx or self.tx()).to_dict())

    def produzir(self):
        return self.client.post("/blocos", json={}, headers=AUTH)

    def test_fluxo_completo_preserva_grandeza_unidade_e_assinatura(self):
        tx = self.tx()
        self.assertEqual(self.enviar(tx).status_code, 202)
        pendente = self.client.get("/transacoes/" + tx.id_transacao, headers=AUTH).get_json()
        self.assertEqual(pendente["situacao"], "pendente")
        resposta = self.produzir()
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.get_json()["transacoes"][0], tx.to_dict())
        self.assertEqual(self.client.get("/validar", headers=AUTH).get_json()["valida"], True)
        historico = self.client.get("/historico/sensor-temp-01", headers=AUTH).get_json()
        self.assertEqual(historico["itens"][0]["medicao"], MEDICAO)
        self.assertEqual(historico["itens"][0]["bloco"], 1)
        self.assertEqual(self.client.get("/estado", headers=AUTH).get_json()["pendentes"], 0)
        with Sistema.abrir(self.pasta) as s:
            self.assertEqual(s.cadeia.validar(), (True, None))

    def test_v2_e_v3_podem_compartilhar_bloco(self):
        self.assertEqual(self.enviar(self.tx(medicao=None)).status_code, 202)
        self.assertEqual(self.enviar().status_code, 202)
        versoes = [t["versao"] for t in self.produzir().get_json()["transacoes"]]
        self.assertEqual(versoes, [2, 3])

    def test_saude_e_rede_publicas_sem_expor_cadastro(self):
        self.assertEqual(self.client.get("/saude").get_json()["status"], "ok")
        resposta = self.client.get("/rede")
        self.assertEqual(resposta.get_json()["rede_id"], self.rede)
        self.assertNotIn("membros", resposta.get_json())
        self.assertEqual(resposta.headers["Cache-Control"], "no-store")
        self.assertNotIn("Access-Control-Allow-Origin", resposta.headers)
        self.assertFalse(self.app.debug)

    def test_consultas_e_administracao_exigem_bearer(self):
        for rota in ("/estado", "/cadeia", "/validar", "/membros", "/pendentes", "/historico/sensor-temp-01"):
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(rota).status_code, 401)
                self.assertEqual(self.client.get(rota, headers={"Authorization": "Bearer errado"}).status_code, 401)
        self.assertEqual(self.client.post("/blocos", json={}).status_code, 401)
        self.assertEqual(self.client.post("/membros", json={}).status_code, 401)
        self.assertEqual(self.client.delete("/pendentes/id").status_code, 401)
        self.assertEqual(self.client.get("/estado", headers={"Authorization": "Basic " + TOKEN}).status_code, 401)
        self.assertEqual(self.client.get("/estado?token=" + TOKEN, headers=AUTH).status_code, 400)

    def test_corpos_malformados_ou_excessivos_nao_entram_na_fila(self):
        casos = [self.client.post("/transacao", json=[]),
                 self.client.post("/transacao", json={"chave_privada": "nao-permitida"}),
                 self.client.post("/transacao", data="{", content_type="application/json"),
                 self.client.post("/transacao", data="{}", content_type="text/plain"),
                 self.client.post("/transacao", data="x" * 65537, content_type="application/json")]
        self.assertEqual([r.status_code for r in casos], [400, 400, 400, 415, 413])
        self.assertEqual(self.client.get("/estado", headers=AUTH).get_json()["pendentes"], 0)

    def test_assinatura_protege_valor_e_metadados(self):
        for alterar in (lambda t: setattr(t, "valor", "99"),
                        lambda t: t.medicao.update(unidade="K")):
            tx = self.tx()
            alterar(tx)
            self.assertEqual(self.enviar(tx).status_code, 422)
        self.assertEqual(self.enviar(self.tx(Identidade("intruso"))).status_code, 422)
        tx = self.tx()
        tx.rede_id = "outra"
        tx.assinatura = self.sensor.assinar(tx.conteudo())
        self.assertEqual(self.enviar(tx).status_code, 422)

    def test_schema_de_medicao_invalido_mesmo_assinado_e_rejeitado(self):
        for medicao in (None, {}, {"grandeza": "temperatura"},
                        {"grandeza": "", "unidade": "°C"}, {"grandeza": 1, "unidade": "°C"}):
            tx = self.tx()
            tx.medicao = medicao
            tx.assinatura = self.sensor.assinar(tx.conteudo())
            self.assertEqual(self.enviar(tx).status_code, 422)

    def test_texto_utf8_invalido_nao_gera_erro_interno(self):
        dados = self.tx().to_dict()
        dados["valor"] = "\ud800"
        resposta = self.client.post("/transacao", data=json.dumps(dados), content_type="application/json")
        self.assertEqual(resposta.status_code, 400)

    def test_replay_na_fila_no_banco_e_apos_reabrir_api(self):
        tx = self.tx()
        self.assertEqual(self.enviar(tx).status_code, 202)
        self.assertEqual(self.enviar(tx).status_code, 409)
        self.assertEqual(self.produzir().status_code, 201)
        self.assertEqual(self.enviar(tx).get_json()["erro"]["codigo"], "replay")
        nova = create_app(self.pasta, SENHA, TOKEN).test_client()
        self.assertEqual(nova.post("/transacao", json=tx.to_dict()).status_code, 409)

    def test_revogacao_bloqueia_pendencia_sem_apagar_outras(self):
        outro = Identidade("sensor-outro")
        self.assertEqual(self.client.post("/membros", json={"nome": outro.nome, "pub_hex": outro.pub_hex}, headers=AUTH).status_code, 201)
        tx = self.tx()
        self.enviar(tx)
        self.enviar(self.tx(outro))
        self.assertEqual(self.client.post("/membros/sensor-temp-01/revogar", json={}, headers=AUTH).status_code, 200)
        self.assertEqual(self.produzir().status_code, 422)
        self.assertEqual(self.enviar().status_code, 422)
        self.assertEqual(self.client.delete("/pendentes/" + tx.id_transacao, headers=AUTH).status_code, 200)
        bloco = self.produzir()
        self.assertEqual(bloco.status_code, 201)
        self.assertEqual(len(bloco.get_json()["transacoes"]), 1)
        self.assertEqual(bloco.get_json()["transacoes"][0]["dispositivo"], outro.nome)

    def test_rotacao_publica_preserva_registros_confirmados(self):
        self.enviar()
        self.produzir()
        novo = Identidade(self.sensor.nome)
        self.assertEqual(self.client.put("/membros/sensor-temp-01", json={"pub_hex": novo.pub_hex}, headers=AUTH).status_code, 200)
        self.assertEqual(self.enviar().status_code, 422)
        self.assertEqual(self.enviar(self.tx(novo)).status_code, 202)
        self.assertEqual(self.produzir().status_code, 201)
        self.assertTrue(self.client.get("/validar", headers=AUTH).get_json()["valida"])

    def test_cadastro_recusa_segredos_e_sobrescrita_implicita(self):
        dados = {"nome": "novo", "pub_hex": Identidade("novo").pub_hex}
        self.assertEqual(self.client.post("/membros", json={**dados, "chave_privada": "segredo"}, headers=AUTH).status_code, 400)
        self.assertEqual(self.client.post("/membros", json=dados, headers=AUTH).status_code, 201)
        self.assertEqual(self.client.post("/membros", json=dados, headers=AUTH).status_code, 409)
        self.assertEqual(self.client.put("/membros/V1", json={"pub_hex": dados["pub_hex"]}, headers=AUTH).status_code, 422)
        self.assertEqual(self.client.post("/membros", json={"nome": "invalido", "pub_hex": "00"}, headers=AUTH).status_code, 400)

    def test_ultima_autoridade_e_preservada(self):
        self.assertEqual(self.client.post("/membros/V1/revogar", json={}, headers=AUTH).status_code, 200)
        self.assertEqual(self.client.post("/membros/V2/revogar", json={}, headers=AUTH).status_code, 422)
        self.enviar()
        self.assertEqual(self.produzir().get_json()["validador"], "V2")

    def test_paginacao_e_recursos_ausentes(self):
        for query in ("limite=0", "limite=101", "inicio=-1", "inicio=abc", "limite=2&limite=3", "campo=1"):
            self.assertEqual(self.client.get("/cadeia?" + query, headers=AUTH).status_code, 400)
        self.assertEqual(len(self.client.get("/cadeia?limite=1", headers=AUTH).get_json()["itens"]), 1)
        self.assertEqual(self.client.get("/cadeia?inicio=100", headers=AUTH).get_json()["itens"], [])
        for rota in ("/blocos/99", "/transacoes/ausente", "/historico/ausente", "/inexistente"):
            self.assertEqual(self.client.get(rota, headers=AUTH).status_code, 404)
        self.assertEqual(self.client.delete("/pendentes/ausente", headers=AUTH).status_code, 404)
        self.assertEqual(self.produzir().status_code, 409)

    def test_fila_limitada_mantem_transacao_anterior(self):
        cliente = create_app(self.pasta, SENHA, TOKEN, max_pendentes=1).test_client()
        self.assertEqual(cliente.post("/transacao", json=self.tx().to_dict()).status_code, 202)
        self.assertEqual(cliente.post("/transacao", json=self.tx().to_dict()).status_code, 429)
        self.assertEqual(cliente.get("/estado", headers=AUTH).get_json()["pendentes"], 1)

    def test_limite_de_requisicoes_nao_confia_em_ip_forjado(self):
        cliente = create_app(self.pasta, SENHA, TOKEN, limite_requisicoes=2).test_client()
        self.assertEqual(cliente.get("/saude").status_code, 200)
        self.assertEqual(cliente.get("/saude").status_code, 200)
        resposta = cliente.get("/saude", headers={"X-Forwarded-For": "1.2.3.4"})
        self.assertEqual(resposta.status_code, 429)
        self.assertEqual(resposta.headers["Retry-After"], "60")

    def test_pendencias_sao_volateis_e_confirmados_sao_recuperados(self):
        tx = self.tx()
        self.enviar(tx)
        self.produzir()
        self.enviar()
        nova = create_app(self.pasta, SENHA, TOKEN).test_client()
        estado = nova.get("/estado", headers=AUTH).get_json()
        self.assertEqual(estado["pendentes"], 0)
        self.assertEqual(estado["transacoes_confirmadas"], 1)

    def test_concorrencia_nao_compartilha_conexoes_sqlite(self):
        transacoes = [self.tx().to_dict() for _ in range(12)]
        def enviar(dados):
            with self.app.test_client() as cliente:
                return cliente.post("/transacao", json=dados).status_code
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(enviar, transacoes)), [202] * 12)
        self.assertEqual(len(self.produzir().get_json()["transacoes"]), 12)
        self.assertTrue(self.client.get("/validar", headers=AUTH).get_json()["valida"])

    def test_replay_concorrente_tem_uma_unica_aceitacao(self):
        tx = self.tx().to_dict()
        def enviar(_):
            with self.app.test_client() as cliente:
                return cliente.post("/transacao", json=tx).status_code
        with ThreadPoolExecutor(max_workers=4) as pool:
            codigos = list(pool.map(enviar, range(8)))
        self.assertEqual(codigos.count(202), 1)
        self.assertEqual(codigos.count(409), 7)

    def test_banco_adulterado_falha_sem_reinicializar(self):
        self.enviar()
        self.produzir()
        with sqlite3.connect(self.pasta / "ledger.db") as con:
            con.execute("UPDATE blocos SET dados = REPLACE(dados, '23.5', '99.9') WHERE indice = 1")
        con.close()
        resposta = self.client.get("/validar", headers=AUTH)
        self.assertEqual(resposta.status_code, 503)
        self.assertEqual(resposta.get_json()["erro"]["codigo"], "estado_indisponivel")

    def test_respostas_nao_expoem_segredos(self):
        self.enviar()
        self.produzir()
        for rota in ("/membros", "/cadeia", "/estado"):
            dados = self.client.get(rota, headers=AUTH).get_data(as_text=True)
            for segredo in (SENHA, TOKEN, self.sensor.exportar_privada(), "PRIVATE KEY"):
                self.assertNotIn(segredo, dados)

    def test_inicializacao_recusa_token_fraco_e_senha_incorreta(self):
        with self.assertRaises(ValueError):
            create_app(self.pasta, SENHA, "curto")
        with self.assertRaises(ValueError):
            create_app(self.pasta, "senha-incorreta-2026", TOKEN)
        with self.assertRaises(ValueError):
            create_app(self.pasta, SENHA, TOKEN, max_pendentes=0)


if __name__ == "__main__":
    unittest.main()
