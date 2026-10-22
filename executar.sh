#!/usr/bin/env bash
# Instala dependências em ambiente virtual e inicia a aplicação local.
# Execute com Bash: bash executar.sh
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd -- "$ROOT"

PORTA=5000
DADOS="$ROOT/dados/apresentacao"
SO_INSTALAR=0
GRAFICOS=0
REINSTALAR=0
APRESENTACAO=1

ajuda() {
    cat <<'AJUDA'
Uso: bash executar.sh [opções]

Sem opções: instala dependências, prepara dados se necessário e abre o serviço
local em http://127.0.0.1:5000/painel (abra esse endereço no navegador).

  --instalar              Apenas instala; não pede senhas nem inicia servidor.
  --graficos              Inclui Matplotlib para exportar figuras científicas.
  --reinstalar            Repete a instalação mesmo com dependências preparadas.
  --dados CAMINHO         Pasta de dados (padrão: dados/apresentacao).
  --porta NUMERO          Porta de 1024 a 65535 (padrão: 5000).
  --sem-apresentacao      Desabilita geração local e laboratório em cópia.
  -h, --ajuda, --help     Mostra esta ajuda.

Requisitos: Bash e Python 3.12 ou superior com venv e pip.
Windows: use Git Bash ou WSL; PowerShell não interpreta arquivos Bash.
Para selecionar um Python: PYTHON=/caminho/python bash executar.sh
As dependências são obtidas do índice configurado no pip (PyPI por padrão).
Na primeira instalação é necessário acesso à internet. Não utiliza sudo.
AJUDA
}

falhar() { printf '\nErro: %s\n' "$*" >&2; exit 1; }
trap 'printf "\nA operação falhou na linha %s. Confira a mensagem anterior.\n" "$LINENO" >&2' ERR

