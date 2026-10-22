# Etapa 4: painel visual para a apresentação do TCC

A etapa seguinte já foi entregue: consulte [ETAPA_5.md](ETAPA_5.md). O roteiro
ao final deste arquivo registra o planejamento existente ao concluir o painel.

Status: concluída. A suíte executou **110 testes aprovados**, sendo 95 das
etapas anteriores e 15 novos testes do painel. O JavaScript passou pela
verificação de sintaxe do Node.js. O fluxo também foi revisado no navegador.

## Como executar

Na pasta do projeto, com as dependências instaladas conforme o README:

```powershell
.\.venv\Scripts\python.exe preparar_demo_api.py .\dados-api
.\.venv\Scripts\python.exe iniciar_api.py .\dados-api --apresentacao
```

O preparador deve ser usado somente se a pasta de dados ainda não existir.
Uma instalação válida da etapa 3 pode ser reutilizada. O preparador cria o
pacote de sensores que permite a geração local de leituras. Na demonstração,
os sensores e validadores usam a senha escolhida nessa preparação.

No navegador, abra `http://127.0.0.1:5000/painel` e informe o mesmo token
administrativo utilizado no início da API. O token precisa ter 32 a 256
caracteres ASCII sem espaços. O formulário não solicita senha de chave privada.
Para outra porta, use `--porta 5001` e abra o endereço correspondente.

Sem `--apresentacao`, as consultas e operações administrativas do painel
continuam disponíveis. Os dois endpoints do laboratório são recusados e os
controles correspondentes ficam desativados. A simulação HTTP da etapa 3
continua funcionando e pode alimentar o painel em qualquer um dos modos.

## Telas entregues

| Tela | Conteúdo e operações |
|---|---|
| Visão geral | Contadores reais, gráfico por sensor, autoridades, blocos recentes, fila e produção de bloco |
| Sensores | Estado de autorização, chave pública, última leitura, histórico paginado, cadastro, rotação e revogação |
| Transações | Pendências e confirmadas, paginação, detalhes assinados e descarte explícito de pendências |
| Blocos | Gênese e blocos regulares, paginação, hashes, produtor, assinaturas, leituras e exportação JSON |
| Integridade | Validação do histórico e laboratório de alteração em cópia isolada |
| Guia da apresentação | Roteiro do sensor até a evidência de adulteração, com limites do protótipo |

Os contadores são obtidos do estado real da API. Blocos confirmados na visão
geral excluem o gênese; o explorador e a verificação indicam quando ele está
incluído. Autoridades autorizadas não são apresentadas como nós distribuídos
online. O rodízio continua sendo uma regra local.

O gráfico utiliza valores numéricos de até 20 registros do sensor escolhido
dentro da janela global das 60 leituras confirmadas mais recentes. Leituras
textuais ou fora dessa janela continuam acessíveis no histórico paginado.
O gráfico não produz uma métrica de desempenho nem valida a plausibilidade
física das leituras. Temperatura e umidade são mostradas separadamente, com
as unidades assinadas, sem misturar escalas.

## Roteiro de apresentação

1. Abra **Sensores** e mostre as identidades e suas chaves públicas.
2. Em **Visão geral**, clique em **Gerar leituras simuladas**. Uma leitura
   por sensor autorizado do pacote será assinada e adicionada à fila.
3. Mostre a fila e clique em **Produzir bloco**. A autoridade da vez assina
   o bloco, que passa a integrar o histórico persistido.
4. Abra um bloco para explicar hash, hash anterior, assinatura e leituras.
5. Consulte o histórico de um sensor para mostrar rastreabilidade.
6. Em **Integridade**, selecione um bloco regular e altere a primeira leitura
   para um valor diferente, por exemplo `99.9`. Execute a demonstração.
7. Marque a opção de recalcular o hash e repita. A cópia continua inválida,
   agora pela assinatura original do validador, que não corresponde ao novo hash.
8. Execute **Verificar agora** para confirmar que a cadeia original continua válida.
9. Explique o problema do oráculo: uma leitura fisicamente falsa pode ter
   assinatura válida, pois o sistema não observa o fenômeno físico.

Sensores revogados ou com chaves diferentes das disponíveis no pacote local
não são usados para gerar novas leituras no painel. Caso uma pendência tenha
sido recebida antes da revogação, ela pode bloquear a produção até seu
descarte explícito. A interface pede confirmação antes de revogar ou descartar.

## Laboratório sem alteração do banco

A demonstração abre e valida o sistema, copia a lista de blocos em memória
e altera somente a primeira transação do bloco escolhido nessa cópia.
Não chama métodos de persistência. O resultado mostra o valor original, o
valor alterado, o hash registrado, o hash recalculado e o motivo da falha.

Quando a opção de recálculo está desmarcada, o conteúdo deixa de corresponder
ao hash armazenado. Quando marcada, o novo hash da cópia não corresponde à
assinatura do validador. O retorno distingue a validade original da validade
da cópia e informa `persistido: false`.

