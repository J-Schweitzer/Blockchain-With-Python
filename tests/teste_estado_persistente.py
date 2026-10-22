"""Integração da etapa 2: reinício real, chaves, cadastro e anti-replay."""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from blockchain_tcc.identidade import DISPOSITIVO, VALIDADOR, Identidade
from blockchain_tcc.nucleo import Bloco, ErroBlockchain, Transacao
from blockchain_tcc.sistema import Sistema
from blockchain_tcc.demos.demo_persistencia import main

SENHA = "senha-apenas-para-testes-2026"


class TestEstadoPersistente(unittest.TestCase):
    def setUp(self):
        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)
        self.raiz = Path(temporario.name)
        self.pasta = self.raiz / "sistema"
        self.validadores = [Identidade(f"V{i}") for i in (1, 2, 3)]
        self.sensor = Identidade("sensor-temp-01")
        self.sistema = Sistema.criar(self.pasta, self.validadores, [self.sensor], SENHA)
        self.addCleanup(self.sistema.fechar)

    def reabrir(self):
        self.sistema.fechar()
        self.sistema = Sistema.abrir(self.pasta)
        self.addCleanup(self.sistema.fechar)
        return self.sistema

    def gravar(self, valor=23.5):
        tx = self.sistema.criar_transacao(self.sensor.nome, valor, SENHA)
        self.sistema.cadeia.adicionar_transacao(tx)
        self.sistema.produzir_bloco(SENHA)
        return tx

    def test_reinicio_recupera_cadeia_cadastro_rede_e_validadores(self):
        self.gravar()
        rede = self.sistema.cadeia.rede_id
        cadastro = self.sistema.registro.exportar_estado()
        self.reabrir()
        self.assertEqual(self.sistema.cadeia.rede_id, rede)
        self.assertEqual(self.sistema.registro.exportar_estado(), cadastro)
        self.assertEqual(self.sistema.cadeia.validadores, ["V1", "V2", "V3"])
        self.assertEqual(self.sistema.cadeia.historico(self.sensor.nome)[0]["valor"], "23.5")
        self.gravar(24)
        self.assertEqual(len(self.sistema.cadeia.blocos), 3)
        self.assertEqual(self.sistema.cadeia.validar(), (True, None))

    def test_replay_na_fila_e_rejeitado(self):
        tx = self.sistema.criar_transacao(self.sensor.nome, 20, SENHA)
        self.sistema.cadeia.adicionar_transacao(tx)
        with self.assertRaisesRegex(ErroBlockchain, "repetida"):
            self.sistema.cadeia.adicionar_transacao(Transacao.from_dict(tx.to_dict()))
        self.assertEqual(len(self.sistema.cadeia.pendentes), 1)

    def test_replay_confirmado_e_rejeitado_apos_reinicio(self):
        tx = self.gravar()
        self.reabrir()
        with self.assertRaisesRegex(ErroBlockchain, "repetida"):
            self.sistema.cadeia.adicionar_transacao(tx)

    def test_id_alterado_sem_nova_assinatura_e_rejeitado(self):
        tx = self.gravar()
        tx.id_transacao = "0" * 32
        with self.assertRaises(ErroBlockchain):
            self.sistema.cadeia.adicionar_transacao(tx)

    def test_transacao_sem_identificador_nao_recebe_id_automatico_ao_ler(self):
        dados = self.sistema.criar_transacao(self.sensor.nome, 20, SENHA).to_dict()
        del dados["id_transacao"]
        with self.assertRaises(ValueError):
            Transacao.from_dict(dados)

    def test_replay_inserido_diretamente_na_fila_nao_e_gravado(self):
        tx = self.gravar()
        self.sistema.cadeia.pendentes.append(tx.to_dict())
        with self.assertRaisesRegex(ErroBlockchain, "repetida"):
            self.sistema.produzir_bloco(SENHA)
        self.assertEqual(len(self.sistema.armazenamento.carregar_blocos()), 2)

    def test_replay_em_bloco_assinado_e_detectado_na_validacao(self):
        tx = self.gravar()
        self.gravar(24)
        b = self.sistema.cadeia.blocos[2]
        b.transacoes = [tx.to_dict()]
        b.hash = b.calcular_hash()
        b.assinatura = self.validadores[1].assinar(b.hash.encode())
        self.assertIn("repetida", self.sistema.cadeia.validar()[1])

    def test_transacao_de_outra_rede_e_rejeitada_mesmo_com_a_mesma_chave(self):
        tx = self.gravar()
        with Sistema.criar(self.raiz / "outra", self.validadores, [self.sensor], SENHA) as outra:
            with self.assertRaises(ErroBlockchain):
                outra.cadeia.adicionar_transacao(tx)

    def test_revogacao_preserva_historico_e_bloqueia_dado_retrodatado(self):
        self.gravar()
        self.sistema.revogar(self.sensor.nome)
        tx = Transacao.criar(self.sensor, 21, self.sistema.cadeia.rede_id)
        tx.ts = 1.0
        tx.assinatura = self.sensor.assinar(tx.conteudo())
        with self.assertRaises(ErroBlockchain):
            self.sistema.cadeia.adicionar_transacao(tx)
        self.reabrir()
        self.assertEqual(self.sistema.cadeia.validar(), (True, None))
        with self.assertRaises(ErroBlockchain):
            self.sistema.carregar_identidade(self.sensor.nome, SENHA)

    def test_snapshot_antigo_nao_autoriza_novo_bloco_apos_revogacao(self):
        self.gravar()
        cadastro_antigo = self.sistema.cadeia.blocos[1].registro_hash
        self.sistema.revogar(self.sensor.nome)
        tx = Transacao.criar(self.sensor, 24, self.sistema.cadeia.rede_id)
        b = Bloco(2, 1.0, [tx.to_dict()], self.sistema.cadeia.blocos[-1].hash, "V2",
                  registro_hash=cadastro_antigo, rede_id=self.sistema.cadeia.rede_id)
        b.hash = b.calcular_hash()
        b.assinatura = self.validadores[1].assinar(b.hash.encode())
        self.sistema.cadeia.blocos.append(b)
        self.assertIn("cadastro", self.sistema.cadeia.validar()[1])

    def test_rotacao_de_sensor_preserva_assinaturas_antigas(self):
        self.gravar()
        novo = Identidade(self.sensor.nome)
        self.sistema.autorizar(novo, DISPOSITIVO, SENHA)
        with self.assertRaises(ErroBlockchain):
            self.sistema.cadeia.adicionar_transacao(
                Transacao.criar(self.sensor, 99, self.sistema.cadeia.rede_id)
            )
        self.gravar(24)
        self.reabrir()
        self.assertEqual(self.sistema.carregar_identidade(novo.nome, SENHA).pub_hex, novo.pub_hex)
        self.assertEqual(self.sistema.cadeia.validar(), (True, None))

    def test_rotacao_de_validador_preserva_blocos_anteriores(self):
        self.gravar()
        novo = Identidade("V1")
        self.sistema.autorizar(novo, VALIDADOR, SENHA)
        self.gravar(24)
        self.gravar(25)
        tx = self.sistema.criar_transacao(self.sensor.nome, 26, SENHA)
        self.sistema.cadeia.adicionar_transacao(tx)
        with self.assertRaises(ErroBlockchain):
            self.sistema.cadeia.produzir_bloco(self.validadores[0])
        self.sistema.produzir_bloco(SENHA)
        self.reabrir()
        self.assertEqual(self.sistema.cadeia.validar(), (True, None))

    def test_validador_revogado_sai_do_rodizio_sem_invalidar_historico(self):
        self.gravar()
        self.sistema.revogar("V1")
        self.assertNotEqual(self.sistema.cadeia.validador_da_vez(2), "V1")
        self.gravar(24)
        self.reabrir()
        self.assertEqual(self.sistema.cadeia.validar(), (True, None))

    def test_ultima_autoridade_ativa_nao_pode_ser_revogada(self):
        self.sistema.revogar("V1")
        self.sistema.revogar("V2")
        antes = self.sistema.registro.exportar_estado()
        with self.assertRaises(ErroBlockchain):
            self.sistema.revogar("V3")
        self.assertEqual(self.sistema.registro.exportar_estado(), antes)
        self.reabrir()
        self.gravar()

    def test_cadastro_adulterado_e_detectado_por_hash_do_bloco(self):
        self.gravar()
        config = self.sistema.armazenamento.carregar_configuracao()
        config["registro"][-1]["membros"][self.sensor.nome]["pub"] = Identidade("falso").pub_hex
        with self.sistema.armazenamento._con:
            self.sistema.armazenamento._con.execute(
                "UPDATE configuracao SET dados = ?", (json.dumps(config),)
            )
        self.sistema.fechar()
        with self.assertRaises(ErroBlockchain):
            Sistema.abrir(self.pasta)

    def test_falha_ao_persistir_revogacao_nao_muda_memoria(self):
        antes = self.sistema.registro.exportar_estado()
        with patch.object(self.sistema.armazenamento, "atualizar_registro",
                          side_effect=sqlite3.OperationalError("disco cheio")):
            with self.assertRaises(ErroBlockchain):
                self.sistema.revogar(self.sensor.nome)
        self.assertEqual(self.sistema.registro.exportar_estado(), antes)
        self.reabrir()
        self.gravar()

    def test_mudanca_da_ordem_dos_validadores_e_detectada(self):
        self.gravar()
        config = self.sistema.armazenamento.carregar_configuracao()
        config["validadores"] = ["V1", "V3", "V2"]
        with self.sistema.armazenamento._con:
            self.sistema.armazenamento._con.execute(
                "UPDATE configuracao SET dados = ?", (json.dumps(config),)
            )
        self.sistema.fechar()
        with self.assertRaises(ErroBlockchain):
            Sistema.abrir(self.pasta)

    def test_inicializacao_falha_nao_publica_estado_incompleto(self):
        destino = self.raiz / "incompleto"
        with patch("blockchain_tcc.sistema.CofreChaves.salvar", side_effect=OSError("disco cheio")):
            with self.assertRaises(OSError):
                Sistema.criar(destino, self.validadores, [self.sensor], SENHA)
        self.assertFalse(destino.exists())

    def test_publicacao_recupera_bloqueio_transitorio_do_windows(self):
        destino = self.raiz / "transitorio"
        renomear = Path.rename
        tentativas = []

        def intermitente(origem, alvo):
            tentativas.append(origem)
            if len(tentativas) == 1:
                raise PermissionError("arquivo temporariamente em uso")
            return renomear(origem, alvo)

        with patch("blockchain_tcc.sistema.Path.rename", intermitente):
            with Sistema.criar(destino, self.validadores, [self.sensor], SENHA) as novo:
                self.assertEqual(novo.cadeia.validar(), (True, None))
        self.assertGreaterEqual(len(tentativas), 2)

    def test_instancia_desatualizada_nao_sobrescreve_cadastro(self):
        with Sistema.abrir(self.pasta) as antiga:
            self.gravar()
            with self.assertRaises(ErroBlockchain):
                antiga.revogar(self.sensor.nome)
        self.assertTrue(self.sistema.registro.to_dict()[self.sensor.nome]["ativo"])

    def test_instancia_com_cadastro_antigo_nao_confirma_bloco(self):
        with Sistema.abrir(self.pasta) as antiga:
            tx = antiga.criar_transacao(self.sensor.nome, 20, SENHA)
            antiga.cadeia.adicionar_transacao(tx)
            self.sistema.revogar(self.sensor.nome)
            with self.assertRaises(ErroBlockchain):
                antiga.produzir_bloco(SENHA)
            self.assertEqual(len(antiga.cadeia.pendentes), 1)
        self.reabrir()
        self.assertEqual(len(self.sistema.cadeia.blocos), 1)

    def test_senha_incorreta_nao_carrega_chave(self):
        with self.assertRaises(ValueError):
            self.sistema.carregar_identidade(self.sensor.nome, "senha-incorreta-2026")
        self.assertEqual(self.sistema.carregar_identidade(self.sensor.nome, SENHA).pub_hex,
                         self.sensor.pub_hex)

    def test_cofre_cifra_sem_sobrescrever_arquivo_existente(self):
        caminho = self.sistema.cofre.caminho(self.sensor.nome, self.sensor.pub_hex)
        antes = caminho.read_bytes()
        self.assertIn(b"BEGIN ENCRYPTED PRIVATE KEY", antes)
        self.assertNotIn(self.sensor.exportar_privada().encode(), antes)
        self.assertNotIn(SENHA.encode(), (self.pasta / "ledger.db").read_bytes())
        with self.assertRaises(FileExistsError):
            self.sistema.cofre.salvar(self.sensor, SENHA)
        self.assertEqual(caminho.read_bytes(), antes)

    def test_chave_substituida_por_outra_chave_valida_e_recusada(self):
        falso = Identidade(self.sensor.nome)
        caminho_falso = self.sistema.cofre.salvar(falso, SENHA)
        caminho_original = self.sistema.cofre.caminho(self.sensor.nome, self.sensor.pub_hex)
        caminho_original.write_bytes(caminho_falso.read_bytes())
        with self.assertRaises(ValueError):
            self.sistema.carregar_identidade(self.sensor.nome, SENHA)

    def test_falha_ao_gravar_chave_remove_apenas_arquivo_parcial(self):
        sensor = Identidade("sensor-novo")
        with patch("blockchain_tcc.cofre.os.fsync", side_effect=OSError("disco cheio")):
            with self.assertRaises(OSError):
                self.sistema.autorizar(sensor, DISPOSITIVO, SENHA)
        self.assertFalse(self.sistema.cofre.caminho(sensor.nome, sensor.pub_hex).exists())
        self.assertNotIn(sensor.nome, self.sistema.registro.to_dict())
        self.sistema.autorizar(sensor, DISPOSITIVO, SENHA)
        self.assertEqual(self.sistema.carregar_identidade(sensor.nome, SENHA).pub_hex, sensor.pub_hex)

    def test_nome_de_sensor_nao_se_torna_caminho_de_arquivo(self):
        sensor = Identidade("../../sensor")
        self.sistema.autorizar(sensor, DISPOSITIVO, SENHA)
        caminho = self.sistema.cofre.caminho(sensor.nome, sensor.pub_hex)
        self.assertTrue(caminho.resolve().is_relative_to((self.pasta / "chaves").resolve()))

    def test_abrir_ausente_nao_cria_banco_silenciosamente(self):
        pasta = self.raiz / "ausente"
        with self.assertRaises(FileNotFoundError):
            Sistema.abrir(pasta)
        self.assertFalse(pasta.exists())

    def test_criar_nao_sobrescreve_sistema_existente(self):
        self.gravar()
        with self.assertRaises(FileExistsError):
            Sistema.criar(self.pasta, self.validadores, [self.sensor], SENHA)
        self.reabrir()
        self.assertEqual(len(self.sistema.cadeia.blocos), 2)

    def test_senha_fraca_nao_publica_pasta(self):
        pasta = self.raiz / "fraco"
        with self.assertRaises(ValueError):
            Sistema.criar(pasta, self.validadores, [self.sensor], "123")
        self.assertFalse(pasta.exists())

    def test_banco_ilegivel_e_recusado_sem_deixar_conexao_aberta(self):
        pasta = self.raiz / "ilegivel"
        pasta.mkdir()
        arquivo = pasta / "ledger.db"
        antes = b"arquivo sem formato SQLite"
        arquivo.write_bytes(antes)
        with self.assertRaises(ErroBlockchain):
            Sistema.abrir(pasta)
        self.assertEqual(arquivo.read_bytes(), antes)
        arquivo.rename(pasta / "original.db")

    def test_ledger_legado_e_recusado_sem_reescrever_arquivo(self):
        pasta = self.raiz / "legado"
        pasta.mkdir()
        arquivo = pasta / "ledger.db"
        with sqlite3.connect(arquivo) as con:
            con.execute("CREATE TABLE blocos (indice INTEGER PRIMARY KEY, dados TEXT NOT NULL)")
            con.execute("INSERT INTO blocos VALUES (0, '{}')")
        con.close()
        antes = arquivo.read_bytes()
        with self.assertRaisesRegex(ErroBlockchain, "migração explícita"):
            Sistema.abrir(pasta)
        self.assertEqual(arquivo.read_bytes(), antes)

    def test_processo_independente_recupera_e_valida_ledger(self):
        self.gravar()
        self.sistema.fechar()
        resultado = subprocess.run(
            [sys.executable, "-m", "blockchain_tcc.demos.demo_persistencia",
             "verificar", str(self.pasta)], capture_output=True, text=True,
            encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=15,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn("Cadeia válida: True", resultado.stdout)
        self.assertIn("Leituras no histórico: 1", resultado.stdout)

    def test_roteiro_completo_da_demonstracao(self):
        pasta = self.raiz / "demonstracao"
        saida = StringIO()
        with patch("blockchain_tcc.demos.demo_persistencia.getpass.getpass", return_value=SENHA), redirect_stdout(saida):
            self.assertEqual(main(["criar", str(pasta)]), 0)
            self.assertEqual(main(["continuar", str(pasta)]), 0)
            self.assertEqual(main(["verificar", str(pasta)]), 0)
        self.assertIn("Replay após reiniciar: rejeitado", saida.getvalue())
        with Sistema.abrir(pasta) as sistema:
            self.assertEqual(len(sistema.cadeia.blocos), 3)
            self.assertEqual(sistema.cadeia.validar(), (True, None))
            self.assertFalse(sistema.registro.to_dict()[self.sensor.nome]["ativo"])


if __name__ == "__main__":
    unittest.main()