while (($#)); do
    case "$1" in
        --instalar) SO_INSTALAR=1; shift ;;
        --graficos) GRAFICOS=1; shift ;;
        --reinstalar) REINSTALAR=1; shift ;;
        --sem-apresentacao) APRESENTACAO=0; shift ;;
        --dados)
            (($# >= 2)) || falhar 'Informe o caminho depois de --dados.'
            [[ -n "$2" ]] || falhar 'A pasta de dados não pode ser vazia.'
            DADOS="$2"; shift 2 ;;
        --porta)
            (($# >= 2)) || falhar 'Informe um número depois de --porta.'
            [[ "$2" =~ ^[0-9]{4,5}$ ]] || falhar 'Porta inválida; use 1024 a 65535.'
            PORTA=$((10#$2)); shift 2 ;;
        -h|--ajuda|--help) ajuda; exit 0 ;;
        *) falhar "Opção desconhecida: $1. Use --ajuda." ;;
    esac
done
((PORTA >= 1024 && PORTA <= 65535)) || falhar 'Use uma porta de 1024 a 65535.'

PYTHON_CMD=()
python_valido() {
    "$@" -c 'import sys, ssl, sqlite3, venv; sys.exit(0 if sys.version_info >= (3,12) else 1)' >/dev/null 2>&1
}
if [[ -n "${PYTHON:-}" ]]; then
    python_valido "$PYTHON" || falhar 'O executável indicado em PYTHON exige Python >= 3.12 com ssl, SQLite e venv.'
    PYTHON_CMD=("$PYTHON")
else
    for candidato in python3 python; do
        if command -v "$candidato" >/dev/null 2>&1 && python_valido "$candidato"; then
            PYTHON_CMD=("$candidato"); break
        fi
    done
    if ((${#PYTHON_CMD[@]} == 0)) && command -v py >/dev/null 2>&1 && python_valido py -3; then
        PYTHON_CMD=(py -3)
    fi
fi
((${#PYTHON_CMD[@]})) || falhar 'Instale Python 3.12 ou superior com venv/pip, reabra o terminal e tente novamente.'

if [[ ! -d "$ROOT/.venv" ]]; then
    printf '\n[1/3] Criando ambiente virtual em .venv...\n'
    "${PYTHON_CMD[@]}" -m venv "$ROOT/.venv"
fi
if [[ -x "$ROOT/.venv/bin/python" ]]; then
    VENV_PY="$ROOT/.venv/bin/python"
elif [[ -f "$ROOT/.venv/Scripts/python.exe" ]]; then
    VENV_PY="$ROOT/.venv/Scripts/python.exe"
else
    falhar 'O ambiente .venv está incompleto ou pertence a outro sistema. Renomeie essa pasta e execute novamente.'
fi
python_valido "$VENV_PY" || falhar 'O Python do ambiente .venv não atende aos requisitos. Renomeie a pasta .venv para recriar.'
"$VENV_PY" -m pip --version >/dev/null || falhar 'pip não está disponível no ambiente virtual.'

REQUISITOS="$ROOT/config/requirements.txt"
((GRAFICOS == 0)) || REQUISITOS="$ROOT/config/requirements-graficos.txt"
ASSINATURA="$("$VENV_PY" -c 'import hashlib,pathlib,sys; p=pathlib.Path("."); h=hashlib.sha256(); [h.update((p/n).read_bytes()) for n in ("pyproject.toml","config/requirements.txt","config/requirements-graficos.txt")]; h.update((str(p.resolve())+sys.version+sys.argv[1]).encode()); print(h.hexdigest())' "$GRAFICOS")"
CARIMBO="$ROOT/.venv/.dependencias.sha256"
if ((REINSTALAR)) || [[ ! -f "$CARIMBO" ]] || [[ "$(cat "$CARIMBO")" != "$ASSINATURA" ]]; then
    printf '\n[1/3] Instalando dependências no ambiente virtual...\n'
    "$VENV_PY" -m pip install --disable-pip-version-check -r "$REQUISITOS"
    "$VENV_PY" -m pip install --disable-pip-version-check --no-deps -e "$ROOT"
    printf '%s\n' "$ASSINATURA" > "$CARIMBO"
else
    printf '\n[1/3] Dependências já preparadas. Use --reinstalar para repetir.\n'
fi
if ((SO_INSTALAR)); then
    printf '\nInstalação concluída. Para iniciar: bash executar.sh\n'
    exit 0
fi

[[ -t 0 ]] || falhar 'Execute em terminal interativo para informar senha e token; para apenas instalar use --instalar.'
# Mantém o caminho no formato do Bash; Git Bash converte argumentos para Python nativo.
INTERATIVO=("$VENV_PY")
# Python nativo do Windows precisa de console para leitura oculta no Git Bash/mintty.
if [[ -n "${MSYSTEM:-}" ]] && command -v winpty >/dev/null 2>&1 && [[ -t 1 ]]; then
    INTERATIVO=(winpty "$VENV_PY")
fi
if [[ ! -e "$DADOS" ]]; then
    printf '\n[2/3] Primeira execução: criando autoridades e sensores.\n'
    printf 'Escolha uma senha com pelo menos 12 caracteres. Ela não será gravada.\n'
    "${INTERATIVO[@]}" -m blockchain_tcc.preparar_demo_api "$DADOS"
elif [[ ! -f "$DADOS/ledger.db" ]]; then
    falhar 'A pasta de dados já existe, mas não contém ledger.db. Use --dados com outra pasta ou recupere sua instalação.'
else
    printf '\n[2/3] Reutilizando o histórico confirmado existente.\n'
fi

printf '\n[3/3] Iniciando o sistema.\n'
printf 'Informe a senha escolhida na preparação e um token de 32 a 256 caracteres sem espaços.\n'
printf 'Use esse mesmo token no painel. Abra: http://127.0.0.1:%s/painel\n' "$PORTA"
printf 'Ctrl+C encerra o serviço. Os blocos confirmados permanecem na pasta de dados.\n\n'
ARGUMENTOS=("$DADOS" --porta "$PORTA")
((APRESENTACAO == 0)) || ARGUMENTOS+=(--apresentacao)
exec "${INTERATIVO[@]}" -m blockchain_tcc.iniciar_api "${ARGUMENTOS[@]}"
