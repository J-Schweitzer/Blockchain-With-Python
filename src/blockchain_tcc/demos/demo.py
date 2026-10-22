"""Demonstração rápida em terminal: grava leituras, adultera e detecta."""
from blockchain_tcc.identidade import DISPOSITIVO, VALIDADOR, Identidade, Registro
from blockchain_tcc.nucleo import Cadeia, Transacao

reg = Registro()
validadores = [Identidade(f"V{i}") for i in (1, 2, 3)]
for v in validadores:
    reg.autorizar(v.nome, v.pub_hex, VALIDADOR)
sensor = Identidade("sensor-temp-01")
reg.autorizar(sensor.nome, sensor.pub_hex, DISPOSITIVO)

cadeia = Cadeia(reg, [v.nome for v in validadores])
for i, valor in enumerate([23.5, 24.1, 23.9]):
    cadeia.adicionar_transacao(Transacao.criar(sensor, valor))
    b = cadeia.produzir_bloco(validadores[i % 3])
    print(f"bloco {b.indice} por {b.validador}  hash={b.hash[:16]}…")

print("cadeia válida?", cadeia.validar())
cadeia.blocos[1].transacoes[0]["valor"] = "99.9"
print("após adulterar o bloco 1:", cadeia.validar())
