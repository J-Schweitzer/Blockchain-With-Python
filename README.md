# Blockchain IoT · TCC

Protótipo Python para demonstrar integridade, autoria e rastreabilidade de
leituras IoT: Ed25519, SHA-256, cadastro versionado, prevenção de replay,
persistência SQLite, API autenticada e painel local.


## Material da banca

[Artigo em PDF](docs/paper/Artigo.pdf) · [Fontes LaTeX](docs/paper/) · [Slides editáveis](docs/apresentacao/Defesa%20do%20TCC.pptx) · [Slides em PDF](docs/apresentacao/Slides%20para%20projeção.pdf) · [Roteiro de fala](docs/apresentacao/Roteiro%20de%20fala.pdf)

## Abrir o painel no Windows

Em uma cópia nova, execute `bash executar.sh --instalar` no Git Bash para preparar o ambiente. Depois, na raiz do repositório, abra o PowerShell e execute:

```powershell
.\.venv\Scripts\python.exe abrir_painel.py
```

Para abrir com dois cliques, crie um atalho para esse executável com o caminho completo de `abrir_painel.py` como argumento e selecione `painel.ico` como ícone. O iniciador abre o navegador na porta 5001 e usa a pasta local `dados/defesa`.

## Iniciar com um comando

Instale **Python 3.12 ou superior** com `venv` e `pip`. No Windows, abra o
**Git Bash** na pasta extraída; no Linux/macOS, use um terminal Bash.
É necessário acesso à internet na primeira instalação.

```bash
bash executar.sh
```

Para iniciar em outra porta:

```bash
bash executar.sh --porta 5001
```

O script cria `.venv`, baixa as dependências e instala o pacote Python.
Na primeira execução, prepara três autoridades e dois sensores em
`dados/apresentacao/`. Nas próximas, reutiliza o histórico confirmado.

1. Preencha `credenciais.local.txt` com `SENHA_CHAVES` (pelo menos 12 caracteres)
   e `TOKEN_ADMIN` (32 a 256 caracteres ASCII, sem espaços). Não use aspas.
2. Execute `bash executar.sh`. Ele lê o arquivo automaticamente e usa a mesma
   senha para criar e abrir as chaves. Sem o arquivo, pede os valores no terminal.
3. Abra **http://127.0.0.1:5000/painel** e informe o `TOKEN_ADMIN`.
4. Gere leituras simuladas e produza um bloco. Use **Integridade** para a
   demonstração em cópia, que preserva o ledger original.

O terminal permanece executando o servidor. **Ctrl+C** encerra o serviço.
O arquivo de credenciais é texto simples e, dentro desta pasta, pode ser
sincronizado pelo OneDrive. Guarde-o em local privado e não o compartilhe.
O `.gitignore` exclui esse arquivo do repositório Git, mas não impede
sincronização ou cópias manuais. Reabrir o painel exige o token da sessão atual;
pendências não confirmadas não sobrevivem ao encerramento.

### Opções úteis

```bash
bash executar.sh --ajuda
bash executar.sh --instalar                  # Somente preparar o ambiente
bash executar.sh --porta 5001                # Outra porta local
bash executar.sh --dados ./dados/defesa      # Instalação independente
bash executar.sh --credenciais /c/caminho/credenciais.txt  # Outro arquivo
bash executar.sh --interativo               # Perguntar os valores no terminal
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
├── credenciais.local.txt         # Senha e token locais; preencher e manter privado
├── pyproject.toml               # Pacote Python, dependências e comandos
├── README.md
├── config/                      # Dependências fixadas da aplicação e gráficos
├── src/blockchain_tcc/           # Código Python da aplicação
│   ├── nucleo.py                # Blocos, transações e validação
│   ├── identidade.py            # Cadastro versionado e assinaturas
│   ├── cofre.py                 # Chaves cifradas
│   ├── credenciais.py           # Leitura do arquivo local de credenciais
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
- [Resultados das 24 execuções](resultados/execucao-final/RESULTADOS.md).
- [Proveniência das medições](resultados/proveniencia/README.md).

## Resultados e situação da validação

A etapa 5 registrou 24 execuções e 9.600 leituras confirmadas. Os CSVs, bancos,
figuras e configurações entregues correspondem à versão anterior à reorganização.
A cópia exata das fontes medidas foi preservada em
`resultados/proveniencia/fontes-medidas.zip`. A reorganização e a leitura de
credenciais locais não foram submetidas a nova coleta de desempenho.

Em 2 de novembro de 2026, uma cópia da distribuição atual passou por
instalação limpa em Windows com Python 3.15.1, `pip check` sem conflitos e
**113 testes automatizados aprovados em 11,738 s**. O servidor local confirmou
duas leituras em um bloco, rejeitou acesso sem token, detectou adulteração
em cópia e recuperou o histórico após reinício. Os 110 testes da etapa 4
permanecem como registro histórico. O instalador não roda testes ou benchmarks.

Na revisão de entrega de 12 de novembro de 2026, o instalador foi executado no Git Bash com Python 3.12.14. O ambiente passou em `pip check` e nos 113 testes (9,241 s). Em dados temporários, dois blocos foram confirmados por V1 e V2. Após reiniciar o serviço pelo mesmo comando, quatro leituras foram recuperadas e o histórico foi validado.

## Limites do protótipo

O sistema executa localmente, com uma regra de rodízio entre identidades de
autoridade. Não há consenso distribuído, replicação P2P ou sensor físico.
Assinaturas verificam autoria e integridade, sem comprovar a veracidade física
do valor. Os experimentos não medem Ethereum/Fabric, HTTP ou a interface.
O serviço escuta somente em `127.0.0.1`. O artigo de entrega está em `docs/paper/`.
