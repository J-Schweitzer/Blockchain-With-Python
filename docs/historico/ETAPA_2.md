# Etapa 2: persistência, identidade e anti-replay

Status: concluída. A suíte executou **62 testes aprovados**: 29 regressões
das etapas anteriores e 33 cenários novos. A validação inclui recuperação em
outro processo e o roteiro completo de criação, reinício, replay e revogação.
Ambiente: Python 3.12.14, cryptography 50.0.2, SQLite 3.53.1, Windows AMD64.

## Entrega

`Sistema.criar(pasta, validadores, dispositivos, senha)` inicializa uma nova
instalação com identificador de rede aleatório. A pasta só é publicada depois
de preparar o cadastro, o bloco gênese e as chaves cifradas. Pastas existentes
são recusadas. `Sistema.abrir(pasta)` recupera o estado sem gerar novas chaves
ou reinicializar silenciosamente o banco. Bancos ausentes ou inválidos geram erro.

O SQLite contém blocos e configuração: versão do sistema, identificador da
rede, ordem fixa dos validadores e todas as versões do cadastro público.
O cadastro armazena nome, papel, chave pública e estado ativo de cada membro.
As chaves privadas e a senha não são gravadas no SQLite.

## Proteção das chaves

O cofre grava arquivos PEM PKCS8 com `BestAvailableEncryption` da biblioteca
cryptography. A senha é exigida para recuperar a chave e nunca é persistida
pela aplicação. A identidade recuperada precisa corresponder à chave pública
cadastrada. Senha incorreta, arquivo inválido ou chave substituída geram erro.

Cada versão de chave possui arquivo próprio. Os caminhos usam hash do nome
e chave pública, evitando interpretar o nome lógico como caminho de arquivo.
Arquivos existentes não são sobrescritos. Uma falha na escrita remove apenas
o arquivo parcial criado pela operação. Se a chave for salva mas a alteração
posterior de cadastro falhar, pode restar um arquivo cifrado sem autorização;
a mesma operação pode ser repetida com a chave e senha correspondentes.

O operador deve guardar a senha e a pasta completa da instalação. A senha
não tem mecanismo de recuperação. A verificação do histórico utiliza somente
chaves públicas e não exige desbloquear o cofre. Chaves desbloqueadas existem
na memória do processo durante o uso. O método legado `exportar_privada()`
continua disponível para interoperabilidade e testes, sem uso no fluxo de gravação.

## Autorização histórica e revogação

Cada alteração do cadastro cria uma versão com número sequencial,
`inicio_bloco` e uma cópia completa dos membros. `inicio_bloco` é a altura do
próximo bloco ainda não confirmado, obtida do núcleo local. Se várias mudanças
ocorrem antes do mesmo bloco, vale a última versão daquela altura.

O cabeçalho de cada bloco regular inclui `registro_hash`: SHA-256 do cadastro
vigente na sua confirmação. Esse campo participa do hash e da assinatura do
validador. A validação histórica exige tanto a versão prevista para aquela
altura quanto a correspondência do hash. O bloco também inclui `governanca_hash`,
que vincula a rede e a ordem fixa das autoridades à assinatura do produtor.

Revogar um sensor bloqueia suas próximas operações e a confirmação de suas
pendências. Os blocos anteriores continuam sendo verificados com as versões
antigas do cadastro. Retroagir o timestamp de uma nova transação não recupera
uma autorização revogada. Trocar uma chave cria nova versão do cadastro;
a chave anterior deixa de autorizar novas operações, preservando as antigas.

Autoridades revogadas são retiradas do rodízio dos próximos blocos. A escolha
usa o índice do bloco e a lista de autoridades ativas na versão correspondente.
A última autoridade ativa não pode ser revogada ou perder seu papel. A lista
de nomes e sua ordem são fixadas na criação; adicionar organizações e alterar
a governança exigirá um procedimento posterior específico.

O administrador do processo local é confiável neste modelo. O histórico de
cadastro não é um protocolo distribuído de governança. Alterações em versões
já usadas por blocos são verificadas pelos hashes assinados. Alterações ainda
não ancoradas em blocos dependem da integridade do armazenamento administrativo.
Também permanece a necessidade de checkpoint externo para detectar retrocesso
ou truncamento do ledger por um administrador que controla todos os arquivos.

## Anti-replay e formato 2

Transações incluem `versao=2`, `id_transacao` aleatório de 128 bits,
`rede_id`, dispositivo, valor, timestamp e assinatura. A assinatura protege
todos os campos do conteúdo. Alterar o identificador ou a rede invalida a
assinatura. Uma transação assinada para outra instalação é rejeitada.

