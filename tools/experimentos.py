"""Experimentos locais da etapa 5. Bancos novos; nenhuma chave privada em disco.

Uso: python experimentos.py resultados/execucao-01
Cada observação roda em um processo novo. Não mede HTTP nem sensores físicos.
"""
import argparse
import csv
import ctypes
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import sqlite3
import statistics
import subprocess
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from blockchain_tcc.armazenamento import Armazenamento
from blockchain_tcc.formato import canonico
from blockchain_tcc.identidade import DISPOSITIVO, VALIDADOR, Identidade, Registro
from blockchain_tcc.nucleo import Cadeia, ErroBlockchain, Transacao


def gravar_json(caminho, dados):
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def gravar_csv(caminho, linhas):
    with caminho.open("w", newline="", encoding="utf-8-sig") as arq:
        writer = csv.DictWriter(arq, fieldnames=list(linhas[0]))
        writer.writeheader()
        writer.writerows(linhas)


def p95(valores):
    """Nearest rank: valor ordenado na posição ceil(0.95*n), contando de 1."""
    return sorted(valores)[math.ceil(0.95 * len(valores)) - 1]


def memoria_pico():
    """Pico de working set de TODO o processo, incluindo imports e preparação."""
    if sys.platform == "win32":
        from ctypes import wintypes

        class Contadores(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (nome, ctypes.c_size_t) for nome in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Contadores), wintypes.DWORD]
        info = Contadores()
        info.cb = ctypes.sizeof(info)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(info), info.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return info.PeakWorkingSetSize
    import resource
    pico = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return pico if sys.platform == "darwin" else pico * 1024


def preparar_ledger(banco):
    sensores = [Identidade(f"sensor-{i:02d}") for i in range(4)]
    validadores = [Identidade(f"V{i}") for i in (1, 2, 3)]
    registro = Registro()
    for membros, papel in ((sensores, DISPOSITIVO), (validadores, VALIDADOR)):
        for identidade in membros:
            registro.autorizar(identidade.nome, identidade.pub_hex, papel)
    armazenamento = Armazenamento(banco)
    cadeia = Cadeia(registro, [v.nome for v in validadores], armazenamento, "experimento-local")
    return cadeia, armazenamento, sensores, validadores


def leitura(i):
    # Mesmo conteúdo lógico e tamanho por índice em todos os modos e repetições.
    return {
        "dispositivo": f"sensor-{i % 4:02d}", "valor": f"{23 + (i % 80) / 10:.1f}",
        "ts": 1700000000.0 + i, "versao": 3,
        "id_transacao": f"{i + 1:032x}", "rede_id": "experimento-local",
        "medicao": {"grandeza": "temperatura", "unidade": "°C"},
    }


