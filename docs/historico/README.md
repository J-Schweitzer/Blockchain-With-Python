# Blockchain para o TCC

Versão de desenvolvimento iniciada a partir da base da Área de Trabalho.
A arquitetura inicial corresponde à seção 5 do manuscrito: dispositivos
simulados assinam leituras com Ed25519, o núcleo forma blocos com SHA-256,
autoridades produzem blocos em rodízio e o SQLite persiste o ledger.

**Cinco etapas técnicas concluídas no escopo local.** O sistema funciona localmente, com painel
visual, API Python, simulador IoT e recuperação do estado persistido.
Consulte [ETAPA_5.md](ETAPA_5.md) para os experimentos, resultados e reprodução;
[TEXTO_TCC_ATUALIZADO.md](TEXTO_TCC_ATUALIZADO.md) para a redação complementar
ao PDF original; e [ROTEIRO_DEFESA.md](ROTEIRO_DEFESA.md) para a demonstração.
Consulte [ETAPA_4.md](ETAPA_4.md) para o painel e o laboratório de integridade,
[ETAPA_3.md](ETAPA_3.md) para o contrato HTTP e o roteiro da API,
[ETAPA_2.md](ETAPA_2.md) para a política de revogação e o formato persistente,
e [ANALISE_E_PLANO.md](ANALISE_E_PLANO.md) para o plano completo.

## Experimentos e resultados

A coleta de referência está em [RESULTADOS.md](resultados/execucao-final/RESULTADOS.md):
24 execuções, volumes de 200/600 leituras, lotes de 10/50 e três repetições por
modo/cenário, comparando o ledger com armazenamento convencional em SQLite.
Os dados brutos e as figuras ficam na mesma pasta. A suíte de 110 testes foi
aprovada na etapa 4; a etapa 5 realizou experimentos próprios, sem reexecutá-la.

Para repetir a coleta em uma pasta nova:

```powershell
.\.venv\Scripts\python.exe experimentos.py .\resultados\nova-execucao
```

Para gerar as figuras, instale a dependência opcional antes de medir:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-experimentos.txt
.\.venv\Scripts\python.exe figuras_experimentos.py .\resultados\nova-execucao
```

As medições avaliam o núcleo com persistência local. Não incluem HTTP, painel,
descriptografia do cofre ou redes distribuídas. O texto do TCC deve preservar
essas definições; não se trata de um benchmark de Ethereum/Fabric.

## Executar no Windows

Abra um terminal nesta pasta, com Python instalado:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe demo.py
.\.venv\Scripts\python.exe -m unittest -v
```

A demonstração cria três blocos com leituras simuladas e mostra a detecção
de uma adulteração deliberada. Ela usa memória; a persistência SQLite é
exercitada nos testes. As chaves da demonstração são novas a cada execução.

Para demonstrar a persistência, execute os comandos abaixo em sequência.
Escolha uma senha de pelo menos 12 caracteres quando solicitado e use a mesma
senha ao continuar. A senha não aparece na tela nem é gravada pelo programa.

```powershell
.\.venv\Scripts\python.exe demo_persistencia.py criar .\dados-tcc
.\.venv\Scripts\python.exe demo_persistencia.py continuar .\dados-tcc
.\.venv\Scripts\python.exe demo_persistencia.py verificar .\dados-tcc
```

`criar` prepara o cadastro, as chaves cifradas e a primeira leitura. A execução
`continuar` recupera as chaves, rejeita o reenvio da leitura anterior, confirma
uma nova leitura e revoga o sensor. `verificar` consulta o histórico e valida
a cadeia sem solicitar a senha. Para repetir todo o roteiro, use outra pasta.
O comando de criação recusa pastas existentes.

## API e simulador IoT

Use uma pasta nova para esta demonstração. A demonstração anterior de
persistência termina com seu sensor revogado.

**1. Prepare os dados e inicie a API em um terminal:**

```powershell
.\.venv\Scripts\python.exe preparar_demo_api.py .\dados-api
.\.venv\Scripts\python.exe iniciar_api.py .\dados-api
```

O preparador solicita uma senha para as chaves. Ao iniciar a API, informe a
mesma senha e escolha um token administrativo com 32 a 256 caracteres ASCII,
sem espaços. Guarde esse token durante a sessão para os outros comandos.
O servidor permanece aberto em `http://127.0.0.1:5000` até Ctrl+C. Para usar
outra porta, acrescente `--porta 5001` e ajuste `--url` nos clientes.

**2. Em outro terminal, envie e confirme leituras:**

```powershell
.\.venv\Scripts\python.exe simulador_iot.py .\dados-api\simulador --amostras 5 --intervalo 1 --confirmar
```

