"""Leitura de credenciais locais sem executar o conteúdo do arquivo."""

from pathlib import Path

from blockchain_tcc.cofre import senha_bytes


def ler_credenciais(caminho):
    """Lê SENHA_CHAVES e TOKEN_ADMIN de um arquivo de texto UTF-8."""
    valores = {}
    try:
        linhas = Path(caminho).read_text(encoding="utf-8-sig").splitlines()
    except UnicodeError as exc:
        raise ValueError("o arquivo de credenciais deve estar em UTF-8") from exc
    for numero, linha in enumerate(linhas, 1):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if "=" not in linha:
            raise ValueError(f"linha {numero} das credenciais: use NOME=valor")
        nome, valor = (parte.strip() for parte in linha.split("=", 1))
        if nome not in ("SENHA_CHAVES", "TOKEN_ADMIN"):
            raise ValueError(f"linha {numero} das credenciais: nome desconhecido")
        if nome in valores:
            raise ValueError(f"linha {numero} das credenciais: nome repetido")
        valores[nome] = valor

    if not valores.get("SENHA_CHAVES") or not valores.get("TOKEN_ADMIN"):
        raise ValueError("preencha SENHA_CHAVES e TOKEN_ADMIN no arquivo de credenciais")
    senha = valores["SENHA_CHAVES"]
    token = valores["TOKEN_ADMIN"]
    senha_bytes(senha)
    if not 32 <= len(token) <= 256 or any(not 33 <= ord(c) <= 126 for c in token):
        raise ValueError("TOKEN_ADMIN exige 32 a 256 caracteres ASCII sem espaços")
    return senha, token
