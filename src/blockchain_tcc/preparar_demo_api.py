"""Prepara três validadores e dois sensores para a demonstração HTTP local."""
import argparse
import getpass
import json
import sys
import tempfile
from pathlib import Path

from blockchain_tcc.cofre import CofreChaves, senha_bytes
from blockchain_tcc.identidade import Identidade
from blockchain_tcc.nucleo import ErroBlockchain
from blockchain_tcc.sistema import Sistema, publicar_pasta


def preparar(pasta, senha):
    senha_bytes(senha)
    destino = Path(pasta).resolve()
    if destino.exists():
        raise FileExistsError("a pasta já existe; escolha uma nova pasta para esta demonstração")
    destino.parent.mkdir(parents=True, exist_ok=True)
    sensores = [Identidade("sensor-temp-01"), Identidade("sensor-umid-01")]
    especificacoes = [({"grandeza": "temperatura", "unidade": "°C"}, [20, 30]),
                      ({"grandeza": "umidade_relativa", "unidade": "%"}, [40, 70])]
    with tempfile.TemporaryDirectory(prefix=".inicializacao-", dir=destino.parent) as tmp:
        preparada = Path(tmp) / "dados"
        with Sistema.criar(preparada, [Identidade(f"V{i}") for i in (1, 2, 3)], sensores, senha) as sistema:
            pacote = preparada / "simulador"
            cofre = CofreChaves(pacote / "chaves")
            itens = []
            for sensor, (medicao, faixa) in zip(sensores, especificacoes):
                cofre.salvar(sensor, senha)
                itens.append({"nome": sensor.nome, "pub_hex": sensor.pub_hex,
                              "medicao": medicao, "faixa": faixa})
            (pacote / "sensores.json").write_text(json.dumps(
                {"versao": 1, "rede_id": sistema.cadeia.rede_id, "sensores": itens},
                ensure_ascii=False, indent=2), encoding="utf-8")
        publicar_pasta(preparada, destino)
    return destino


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pasta")
    args = parser.parse_args(argv)
    try:
        senha = getpass.getpass("Senha para cifrar as chaves (mínimo 12 caracteres): ")
        if senha != getpass.getpass("Confirme a senha: "):
            raise ValueError("as senhas não coincidem")
        pasta = preparar(args.pasta, senha)
        print(f"Demonstração preparada em {pasta}")
        print("Sensores: sensor-temp-01 (°C) e sensor-umid-01 (%).")
    except (OSError, ValueError, ErroBlockchain) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