Informe a senha dos sensores e o token escolhido ao iniciar a API. Cada ciclo
envia temperatura e umidade; `--confirmar` solicita a produção de um bloco por
ciclo. O resultado esperado é 10 leituras em 5 blocos, além do gênese.
Sem `--confirmar`, o simulador somente envia à fila e não pede token administrativo.
Use `--semente 7` para repetir a sequência de valores simulados; identificadores,
chaves e timestamps continuam sendo próprios de cada execução.

**3. Consulte o resultado pelo cliente administrativo:**

```powershell
.\.venv\Scripts\python.exe cliente_api.py estado
.\.venv\Scripts\python.exe cliente_api.py historico --dispositivo sensor-temp-01
.\.venv\Scripts\python.exe cliente_api.py validar
```

Todos esses comandos solicitam o token. A senha das chaves e o token não são
enviados como argumentos de terminal ou gravados pelo programa. A senha dos
sensores permanece no simulador, que envia apenas transações assinadas.

## Painel visual para a apresentação

Se ainda não tiver os dados, execute o preparador em uma pasta nova:

```powershell
.\.venv\Scripts\python.exe preparar_demo_api.py .\dados-api
```

Depois inicie a aplicação com o laboratório local habilitado:

```powershell
.\.venv\Scripts\python.exe iniciar_api.py .\dados-api --apresentacao
```

Abra **http://127.0.0.1:5000/painel** no navegador e informe o mesmo token
administrativo escolhido ao iniciar a API. O token fica somente na memória
da aba; recarregar a página ou desconectar exige uma nova conexão.

Roteiro de demonstração pelo painel:

1. Em **Visão geral**, clique em **Gerar leituras simuladas**.
2. Observe as leituras na fila e clique em **Produzir bloco**.
3. Abra **Blocos** para inspecionar hashes, assinaturas e leituras incluídas.
4. Em **Sensores**, consulte o **Histórico** de um dispositivo.
5. Em **Integridade**, execute o teste com valor `99.9` em um bloco regular.
6. Marque **Recalcular o hash após alterar o valor** e repita o teste.

O laboratório trabalha somente em uma cópia em memória. O banco e a fila
originais permanecem preservados. Há também um **Guia da apresentação**
dentro do painel. Os registros e contadores são obtidos da API, sem métricas
de desempenho inventadas ou números fixos de demonstração na interface.

Sem `--apresentacao`, o painel continua disponível para consulta e administração,
e as leituras podem chegar pelo simulador HTTP. A geração local de leituras
e o laboratório ficam desativados. Esse modo adicional exige o pacote
`simulador/` criado pelo preparador e a senha utilizada na demonstração.

Ambiente verificado: Python 3.12.14, cryptography 50.0.2, SQLite 3.53.1,
Flask 3.1.3, Waitress 3.0.2 e Werkzeug 3.1.9, Windows AMD64.
As dependências diretas estão fixadas em `requirements.txt`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `sistema.py` | Criação e recuperação da aplicação, cadastro e uso das chaves |
| `api.py` | Rotas Flask, autenticação administrativa, limites e respostas JSON |
| `servico.py` | Operações serializadas e conexão SQLite por operação |
| `iniciar_api.py` | Servidor Waitress em loopback |
| `preparar_demo_api.py` | Instalação de demonstração com três autoridades e dois sensores |
| `simulador_iot.py` | Assinatura local e envio HTTP de temperatura e umidade |
| `cliente_api.py` | Consultas administrativas e produção manual por HTTP |
| `painel/templates/painel.html` | Telas e formulários do painel local |
| `painel/static/` | Estilos, JavaScript e ícone; sem dependências externas |
| `identidade.py` | Ed25519 e histórico de versões do cadastro |
| `cofre.py` | Chaves privadas PKCS8 cifradas por senha |
| `formato.py` | Serialização canônica e hashes compartilhados |
| `nucleo.py` | Transações identificadas, anti-replay, blocos e validação histórica |
| `armazenamento.py` | Blocos, cadastro e configuração no SQLite |
| `demo.py` | Demonstração de integridade em terminal |
| `demo_persistencia.py` | Roteiro de reinício, replay e revogação |
| `teste_i1_i2.py` | 13 testes da base, com rejeição antecipada de chave falsa |
| `teste_seguranca_nucleo.py` | 16 regressões para produção, corrupção e falhas de gravação |
| `teste_estado_persistente.py` | 33 cenários da etapa 2, incluindo reinício em outro processo |
| `teste_api.py` | 22 testes de API, autorização, concorrência e entradas inválidas |
| `teste_simulador_http.py` | 11 testes de integração com Waitress e sensor em outro processo |
| `teste_painel.py` | 15 testes de acesso, resumo, simulação e preservação do ledger |

## Etapa 1 concluída: consistência do núcleo

