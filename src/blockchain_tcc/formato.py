"""Representação canônica compartilhada por assinaturas e cadastros."""
import hashlib
import json


def canonico(obj) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def sha256_hex(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def hash_governanca(rede_id, validadores):
    return sha256_hex(canonico({"versao": 2, "rede_id": rede_id, "validadores": validadores}))
