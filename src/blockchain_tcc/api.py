"""API Flask local: ingresso assinado e administração por Bearer token."""
import hashlib
import hmac
import time
from collections import defaultdict, deque
from threading import Lock

from flask import Flask, jsonify, request, render_template, redirect
from werkzeug.exceptions import HTTPException

from blockchain_tcc.servico import ErroServico, ServicoBlockchain


def create_app(pasta, senha_validadores, token_admin, *, limite_requisicoes=300, max_pendentes=1000,
               modo_apresentacao=False):
    if (not isinstance(token_admin, str) or not 32 <= len(token_admin) <= 256
            or any(not 33 <= ord(c) <= 126 for c in token_admin)):
        raise ValueError("o token administrativo deve ter 32 a 256 caracteres ASCII sem espaços")
    if type(limite_requisicoes) is not int or limite_requisicoes < 1:
        raise ValueError("limite de requisições inválido")
    if type(modo_apresentacao) is not bool:
        raise ValueError("modo de apresentação inválido")
    app = Flask(__name__, static_folder="painel/static", static_url_path="/painel/static",
                template_folder="painel/templates")
    app.config.update(MAX_CONTENT_LENGTH=65536, JSON_SORT_KEYS=False,
                      TRUSTED_HOSTS=["localhost", "127.0.0.1", "[::1]"])
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    servico = ServicoBlockchain(pasta, senha_validadores, max_pendentes, modo_apresentacao)
    app.extensions["blockchain"] = servico
    digest_admin = hashlib.sha256(token_admin.encode("ascii")).digest()
    acessos = defaultdict(deque)
    lock_limite = Lock()

    @app.before_request
    def proteger():
        agora = time.monotonic()
        ip = request.remote_addr or "local"
        with lock_limite:
            # Não usa X-Forwarded-For; o servidor atende diretamente em loopback.
            for chave in list(acessos):
                fila = acessos[chave]
                while fila and fila[0] <= agora - 60:
                    fila.popleft()
                if not fila:
                    del acessos[chave]
            if ip not in acessos and len(acessos) >= 1024:
                raise ErroServico(429, "limite_requisicoes", "Limite de requisições atingido.")
            fila = acessos[ip]
            if len(fila) >= limite_requisicoes:
                raise ErroServico(429, "limite_requisicoes", "Limite de requisições atingido; aguarde um minuto.")
            fila.append(agora)
        if "token" in request.args or "senha" in request.args:
            raise ErroServico(400, "credencial_na_url", "Credenciais não são aceitas na URL.")
        if request.endpoint not in {"saude", "rede", "receber", "painel", "inicio", "static"}:
            cabecalho = request.headers.get("Authorization", "")
            esquema, _, token = cabecalho.partition(" ")
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            if esquema.lower() != "bearer" or not hmac.compare_digest(digest_admin, digest):
                raise ErroServico(401, "nao_autorizado", "Token administrativo ausente ou inválido.")

    @app.after_request
    def cabecalhos(resposta):
        resposta.headers["Cache-Control"] = "no-store"
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        resposta.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        return resposta

    @app.errorhandler(ErroServico)
    def erro_servico(exc):
        resposta = jsonify(erro={"codigo": exc.codigo, "mensagem": str(exc)})
        resposta.status_code = exc.status
        if exc.status == 401:
            resposta.headers["WWW-Authenticate"] = "Bearer"
        if exc.status == 429 and exc.codigo == "limite_requisicoes":
            resposta.headers["Retry-After"] = "60"
        return resposta

    @app.errorhandler(HTTPException)
    def erro_http(exc):
        mensagens = {400: "JSON ou requisição inválida.", 404: "Rota não encontrada.",
                    405: "Método não permitido.", 413: "Corpo excede 64 KiB.",
                    415: "Envie Content-Type: application/json."}
        return jsonify(erro={"codigo": f"http_{exc.code}",
                             "mensagem": mensagens.get(exc.code, "Requisição recusada.")}), exc.code

    @app.errorhandler(Exception)
    def erro_interno(exc):
        app.logger.exception("Falha interna na API.")
        return jsonify(erro={"codigo": "erro_interno", "mensagem": "Não foi possível concluir a operação."}), 500

    def corpo(campos=None):
        dados = request.get_json()
        if not isinstance(dados, dict) or (campos is not None and set(dados) != set(campos)):
            raise ErroServico(400, "schema_invalido", "Campos do objeto JSON inválidos.")
        return dados

    def pagina():
        if any(k not in {"inicio", "limite"} or len(request.args.getlist(k)) != 1 for k in request.args):
            raise ErroServico(400, "paginacao_invalida", "Use somente inicio e limite, uma vez cada.")
        valores = []
        for nome, padrao in (("inicio", "0"), ("limite", "50")):
            valor = request.args.get(nome, padrao)
            if len(valor) > 8 or not valor.isascii() or not valor.isdecimal():
                raise ErroServico(400, "paginacao_invalida", "Paginação exige inteiros não negativos.")
            valores.append(int(valor))
        if not 1 <= valores[1] <= 100:
            raise ErroServico(400, "paginacao_invalida", "Limite deve estar entre 1 e 100.")
        return valores

    @app.get("/")
    def inicio():
        return redirect("/painel")

    @app.get("/painel")
    def painel():
        return render_template("painel.html")

    @app.get("/painel/dados")
    def painel_dados():
        return jsonify(servico.painel())

    @app.get("/transacoes")
    def transacoes():
        return jsonify(servico.transacoes(*pagina()))

    @app.post("/apresentacao/leituras")
    def simular_leituras():
        corpo(set())
        return jsonify(servico.simular_leituras()), 202

    @app.post("/apresentacao/integridade")
    def demonstrar_integridade():
        dados = corpo({"bloco", "valor", "recalcular_hash"})
        return jsonify(servico.demonstrar_integridade(dados["bloco"], dados["valor"], dados["recalcular_hash"]))

    @app.get("/saude")
    def saude():
        return jsonify(status="ok", servico="blockchain-tcc", versao_api=1)

    @app.get("/rede")
    def rede():
        return jsonify(servico.rede())

    @app.get("/estado")
    def estado():
        return jsonify(servico.estado())

    @app.get("/cadeia")
    def cadeia():
        return jsonify(servico.cadeia(*pagina()))

    @app.get("/blocos/<int:indice>")
    def bloco(indice):
        return jsonify(servico.bloco(indice))

    @app.get("/validar")
    def validar():
        return jsonify(servico.validar())

    @app.get("/historico/<path:nome>")
    def historico(nome):
        return jsonify(servico.historico(nome, *pagina()))

    @app.get("/pendentes")
    def pendentes():
        return jsonify(servico.pendentes(*pagina()))

    @app.get("/transacoes/<identificador>")
    def transacao(identificador):
        return jsonify(servico.transacao(identificador))

    @app.post("/transacao")
    def receber():
        return jsonify(servico.receber(corpo())), 202

    @app.post("/blocos")
    def produzir():
        corpo(set())
        return jsonify(servico.produzir()), 201

    @app.delete("/pendentes/<identificador>")
    def descartar(identificador):
        return jsonify(servico.descartar(identificador))

    @app.get("/membros")
    def membros():
        return jsonify(servico.membros(*pagina()))

    @app.post("/membros")
    def cadastrar():
        dados = corpo({"nome", "pub_hex"})
        return jsonify(servico.cadastrar(dados["nome"], dados["pub_hex"])), 201

    @app.put("/membros/<path:nome>")
    def rotacionar(nome):
        dados = corpo({"pub_hex"})
        return jsonify(servico.rotacionar(nome, dados["pub_hex"]))

    @app.post("/membros/<path:nome>/revogar")
    def revogar(nome):
        corpo(set())
        return jsonify(servico.revogar(nome))

    return app
