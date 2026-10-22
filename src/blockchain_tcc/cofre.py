"""Arquivos PKCS8 cifrados; a senha é fornecida pelo operador a cada uso."""
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from blockchain_tcc.formato import sha256_hex
from blockchain_tcc.identidade import Identidade


def senha_bytes(senha):
    if not isinstance(senha, str) or len(senha) < 12:
        raise ValueError("use uma senha com pelo menos 12 caracteres")
    return senha.encode("utf-8")


class CofreChaves:
    def __init__(self, pasta):
        self.pasta = Path(pasta)

    def caminho(self, nome, pub_hex):
        if not isinstance(nome, str) or not nome.strip():
            raise ValueError("nome inválido")
        if (not isinstance(pub_hex, str) or len(pub_hex) != 64
                or any(c not in "0123456789abcdef" for c in pub_hex)):
            raise ValueError("chave pública inválida")
        # O nome lógico nunca é usado diretamente como caminho de arquivo.
        return self.pasta / sha256_hex(nome.encode("utf-8")) / (pub_hex + ".pem")

    def salvar(self, identidade, senha):
        dados = identidade._priv.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(senha_bytes(senha)),
        )
        arquivo = self.caminho(identidade.nome, identidade.pub_hex)
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(arquivo, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as destino:
                destino.write(dados)
                destino.flush()
                os.fsync(destino.fileno())
        except OSError:
            # Este arquivo foi criado exclusivamente nesta chamada; remove gravação parcial.
            arquivo.unlink(missing_ok=True)
            raise
        return arquivo

    def carregar(self, nome, pub_hex, senha):
        dados = self.caminho(nome, pub_hex).read_bytes()
        try:
            privada = serialization.load_pem_private_key(dados, password=senha_bytes(senha))
            if not isinstance(privada, Ed25519PrivateKey):
                raise ValueError("tipo de chave incompatível")
            identidade = Identidade(nome, privada)
            if identidade.pub_hex != pub_hex:
                raise ValueError("chave não corresponde ao cadastro")
            return identidade
        except (TypeError, ValueError) as exc:
            raise ValueError("senha incorreta ou arquivo de chave inválido") from exc
