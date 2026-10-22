"""Cliente HTTP local, sem proxies, redirecionamentos ou repetição automática."""
import argparse
import getpass
import http.client
import json
import sys
from urllib.parse import quote, urlsplit


class ErroCliente(Exception):
    def __init__(self, status, codigo, mensagem):
        super().__init__(mensagem)
        self.status, self.codigo = status, codigo


class ClienteAPI:
    def __init__(self, url="http://127.0.0.1:5000", token_admin=None, timeout=5):
        partes = urlsplit(url)
        if (partes.scheme != "http" or partes.hostname not in {"127.0.0.1", "localhost", "::1"}
                or partes.username is not None or partes.password is not None
                or partes.query or partes.fragment or partes.path not in {"", "/"}):
            raise ValueError("use uma URL HTTP local, sem credenciais, caminho ou parâmetros")
        self.host, self.porta = partes.hostname, partes.port or 80
        self._token, self.timeout = token_admin, timeout

    def chamar(self, metodo, caminho, dados=None, *, administrativo=False):
        if not caminho.startswith("/") or caminho.startswith("//"):
            raise ValueError("caminho HTTP inválido")
        headers = {"Accept": "application/json"}
        corpo = None
        if dados is not None:
            corpo = json.dumps(dados, ensure_ascii=False, allow_nan=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if administrativo:
            if not self._token:
                raise ValueError("token administrativo necessário")
            headers["Authorization"] = "Bearer " + self._token
        con = http.client.HTTPConnection(self.host, self.porta, timeout=self.timeout)
        try:
            con.request(metodo, caminho, body=corpo, headers=headers)
            resposta = con.getresponse()
            dados_brutos = resposta.read(16 * 1024 * 1024 + 1)
            if len(dados_brutos) > 16 * 1024 * 1024:
                raise ErroCliente(resposta.status, "resposta_grande", "Resposta excede o limite do cliente.")
            try:
                resultado = json.loads(dados_brutos)
            except (ValueError, UnicodeError) as exc:
                raise ErroCliente(resposta.status, "resposta_invalida", "O servidor não devolveu JSON válido.") from exc
            if not isinstance(resultado, dict):
                raise ErroCliente(resposta.status, "resposta_invalida", "Resposta incompatível com a API.")
            if not 200 <= resposta.status < 300:
                erro = resultado.get("erro", {})
                if not isinstance(erro, dict):
                    raise ErroCliente(resposta.status, "resposta_invalida", "Erro incompatível com a API.")
                raise ErroCliente(resposta.status, erro.get("codigo", "erro_http"),
                                  erro.get("mensagem", "Requisição recusada."))
            return resultado
        except (OSError, http.client.HTTPException) as exc:
            raise ErroCliente(0, "falha_conexao", "Falha na conexão; consulte o estado antes de repetir uma operação.") from exc
        finally:
            con.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=("estado", "validar", "cadeia", "membros", "pendentes", "produzir", "historico"))
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    parser.add_argument("--dispositivo", default="sensor-temp-01")
    args = parser.parse_args(argv)
    try:
        token = getpass.getpass("Token administrativo: ")
        cliente = ClienteAPI(args.url, token)
        caminho = "/historico/" + quote(args.dispositivo, safe="") if args.acao == "historico" else "/" + args.acao
        metodo, dados = ("GET", None)
        if args.acao == "produzir":
            metodo, caminho, dados = "POST", "/blocos", {}
        resultado = cliente.chamar(metodo, caminho, dados, administrativo=True)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    except (ErroCliente, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
