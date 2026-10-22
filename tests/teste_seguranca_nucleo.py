"""Regressões de integridade e recuperação da primeira etapa do TCC."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from blockchain_tcc.identidade import Identidade
from blockchain_tcc.armazenamento import Armazenamento
from blockchain_tcc.nucleo import Cadeia, ErroBlockchain, Transacao
from teste_i1_i2 import cenario, grava


class TestSegurancaNucleo(unittest.TestCase):
    def test_assinatura_falsa_em_bloco_existente_e_detectada(self):
        cadeia, vals, sensor, _ = cenario()
        bloco = grava(cadeia, vals[0], sensor, 20)
        bloco.assinatura = Identidade("V1").assinar(bloco.hash.encode())
        self.assertFalse(cadeia.validar()[0])

    def test_chave_falsa_nao_altera_ledger_nem_pendencias(self):
        cadeia, _, sensor, _ = cenario()
        cadeia.adicionar_transacao(Transacao.criar(sensor, 20))
        with self.assertRaises(ErroBlockchain):
            cadeia.produzir_bloco(Identidade("V1"))
        self.assertEqual(len(cadeia.blocos), 1)
        self.assertEqual(len(cadeia.pendentes), 1)
        self.assertEqual(cadeia.validar(), (True, None))

    def test_falha_de_gravacao_preserva_estado_e_permite_repetir(self):
        cadeia, vals, sensor, _ = cenario()
        cadeia.adicionar_transacao(Transacao.criar(sensor, 20))
        with patch.object(cadeia, "armazenamento") as armazenamento:
            armazenamento.salvar_bloco.side_effect = sqlite3.OperationalError("disco cheio")
            with self.assertRaises(ErroBlockchain):
                cadeia.produzir_bloco(vals[0])
        self.assertEqual(len(cadeia.blocos), 1)
        self.assertEqual(len(cadeia.pendentes), 1)
        grava_antes = cadeia.pendentes[0].copy()
        bloco = cadeia.produzir_bloco(vals[0])
        self.assertEqual(bloco.transacoes, [grava_antes])
        self.assertEqual(cadeia.pendentes, [])
        self.assertEqual(cadeia.validar(), (True, None))

    def test_pendente_adulterada_nao_e_confirmada(self):
        cadeia, vals, sensor, _ = cenario()
        cadeia.adicionar_transacao(Transacao.criar(sensor, 20))
        cadeia.pendentes[0]["valor"] = "99"
        with self.assertRaises(ErroBlockchain):
            cadeia.produzir_bloco(vals[0])
        self.assertEqual(len(cadeia.blocos), 1)
        self.assertEqual(len(cadeia.pendentes), 1)

    def test_dispositivo_revogado_antes_da_producao_nao_grava(self):
        cadeia, vals, sensor, registro = cenario()
        cadeia.adicionar_transacao(Transacao.criar(sensor, 20))
        registro.revogar(sensor.nome)
        with self.assertRaises(ErroBlockchain):
            cadeia.produzir_bloco(vals[0])
        self.assertEqual(len(cadeia.blocos), 1)

    def test_genesis_reescrito_com_hash_recalculado_e_recusado(self):
        cadeia, *_ = cenario()
        genesis = cadeia.blocos[0]
        genesis.validador = "intruso"
        genesis.hash = genesis.calcular_hash()
        self.assertFalse(cadeia.validar()[0])

    def test_cadeia_vazia_nao_e_considerada_valida(self):
        cadeia, *_ = cenario()
        cadeia.blocos.clear()
        self.assertFalse(cadeia.validar()[0])

    def test_estrutura_malformada_retorna_diagnostico(self):
        cadeia, vals, sensor, _ = cenario()
        bloco = grava(cadeia, vals[0], sensor, 20)
        bloco.transacoes = [{"dispositivo": sensor.nome}]
        bloco.hash = bloco.calcular_hash()
        bloco.assinatura = vals[0].assinar(bloco.hash.encode())
        ok, erro = cadeia.validar()
        self.assertFalse(ok)
        self.assertIsInstance(erro, str)

    def test_bloco_vazio_assinado_nao_e_valido(self):
        cadeia, vals, sensor, _ = cenario()
        bloco = grava(cadeia, vals[0], sensor, 20)
        bloco.transacoes = []
        bloco.hash = bloco.calcular_hash()
        bloco.assinatura = vals[0].assinar(bloco.hash.encode())
        self.assertFalse(cadeia.validar()[0])

    def test_timestamp_nao_finito_assinado_e_recusado(self):
        cadeia, _, sensor, _ = cenario()
        tx = Transacao(sensor.nome, "20", float("inf"))
        # Representação aceita pela versão original, mas inválida como JSON interoperável.
        tx.assinatura = sensor.assinar(
            b'{"dispositivo":"sensor-temp-01","ts":Infinity,"valor":"20"}'
        )
        with self.assertRaises(ErroBlockchain):
            cadeia.adicionar_transacao(tx)

    def test_cadeia_corrompida_nao_recebe_novo_bloco(self):
        cadeia, vals, sensor, _ = cenario()
        grava(cadeia, vals[0], sensor, 20)
        cadeia.blocos[1].transacoes[0]["valor"] = "99"
        cadeia.adicionar_transacao(Transacao.criar(sensor, 21))
        with self.assertRaises(ErroBlockchain):
            cadeia.produzir_bloco(vals[1])
        self.assertEqual(len(cadeia.blocos), 2)

    def test_carregamento_malformado_gera_erro_da_aplicacao(self):
        _, _, _, registro = cenario()
        with patch("blockchain_tcc.armazenamento.Armazenamento") as armazenamento:
            armazenamento.carregar_blocos.return_value = [{"indice": 0}]
            with self.assertRaises(ErroBlockchain):
                Cadeia(registro, ["V1", "V2", "V3"], armazenamento)


class TestPersistenciaSegura(unittest.TestCase):
    def setUp(self):
        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)
        self.db = Path(temporario.name) / "ledger.db"
        self.arm = self.abrir()
        self.cadeia, self.vals, self.sensor, self.registro = cenario(self.arm)

    def abrir(self):
        arm = Armazenamento(self.db)
        self.addCleanup(arm.fechar)
        return arm

    def test_chave_falsa_nao_e_persistida(self):
        self.cadeia.adicionar_transacao(Transacao.criar(self.sensor, 20))
        with self.assertRaises(ErroBlockchain):
            self.cadeia.produzir_bloco(Identidade("V1"))
        self.assertEqual(len(self.arm.carregar_blocos()), 1)

    def test_rollback_apos_falha_permite_proxima_gravacao(self):
        genesis = self.cadeia.blocos[0].to_dict()
        with self.assertRaises(sqlite3.IntegrityError):
            self.arm.salvar_bloco(genesis)
        self.assertFalse(self.arm._con.in_transaction)
        grava(self.cadeia, self.vals[0], self.sensor, 20)
        self.arm.fechar()
        recarregada = Cadeia(self.registro, [v.nome for v in self.vals], self.abrir())
        self.assertEqual(len(recarregada.blocos), 2)
        self.assertEqual(recarregada.validar(), (True, None))

    def test_json_corrompido_e_recusado_na_reabertura(self):
        with self.arm._con:
            self.arm._con.execute("UPDATE blocos SET dados = '{' WHERE indice = 0")
        with self.assertRaises(ErroBlockchain):
            Cadeia(self.registro, [v.nome for v in self.vals], self.arm)

    def test_indice_sql_divergente_e_recusado_na_reabertura(self):
        grava(self.cadeia, self.vals[0], self.sensor, 20)
        with self.arm._con:
            self.arm._con.execute("UPDATE blocos SET indice = 100 WHERE indice = 1")
        with self.assertRaises(ErroBlockchain):
            Cadeia(self.registro, [v.nome for v in self.vals], self.arm)


if __name__ == "__main__":
    unittest.main()
