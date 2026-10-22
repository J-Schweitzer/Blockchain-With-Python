# Complemento técnico para atualização do TCC

Este arquivo propõe a atualização das seções técnicas do PDF recebido. Não
substitui o trabalho completo nem altera sua revisão bibliográfica. Os títulos
abaixo correspondem às seções que precisam ser revisadas. Os dados referem-se
à versão evoluída em Windows; a execução anterior com 13 testes em Linux deve
permanecer identificada como evidência histórica, se for mantida no texto.

## Resumo das mudanças necessárias

| Local no PDF | Atualização proposta |
|---|---|
| Resumo e introdução | Mencionar API local, painel e avaliação experimental, sem apresentar o protótipo como rede distribuída |
| 4.3 e 4.5 | Ampliar os critérios de recuperação, identidade, anti-replay e descrição dos módulos |
| 4.6 | Separar o ambiente inicial em Linux da versão evoluída em Windows |
| 4.7 | Substituir plano futuro pelo protocolo executado abaixo |
| 5.1 a 5.7 e Tabela 3 | Atualizar arquitetura, transações, cadastro, cofre, API, painel e ordem de persistência |
| Figuras 2 e 3 | Incluir API/painel, registro persistente e commit anterior à alteração em memória |
| 5.8 e 5.9 | Atualizar controles existentes, mantendo limites do modelo local e do administrador |
| 6.1, 6.2 e Tabela 4 | Identificar os 110 testes da etapa 4; chave falsa passa a ser recusada antes da gravação |
| 6.3 | Incluir resultados medidos, com definições e limitações |
| 8.1 a 8.3 | Rever limitações já corrigidas e acrescentar ameaças à validade experimental |
| 10 | Atualizar entregas, resultados e trabalhos futuros |

As citações e a comparação de Ethereum/Fabric do documento original precisam
de revisão bibliográfica própria. Os resultados abaixo não validam números
de plataformas externas ou alegações jurídicas.

## 4.7 Protocolo de avaliação de desempenho — redação proposta

A versão evoluída foi avaliada por meio de experimentos locais controlados,
com dois volumes de dados, 200 e 600 leituras, e dois tamanhos de agrupamento,
10 e 50 leituras por confirmação. Foram realizadas três repetições por
combinação para dois modos: ledger Python com persistência SQLite e controle
convencional em SQLite. O desenho totalizou 24 execuções. Cada execução foi
realizada em um processo Python novo e em banco exclusivo, inicialmente vazio.
Os modos foram alternados entre repetições para reduzir o efeito de uma ordem
fixa de execução. Não houve descarte de observações.

Quatro dispositivos simulados emitiram leituras de temperatura. Os valores,
identificadores, unidades e timestamps foram definidos deterministicamente
por índice, assegurando o mesmo conteúdo lógico nos cenários comparáveis.
As chaves Ed25519 foram geradas por processo e mantidas em memória. Ambos os
modos assinaram as leituras durante a janela medida. O controle persistiu o
JSON assinado, enquanto o ledger também executou as verificações de identidade,
replay, assinaturas e histórico, o encadeamento, a assinatura do produtor e a
persistência dos blocos. A comparação, portanto, representa conjuntos de
operações com garantias diferentes, sem isolar o custo de cada mecanismo.

A carga foi sequencial, sem intervalo artificial entre leituras, e não modelou
clientes concorrentes nem taxas externas de chegada. A confirmação foi definida
como o retorno do commit local. O throughput correspondeu ao número de leituras
confirmadas dividido pela duração da carga, medida com relógio monotônico de
alta resolução. A latência individual começou imediatamente antes da construção
e assinatura da leitura e terminou no retorno do commit de seu lote. Assim,
a latência incluiu a espera pelas demais leituras do mesmo lote. O timestamp
declarado no conteúdo da leitura não foi usado para medir essa duração.

Para cada execução foram obtidos média, mediana e percentil 95 das latências,
tempo de CPU, pico de memória do processo e tamanho do arquivo de dados após
o fechamento. O P95 foi calculado pelo método nearest rank, na posição
ceil(0,95 × N) dos valores ordenados. Os resultados agregados apresentam média
e desvio padrão amostral entre repetições. A média dos P95 não representa o
percentil de uma população formada pela combinação de todas as latências.

