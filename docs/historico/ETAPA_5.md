# Etapa 5: experimentos, evidências e material para o TCC

## Entrega e escopo

Esta etapa acrescenta um experimento local reproduzível, uma comparação com
SQLite convencional, dados brutos, estatísticas descritivas, figuras e texto
complementar para atualizar o manuscrito. O núcleo, a API e o painel das etapas
anteriores permanecem a aplicação utilizada na apresentação.

Status: concluída. A coleta final contém 24 execuções e 9.600 leituras
confirmadas, com uma latência individual registrada para cada leitura. As
impressões das fontes medidas correspondem aos arquivos entregues. Os quatro
cenários de rejeição foram observados; o histórico permaneceu válido após
revogação e o banco foi preservado nas demonstrações em cópia e no replay.

O PDF recebido corresponde à versão inicial do sistema. Como não há fonte
editável disponível, `TEXTO_TCC_ATUALIZADO.md` reúne a redação técnica para
incorporação ao trabalho. O PDF original foi preservado. A revisão bibliográfica
e os requisitos formais da instituição devem ser consolidados pelos autores;
esta etapa não executou redes reais de Ethereum ou Hyperledger Fabric.

## Reproduzir no Windows

Na pasta `blockchain-tcc`, com as dependências da aplicação instaladas:

```powershell
.\.venv\Scripts\python.exe experimentos.py .\resultados\minha-execucao
```

O destino deve ser novo. Uma execução interrompida preserva o que foi coletado;
para repetir, use outro nome. Somente a presença de `CONCLUIDO.json` identifica
uma coleta completa. O comando padrão realiza 24 execuções: dois volumes,
dois tamanhos de lote, dois modos e três repetições por combinação.

Para escolher uma carga maior, depois de avaliar o tempo necessário:

```powershell
.\.venv\Scripts\python.exe experimentos.py .\resultados\carga-maior --leituras 1000 2000 --lotes 10 50 --repeticoes 5
```

Isso mede novos cenários e não reproduz os valores da coleta entregue. O custo
da revalidação integral pode tornar grandes históricos demorados. Registre
mudanças de ambiente e evite instalações, cargas concorrentes e sincronização
intensiva durante a coleta. Não há leitura dos dados de demonstração da API.

