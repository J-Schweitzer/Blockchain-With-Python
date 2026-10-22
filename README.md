# Blockchain IoT · TCC

Protótipo Python para demonstrar integridade, autoria e rastreabilidade de
leituras IoT: Ed25519, SHA-256, cadastro versionado, prevenção de replay,
persistência SQLite, API autenticada e painel local.

## Iniciar com um comando

Instale **Python 3.12 ou superior** com `venv` e `pip`. No Windows, abra o
**Git Bash** na pasta extraída; no Linux/macOS, use um terminal Bash.
É necessário acesso à internet na primeira instalação.

```bash
bash executar.sh
```

O script cria `.venv`, baixa as dependências e instala o pacote Python.
Na primeira execução, prepara três autoridades e dois sensores em
`dados/apresentacao/`. Nas próximas, reutiliza o histórico confirmado.

1. Escolha uma senha de pelo menos 12 caracteres para cifrar as chaves.
2. Ao iniciar a API, informe a mesma senha e escolha um token administrativo
   com 32 a 256 caracteres ASCII, sem espaços. As entradas ficam ocultas.
3. Abra **http://127.0.0.1:5000/painel** e informe esse mesmo token.
4. Gere leituras simuladas e produza um bloco. Use **Integridade** para a
   demonstração em cópia, que preserva o ledger original.

O terminal permanece executando o servidor. **Ctrl+C** encerra o serviço.
Senhas e tokens não são gravados pelo script. Reabrir o painel exige o token
da sessão atual; pendências não confirmadas não sobrevivem ao encerramento.

### Opções úteis

```bash
bash executar.sh --ajuda
bash executar.sh --instalar                  # Somente preparar o ambiente
bash executar.sh --porta 5001                # Outra porta local
bash executar.sh --dados ./dados/defesa      # Instalação independente
bash executar.sh --sem-apresentacao         # Desabilitar o laboratório e a geração local
bash executar.sh --graficos --instalar      # Incluir ferramenta de gráficos
bash executar.sh --reinstalar               # Repetir instalação das dependências
```

Dependências já preparadas são reutilizadas. Mudanças de configuração de
instalação ou de localização do projeto provocam nova instalação do pacote.
O Bash não instala Python nem Git Bash, não usa `sudo` e não altera bibliotecas
globais. Uma falha interrompe a execução sem apagar dados anteriores.

## Estrutura do projeto

```text
blockchain-tcc-profissional/
├── executar.sh                  # Instalação e inicialização
├── pyproject.toml               # Pacote Python, dependências e comandos
├── README.md
├── config/                      # Dependências fixadas da aplicação e gráficos
├── src/blockchain_tcc/           # Código Python da aplicação
│   ├── nucleo.py                # Blocos, transações e validação
│   ├── identidade.py            # Cadastro versionado e assinaturas
│   ├── cofre.py                 # Chaves cifradas
│   ├── armazenamento.py         # Persistência SQLite
│   ├── sistema.py               # Configuração e recuperação
│   ├── servico.py               # Operações serializadas
│   ├── api.py                   # API e painel autenticado
│   ├── iniciar_api.py           # Inicialização com Waitress
│   ├── preparar_demo_api.py     # Provisionamento da demonstração
│   ├── simulador_iot.py         # Emissor de leituras assinadas
│   ├── cliente_api.py           # Cliente administrativo HTTP
│   ├── formato.py              # Serialização e hashes
│   ├── demos/                  # Demonstrações do núcleo
│   └── painel/                 # Templates, CSS, JavaScript e ícone
├── tests/                       # Suíte funcional existente, com imports atualizados
├── examples/                    # Guia das demonstrações
├── tools/                       # Coleta de experimentos e geração de figuras
├── docs/                        # Guias atuais, redação e roteiro da defesa
│   └── historico/               # Registros das etapas no layout anterior
├── dados/                       # Instalações geradas na execução
└── resultados/
    ├── execucao-final/          # Dados brutos, estatísticas e figuras da etapa 5
    └── proveniencia/           # Fontes exatas usadas nas medições anteriores
```

## Documentação

- [Guia de execução](docs/GUIA_EXECUCAO.md): Bash, instalação manual e comandos.
- [Organização e migração](docs/ORGANIZACAO.md): caminhos e rastreabilidade.
- [Roteiro de defesa](docs/ROTEIRO_DEFESA.md).
- [Texto complementar para o TCC](docs/TEXTO_TCC_ATUALIZADO.md).
- [Resultados das 24 execuções](resultados/execucao-final/RESULTADOS.md).
- [Proveniência das medições](resultados/proveniencia/README.md).

## Resultados e situação da validação

A etapa 5 registrou 24 execuções e 9.600 leituras confirmadas. Os CSVs, bancos,
figuras e configurações entregues correspondem à versão anterior à reorganização.
A cópia exata das fontes medidas foi preservada em
`resultados/proveniencia/fontes-medidas.zip`. A reorganização ajustou imports,
empacotamento e caminhos; não realizou novas medições nem reexecutou os testes.

Os **110 testes aprovados na etapa 4** são evidência daquela versão. A suíte
foi mantida em `tests/`, com os endereços de módulos atualizados. As instruções
para execução manual estão no guia; o instalador não roda testes ou benchmarks.

## Limites do protótipo

O sistema executa localmente, com uma regra de rodízio entre identidades de
autoridade. Não há consenso distribuído, replicação P2P ou sensor físico.
Assinaturas verificam autoria e integridade, sem comprovar a veracidade física
do valor. Os experimentos não medem Ethereum/Fabric, HTTP ou a interface.
O serviço escuta somente em `127.0.0.1`. O PDF original não foi modificado.
