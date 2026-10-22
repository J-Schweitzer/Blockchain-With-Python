"""Integração com sockets reais, Waitress e sensor em outro processo."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from flask import jsonify
from waitress.server import create_server

from blockchain_tcc.api import create_app
from blockchain_tcc.cliente_api import ClienteAPI, ErroCliente, main as cliente_main
from blockchain_tcc.iniciar_api import main as servidor_main
from blockchain_tcc.preparar_demo_api import preparar
from blockchain_tcc.simulador_iot import carregar_sensores, simular
from blockchain_tcc.sistema import Sistema

SENHA = "senha-teste-simulador-2026"
TOKEN = "token-administrativo-integracao-http-2026"


class TestSimuladorHTTP(unittest.TestCase):
    def setUp(self):
        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)
        self.pasta = preparar(Path(temporario.name) / "dados", SENHA)
        self.pacote = self.pasta / "simulador"
        self.app = create_app(self.pasta, SENHA, TOKEN, limite_requisicoes=10000)

        @self.app.get("/redirecionar")
        def redirecionar():
            return jsonify(erro={"codigo": "redirecionamento", "mensagem": "Não siga este destino."}), 302, {"Location": "http://127.0.0.1:1/destino"}

        @self.app.get("/erro-incompativel")
        def erro_incompativel():
            return jsonify(erro="formato-errado"), 400

        self.server = create_server(self.app, host="127.0.0.1", port=0, threads=2,
                                    asyncore_loop_timeout=0.02, max_request_body_size=65536)
        self.parar = threading.Event()

        def atender():
            while not self.parar.is_set():
                self.server.asyncore.loop(timeout=0.02, map=self.server._map, count=1)

        self.thread = threading.Thread(target=atender, daemon=True)
        self.thread.start()
        self.addCleanup(self.encerrar)
        self.url = f"http://127.0.0.1:{self.server.effective_port}"
        self.cliente = ClienteAPI(self.url, TOKEN)

    def encerrar(self):
        self.parar.set()
        self.thread.join(3)
        self.server.task_dispatcher.shutdown()
        self.server.close()
        for canal in list(self.server._map.values()):
            canal.close()

    def test_sensor_em_outro_processo_confirma_leituras_via_http(self):
        script = (
            "import json,sys; from unittest.mock import patch; from blockchain_tcc.simulador_iot import main; "
            "d=json.load(sys.stdin); "
            "p=patch('blockchain_tcc.simulador_iot.getpass.getpass',side_effect=[d['senha'],d['token']]); p.start(); "
            "sys.exit(main([sys.argv[1],'--url',sys.argv[2],'--amostras','2','--intervalo','0','--semente','7','--confirmar']))"
        )
        resultado = subprocess.run([sys.executable, "-c", script, str(self.pacote), self.url],
                                   input=json.dumps({"senha": SENHA, "token": TOKEN}),
                                   text=True, encoding="utf-8", capture_output=True, timeout=20,
                                   cwd=Path(__file__).parent,
                                   env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn("4 leituras enviadas; 2 blocos confirmados", resultado.stdout)
        estado = self.cliente.chamar("GET", "/estado", administrativo=True)
        self.assertEqual(estado["transacoes_confirmadas"], 4)
        self.assertEqual(estado["blocos"], 3)
        self.assertTrue(self.cliente.chamar("GET", "/validar", administrativo=True)["valida"])
        for nome, unidade in (("sensor-temp-01", "°C"), ("sensor-umid-01", "%")):
            historico = self.cliente.chamar("GET", "/historico/" + nome, administrativo=True)
            self.assertEqual(historico["total"], 2)
            self.assertEqual(historico["itens"][0]["medicao"]["unidade"], unidade)
        self.assertNotIn(SENHA, resultado.stdout + resultado.stderr)
        self.assertNotIn(TOKEN, resultado.stdout + resultado.stderr)

    def test_sensor_sem_papel_administrativo_somente_enfileira(self):
        sem_token = ClienteAPI(self.url)
        with redirect_stdout(StringIO()):
            resultado = simular(self.pacote, SENHA, sem_token, amostras=1, intervalo=0)
        self.assertEqual(resultado, {"enviados": 2, "blocos": []})
        self.assertEqual(self.cliente.chamar("GET", "/estado", administrativo=True)["pendentes"], 2)
        with self.assertRaises(ErroCliente) as erro:
            ClienteAPI(self.url, "errado").chamar("POST", "/blocos", {}, administrativo=True)
        self.assertEqual(erro.exception.status, 401)
        self.assertEqual(len(self.cliente.chamar("POST", "/blocos", {}, administrativo=True)["transacoes"]), 2)

    def test_servidor_rejeita_replay_enviado_pelo_cliente(self):
        with redirect_stdout(StringIO()):
            simular(self.pacote, SENHA, self.cliente, amostras=1, intervalo=0, confirmar=True)
        bloco = self.cliente.chamar("GET", "/blocos/1", administrativo=True)
        with self.assertRaises(ErroCliente) as erro:
            self.cliente.chamar("POST", "/transacao", bloco["transacoes"][0])
        self.assertEqual(erro.exception.status, 409)
        self.assertEqual(erro.exception.codigo, "replay")

    def test_revogacao_e_respeitada_pelo_ingresso_http(self):
        self.cliente.chamar("POST", "/membros/sensor-temp-01/revogar", {}, administrativo=True)
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            with self.assertRaises(ErroCliente) as erro:
                simular(self.pacote, SENHA, self.cliente, amostras=1, intervalo=0)
        self.assertEqual(erro.exception.status, 422)
        self.assertEqual(self.cliente.chamar("GET", "/estado", administrativo=True)["pendentes"], 0)

    def test_manifesto_somente_contem_chaves_dos_sensores(self):
        config = json.loads((self.pacote / "sensores.json").read_text(encoding="utf-8"))
        self.assertEqual({s["nome"] for s in config["sensores"]}, {"sensor-temp-01", "sensor-umid-01"})
        self.assertEqual(len(list((self.pacote / "chaves").rglob("*.pem"))), 2)
        with Sistema.abrir(self.pasta) as sistema:
            for nome, m in sistema.registro.to_dict().items():
                if m["papel"] == "validador":
                    self.assertFalse((self.pacote / "chaves" / sistema.cofre.caminho(nome, m["pub"]).parent.name / (m["pub"] + ".pem")).exists())

    def test_rede_diferente_e_senha_incorreta_impedem_envio(self):
        cliente = Mock()
        cliente.chamar.return_value = {"rede_id": "0" * 32}
        with self.assertRaises(ValueError):
            simular(self.pacote, SENHA, cliente, amostras=1, intervalo=0)
        cliente.chamar.assert_called_once_with("GET", "/rede")
        cliente.reset_mock()
        with self.assertRaises(ValueError):
            simular(self.pacote, "senha-incorreta-2026", cliente, amostras=1, intervalo=0)
        cliente.chamar.assert_not_called()

    def test_manifesto_e_parametros_invalidos_sao_recusados(self):
        for kwargs in ({"amostras": 0}, {"amostras": 1001}, {"intervalo": -1}, {"intervalo": float("inf")}):
            with self.assertRaises(ValueError):
                simular(self.pacote, SENHA, self.cliente, **kwargs)
        arquivo = self.pacote / "sensores.json"
        config = json.loads(arquivo.read_text(encoding="utf-8"))
        config["sensores"][0]["faixa"] = [30, 20]
        arquivo.write_text(json.dumps(config), encoding="utf-8")
        with self.assertRaises(ValueError):
            carregar_sensores(self.pacote, SENHA)

    def test_cliente_nao_segue_redirecionamento_com_credenciais(self):
        with self.assertRaises(ErroCliente) as erro:
            self.cliente.chamar("GET", "/redirecionar", administrativo=True)
        self.assertEqual(erro.exception.status, 302)
        for url in ("http://example.org", "http://usuario:senha@localhost:5000", "http://localhost:5000/?token=x"):
            with self.assertRaises(ValueError):
                ClienteAPI(url)

    def test_preparacao_nao_sobrescreve_instalacao(self):
        antes = (self.pacote / "sensores.json").read_bytes()
        with self.assertRaises(FileExistsError):
            preparar(self.pasta, SENHA)
        self.assertEqual((self.pacote / "sensores.json").read_bytes(), antes)

    def test_cliente_controla_erro_de_servico_incompativel(self):
        with self.assertRaises(ErroCliente) as erro:
            self.cliente.chamar("GET", "/erro-incompativel", administrativo=True)
        self.assertEqual(erro.exception.codigo, "resposta_invalida")

    def test_comandos_de_servidor_e_consulta_nao_expoem_senhas(self):
        saida = StringIO()
        with patch("blockchain_tcc.iniciar_api.getpass.getpass", side_effect=[SENHA, TOKEN]), \
                patch("blockchain_tcc.iniciar_api.serve") as servir, redirect_stdout(saida):
            self.assertEqual(servidor_main([str(self.pasta)]), 0)
        self.assertEqual(servir.call_args.kwargs["host"], "127.0.0.1")
        with patch("blockchain_tcc.cliente_api.getpass.getpass", return_value=TOKEN), redirect_stdout(saida):
            self.assertEqual(cliente_main(["estado", "--url", self.url]), 0)
        self.assertNotIn(SENHA, saida.getvalue())
        self.assertNotIn(TOKEN, saida.getvalue())


if __name__ == "__main__":
    unittest.main()
