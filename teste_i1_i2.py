"""Testes dos marcos I1 (núcleo) e I2 (permissão e consenso). Rodar: python -m unittest -v"""
import os
import sqlite3
import tempfile
import unittest

from armazenamento import Armazenamento
from identidade import DISPOSITIVO, VALIDADOR, Identidade, Registro
from nucleo import Cadeia, ErroBlockchain, Transacao


def cenario(armazenamento=None):
    reg = Registro()
    vals = [Identidade(f"V{i}") for i in (1, 2, 3)]
    for v in vals:
        reg.autorizar(v.nome, v.pub_hex, VALIDADOR)
    sensor = Identidade("sensor-temp-01")
    reg.autorizar(sensor.nome, sensor.pub_hex, DISPOSITIVO)
    cadeia = Cadeia(reg, [v.nome for v in vals], armazenamento)
    return cadeia, vals, sensor, reg


def grava(cadeia, validador, sensor, valor):
    cadeia.adicionar_transacao(Transacao.criar(sensor, valor))
    return cadeia.produzir_bloco(validador)


class TestNucleo(unittest.TestCase):
    def test_cadeia_nova_e_valida(self):
        cadeia, *_ = cenario()
        self.assertEqual(cadeia.validar(), (True, None))
        self.assertEqual(len(cadeia.blocos), 1)

    def test_blocos_encadeados(self):
        cadeia, vals, sensor, _ = cenario()
        b1 = grava(cadeia, vals[0], sensor, 23.5)
        b2 = grava(cadeia, vals[1], sensor, 24.1)
        self.assertEqual(b2.hash_anterior, b1.hash)
        self.assertTrue(cadeia.validar()[0])

    def test_adulterar_valor_e_detectado(self):
        cadeia, vals, sensor, _ = cenario()
        grava(cadeia, vals[0], sensor, 23.5)
        cadeia.blocos[1].transacoes[0]["valor"] = "99.9"
        ok, erro = cadeia.validar()
        self.assertFalse(ok)
        self.assertIn("hash", erro)

    def test_recalcular_hash_nao_esconde_fraude(self):
        cadeia, vals, sensor, _ = cenario()
        grava(cadeia, vals[0], sensor, 23.5)
        grava(cadeia, vals[1], sensor, 24.1)
        b = cadeia.blocos[1]
        b.transacoes[0]["valor"] = "99.9"
        b.hash = b.calcular_hash()  # atacante recalcula o hash do bloco
        ok, erro = cadeia.validar()
        self.assertFalse(ok)
        self.assertIn("bloco 1", erro)  # assinatura do validador não confere


class TestPermissaoConsenso(unittest.TestCase):
    def test_dispositivo_nao_autorizado_rejeitado(self):
        cadeia, *_ = cenario()
        intruso = Identidade("sensor-falso")
        with self.assertRaises(ErroBlockchain):
            cadeia.adicionar_transacao(Transacao.criar(intruso, 10))

    def test_assinatura_adulterada_rejeitada(self):
        cadeia, _, sensor, _ = cenario()
        tx = Transacao.criar(sensor, 23.5)
        tx.valor = "50"  # alterado depois de assinar
        with self.assertRaises(ErroBlockchain):
            cadeia.adicionar_transacao(tx)

    def test_validador_fora_da_vez_rejeitado(self):
        cadeia, vals, sensor, _ = cenario()
        cadeia.adicionar_transacao(Transacao.criar(sensor, 1))
        with self.assertRaises(ErroBlockchain):
            cadeia.produzir_bloco(vals[1])  # vez de V1

    def test_rodizio_poa(self):
        cadeia, vals, sensor, _ = cenario()
        nomes = [grava(cadeia, vals[i % 3], sensor, i).validador for i in range(4)]
        self.assertEqual(nomes, ["V1", "V2", "V3", "V1"])

    def test_validador_com_chave_falsa_e_detectado(self):
        cadeia, vals, sensor, reg = cenario()
        cadeia.adicionar_transacao(Transacao.criar(sensor, 1))
        falso = Identidade("V1")  # mesmo nome, outra chave
        cadeia.produzir_bloco(falso)
        self.assertFalse(cadeia.validar()[0])

    def test_oraculo_dado_falso_de_sensor_autorizado_e_aceito(self):
        """Limite assumido: a cadeia não sabe se a leitura é verdadeira (problema do oráculo)."""
        cadeia, vals, sensor, _ = cenario()
        grava(cadeia, vals[0], sensor, 999.9)  # leitura absurda, mas assinada por sensor autorizado
        self.assertTrue(cadeia.validar()[0])
        self.assertEqual(cadeia.historico("sensor-temp-01")[0]["valor"], "999.9")

    def test_historico_por_dispositivo(self):
        cadeia, vals, sensor, _ = cenario()
        grava(cadeia, vals[0], sensor, 20)
        grava(cadeia, vals[1], sensor, 21)
        h = cadeia.historico("sensor-temp-01")
        self.assertEqual([x["valor"] for x in h], ["20", "21"])
        self.assertEqual([x["bloco"] for x in h], [1, 2])


class TestPersistencia(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "ledger.db")

    def test_recarrega_cadeia_valida(self):
        arm = Armazenamento(self.db)
        cadeia, vals, sensor, reg = cenario(arm)
        grava(cadeia, vals[0], sensor, 23.5)
        arm.fechar()
        arm2 = Armazenamento(self.db)
        nova = Cadeia(reg, [v.nome for v in vals], arm2)
        self.assertEqual(len(nova.blocos), 2)
        self.assertTrue(nova.validar()[0])

    def test_banco_adulterado_e_recusado(self):
        arm = Armazenamento(self.db)
        cadeia, vals, sensor, reg = cenario(arm)
        grava(cadeia, vals[0], sensor, 23.5)
        arm.fechar()
        con = sqlite3.connect(self.db)
        con.execute("UPDATE blocos SET dados = REPLACE(dados, '23.5', '99.9') WHERE indice = 1")
        con.commit()
        con.close()
        with self.assertRaises(ErroBlockchain):
            Cadeia(reg, [v.nome for v in vals], Armazenamento(self.db))


if __name__ == "__main__":
    unittest.main()