As figuras são geradas **depois** de medir. A dependência gráfica é opcional:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-experimentos.txt
.\.venv\Scripts\python.exe figuras_experimentos.py .\resultados\minha-execucao
```

Instale a dependência antes de iniciar uma nova coleta. O benchmark não importa
Matplotlib, não abre navegador e não inicia servidor HTTP.

## Desenho experimental

| Elemento | Definição |
|---|---|
| Unidade de observação | Execução completa em processo Python novo, banco inicialmente vazio |
| Volume | 200 e 600 leituras por execução |
| Agrupamento | 10 e 50 leituras por commit; bloco no ledger, transação SQL no controle |
| Repetições | Três por combinação, sem descartar resultados |
| Dispositivos | Quatro sensores sintéticos de temperatura |
| Autoridades | Três identidades em rodízio local |
| Emissão | Sequencial, em laço fechado, sem intervalo artificial |
| Aquecimento | 20 assinaturas e verificações antes da janela, sem escrita no banco medido |
| Ordem | Ledger/SQLite alternados entre repetições dentro de cada cenário |
| Chaves | Geradas por processo, mantidas apenas em memória |
| Conteúdo | Valores, identificadores, timestamps e unidades determinísticos por índice |
| Assinatura | Ed25519 incluída nos dois modos; chaves diferentes, tamanho de assinatura igual |
| Instrumentação | `perf_counter_ns`, `process_time_ns` e pico de memória do processo |

A quantidade por bloco é variável independente. O volume total também é
variável independente. Não se trata de uma avaliação de taxas de chegada,
clientes concorrentes, saturação de rede ou disponibilidade de nós.

### Controle em SQLite

O controle armazena o mesmo JSON de transação assinada em uma tabela `leituras`
com chave primária para o identificador. Utiliza o mesmo SQLite, diretório,
volume e tamanho de lote. Ambos usam os valores efetivos de `journal_mode`,
`synchronous` e `page_size` registrados em cada `medicao.json`.

O ledger utiliza `Cadeia` e `Armazenamento` da aplicação, incluindo validação
histórica, verificações de assinatura, autorização, prevenção de replay,
canonicalização, produção de bloco e commit. O controle não reimplementa essas
garantias: seus custos não são equivalentes aos de uma blockchain. A diferença
observada representa o conjunto de mecanismos; não isola o custo causal de
SHA-256, Ed25519 ou um método individual.

A preparação cria as mesmas identidades e um ledger inicial nos dois modos;
no controle, os dados medidos vão para um segundo banco convencional. O tamanho
reportado considera apenas o banco de dados medido, excluindo esse banco de
preparação. Essa preparação fica fora da janela de tempo e faz parte do pico
de memória do processo.

### Métricas

- **Confirmação:** retorno do método que conclui o commit local. Não equivale
  a consenso nem a garantia de recuperação após perda de energia do hardware.
- **TPS:** número de leituras confirmadas dividido pelo tempo da carga inteira,
  do primeiro lote ao último commit. Inclui assinatura, processamento, gravação
  e instrumentação do laço; exclui preparação e consulta posterior.
- **Latência individual:** imediatamente antes de construir e assinar a leitura
  até o retorno do commit do seu lote. Inclui a espera pelas demais leituras
  daquele lote. Não usa o relógio declarado pelo sensor para medir duração.
- **Média e mediana:** calculadas a partir das latências da execução.
- **P95:** posição `ceil(0,95 × N)` no vetor ordenado, contando de 1. A tabela
  apresenta a média dos P95 das três execuções, não um percentil combinado.
- **CPU:** diferença de tempo de CPU do processo na mesma janela. O percentual
  em `execucoes.csv` é relativo a um núcleo, não à capacidade total do computador.
  A resolução do contador no Windows limita a precisão de intervalos curtos.
- **Memória:** pico de working set no Windows, em MiB, abrangendo toda a vida
  do processo até depois da recuperação, inclusive imports e preparação. Não
  corresponde à memória incremental da carga nem ao total da aplicação com API.
- **Banco:** tamanho lógico do arquivo fechado, em bytes. Não mede escritas
  físicas, amplificação de escrita, journal temporário ou espaço de todo o projeto.
- **Validação final:** duração de `Cadeia.validar()` após a carga, fora da janela
  de TPS. Não aplicável ao controle sem validação criptográfica.
- **Recuperação:** abrir, carregar e validar o ledger; no SQLite, abrir e carregar
  todos os JSONs ordenados. As operações têm garantias diferentes e são descritas
  como tal; não incluem descriptografia de cofre ou abertura da interface.

Os tempos dos lotes ajudam a observar a evolução do custo ao longo do histórico.
Não são latências independentes de todos os fatores: incluem assinatura e
submissão do lote, validação da cadeia, assinatura do bloco e persistência.

## Evidências entregues

Use `resultados/execucao-final/` como coleta de referência. `execucao-01` foi
um piloto de preparação e não compõe as tabelas ou conclusões finais.

| Arquivo | Conteúdo |
|---|---|
| `RESULTADOS.md` | Tabela legível com médias e desvios padrão |
| `execucoes.csv` | Uma linha por execução, preservando as 24 observações |
| `resumo.csv` | Estatísticas por combinação, sem misturar cenários |
| `<modo>-n...-b...-r.../latencias.csv` | Latência de cada leitura, com número do lote |
| `<modo>-n...-b...-r.../lotes.csv` | Tempo de cada lote e contagem acumulada |
| `<modo>-n...-b...-r.../medicao.json` | Métricas e configuração SQLite da execução |
| `ambiente.json` | Sistema, Python, CPU, bibliotecas e resolução do relógio |
| `protocolo.json` | Parâmetros, comando, exclusões e data UTC |
| `fontes_sha256.json` | Impressões dos arquivos de implementação e dependências |
| `carga_sha256.json` | Impressões dos conteúdos lógicos das cargas sem assinatura |
| `integridade/integridade.json` | Resultados dos cenários de adulteração, replay e revogação |
| `figura_desempenho.png` e `.svg` | Figuras exportáveis para apresentação/manuscrito |
| `CONCLUIDO.json` | Encerramento bem-sucedido da coleta completa |

Os bancos exclusivos dos experimentos ficam localmente para inspeção. Não
contêm chaves privadas. A ausência de cache frio controlado, a execução em
Windows e o diretório no OneDrive devem ser considerados na interpretação.
Os hashes das fontes não constituem assinatura digital nem certificação externa.

## Integridade e aplicação

O roteiro experimental também exige rejeição da alteração de valor, da alteração
com recálculo do hash, do reenvio de transação confirmada e de uma nova leitura
de sensor revogado. Exige ainda que o histórico permaneça válido após revogação.
Antes da revogação legítima, compara o hash do arquivo SQLite para confirmar
que as cópias adulteradas e o reenvio recusado não escreveram no banco.

Esses cenários são executados em banco separado. Não são novos testes unitários
nem prova formal de segurança. A referência funcional permanece a suíte de
110 testes aprovada na etapa 4; esta etapa não altera os módulos da aplicação.

## Limitações e continuidade acadêmica

Três repetições oferecem estatística descritiva preliminar. Não sustentam
significância estatística, capacidade máxima ou uma garantia operacional de
latência. Não foram controlados frequência da CPU, carga de fundo, antivírus,
cache do sistema de arquivos ou sincronização do OneDrive. Não se mediu energia.

Não foram incluídos rede, API, atualização do painel, descriptografia das chaves,
sensores físicos, ataques distribuídos nem múltiplos nós. Pendências continuam
voláteis; não existe checkpoint externo contra truncamento do ledger. A
assinatura prova vínculo com uma chave, sem provar a veracidade física do valor.

O roteiro de defesa e as sugestões de redação estão em `ROTEIRO_DEFESA.md` e
`TEXTO_TCC_ATUALIZADO.md`. As cinco etapas técnicas estão entregues no escopo
local definido. A incorporação ao documento institucional e a consolidação da
revisão bibliográfica continuam sendo atividades de redação dos autores.