Preparação do banco, geração das chaves, aquecimento, consultas finais e
recuperação ficaram fora da janela de throughput. O aquecimento consistiu em
20 assinaturas e verificações, sem gravações no banco medido. A instrumentação
do laço integrou a duração medida. A recuperação e a validação integral posterior
foram cronometradas separadamente. HTTP, painel, descriptografia do cofre,
sensores físicos, rede entre nós e consenso distribuído não foram medidos.

A coleta de referência iniciou-se em 22 de outubro de 2026, às 02:01:49 UTC,
correspondente a 21 de outubro às 22:01:49 em Cuiabá. O ambiente reportou Windows
11, Python 3.12.14, cryptography 50.0.2, SQLite 3.53.1, arquitetura AMD64 e
12 CPUs lógicas. O processador foi identificado como Intel64 Family 6 Model
186 Stepping 2. Nos dois modos, o SQLite reportou journal_mode DELETE,
synchronous 2 e páginas de 4096 bytes. O diretório utilizado está no OneDrive.
Os comandos, versões, configurações e impressões SHA-256 dos arquivos de
implementação e das cargas lógicas foram preservados junto aos resultados.

## 5 Arquitetura e implementação — redação proposta

### 5.1 Visão geral

A versão de apresentação compreende o núcleo de ledger local, o cadastro
versionado de identidades, um cofre de chaves cifradas, persistência SQLite,
API HTTP autenticada, simulador de dispositivos e painel web. A API e o painel
executam no computador do operador. As leituras são sintéticas e não dependem
de sensores físicos. As três autoridades são identidades em um processo local;
não correspondem a nós independentes comunicando-se por rede.

O dispositivo cria e assina a leitura. O núcleo verifica estrutura, rede,
autorização, assinatura e duplicidade antes de incluí-la na fila. A produção
de bloco revalida o histórico, confere a autoridade prevista no rodízio, calcula
o hash do conteúdo e assina esse hash. O candidato é validado antes da gravação.
O commit no SQLite precede a atualização do histórico em memória e a limpeza
das pendências. Essa ordem preserva as pendências quando a gravação falha.

**Figura 2 — composição sugerida:** dispositivo simulado e cofre do sensor →
transação assinada → API e serviço serializado → núcleo e cadastro versionado →
bloco assinado → SQLite. O painel acessa consultas e operações administrativas
da mesma API. O cofre de autoridades permanece no processo local. A figura
deve identificar a fronteira de confiança administrativa e a ausência de P2P.

### 5.2 Transação e serialização

As transações possuem versão, identificador único, identificador de rede,
dispositivo, valor textual, timestamp e assinatura. A versão 3 inclui também
os metadados de grandeza e unidade. Esses campos integram o conteúdo assinado
em JSON canônico com chaves ordenadas e codificação UTF-8. A versão 2 continua
aceita para registros sem metadados de medição, segundo seu esquema próprio.

O identificador é usado para recusar reenvios de transações pendentes ou
confirmadas. O identificador da rede impede aceitação em outra configuração
local sem uma assinatura correspondente. A prevenção de replay não equivale
a uma política completa de atualidade temporal: o relógio do dispositivo
continua sendo uma informação declarada, sem prova do instante físico.

O valor permanece textual. O painel interpreta valores numéricos para gráficos,
mas não altera o conteúdo assinado. Grandezas e unidades são apresentadas
separadamente. O programa não comprova calibração, qualidade do sensor ou
plausibilidade física de uma leitura autenticada.

### 5.3 Blocos, encadeamento e validação

Os blocos regulares contêm índice, timestamp, transações, hash anterior,
autoridade produtora, assinatura, hash, versão e identificadores da rede,
da versão de cadastro e da governança. O hash da versão de cadastro associa
o bloco às regras de identidade vigentes em sua altura. A governança registra
a rede e a lista ordenada de validadores. O gênese segue um modelo fixo.

A validação verifica estrutura, sequência, encadeamento, conteúdo e hash,
produtor permitido e assinaturas. A chave de um produtor que usa o nome de
uma autoridade conhecida também precisa corresponder ao cadastro. A versão
evoluída recusa esse candidato antes de persistir, atualizando o comportamento
anterior que dependia da detecção posterior.

O histórico é validado integralmente antes de produzir cada novo bloco. Essa
estratégia favorece clareza e detecção de inconsistências, mas repete trabalho
conforme o histórico cresce. As medições avaliam seu custo no conjunto da
aplicação. Não há árvore de Merkle ou mecanismo de prova de inclusão compacta.

