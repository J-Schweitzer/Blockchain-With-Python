"""Inicia o serviço local com Waitress, sem depurador ou recarregamento."""
import argparse
import getpass
import sys

from waitress import serve

from blockchain_tcc.api import create_app
from blockchain_tcc.nucleo import ErroBlockchain


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pasta", help="instalação criada na etapa 2 ou por preparar_demo_api.py")
    parser.add_argument("--porta", type=int, default=5000)
    parser.add_argument("--apresentacao", action="store_true", help="habilita geração local de leituras e laboratório em cópia")
    args = parser.parse_args(argv)
    if not 1024 <= args.porta <= 65535:
        parser.error("use uma porta entre 1024 e 65535")
    try:
        senha = getpass.getpass("Senha das chaves dos validadores: ")
        token = getpass.getpass("Token administrativo (32 a 256 caracteres, sem espaços): ")
        app = create_app(args.pasta, senha, token, modo_apresentacao=args.apresentacao)
        del senha, token
        print(f"API disponível em http://127.0.0.1:{args.porta}; Ctrl+C para encerrar.", flush=True)
        print(f"Painel: http://127.0.0.1:{args.porta}/painel", flush=True)
        serve(app, host="127.0.0.1", port=args.porta, threads=4,
              max_request_body_size=65536, channel_timeout=30, ident="blockchain-tcc")
    except (ValueError, OSError, ErroBlockchain) as exc:
        print(f"Erro ao iniciar: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
