"""Sensores simulados: assinam localmente e enviam leituras pela API."""
import argparse
import getpass
import json
import math
import random
import sys
import time
from pathlib import Path

from blockchain_tcc.cliente_api import ClienteAPI, ErroCliente
from blockchain_tcc.cofre import CofreChaves
from blockchain_tcc.identidade import DISPOSITIVO, Registro
from blockchain_tcc.nucleo import Transacao


def carregar_sensores(pasta, senha):
    pasta = Path(pasta)
    config = json.loads((pasta / "sensores.json").read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != {"versao", "rede_id", "sensores"}:
        raise ValueError("manifesto de sensores inválido")
    rede = config["rede_id"]
    if (type(config["versao"]) is not int or config["versao"] != 1
            or not isinstance(rede, str) or len(rede) != 32
            or any(c not in "0123456789abcdef" for c in rede)):
        raise ValueError("versão ou identificação de rede inválida")
    if not isinstance(config["sensores"], list) or not 1 <= len(config["sensores"]) <= 100:
        raise ValueError("quantidade de sensores inválida")
    sensores, nomes = [], set()
    for item in config["sensores"]:
        if not isinstance(item, dict) or set(item) != {"nome", "pub_hex", "medicao", "faixa"}:
            raise ValueError("sensor inválido")
        Registro._conferir_membro(item["nome"], item["pub_hex"], DISPOSITIVO)
        if len(item["nome"]) > 128:
            raise ValueError("nome do sensor excede 128 caracteres")
        if item["nome"] in nomes:
            raise ValueError("sensor duplicado no manifesto")
        nomes.add(item["nome"])
        medicao, faixa = item["medicao"], item["faixa"]
        if (not isinstance(medicao, dict) or set(medicao) != {"grandeza", "unidade"}
                or any(not isinstance(v, str) or not v.strip() or len(v) > 64 for v in medicao.values())):
            raise ValueError("grandeza ou unidade inválida")
        try:
            if (not isinstance(faixa, list) or len(faixa) != 2
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in faixa)
                    or faixa[0] > faixa[1]):
                raise ValueError("faixa de valores inválida")
        except OverflowError as exc:
            raise ValueError("faixa de valores inválida") from exc
        identidade = CofreChaves(pasta / "chaves").carregar(item["nome"], item["pub_hex"], senha)
        sensores.append((identidade, medicao, faixa))
    return rede, sensores


def simular(pasta, senha, cliente, *, amostras=5, intervalo=1.0, confirmar=False, semente=None):
    if type(amostras) is not int or not 1 <= amostras <= 1000:
        raise ValueError("amostras deve estar entre 1 e 1000")
    if type(intervalo) not in (int, float) or not math.isfinite(intervalo) or not 0 <= intervalo <= 3600:
        raise ValueError("intervalo deve estar entre 0 e 3600 segundos")
    rede, sensores = carregar_sensores(pasta, senha)
    if cliente.chamar("GET", "/rede")["rede_id"] != rede:
        raise ValueError("o manifesto pertence a outra rede; nenhuma leitura foi enviada")
    gerador = random.Random(semente)
    enviados, blocos = 0, []
    for numero in range(amostras):
        for sensor, medicao, faixa in sensores:
            valor = round(gerador.uniform(*faixa), 2)
            tx = Transacao.criar(sensor, valor, rede, medicao=medicao)
            try:
                recibo = cliente.chamar("POST", "/transacao", tx.to_dict())
            except ErroCliente:
                print(f"Envio não concluído; id_transacao={tx.id_transacao}.", file=sys.stderr)
                raise
            if recibo.get("id_transacao") != tx.id_transacao or recibo.get("situacao") != "pendente":
                raise ValueError("recibo de transação incompatível")
            enviados += 1
            print(f"{sensor.nome}: {valor} {medicao['unidade']} -> pendente ({tx.id_transacao})", flush=True)
        if confirmar:
            bloco = cliente.chamar("POST", "/blocos", {}, administrativo=True)
            blocos.append(bloco["indice"])
            print(f"Bloco {bloco['indice']} confirmado por {bloco['validador']}.", flush=True)
        if numero + 1 < amostras:
            time.sleep(intervalo)
    return {"enviados": enviados, "blocos": blocos}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pasta", help="pacote com sensores.json e chaves cifradas dos sensores")
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    parser.add_argument("--amostras", type=int, default=5, help="ciclos; cada sensor envia uma leitura por ciclo")
    parser.add_argument("--intervalo", type=float, default=1.0)
    parser.add_argument("--semente", type=int)
    parser.add_argument("--confirmar", action="store_true", help="solicita token administrativo e confirma um bloco por ciclo")
    args = parser.parse_args(argv)
    try:
        senha = getpass.getpass("Senha das chaves dos sensores: ")
        token = getpass.getpass("Token administrativo: ") if args.confirmar else None
        resultado = simular(args.pasta, senha, ClienteAPI(args.url, token),
                            amostras=args.amostras, intervalo=args.intervalo,
                            confirmar=args.confirmar, semente=args.semente)
        print(f"Concluído: {resultado['enviados']} leituras enviadas; {len(resultado['blocos'])} blocos confirmados.")
    except (OSError, ValueError, TypeError, ErroCliente) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Simulação interrompida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