### 5.4 Identidades e controle de acesso

O registro persiste versões de membros por altura de bloco. Revogações e
trocas de chave passam a valer no próximo bloco, enquanto a validação de
eventos anteriores consulta a versão histórica correspondente. A política
preserva a validade dos registros anteriores à revogação. O timestamp do
sensor não determina qual versão de autorização é aplicada.

As chaves operacionais são armazenadas em PKCS8 cifrado, protegido pela senha
fornecida ao programa. O mecanismo de exportação bruta existente para testes
e interoperabilidade não é usado como persistência operacional. A proteção
por senha não substitui controle de acesso ao computador, backup seguro ou
proteção contra comprometimento do processo enquanto as chaves estão em uso.

O cadastro é administrado localmente. Não existe votação distribuída para
admitir membros, autoridade certificadora completa ou gestão institucional de
credenciais equivalente à de plataformas de produção.

### 5.5 Persistência e recuperação

SQLite armazena os blocos e a configuração, incluindo versões do cadastro e
lista de validadores. A abertura reconstrói o estado e valida o ledger antes
de disponibilizá-lo. Falhas de estrutura, divergência entre índice SQL e bloco
ou inconsistências criptográficas provocam recusa da recuperação.

As pendências permanecem em memória e são perdidas ao encerrar o processo.
A recuperação cobre o histórico confirmado e sua configuração, sem constituir
replicação, backup externo ou tolerância a falhas de nós. Também não há um
checkpoint confiável externo que assegure a detecção de todo truncamento do
final do ledger.

### 5.6 Fluxo de uma leitura

**Figura 3 — sequência atualizada:** (1) construir e assinar a leitura;
(2) autenticar a chamada e validar esquema, identidade, rede e assinatura;
(3) verificar duplicidade e publicar na fila; (4) validar histórico e selecionar
a autoridade da vez; (5) construir e assinar o bloco; (6) validar o candidato;
(7) confirmar no SQLite; (8) atualizar memória e limpar pendências.

Consultas apresentam o histórico confirmado, detalhes de blocos e identidades.
O painel inclui laboratório que altera somente uma cópia dos blocos em memória.
O laboratório mostra que a alteração invalida o hash e que o recálculo do hash
invalida a assinatura original do produtor, preservando a cadeia original.

### 5.7 Módulos e fronteiras

| Componente | Responsabilidade |
|---|---|
| `identidade.py`, `cofre.py` | Assinaturas, papéis, cadastro versionado e material de chave cifrado |
| `formato.py`, `nucleo.py` | Canonicalização, hashes, transações, blocos, validação, replay e histórico |
| `armazenamento.py`, `sistema.py` | Persistência, configuração e recuperação da aplicação local |
| `servico.py`, `api.py`, `-m blockchain_tcc.iniciar_api` | Coordenação serializada, autenticação administrativa e HTTP local |
| `cliente_api.py`, `simulador_iot.py` | Envio de leituras assinadas e simulação de medições |
| `painel/` | Interface local para consulta, administração e demonstração |
| `experimentos.py`, `figuras_experimentos.py` | Coleta isolada e geração posterior de figuras |

As operações de dados exigem token administrativo na API. A interface de
acesso e seus recursos estáticos não expõem dados do ledger. O token permanece
somente em memória da aba. O serviço inclui limites de requisições e da fila,
sem pretensão de comprovar resistência a negação de serviço. O modo explícito
de apresentação habilita a geração local e o laboratório em cópia.

### 5.8 e 5.9 Limites e modelo de ameaça

Os cenários avaliados contemplam alteração de conteúdo, hash recalculado,
assinatura inválida, identidade sem autorização, chave falsa, reenvio de leitura,
revogação e inconsistências na persistência. Esses controles não demonstram
segurança formal ou proteção diante de todo comportamento de um administrador
que controle processo, banco e chaves. Uma reescrita completa autorizada pelas
chaves comprometidas está fora das garantias demonstradas.

O sistema não implementa P2P, replicação, consenso distribuído, tolerância a
partições ou disponibilidade após perda de nós. Não comprova a veracidade
física das leituras, não substitui governança operacional e não garante
conformidade jurídica pelo uso de hashes ou assinaturas. A pendência volátil
e a ausência de checkpoint externo continuam limitações explícitas.