def executar_worker(pasta, modo, quantidade, lote):
    pasta.mkdir()  # Recusa reutilização, inclusive execução parcial.
    banco = pasta / "ledger.db"
    cadeia, armazenamento, sensores, validadores = preparar_ledger(banco)
    if modo == "sqlite":
        # Preserva preparação equivalente, mas usa outro banco para os dados medidos.
        armazenamento.fechar()
        banco = pasta / "convencional.db"
        con = sqlite3.connect(banco)
        con.execute("CREATE TABLE leituras (id TEXT PRIMARY KEY, dados TEXT NOT NULL)")
        con.commit()
    else:
        con = armazenamento._con
    pragmas = {nome: con.execute(f"PRAGMA {nome}").fetchone()[0]
               for nome in ("journal_mode", "synchronous", "page_size")}
    # Aquecimento independente do banco medido: assinatura e verificação, sem blocos.
    for _ in range(20):
        tx = Transacao.criar(sensores[0], "23.0", cadeia.rede_id)
        if not cadeia._transacao_valida(tx):
            raise RuntimeError("aquecimento inválido")
    latencias, blocos = [], []
    cpu_inicio = time.process_time_ns()
    inicio = time.perf_counter_ns()
    for primeiro in range(0, quantidade, lote):
        inicios, registros = [], []
        inicio_lote = time.perf_counter_ns()
        for i in range(primeiro, min(primeiro + lote, quantidade)):
            inicios.append(time.perf_counter_ns())
            tx = Transacao.from_dict(dict(leitura(i), assinatura=""))
            tx.assinatura = sensores[i % 4].assinar(tx.conteudo())
            if modo == "ledger":
                cadeia.adicionar_transacao(tx)
            else:
                registros.append((tx.id_transacao, canonico(tx.to_dict()).decode("utf-8")))
        if modo == "ledger":
            nome = cadeia.validador_da_vez(len(cadeia.blocos))
            cadeia.produzir_bloco(next(v for v in validadores if v.nome == nome))
        else:
            with con:
                con.executemany("INSERT INTO leituras VALUES (?, ?)", registros)
        confirmado = time.perf_counter_ns()
        for deslocamento, chegada in enumerate(inicios):
            latencias.append({"transacao": primeiro + deslocamento + 1,
                              "lote": len(blocos) + 1, "latencia_ms": (confirmado - chegada) / 1e6})
        blocos.append({"lote": len(blocos) + 1, "confirmadas": len(latencias),
                       "tempo_ms": (confirmado - inicio_lote) / 1e6})
    fim = time.perf_counter_ns()
    cpu_ns = time.process_time_ns() - cpu_inicio
    segundos = (fim - inicio) / 1e9
    # Checagens finais fora da janela de desempenho, sem adulterar o banco.
    if modo == "ledger":
        n = sum(len(b.transacoes) for b in cadeia.blocos)
        t = time.perf_counter_ns()
        valido, erro = cadeia.validar()
        validar_ms = (time.perf_counter_ns() - t) / 1e6
        if not valido or n != quantidade:
            raise RuntimeError(f"resultado inconsistente: {erro}")
        armazenamento.fechar()
        t = time.perf_counter_ns()
        aberto = Armazenamento(banco)
        try:
            recuperada = Cadeia(Registro.from_estado(aberto.carregar_configuracao()["registro"]),
                                cadeia.validadores, aberto, cadeia.rede_id)
            if sum(len(b.transacoes) for b in recuperada.blocos) != quantidade:
                raise RuntimeError("recuperação divergente")
        finally:
            aberto.fechar()
        reabrir_ms = (time.perf_counter_ns() - t) / 1e6
    else:
        if con.execute("SELECT COUNT(*) FROM leituras").fetchone()[0] != quantidade:
            raise RuntimeError("contagem SQLite divergente")
        validar_ms = None  # SQLite convencional não oferece validação criptográfica.
        con.close()
        t = time.perf_counter_ns()
        consulta = sqlite3.connect(banco)
        try:
            registros = [json.loads(r[0]) for r in consulta.execute("SELECT dados FROM leituras ORDER BY id")]
            if len(registros) != quantidade:
                raise RuntimeError("recuperação SQLite divergente")
        finally:
            consulta.close()
        reabrir_ms = (time.perf_counter_ns() - t) / 1e6
    pico = memoria_pico()
    valores = [l["latencia_ms"] for l in latencias]
    resultado = {
        "modo": modo, "leituras": quantidade, "por_lote": lote, "lotes": len(blocos),
        "tempo_s": segundos, "tps": quantidade / segundos,
        "latencia_media_ms": statistics.mean(valores), "latencia_mediana_ms": statistics.median(valores),
        "latencia_p95_ms": p95(valores), "cpu_s": cpu_ns / 1e9,
        "cpu_um_nucleo_pct": cpu_ns / (fim - inicio) * 100,
        "pico_processo_mib": pico / (1024 ** 2), "banco_bytes": banco.stat().st_size,
        "validar_final_ms": validar_ms, "reabrir_carregar_ms": reabrir_ms,
        "pragmas": pragmas,
    }
    gravar_csv(pasta / "latencias.csv", latencias)
    gravar_csv(pasta / "lotes.csv", blocos)
    gravar_json(pasta / "medicao.json", resultado)