O identificador é verificado contra as pendências e os blocos já confirmados.
A produção revalida as transações, e a validação integral procura duplicatas
dentro de cada bloco e entre blocos. Após reiniciar, o conjunto confirmado é
obtido dos próprios blocos; não depende de um contador somente em memória.

Uma nova mensagem com outro identificador, assinada por sensor autorizado,
é uma nova transação. O anti-replay não comprova que duas leituras representam
medições físicas distintas nem resolve o problema do oráculo.

O bloco gênese mantém o modelo fixo. Blocos regulares usam formato 2 e
incluem rede, hash do cadastro e hash de governança no conteúdo protegido.
Bancos antigos sem o cadastro histórico são recusados com pedido de migração
explícita. Não é possível inferir retroativamente qual cadastro estava vigente
apenas pelos blocos da versão antiga. Esta etapa não fornece um migrador;
o banco original deve continuar guardado como evidência da execução anterior.

`Cadeia` mantém o identificador `local` para os exemplos em memória. Aplicações
persistentes devem usar `Sistema`, que gera uma identificação própria para
cada instalação e recupera a configuração ao abrir o banco.

## Consistência e reinicialização

Cadastro e gênese são inicializados em uma transação SQLite. Alterações de
cadastro são gravadas antes de publicar a nova versão na memória. A gravação
do bloco continua ocorrendo antes de anexá-lo em memória e limpar a fila.
Uma falha preserva o estado em memória para tentativa posterior.

Operações de gravação verificam o cadastro e a altura persistidos. Uma
instância desatualizada não pode sobrescrever um cadastro posterior ou confirmar
um bloco usando uma autorização já revogada por outra instância. Essas
verificações não tornam a aplicação uma rede com consenso; o modo previsto
continua sendo uma aplicação local, com operações administrativas sequenciais.

Pendências ainda são voláteis. Ao reiniciar, as transações não confirmadas
precisam ser reenviadas pelo emissor. Uma pendência revogada bloqueia a produção
até sua remoção explícita por `cadeia.descartar_pendente(id_transacao)`.
A proteção anti-replay após reinício se refere aos registros confirmados.

## Roteiro para apresentação

Instale as dependências conforme o README e execute na pasta do projeto:

```powershell
.\.venv\Scripts\python.exe demo_persistencia.py criar .\dados-tcc
.\.venv\Scripts\python.exe demo_persistencia.py continuar .\dados-tcc
.\.venv\Scripts\python.exe demo_persistencia.py verificar .\dados-tcc
```

1. `criar`: solicita e confirma a senha; cadastra V1, V2, V3 e sensor-temp-01;
   confirma a primeira leitura e fecha o banco. Um recibo JSON público fica
   salvo apenas para o roteiro de replay.
2. `continuar`: solicita a mesma senha; recupera as chaves; rejeita o recibo
   anterior; confirma outra leitura; revoga o sensor; rejeita nova operação
   assinada por ele; fecha e reabre o banco para verificar o histórico.
3. `verificar`: abre somente para consulta e validação, sem solicitar a senha.

Ao final, há três blocos incluindo o gênese, duas leituras no histórico e o
sensor revogado. Esse estado permanece válido em execuções posteriores.
Para repetir o roteiro completo, forneça outra pasta ao comando de criação.

## Testes e atualização do TCC

Os 33 testes novos cobrem reinício, replay na fila e no histórico, isolamento
entre redes, assinatura do identificador, revogação com leitura retrodatada,
reuso de cadastro antigo, rotação de sensores e autoridades, bloqueio da última
autoridade, adulteração de cadastro e governança, falhas de gravação,
instâncias desatualizadas, senha incorreta, troca de arquivos de chave,
inicialização incompleta, banco legado/ilegível, processo separado e roteiro CLI.
O conjunto das 62 verificações passou; não houve medição de desempenho.

No texto do TCC, as seções 5.2, 5.3, 5.4 e 5.5 devem refletir o formato 2,
anti-replay, cadastro por altura, política de revogação e arquivos cifrados.
A Figura 2 deve incluir o cadastro persistente e o cofre. A seção 6 deve
distinguir a evidência anterior de 13/29 testes da versão atual com 62 testes.
O ambiente desta execução é Windows; o ambiente Linux citado no PDF pertence
à verificação anterior. O manuscrito não foi alterado nesta etapa.

A próxima etapa é a API Python com simulador IoT. Permanecem para as etapas
seguintes o painel, os experimentos e a atualização final da documentação.