## 6 Resultados — redação proposta

### 6.1 e 6.2 Evidências funcionais

A evolução foi organizada em etapas. A primeira consolidou o núcleo e atingiu
29 testes; a segunda acrescentou estado recuperável e identidades, totalizando
62; a terceira acrescentou API e simulador, atingindo 95; e a quarta entregou
o painel e o laboratório, com 110 testes aprovados. Esses números são totais
acumulados de cada etapa, e não quantidades a somar. A etapa experimental não
acrescentou nem reexecutou a suíte unitária: utilizou o núcleo preservado e
executou cargas e cenários próprios de consistência.

Na coleta experimental, a alteração de valor foi rejeitada por divergência
entre conteúdo e hash. Após o recálculo, foi rejeitada pela assinatura do
validador. O reenvio de transação confirmada e a nova leitura de um sensor
revogado foram recusados. A cadeia histórica permaneceu válida após revogação.
O hash do arquivo SQLite permaneceu igual antes e depois das cópias adulteradas
e do replay recusado, antes da gravação legítima da revogação.

Esses resultados caracterizam comportamentos selecionados. Não representam
medição de cobertura de linhas, prova formal, ataque de rede ou validação da
veracidade física de dados. A demonstração visual revisada na etapa 4 utiliza
a mesma API e permite expor essas distinções durante a defesa.

### 6.3 Resultados de desempenho

A Tabela 5 apresenta os resultados da coleta de referência. TPS refere-se a
leituras confirmadas por segundo; o P95 apresentado é a média dos percentis
calculados individualmente nas três execuções. DP indica desvio padrão amostral.

| Modo | Leituras | Lote | TPS, média ± DP | Latência média (ms) | P95 médio (ms) |
|---|---:|---:|---:|---:|---:|
| Ledger | 200 | 10 | 187,34 ± 18,57 | 52,013 | 81,844 |
| SQLite | 200 | 10 | 773,69 ± 15,46 | 12,148 | 16,161 |
| Ledger | 200 | 50 | 675,37 ± 83,43 | 66,121 | 102,368 |
| SQLite | 200 | 50 | 3.135,89 ± 237,07 | 12,881 | 17,902 |
| Ledger | 600 | 10 | 61,31 ± 7,84 | 162,616 | 329,223 |
| SQLite | 600 | 10 | 822,52 ± 6,93 | 11,464 | 16,306 |
| Ledger | 600 | 50 | 320,10 ± 63,50 | 149,602 | 321,239 |
| SQLite | 600 | 50 | 3.284,37 ± 198,81 | 12,657 | 16,402 |

Fonte: `resultados/execucao-final/resumo.csv`; três repetições por linha.

Em ambos os volumes, os lotes maiores apresentaram maior taxa de confirmação
no ledger. O aumento não implicou redução uniforme de latência: com 200
leituras, o lote de 50 apresentou latência média superior à do lote de 10.
Isso ilustra a influência do agrupamento e da espera dentro do lote.

No ledger com lote de 10, a taxa média caiu de 187,34 para 61,31 leituras/s ao
passar de 200 para 600 leituras por execução. Com lote de 50, caiu de 675,37
para 320,10 leituras/s. Essa observação é compatível com a revalidação integral
do histórico antes de cada bloco e com outras varreduras realizadas pelo núcleo.
O experimento não instrumentou cada método separadamente e não permite atribuir
a variação exclusivamente a um deles.

A validação integral final do ledger levou, em média, 80,029 ms e 278,003 ms
nos volumes de 200 e 600 com lote de 10. Com lote de 50, levou 60,765 ms e
167,046 ms. Diferentes quantidades de blocos, serialização e variações de
ambiente também contribuem para essas medidas. O gráfico temporal preserva
picos observados nos lotes, sem removê-los como outliers.

O tempo médio de CPU durante a carga variou de 0,229 a 7,120 s no ledger e
de 0,042 a 0,302 s no controle. O pico de memória do processo variou de 31,75
a 33,09 MiB no ledger e de 31,53 a 32,83 MiB no controle. Como o pico inclui
imports, preparação e recuperação, esses números não isolam a memória adicional
da carga. O tamanho dos bancos do ledger variou de 84 a 284 KiB; no controle,
foi de 100 KiB para 200 leituras e 280 KiB para 600. A organização dos dados e
a quantidade de linhas são diferentes, portanto o tamanho não mede diretamente
o custo das garantias criptográficas.

