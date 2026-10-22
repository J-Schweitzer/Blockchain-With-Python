# Resultados observados da etapa 5

Médias de repetições independentes. P95 é calculado em cada execução e depois agregado; não é o P95 combinado.

| Modo | Leituras | Lote | Repetições | TPS (média ± DP) | Latência média (ms) | P95 médio (ms) | CPU (s) | Pico processo (MiB) | Banco (KiB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ledger | 200 | 10 | 3 | 187.34 ± 18.57 | 52.013 | 81.844 | 0.807 | 31.75 | 104.0 |
| sqlite | 200 | 10 | 3 | 773.69 ± 15.46 | 12.148 | 16.161 | 0.094 | 31.59 | 100.0 |
| ledger | 200 | 50 | 3 | 675.37 ± 83.43 | 66.121 | 102.368 | 0.229 | 31.77 | 84.0 |
| sqlite | 200 | 50 | 3 | 3135.89 ± 237.07 | 12.881 | 17.902 | 0.042 | 31.53 | 100.0 |
| ledger | 600 | 10 | 3 | 61.31 ± 7.84 | 162.616 | 329.223 | 7.120 | 33.09 | 284.0 |
| sqlite | 600 | 10 | 3 | 822.52 ± 6.93 | 11.464 | 16.306 | 0.302 | 32.83 | 280.0 |
| ledger | 600 | 50 | 3 | 320.10 ± 63.50 | 149.602 | 321.239 | 1.391 | 32.70 | 228.0 |
| sqlite | 600 | 50 | 3 | 3284.37 ± 198.81 | 12.657 | 16.402 | 0.115 | 32.45 | 280.0 |

A assinatura da leitura está incluída nos dois modos. O ledger também verifica autorização, replay, histórico e assinaturas e produz blocos assinados. SQLite armazena o mesmo JSON assinado, sem essas garantias.

Confirmação: retorno do commit local. A carga é sequencial, sem intervalo artificial, e o agrupamento é igual nos dois modos. Não mede filas de rede, HTTP, painel ou consenso distribuído.

CPU é tempo de processo na janela da carga. Pico de memória abrange a vida do processo, incluindo imports, preparação e recuperação. Banco é tamanho lógico do arquivo após fechar, não bytes escritos nem consumo total em disco.

Consulte ambiente.json, protocolo.json, fontes_sha256.json, execucoes.csv e os CSVs individuais para reprodução. Não extrapolar estes resultados para Ethereum ou Fabric.