- O bloco candidato e suas transações são verificados antes de serem gravados.
- A chave do produtor deve corresponder à autoridade cadastrada.
- A gravação no SQLite ocorre antes de alterar os blocos e limpar as pendências.
  Uma falha de banco mantém os dados disponíveis para uma nova tentativa.
- A validação exige o gênese fixo e rejeita cadeia vazia, blocos não iniciais
  sem transações, estruturas malformadas e timestamps negativos ou não finitos.
- A recuperação confere a correspondência entre o índice SQL e o índice do JSON.
- A cadeia existente é validada antes da produção do próximo bloco.

Essa etapa foi validada originalmente com 29 testes. O teste de validador com
chave falsa exige rejeição antes da gravação; outra regressão verifica uma
assinatura falsa em bloco já existente.

## Etapa 2 concluída: configuração e identidades recuperáveis

- Cadastro versionado e ordem dos validadores persistidos no SQLite.
- Chaves recuperadas de arquivos cifrados; senha fornecida pelo operador.
- Revogação e troca de chave preservam a validação dos blocos já confirmados.
- Revogação entra em vigor no próximo bloco, independentemente do timestamp do sensor.
- Transações contêm versão, identificador único e identificador de rede assinados.
- Reenvios são rejeitados na fila, na produção e na validação histórica, inclusive
  depois de reabrir a aplicação.
- Blocos assinam referências ao cadastro e à configuração de governança usados.
- **62 testes aprovados** nas duas etapas, incluindo o roteiro completo da demonstração.

O formato persistente agora é a versão 2. Bancos da etapa 1 sem o cadastro
histórico exigem migração explícita; esta implementação os recusa e não
reescreve seus registros. Use `Sistema.criar` para um novo banco e
`Sistema.abrir` para recuperar uma instalação da etapa 2.

## Etapa 3 concluída: API e sensores simulados

- Recebimento de transações já assinadas, confirmação de blocos e consultas paginadas.
- Cadastro e rotação de dispositivos por chave pública, revogação e descarte de pendências.
- Autenticação Bearer nas consultas privadas e operações administrativas.
- Leituras no formato 3 com grandeza e unidade protegidas pela assinatura.
  Transações do formato 2 e instalações da etapa 2 continuam sendo aceitas.
- Conexão SQLite própria em cada operação, com acesso serializado entre threads.
- Simulador com pacote contendo apenas as chaves cifradas dos sensores.
- **95 testes aprovados**: os 62 anteriores, 22 da API e 11 da integração HTTP real.

## Etapa 4 concluída: observatório visual

- Visão geral com contadores reais, gráfico de leituras e próxima autoridade.
- Cadastro e consulta de sensores, rotação de chave pública e revogação.
- Fila de pendências, confirmação e inspeção das transações.
- Explorador paginado de blocos, hashes, assinaturas e exportação JSON.
- Verificação de integridade e demonstração de adulteração em cópia isolada.
- Atualização automática a cada seis segundos, com pausa e estados de erro.
- Interface revisada em desktop e celular; arquivos locais para uso sem CDN.
- **110 testes aprovados**, mais revisão funcional e visual no navegador.

## Limites atuais

O rodízio é uma regra de autoridade local. Ainda não existe comunicação entre
nós, consenso distribuído, sensor físico ou benchmark.
O serviço HTTP atende somente em loopback, em um processo com múltiplas threads.
As assinaturas verificam autoria e integridade; os valores enviados são simulados.
O cadastro HTTP recebe chaves públicas; provisionar e proteger chaves de sensores
reais continuará sendo responsabilidade dos dispositivos e de seu administrador.
O laboratório do painel é uma demonstração controlada; não executa um ataque
de rede nem mede a segurança de uma instalação distribuída.
As pendências ainda ficam em memória: somente leituras confirmadas sobrevivem
ao reinício. Uma pendência de sensor revogado é bloqueada e pode ser removida
explicitamente com `cadeia.descartar_pendente(id_transacao)`.
O método antigo de exportação bruta de chave permanece para interoperabilidade
e testes; o fluxo persistente usa exclusivamente o cofre cifrado.

Uma leitura falsa pode ter assinatura válida. A validação criptográfica verifica
conteúdo e autoria, sem provar a veracidade física do sensor. A remoção dos
últimos blocos pode deixar um prefixo válido: detectar esse tipo de retrocesso
exigirá um ponto de controle confiável ou ancoragem externa. Essa proteção
continua fora da implementação atual. A administração local e a proteção
dos arquivos do sistema fazem parte do modelo de confiança.

A validação integral antes de cada produção privilegia a consistência da
demonstração. Seu custo cresce com o histórico e deverá ser considerado na
etapa de desempenho. A contagem ou duração dos testes não equivale a TPS.