O controle SQLite apresentou maior throughput nos cenários avaliados. A
interpretação está limitada às operações medidas: ele armazena as leituras
assinadas, sem validar o histórico ou construir blocos. A diferença não deve
ser apresentada como comparação entre SQLite e toda blockchain possível.

**Figura 4 sugerida:** inserir `figura_desempenho.svg` ou o PNG correspondente.
Legenda: taxa de confirmação, P95, validação final e duração dos lotes no
protótipo local; barras representam média ± desvio padrão entre três repetições;
os valores não medem Ethereum, Hyperledger Fabric ou consenso distribuído.

### 6.4 Comparação bibliográfica

Manter a comparação das plataformas identificada como componente bibliográfico.
As medições do protótipo e de seu controle SQLite formam um experimento local
distinto. Não inserir seus números em um ranking com resultados de Ethereum
ou Fabric obtidos em cargas, redes e ambientes diferentes.

## 8.3 Ameaças à validade — complemento proposto

A validade interna pode ser afetada por erros de instrumentação, resolução do
tempo de CPU, cache, frequência dinâmica, antivírus, tarefas de fundo e
sincronização do diretório OneDrive. A preparação das ferramentas gráficas
precedeu a coleta final; uma execução piloto anterior foi preservada e excluída
da consolidação. Não houve isolamento completo da máquina ou cache frio
controlado. A alternância dos modos reduz apenas parte do viés de ordem.

A validade de construto depende da definição de confirmação. Mediu-se o retorno
do commit local, não entrega em sensor físico, confirmação em múltiplos nós,
finalidade econômica ou recuperação após perda de energia. A assinatura foi
incluída nos dois modos, mas a descriptografia das chaves e o caminho HTTP não
foram incluídos. A memória representa o pico do processo completo, sem equivaler
à memória incremental da carga ou ao consumo da interface com servidor.

A validade externa é limitada por um computador, um sistema operacional,
dados sintéticos, quatro identidades de sensores, três autoridades locais,
dois volumes pequenos e três repetições por combinação. Não foram estimados
intervalos de confiança ou significância estatística. Os resultados são
descritivos e não definem capacidade máxima ou limite operacional de latência.

A validade de segurança permanece restrita aos cenários executados. Não foram
avaliados comprometimento de sistema operacional, roubo de chaves, falhas de
hardware ou adversários distribuídos. A revisão bibliográfica mantém suas
próprias exigências de seleção, extração e rastreabilidade das fontes.

## 10 Conclusão — redação proposta

O trabalho evoluiu um protótipo Python de integridade e rastreabilidade de dados
IoT, com SHA-256, assinaturas Ed25519, cadastro versionado, chaves cifradas,
prevenção de replay, persistência SQLite, API autenticada, simulador e painel.
A sequência de desenvolvimento consolidou 110 testes funcionais na etapa 4 e
produziu uma avaliação local com 24 execuções de carga na etapa experimental.

Os cenários executados demonstraram rejeição de adulterações, replay e novas
operações de um sensor revogado, com preservação da validade histórica. Os
experimentos mostraram diferenças de throughput e latência conforme volume e
agrupamento, além de custo crescente associado ao processamento de históricos
maiores. O controle SQLite foi mais rápido nas operações medidas, executando
um conjunto menor de verificações. Os resultados são reproduzíveis pelo código
e pelos dados brutos fornecidos, com variação esperada entre ambientes.

O protótipo continua local, sem replicação ou consenso entre nós independentes.
Seus resultados não representam desempenho de Ethereum ou Hyperledger Fabric
e não comprovam veracidade física das medições. Entre as extensões de pesquisa
estão persistência de pendências, checkpoint confiável externo, avaliação de
concorrência e do caminho HTTP, instrumentação por componente e integração
com sensores reais. Uma avaliação distribuída exigirá protocolo explícito,
implantação de múltiplos nós e outro desenho experimental.

Integridade, autoria, autorização, rastreabilidade, consenso, disponibilidade e
veracidade física são propriedades relacionadas com garantias distintas. A
contribuição do protótipo é tornar esses mecanismos observáveis em uma aplicação
local e fornecer evidências funcionais e experimentais delimitadas por código,
configuração, carga e ambiente de execução.
