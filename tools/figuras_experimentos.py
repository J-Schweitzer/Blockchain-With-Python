"""Gera figuras de uma execução concluída, sem repetir a carga medida."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pasta", type=Path)
    args = parser.parse_args()
    pasta = args.pasta.resolve()
    if not (pasta / "CONCLUIDO.json").is_file():
        parser.error("a execução precisa estar concluída")
    with (pasta / "resumo.csv").open(encoding="utf-8-sig", newline="") as arq:
        dados = list(csv.DictReader(arq))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "savefig.dpi": 180, "svg.fonttype": "none"})
    cores = {"ledger": "#26766b", "sqlite": "#526eab"}
    cenarios = sorted({(int(d["leituras"]), int(d["por_lote"])) for d in dados})
    fig, eixos = plt.subplots(2, 2, figsize=(13, 9), layout="constrained")
    for eixo, metrica, titulo, unidade in (
        (eixos[0, 0], "tps", "Taxa de confirmação local", "Leituras confirmadas / segundo"),
        (eixos[0, 1], "latencia_p95_ms", "Latência P95 por execução", "Milissegundos (escala log)")):
        for modo, offset, label in (("ledger", -.18, "Ledger local"), ("sqlite", .18, "SQLite convencional")):
            linhas = [next(d for d in dados if d["modo"] == modo and
                           (int(d["leituras"]), int(d["por_lote"])) == c) for c in cenarios]
            eixo.bar([i + offset for i in range(len(cenarios))],
                     [float(d[metrica + "_media"]) for d in linhas], width=.34,
                     yerr=[float(d[metrica + "_desvio"] or 0) for d in linhas],
                     color=cores[modo], label=label, capsize=3)
        eixo.set_xticks(range(len(cenarios)), [f"N={n}\nlote={l}" for n, l in cenarios])
        eixo.set(title=titulo, ylabel=unidade)
        eixo.grid(axis="y", alpha=.2)
        eixo.set_axisbelow(True)
        eixo.legend(frameon=False, fontsize=9)
    eixos[0, 1].set_yscale("log")
    eixo = eixos[1, 0]
    lotes = sorted({c[1] for c in cenarios})
    for lote in lotes:
        linhas = sorted([d for d in dados if d["modo"] == "ledger" and int(d["por_lote"]) == lote], key=lambda d: int(d["leituras"]))
        eixo.errorbar([int(d["leituras"]) for d in linhas], [float(d["validar_final_ms_media"]) for d in linhas],
                      yerr=[float(d["validar_final_ms_desvio"] or 0) for d in linhas],
                      marker="o", capsize=3, label=f"Lote {lote}")
    eixo.set(title="Validação integral após a carga", xlabel="Leituras no histórico", ylabel="Milissegundos")
    eixo.legend(frameon=False)
    eixo.grid(alpha=.2)
    eixo = eixos[1, 1]
    n, lote = max(c[0] for c in cenarios), min(c[1] for c in cenarios)
    for caminho in sorted(pasta.glob(f"ledger-n{n}-b{lote}-r*/lotes.csv")):
        with caminho.open(encoding="utf-8-sig", newline="") as arq:
            linhas = list(csv.DictReader(arq))
        eixo.plot([int(d["confirmadas"]) for d in linhas], [float(d["tempo_ms"]) for d in linhas],
                  alpha=.8, linewidth=1.1, label=caminho.parent.name.rsplit("-", 1)[1])
    eixo.set(title=f"Tempo por lote ao longo do histórico (N={n}, lote={lote})",
             xlabel="Leituras já confirmadas", ylabel="Milissegundos por lote")
    eixo.legend(frameon=False)
    eixo.grid(alpha=.2)
    fig.suptitle("Experimentos do protótipo Python · processo local e persistência SQLite", fontsize=15)
    fig.supxlabel("Barras: média ± desvio padrão entre repetições. Carga sequencial; assinatura incluída nos dois modos.\n"
                  "Resultados deste computador; não representam Ethereum, Fabric ou consenso distribuído.", fontsize=10)
    for extensao in ("png", "svg"):
        fig.savefig(pasta / f"figura_desempenho.{extensao}")
    plt.close(fig)
    (pasta / "figura_ambiente.json").write_text(json.dumps({"matplotlib": matplotlib.__version__}, indent=2), encoding="utf-8")
    print(pasta / "figura_desempenho.png")


if __name__ == "__main__":
    main()