def integridade(pasta):
    pasta.mkdir()
    banco = pasta / "ledger.db"
    cadeia, armaz, sensores, validadores = preparar_ledger(banco)
    try:
        tx = Transacao.criar(sensores[0], "23.0", cadeia.rede_id)
        cadeia.adicionar_transacao(tx)
        cadeia.produzir_bloco(validadores[0])
        original = deepcopy(cadeia.blocos)
        antes = hashlib.sha256(banco.read_bytes()).hexdigest()
        resultados = []
        for recalcular in (False, True):
            cadeia.blocos = deepcopy(original)
            cadeia.blocos[1].transacoes[0]["valor"] = "99.9"
            if recalcular:
                cadeia.blocos[1].hash = cadeia.blocos[1].calcular_hash()
            valido, erro = cadeia.validar()
            if valido:
                raise RuntimeError("adulteração não detectada")
            resultados.append({"cenario": "valor alterado" + (" e hash recalculado" if recalcular else ""),
                               "rejeitado": not valido, "motivo": erro})
        cadeia.blocos = original
        try:
            cadeia.adicionar_transacao(tx)
        except ErroBlockchain as exc:
            resultados.append({"cenario": "reenvio confirmado", "rejeitado": True, "motivo": str(exc)})
        else:
            raise RuntimeError("replay aceito")
        banco_preservado = hashlib.sha256(banco.read_bytes()).hexdigest() == antes
        if not banco_preservado:
            raise RuntimeError("laboratório alterou o banco")
        cadeia.registro.revogar(sensores[0].nome)
        if not cadeia.validar()[0]:
            raise RuntimeError("revogação invalidou histórico")
        try:
            cadeia.adicionar_transacao(Transacao.criar(sensores[0], "24.0", cadeia.rede_id))
        except ErroBlockchain as exc:
            resultados.append({"cenario": "nova leitura de sensor revogado", "rejeitado": True, "motivo": str(exc)})
        else:
            raise RuntimeError("revogação não aplicada")
        # A revogação altera configuração legitimamente; comparar só antes dela.
        gravar_json(pasta / "integridade.json", {
            "cenarios": resultados, "historico_valido_apos_revogacao": cadeia.validar()[0],
            "banco_preservado_apos_copias_e_replay": banco_preservado,
            "hash_banco_antes_laboratorio": antes,
            "observacao": "Adulterações feitas em cópia da lista; revogação persistida no banco exclusivo do experimento."})
    finally:
        armaz.fechar()