Os testes comparam os bytes do SQLite antes e depois, além do conteúdo do
bloco e da fila: ambos os cenários preservam o estado original. Trata-se de
uma demonstração funcional controlada, sem adulteração do ledger real,
ataque de rede ou prova formal de segurança.

## Extensões da API

Todas as rotas de dados e demonstração continuam exigindo Bearer token.

| Método e rota | Finalidade |
|---|---|
| `GET /` | Redireciona para `/painel` |
| `GET /painel` | Estrutura pública da tela de acesso, sem dados do ledger |
| `GET /painel/static/<arquivo>` | Recursos locais do painel |
| `GET /painel/dados` | Retrato consistente para contadores, membros, últimas leituras, blocos e fila |
| `GET /transacoes?inicio=0&limite=50` | Transações confirmadas paginadas, da mais recente para a mais antiga |
| `POST /apresentacao/leituras` | Gera um lote local de leituras assinadas; exige modo de apresentação |
| `POST /apresentacao/integridade` | Executa a análise em cópia; exige modo de apresentação |

O corpo para geração local é `{}`. O corpo do teste é:

```json
{"bloco": 1, "valor": "99.9", "recalcular_hash": false}
```

O bloco deve ser regular, existente e conter leituras. O novo valor deve ser
textual, diferente do original e ter até 4096 bytes UTF-8. Índices e opções
inválidos são recusados. Sem modo de apresentação, as rotas retornam 403.
Sem pacote, com rede divergente ou sem sensores elegíveis, a geração retorna
409. A capacidade da fila é verificada antes de publicar o lote completo.

Os endpoints anteriores permanecem disponíveis. O painel usa os mesmos
controles de autorização, regras de revogação e armazenamento já implementados.
A opção local de apresentação lê o pacote cifrado dos sensores e não pretende
representar um sensor remoto real nem um mecanismo de assinatura no navegador.

## Sessão e interface

- Token apenas em variável JavaScript da aba, sem cookies, localStorage ou
  sessionStorage. O campo é limpo após conectar; recarregar exige novo acesso.
- Requisições enviam o token no cabeçalho Authorization, sem credenciais na URL.
- Desconectar limpa os dados exibidos, encerra atualizações e cancela consultas.
- Atualização automática a cada seis segundos, com opção de pausa.
  Abas em segundo plano não fazem consultas periódicas.
- Erros de conexão e indisponibilidade deixam claro que os valores exibidos
  pertencem à última atualização bem-sucedida. Uma resposta 401 encerra a sessão.
- As chamadas de escrita exigem ação do operador; a atualização periódica
  não gera leituras, não produz blocos e não altera cadastros.
- HTML, CSS, JavaScript e ícones locais. Não há fontes, gráficos ou scripts
  carregados de CDNs. O painel não exige outra ferramenta de build.
- Política CSP restringe scripts, estilos e conexões à mesma origem, impede
  incorporação em frames e desativa objetos externos. Conteúdo vindo da API
  é inserido como texto ou atributos controlados, sem montar HTML com leituras.
- Gráficos e tabelas têm estados vazios. Formulários possuem rótulos e os
  diálogos podem ser fechados por teclado. O menu é recolhível em telas pequenas.

O acesso por token mantém o modelo administrativo local da aplicação. Não
foram adicionados usuários com papéis diferentes, autenticação multifator ou
exposição pública do serviço.

## Verificação realizada

Ambiente preservado: Python 3.12.14, SQLite 3.53.1, cryptography 50.0.2,
Flask 3.1.3 e Waitress 3.0.2, Windows AMD64. Sem novas dependências Python.

As 15 verificações novas cobrem estrutura pública sem segredos, autenticação
dos dados, ativação explícita do modo, resumo consistente, paginação, geração
de leituras, revogação, rotação, fila cheia sem lote parcial, pacote ausente,
rede divergente, análise sem gravação, recálculo do hash, entradas inválidas
e habilitação pela linha de comando. O total das quatro etapas é 110 testes.
O JavaScript passou por `node --check`.

No navegador foram conferidos login, token incorreto, encerramento de sessão,
geração e confirmação de leituras, detalhes de bloco, histórico paginado,
transações, laboratório com e sem recálculo e layout responsivo em viewport
de desktop (1440 × 1000) e celular (390 × 844), sem transbordamento horizontal
da página móvel. Foram usados dados sintéticos em instalação temporária.

## Texto do TCC e próxima etapa

As seções 5.1, 5.6, 5.7 e a Figura 2 precisam refletir o painel e seu fluxo.
A discussão de segurança deve explicar a diferença entre o laboratório em
cópia e um ataque real. A seção de resultados deve registrar os 110 testes
e a revisão visual, separando-os da execução anterior do manuscrito.
O PDF permanece sem edição nesta etapa.

Resta a **etapa 5**: experimentos controlados de desempenho, consolidação das
evidências, atualização do manuscrito e roteiro final da defesa. A interface
atual não inventa TPS, latência, cobertura de testes ou disponibilidade de nós.
