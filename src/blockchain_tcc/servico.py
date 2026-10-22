"""Operações serializadas; cada chamada utiliza sua própria conexão SQLite."""
import sqlite3
import random
import time
from copy import deepcopy
from pathlib import Path
from threading import RLock

from blockchain_tcc.identidade import DISPOSITIVO, VALIDADOR, Registro
from blockchain_tcc.nucleo import ErroBlockchain, Transacao
from blockchain_tcc.sistema import Sistema


class ErroServico(Exception):
    def __init__(self, status, codigo, mensagem):
        super().__init__(mensagem)
        self.status, self.codigo = status, codigo


class ServicoBlockchain:
    def __init__(self, pasta, senha_validadores, max_pendentes=1000, modo_apresentacao=False):
        if type(max_pendentes) is not int or not 1 <= max_pendentes <= 10000:
            raise ValueError("capacidade da fila deve estar entre 1 e 10000")
        self.pasta = pasta
        self._senha = senha_validadores
        self._lock = RLock()
        self._pendentes = []
        self.max_pendentes = max_pendentes
        self.modo_apresentacao = modo_apresentacao
        # Verifica o banco e as chaves antes de aceitar conexões HTTP.
        with Sistema.abrir(pasta) as sistema:
            for nome, m in sistema.registro.to_dict().items():
                if m["ativo"] and m["papel"] == VALIDADOR:
                    sistema.carregar_identidade(nome, senha_validadores)

    def _usar(self, operacao):
        with self._lock:
            try:
                with Sistema.abrir(self.pasta) as sistema:
                    sistema.cadeia.pendentes = deepcopy(self._pendentes)
                    resultado = operacao(sistema)
                    self._pendentes = deepcopy(sistema.cadeia.pendentes)
                    return resultado
            except ErroServico:
                raise
            except (OSError, sqlite3.Error, ErroBlockchain, ValueError) as exc:
                raise ErroServico(503, "estado_indisponivel", "Não foi possível abrir ou atualizar o estado do sistema.") from exc

    def rede(self):
        return self._usar(lambda s: {"rede_id": s.cadeia.rede_id, "formatos_transacao": [2, 3]})

    def estado(self):
        def ler(s):
            return {"rede_id": s.cadeia.rede_id, "blocos": len(s.cadeia.blocos),
                    "transacoes_confirmadas": sum(len(b.transacoes) for b in s.cadeia.blocos),
                    "pendentes": len(s.cadeia.pendentes),
                    "proximo_validador": s.cadeia.validador_da_vez(len(s.cadeia.blocos)),
                    "modo": "local", "versao_sistema": 2}
        return self._usar(ler)

    def painel(self):
        """Um retrato consistente para atualização do painel, sem várias consultas."""
        def ler(s):
            membros = s.registro.to_dict()
            estatisticas = {n: {"nome": n, "leituras": 0, "ultima": None}
                            for n, m in membros.items() if m["papel"] == DISPOSITIVO}
            recentes = []
            total = 0
            for b in s.cadeia.blocos:
                for tx in b.transacoes:
                    item = {"bloco": b.indice, **tx}
                    total += 1
                    if tx["dispositivo"] in estatisticas:
                        estatisticas[tx["dispositivo"]]["leituras"] += 1
                        estatisticas[tx["dispositivo"]]["ultima"] = item
                    recentes.append(item)
                    if len(recentes) > 60:
                        recentes.pop(0)
            blocos = [{"indice": b.indice, "ts": b.ts, "validador": b.validador,
                       "hash": b.hash, "hash_anterior": b.hash_anterior,
                       "transacoes": len(b.transacoes)} for b in reversed(s.cadeia.blocos[-6:])]
            return {"rede_id": s.cadeia.rede_id, "blocos": len(s.cadeia.blocos),
                    "transacoes_confirmadas": total, "pendentes": len(s.cadeia.pendentes),
                    "proximo_validador": s.cadeia.validador_da_vez(len(s.cadeia.blocos)),
                    "membros": [{"nome": n, **m} for n, m in sorted(membros.items())],
                    "sensores": list(estatisticas.values()), "leituras_recentes": recentes,
                    "ultimos_blocos": blocos, "fila_recente": s.cadeia.pendentes[:6],
                    "validacao": {"valida": True, "verificado_em": time.time()},
                    "apresentacao": self.modo_apresentacao,
                    "simulacao_disponivel": self.modo_apresentacao and (Path(self.pasta) / "simulador" / "sensores.json").is_file()}
        return self._usar(ler)

    def transacoes(self, inicio=0, limite=50):
        return self._usar(lambda s: self._pagina(
            [{"bloco": b.indice, **t} for b in reversed(s.cadeia.blocos)
             for t in reversed(b.transacoes)], inicio, limite))

    def _exigir_apresentacao(self):
        if not self.modo_apresentacao:
            raise ErroServico(403, "apresentacao_desativada", "Inicie a API com --apresentacao para usar o laboratório local.")

    def simular_leituras(self):
        self._exigir_apresentacao()
        from blockchain_tcc.simulador_iot import carregar_sensores

        def gerar(s):
            pacote = Path(self.pasta) / "simulador"
            if not (pacote / "sensores.json").is_file():
                raise ErroServico(409, "pacote_ausente", "Prepare uma instalação de demonstração para gerar leituras pelo painel.")
            rede, sensores = carregar_sensores(pacote, self._senha)
            if rede != s.cadeia.rede_id:
                raise ErroServico(409, "rede_divergente", "O pacote de simulação pertence a outra rede.")
            membros = s.registro.to_dict()
            ativos = [(i, m, f) for i, m, f in sensores if membros.get(i.nome, {}).get("ativo")
                      and membros[i.nome]["papel"] == DISPOSITIVO and membros[i.nome]["pub"] == i.pub_hex]
            if not ativos:
                raise ErroServico(409, "sensores_inativos", "Não há sensores do pacote autorizados com suas chaves atuais.")
            if len(s.cadeia.pendentes) + len(ativos) > self.max_pendentes:
                raise ErroServico(429, "fila_cheia", "A fila de transações está cheia.")
            gerador = random.SystemRandom()
            leituras = []
            for identidade, medicao, faixa in ativos:
                tx = Transacao.criar(identidade, round(gerador.uniform(*faixa), 2), rede, medicao=medicao)
                s.cadeia.adicionar_transacao(tx)
                leituras.append(tx.to_dict())
            return {"situacao": "pendente", "simuladas": True, "leituras": leituras,
                    "sensores_ignorados": [i.nome for i, _, _ in sensores if not any(i.nome == a.nome for a, _, _ in ativos)]}
        return self._usar(gerar)

    def demonstrar_integridade(self, indice, valor, recalcular=False):
        self._exigir_apresentacao()
        if type(indice) is not int or indice < 1 or not isinstance(valor, str) or not valor.strip():
            raise ErroServico(400, "teste_invalido", "Escolha um bloco regular e um novo valor textual.")
        try:
            if len(valor.encode("utf-8")) > 4096 or type(recalcular) is not bool:
                raise ValueError("valor inválido")
        except (ValueError, UnicodeError) as exc:
            raise ErroServico(400, "teste_invalido", "Valor ou opção de recálculo inválidos.") from exc

        def demonstrar(s):
            if indice >= len(s.cadeia.blocos):
                raise ErroServico(404, "bloco_ausente", "Bloco não encontrado.")
            # Somente a lista em memória desta instância de leitura é substituída.
            # Não há chamada de gravação: o ledger e a fila continuam intactos.
            s.cadeia.blocos = deepcopy(s.cadeia.blocos)
            bloco = s.cadeia.blocos[indice]
            original = bloco.transacoes[0]["valor"]
            if original == valor:
                raise ErroServico(409, "valor_igual", "Informe um valor diferente do registro original.")
            hash_registrado = bloco.hash
            bloco.transacoes[0]["valor"] = valor
            hash_recalculado = bloco.calcular_hash()
            if recalcular:
                bloco.hash = hash_recalculado
            ok, motivo = s.cadeia.validar()
            return {"bloco": indice, "valor_original": original, "valor_alterado": valor,
                    "hash_registrado": hash_registrado, "hash_recalculado": hash_recalculado,
                    "hash_atualizado_na_copia": recalcular,
                    "original_valida": True, "copia_valida": ok, "motivo": motivo,
                    "persistido": False}
        return self._usar(demonstrar)

    @staticmethod
    def _pagina(itens, inicio, limite):
        return {"total": len(itens), "inicio": inicio, "limite": limite,
                "itens": itens[inicio:inicio + limite]}

    def cadeia(self, inicio=0, limite=50):
        return self._usar(lambda s: self._pagina([b.to_dict() for b in s.cadeia.blocos], inicio, limite))

    def bloco(self, indice):
        def ler(s):
            if indice >= len(s.cadeia.blocos):
                raise ErroServico(404, "bloco_ausente", "Bloco não encontrado.")
            return s.cadeia.blocos[indice].to_dict()
        return self._usar(ler)

    def validar(self):
        def ler(s):
            ok, erro = s.cadeia.validar()
            return {"valida": ok, "motivo": erro, "blocos": len(s.cadeia.blocos)}
        return self._usar(ler)

    def membros(self, inicio=0, limite=50):
        return self._usar(lambda s: self._pagina(
            [{"nome": n, **m} for n, m in sorted(s.registro.to_dict().items())], inicio, limite))

    def historico(self, nome, inicio=0, limite=50):
        def ler(s):
            if nome not in s.registro.to_dict():
                raise ErroServico(404, "membro_ausente", "Membro não encontrado.")
            itens = [{"bloco": b.indice, **t} for b in s.cadeia.blocos
                     for t in b.transacoes if t["dispositivo"] == nome]
            return self._pagina(itens, inicio, limite)
        return self._usar(ler)

    def pendentes(self, inicio=0, limite=50):
        return self._usar(lambda s: self._pagina(s.cadeia.pendentes, inicio, limite))

    def transacao(self, identificador):
        def ler(s):
            for b in s.cadeia.blocos:
                for t in b.transacoes:
                    if t["id_transacao"] == identificador:
                        return {"situacao": "confirmada", "bloco": b.indice, "transacao": t}
            for t in s.cadeia.pendentes:
                if t["id_transacao"] == identificador:
                    return {"situacao": "pendente", "transacao": t}
            raise ErroServico(404, "transacao_ausente", "Transação não encontrada.")
        return self._usar(ler)

    def receber(self, dados):
        try:
            tx = Transacao.from_dict(dados)
        except (ValueError, TypeError) as exc:
            raise ErroServico(400, "schema_invalido", str(exc)) from exc
        try:
            tamanho = len(tx.valor.encode("utf-8")) if isinstance(tx.valor, str) else 4097
            if isinstance(tx.dispositivo, str):
                tx.dispositivo.encode("utf-8")
        except UnicodeError as exc:
            raise ErroServico(400, "campo_invalido", "Texto deve ter codificação UTF-8 válida.") from exc
        if (not isinstance(tx.dispositivo, str) or len(tx.dispositivo) > 128 or tamanho > 4096):
            raise ErroServico(400, "campo_invalido", "Nome ou valor fora dos limites permitidos.")

        def gravar(s):
            if len(s.cadeia.pendentes) >= self.max_pendentes:
                raise ErroServico(429, "fila_cheia", "A fila de transações está cheia.")
            try:
                s.cadeia.adicionar_transacao(tx)
            except ErroBlockchain as exc:
                repetida = "repetida" in str(exc)
                raise ErroServico(409 if repetida else 422,
                                  "replay" if repetida else "transacao_invalida", str(exc)) from exc
            return {"situacao": "pendente", "id_transacao": tx.id_transacao}
        return self._usar(gravar)

    def produzir(self):
        def gravar(s):
            if not s.cadeia.pendentes:
                raise ErroServico(409, "fila_vazia", "Não há transações pendentes.")
            # A fila é revalidada antes de qualquer gravação.
            if any(not s.cadeia._transacao_valida(Transacao.from_dict(t)) for t in s.cadeia.pendentes):
                raise ErroServico(422, "pendencia_invalida", "Há pendência inválida ou de identidade revogada; descarte-a antes de produzir.")
            bloco = s.produzir_bloco(self._senha)
            return bloco.to_dict()
        return self._usar(gravar)

    def descartar(self, identificador):
        def gravar(s):
            if not any(t["id_transacao"] == identificador for t in s.cadeia.pendentes):
                raise ErroServico(404, "pendencia_ausente", "Pendência não encontrada.")
            s.cadeia.descartar_pendente(identificador)
            return {"id_transacao": identificador, "situacao": "descartada"}
        return self._usar(gravar)

    def cadastrar(self, nome, pub_hex):
        self._conferir_membro(nome, pub_hex)
        def gravar(s):
            if nome in s.registro.to_dict():
                raise ErroServico(409, "membro_existente", "Nome já cadastrado; use a operação de rotação.")
            s.registro.autorizar(nome, pub_hex, DISPOSITIVO)
            return {"nome": nome, "papel": DISPOSITIVO, "pub": pub_hex, "ativo": True}
        return self._usar(gravar)

    @staticmethod
    def _conferir_membro(nome, pub_hex):
        try:
            if not isinstance(nome, str) or len(nome) > 128:
                raise ValueError("nome inválido")
            nome.encode("utf-8")
            Registro._conferir_membro(nome, pub_hex, DISPOSITIVO)
        except (ValueError, TypeError) as exc:
            raise ErroServico(400, "membro_invalido", "Nome ou chave pública inválidos.") from exc

    def rotacionar(self, nome, pub_hex):
        self._conferir_membro(nome, pub_hex)
        def gravar(s):
            membro = s.registro.to_dict().get(nome)
            if not membro:
                raise ErroServico(404, "membro_ausente", "Membro não encontrado.")
            if membro["papel"] != DISPOSITIVO:
                raise ErroServico(422, "papel_invalido", "Esta operação altera somente chaves de dispositivos.")
            s.registro.autorizar(nome, pub_hex, DISPOSITIVO)
            return {"nome": nome, "pub": pub_hex, "ativo": True}
        return self._usar(gravar)

    def revogar(self, nome):
        def gravar(s):
            if nome not in s.registro.to_dict():
                raise ErroServico(404, "membro_ausente", "Membro não encontrado.")
            try:
                s.revogar(nome)
            except ErroBlockchain as exc:
                if not any(n != nome and m["ativo"] and m["papel"] == VALIDADOR
                           for n, m in s.registro.to_dict().items()):
                    raise ErroServico(422, "ultima_autoridade", "É preciso manter uma autoridade ativa.") from exc
                raise
            return {"nome": nome, "ativo": False}
        return self._usar(gravar)