def consolidar(pasta, observacoes):
    gravar_csv(pasta / "execucoes.csv", [{k: v for k, v in o.items() if k != "pragmas"} for o in observacoes])
    resumo = []
    for n, lote, modo in sorted({(o["leituras"], o["por_lote"], o["modo"]) for o in observacoes}):
        grupo = [o for o in observacoes if (o["leituras"], o["por_lote"], o["modo"]) == (n, lote, modo)]
        linha = {"modo": modo, "leituras": n, "por_lote": lote, "repeticoes": len(grupo)}
        for campo in ("tps", "latencia_media_ms", "latencia_p95_ms", "cpu_s", "pico_processo_mib",
                      "banco_bytes", "validar_final_ms", "reabrir_carregar_ms"):
            vals = [o[campo] for o in grupo if o[campo] is not None]
            linha[campo + "_media"] = statistics.mean(vals) if vals else None
            linha[campo + "_desvio"] = statistics.stdev(vals) if len(vals) > 1 else None
        resumo.append(linha)
    gravar_csv(pasta / "resumo.csv", resumo)
    texto = ["# Resultados observados da etapa 5", "",
             "Médias de repetições independentes. P95 é calculado em cada execução e depois agregado; não é o P95 combinado.", "",
             "| Modo | Leituras | Lote | Repetições | TPS (média ± DP) | Latência média (ms) | P95 médio (ms) | CPU (s) | Pico processo (MiB) | Banco (KiB) |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in resumo:
        texto.append(f"| {r['modo']} | {r['leituras']} | {r['por_lote']} | {r['repeticoes']} | "
                     f"{r['tps_media']:.2f} ± {(r['tps_desvio'] or 0):.2f} | {r['latencia_media_ms_media']:.3f} | "
                     f"{r['latencia_p95_ms_media']:.3f} | {r['cpu_s_media']:.3f} | "
                     f"{r['pico_processo_mib_media']:.2f} | {r['banco_bytes_media']/1024:.1f} |")
    texto += ["", "A assinatura da leitura está incluída nos dois modos. O ledger também verifica autorização, replay, histórico e assinaturas e produz blocos assinados. SQLite armazena o mesmo JSON assinado, sem essas garantias.",
              "", "Confirmação: retorno do commit local. A carga é sequencial, sem intervalo artificial, e o agrupamento é igual nos dois modos. Não mede filas de rede, HTTP, painel ou consenso distribuído.",
              "", "CPU é tempo de processo na janela da carga. Pico de memória abrange a vida do processo, incluindo imports, preparação e recuperação. Banco é tamanho lógico do arquivo após fechar, não bytes escritos nem consumo total em disco.",
              "", "Consulte ambiente.json, protocolo.json, fontes_sha256.json, execucoes.csv e os CSVs individuais para reprodução. Não extrapolar estes resultados para Ethereum ou Fabric."]
    (pasta / "RESULTADOS.md").write_text("\n".join(texto) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pasta", type=Path)
    parser.add_argument("--leituras", type=int, nargs="+", default=[200, 600])
    parser.add_argument("--lotes", type=int, nargs="+", default=[10, 50])
    parser.add_argument("--repeticoes", type=int, default=3)
    parser.add_argument("--worker", choices=["ledger", "sqlite"], help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.repeticoes < 1 or any(n < 1 for n in args.leituras + args.lotes):
        parser.error("parâmetros devem ser positivos")
    if args.worker:
        executar_worker(args.pasta, args.worker, args.leituras[0], args.lotes[0])
        return
    pasta = args.pasta.resolve()
    pasta.mkdir(parents=True, exist_ok=False)
    protocolo = {"inicio_utc": datetime.now(timezone.utc).isoformat(), "leituras": args.leituras,
                 "lotes": args.lotes, "repeticoes": args.repeticoes, "sensores": 4,
                 "validadores": 3, "aquecimento": "20 assinaturas/verificações sem escrita; fora da janela",
                 "carga": "sequencial, laço fechado, sem espera; banco novo por processo",
                 "latencia": "antes de assinar a leitura até commit do lote; perf_counter_ns",
                 "p95": "nearest rank ceil(0.95*n); média e DP entre repetições",
                 "exclusoes": "imports, chaves, preparação, aquecimento, consulta final, recuperação, HTTP, KDF, painel",
                 "comando": [sys.executable] + sys.argv, "diretorio": str(Path.cwd())}
    gravar_json(pasta / "protocolo.json", protocolo)
    ambiente = {"python": sys.version, "plataforma": platform.platform(), "maquina": platform.machine(),
                "processador": platform.processor(), "cpus_logicas": os.cpu_count(),
                "identificador_processador": os.environ.get("PROCESSOR_IDENTIFIER"),
                "relogio": {"implementacao": time.get_clock_info("perf_counter").implementation,
                            "resolucao_s": time.get_clock_info("perf_counter").resolution},
                "sqlite": sqlite3.sqlite_version, "executavel": sys.executable,
                "bibliotecas": {p: importlib.metadata.version(p) for p in ("cryptography", "Flask", "waitress")}}
    gravar_json(pasta / "ambiente.json", ambiente)
    raiz = Path(__file__).resolve().parent.parent
    fontes = [p for p in raiz.rglob("*") if p.is_file() and p.suffix in (".py", ".js", ".css", ".html", ".svg", ".txt")
              and not any(parte in (".venv", "__pycache__", ".tmp", "resultados", "dados", ".git") for parte in p.relative_to(raiz).parts)]
    gravar_json(pasta / "fontes_sha256.json", {str(p.relative_to(raiz)): hashlib.sha256(p.read_bytes()).hexdigest() for p in fontes})
    gravar_json(pasta / "carga_sha256.json", {str(n): hashlib.sha256(canonico([leitura(i) for i in range(n)])).hexdigest()
                                             for n in args.leituras})
    observacoes = []
    for n in args.leituras:
        for lote in args.lotes:
            for repeticao in range(1, args.repeticoes + 1):
                # Alternância reduz viés de sempre medir o mesmo modo primeiro.
                modos = ("ledger", "sqlite") if repeticao % 2 else ("sqlite", "ledger")
                for modo in modos:
                    destino = pasta / f"{modo}-n{n}-b{lote}-r{repeticao}"
                    print(f"{modo}: {n} leituras, lote {lote}, repetição {repeticao}", flush=True)
                    subprocess.run([sys.executable, str(Path(__file__).resolve()), str(destino),
                                    "--worker", modo, "--leituras", str(n), "--lotes", str(lote)], check=True)
                    obs = json.loads((destino / "medicao.json").read_text(encoding="utf-8"))
                    obs["repeticao"] = repeticao
                    obs["diretorio"] = destino.name
                    observacoes.append(obs)
    integridade(pasta / "integridade")
    consolidar(pasta, observacoes)
    gravar_json(pasta / "CONCLUIDO.json", {"fim_utc": datetime.now(timezone.utc).isoformat(), "execucoes": len(observacoes)})
    print(f"Resultados concluídos: {pasta}")


if __name__ == "__main__":
    main()
