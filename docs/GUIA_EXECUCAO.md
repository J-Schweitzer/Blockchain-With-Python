# Guia de instalação e execução

Execute os comandos a partir da raiz da pasta extraída. O projeto requer
Python 3.12 ou superior. A primeira instalação baixa bibliotecas do índice
configurado no pip, PyPI por padrão. O painel utiliza recursos locais.

## Bash: Windows, Linux e macOS

```bash
bash executar.sh
```

No Windows, use Git Bash, ou WSL com um Python instalado dentro do Linux.
PowerShell e Prompt de Comando não interpretam Bash. Não é necessário tornar
o arquivo executável quando se utiliza `bash executar.sh`.

Se houver múltiplos Pythons, selecione um executável específico:

```bash
PYTHON=/usr/bin/python3.12 bash executar.sh
# Exemplo no Git Bash, inclusive com espaço no caminho:
PYTHON='/c/Program Files/Python312/python.exe' bash executar.sh
# Neste computador, em uma porta alternativa:
PYTHON=/c/Users/joaos/AppData/Local/Python/bin/python.exe bash executar.sh --porta 5001
```

O script procura `python3`, `python` ou `py -3`, exige versão compatível e
cria `.venv`. Não é necessário ativar o ambiente. O prefixo `PYTHON` deve
conter o caminho do executável, sem argumentos extras.

No Linux, caso a criação do ambiente falhe por ausência de `venv`/`ensurepip`,
instale o componente de ambiente virtual de sua distribuição. O script não
altera pacotes do sistema automaticamente.

No Git Bash com mintty, `winpty` é utilizado quando disponível para permitir
as entradas ocultas do Python nativo no modo interativo. Se o terminal não
aceitar a senha, preencha o arquivo de credenciais descrito abaixo ou use os
comandos manuais de PowerShell.

### Primeira execução e retomada

A pasta padrão é `dados/apresentacao`. Preencha `credenciais.local.txt`, na
raiz do projeto, com duas linhas sem aspas:

```text
SENHA_CHAVES=senha_já_usada_para_criar_o_ledger
TOKEN_ADMIN=token_privado_de_32_a_256_caracteres_sem_espacos
```

A senha deve ter pelo menos 12 caracteres. Se `dados/apresentacao` já existe,
use a mesma senha que cifrou suas chaves; outra senha impedirá a abertura.
O token deve conter 32 a 256 caracteres ASCII sem espaços e é digitado
também no painel. O script usa esse arquivo automaticamente e não pede
credenciais no terminal. Sem o arquivo, usa prompts ocultos. `--interativo`
força os prompts; `--credenciais CAMINHO` seleciona outro arquivo.

O arquivo local contém segredos em texto simples e pode ser sincronizado
pelo OneDrive. Não o compartilhe; para mantê-lo fora dessa pasta, use
`--credenciais` com um caminho privado. Nunca passe a senha ou o token
diretamente como argumentos do comando.

Se a pasta indicada já existir sem `ledger.db`, a execução é interrompida.
Escolha outra pasta com `--dados`; o script não apaga nem recria instalações.
Se o ledger estiver inválido, o sistema recusa a abertura conforme suas regras.

Uma pasta de dados criada por uma etapa anterior com configuração compatível
pode ser indicada em `--dados`. Ela será usada diretamente, incluindo eventuais
sensores já revogados. Para uma demonstração limpa, escolha uma pasta nova.

### Instalação sem iniciar

```bash
bash executar.sh --instalar
bash executar.sh --graficos --instalar
```

O primeiro comando prepara a aplicação; o segundo inclui Matplotlib.
O carimbo `.venv/.dependencias.sha256` evita reinstalação desnecessária.
Use `--reinstalar` se bibliotecas forem removidas manualmente. Não compartilhe
uma mesma `.venv` entre Windows e WSL/Linux: renomeie a pasta do ambiente
para preservá-la e permita que o script crie outra no sistema escolhido.

## PowerShell: alternativa manual no Windows

Neste computador, o executável de Python está no caminho usado abaixo;
em outra máquina, substitua esse caminho pelo Python 3.12 ou superior instalado.

```powershell
& 'C:\Users\joaos\AppData\Local\Python\bin\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\config\requirements.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m blockchain_tcc.preparar_demo_api .\dados\apresentacao --credenciais .\credenciais.local.txt
.\.venv\Scripts\python.exe -m blockchain_tcc.iniciar_api .\dados\apresentacao --apresentacao --credenciais .\credenciais.local.txt
```

O preparador é apenas para uma pasta de dados nova. Nas próximas execuções,
utilize somente o último comando. Abra `http://127.0.0.1:5000/painel`.
Para trocar a porta, acrescente `--porta 5001` ao comando do servidor.

## Comandos adicionais

Depois da instalação, selecione o Python do ambiente para a sessão atual:

```bash
# Linux/macOS/WSL
PY=.venv/bin/python
# Git Bash com Python nativo do Windows
PY=.venv/Scripts/python.exe
```

Use a linha correspondente ao seu sistema, e então:

```bash
# Em outro terminal, com o servidor já iniciado:
"$PY" -m blockchain_tcc.simulador_iot dados/apresentacao/simulador --amostras 5 --intervalo 1 --confirmar
"$PY" -m blockchain_tcc.cliente_api estado
"$PY" -m blockchain_tcc.cliente_api historico --dispositivo sensor-temp-01
"$PY" -m blockchain_tcc.cliente_api validar

# Demonstração em memória, sem servidor:
"$PY" -m blockchain_tcc.demos.demo

# Demonstração de persistência, em uma pasta nova:
"$PY" -m blockchain_tcc.demos.demo_persistencia criar dados/exemplo-persistencia
"$PY" -m blockchain_tcc.demos.demo_persistencia continuar dados/exemplo-persistencia
"$PY" -m blockchain_tcc.demos.demo_persistencia verificar dados/exemplo-persistencia
```

O cliente/simulador utiliza a porta padrão 5000. Para outra porta, consulte
`--help` e informe `--url http://127.0.0.1:5001`.

## Experimentos

Instale os gráficos antes de medir, se precisar deles:

```bash
bash executar.sh --graficos --instalar
"$PY" tools/experimentos.py resultados/nova-execucao
"$PY" tools/figuras_experimentos.py resultados/nova-execucao
```

Cada destino deve ser novo. Não execute a carga durante a apresentação.
Consulte o protocolo da etapa 5 em `docs/historico/ETAPA_5.md`, usando os
comandos atualizados deste guia. As coletas novas terão impressões de arquivos
da estrutura organizada, distintas das fontes históricas entregues.

## Suíte existente: execução opcional pelo desenvolvedor

O instalador não executa testes. Para executá-los explicitamente após instalar:

```bash
"$PY" -m unittest discover -s tests -p 'teste_*.py' -v
```

Os testes HTTP abrem portas locais. Em 2 de novembro de 2026, uma instalação
limpa da distribuição atual com Python 3.15.1 passou nos 113 testes em
11,738 s. A coleta quantitativa arquivada não foi repetida nessa versão.
