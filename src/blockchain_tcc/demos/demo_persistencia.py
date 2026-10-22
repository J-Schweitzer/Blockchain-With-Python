"""Roteiro da etapa 2 em execuções separadas. Nunca grava a senha."""
import argparse
import getpass
import json
import sqlite3
import sys
from pathlib import Path

from blockchain_tcc.identidade import Identidade
from blockchain_tcc.nucleo import ErroBlockchain, Transacao
from blockchain_tcc.sistema import Sistema

SENSOR = "sensor-temp-01"


def verificar(pasta):
    with Sistema.abrir(pasta) as sistema:
        ok, erro = sistema.cadeia.validar()
        print(f"Cadeia válida: {ok}; blocos: {len(sistema.cadeia.blocos)} (inclui gênese).")
        print(f"Validadores cadastrados: {', '.join(sistema.cadeia.validadores)}.")
        ativo = sistema.registro.to_dict().get(SENSOR, {}).get("ativo", False)
        print(f"Sensor da demonstração ativo: {ativo}.")
        print(f"Leituras no histórico: {len(sistema.cadeia.historico(SENSOR))}.")
        if not ok:
            raise ErroBlockchain(erro)


def criar(pasta, senha):
    validadores = [Identidade(f"V{i}") for i in (1, 2, 3)]
    with Sistema.criar(pasta, validadores, [Identidade(SENSOR)], senha) as sistema:
        tx = sistema.criar_transacao(SENSOR, 23.5, senha)
        sistema.cadeia.adicionar_transacao(tx)
        sistema.produzir_bloco(senha)
        # Recibo público da transação, usado para demonstrar replay na próxima execução.
        (sistema.pasta / "transacao_demonstracao.json").write_text(
            json.dumps(tx.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print("Sistema criado; primeira leitura confirmada e chaves cifradas.")
    verificar(pasta)


def continuar(pasta, senha):
    with Sistema.abrir(pasta) as sistema:
        if not sistema.registro.to_dict().get(SENSOR, {}).get("ativo"):
            raise ErroBlockchain("a demonstração já revogou o sensor; use verificar ou crie outra pasta")
        sensor = sistema.carregar_identidade(SENSOR, senha)
        dados = (sistema.pasta / "transacao_demonstracao.json").read_text(encoding="utf-8")
        tx = Transacao.from_dict(json.loads(dados))
        try:
            sistema.cadeia.adicionar_transacao(tx)
        except ErroBlockchain as exc:
            if "repetida" not in str(exc):
                raise
            print("Replay após reiniciar: rejeitado.")
        else:
            raise ErroBlockchain("o recibo não corresponde a uma transação confirmada")
        nova = sistema.criar_transacao(SENSOR, 24.1, senha)
        sistema.cadeia.adicionar_transacao(nova)
        sistema.produzir_bloco(senha)
        print("Nova leitura assinada com chave recuperada: confirmada.")
        sistema.revogar(SENSOR)
        falsa = Transacao.criar(sensor, 999.9, sistema.cadeia.rede_id)
        try:
            sistema.cadeia.adicionar_transacao(falsa)
        except ErroBlockchain:
            print("Nova operação do sensor revogado: rejeitada.")
        else:
            raise ErroBlockchain("a revogação não foi aplicada")
    verificar(pasta)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=("criar", "continuar", "verificar"))
    parser.add_argument("pasta", type=Path, help="pasta de dados da demonstração")
    args = parser.parse_args(argv)
    try:
        if args.acao == "verificar":
            verificar(args.pasta)
        else:
            senha = getpass.getpass("Senha das chaves (mínimo 12 caracteres): ")
            if args.acao == "criar":
                if senha != getpass.getpass("Confirme a senha: "):
                    raise ValueError("as senhas não coincidem")
                criar(args.pasta, senha)
            else:
                continuar(args.pasta, senha)
    except (ErroBlockchain, ValueError, OSError, sqlite3.Error) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
