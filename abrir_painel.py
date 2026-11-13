"""Iniciador do atalho local do Windows para a demonstração do TCC."""
import getpass
import webbrowser
from pathlib import Path

from waitress import create_server

from blockchain_tcc.api import create_app
from blockchain_tcc.cofre import senha_bytes
from blockchain_tcc.credenciais import ler_credenciais
from blockchain_tcc.nucleo import ErroBlockchain
from blockchain_tcc.preparar_demo_api import preparar


def executar(raiz, porta=5001):
    dados = raiz / "dados" / "defesa"
    arquivo = raiz / "credenciais.local.txt"
    print("Blockchain IoT | Demonstração do TCC")
    if arquivo.is_file():
        senha, token = ler_credenciais(arquivo)
        print("Use o TOKEN_ADMIN do seu arquivo de credenciais para entrar no painel.")
    else:
        nova = not dados.exists()
        senha = getpass.getpass("Crie uma senha para as chaves (mínimo 12 caracteres): "
                                if nova else "Senha das chaves da demonstração: ")
        senha_bytes(senha)
        if nova and senha != getpass.getpass("Confirme a senha das chaves: "):
            raise ValueError("As senhas não coincidem.")
        token = getpass.getpass("Escolha um token para entrar no painel (32 a 256 caracteres ASCII sem espaços): ")
        if not 32 <= len(token) <= 256 or any(not 33 <= ord(c) <= 126 for c in token):
            raise ValueError("O token deve ter de 32 a 256 caracteres ASCII sem espaços.")
    if not dados.exists():
        preparar(dados, senha)
    app = create_app(dados, senha, token, modo_apresentacao=True)
    try:
        servidor = create_server(app, host="127.0.0.1", port=porta, threads=4,
                                 max_request_body_size=65536, channel_timeout=30,
                                 ident="blockchain-tcc")
    except OSError as erro:
        if getattr(erro, "winerror", None) == 10048:
            raise ValueError(f"A porta {porta} já está em uso. Se o painel já estiver aberto, use aquela janela.") from erro
        raise
    url = f"http://127.0.0.1:{servidor.effective_port}/painel"
    print(f"Painel: {url}\nMantenha esta janela aberta. Para encerrar, pressione Ctrl+C.", flush=True)
    try:
        try:
            webbrowser.open(url)
        except (OSError, webbrowser.Error):
            print("Abra o endereço acima no navegador.")
        servidor.run()
    finally:
        servidor.close()


if __name__ == "__main__":
    try:
        executar(Path(__file__).resolve().parent)
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, ErroBlockchain) as erro:
        print(f"Não foi possível iniciar o painel: {erro}")
        input("Pressione Enter para fechar.")
        raise SystemExit(1)
