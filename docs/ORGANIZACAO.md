# Organização e migração

A pasta `blockchain-tcc-profissional` é a distribuição organizada. A versão
anterior `blockchain-tcc` foi preservada como referência, sem mover ou apagar
seus arquivos. Use a pasta profissional para iniciar esta distribuição.

## Critérios

- `src/blockchain_tcc/`: pacote da aplicação, sem dados ou resultados gerados.
- `src/blockchain_tcc/painel/`: recursos web distribuídos com o pacote.
- `src/blockchain_tcc/demos/`: exemplos executáveis como módulos.
- `tests/`: casos funcionais existentes, separados do código da aplicação.
- `tools/`: programas de pesquisa e exportação, separados do servidor.
- `config/`: dependências fixadas por finalidade.
- `docs/`: guias atuais e material acadêmico; `historico/` conserva os registros
  das etapas anteriores, inclusive seus comandos e caminhos da época.
- `dados/`: pastas geradas pelo provisionamento e histórico operacional.
- `resultados/`: evidências científicas, não utilizadas como banco do servidor.

O arquivo `pyproject.toml` define instalação no layout `src`, comandos Python
e inclusão dos recursos do painel. Imports usam o namespace `blockchain_tcc`.
Isso permite executar módulos sem depender de arquivos soltos na raiz ou de
alteração manual de `PYTHONPATH`. A instalação pelo Bash é em modo editável.

Não foram alteradas as regras de assinatura, produção de blocos, autorização
ou persistência. Foram ajustados imports, referências em mocks, invocações de
subprocesso e descoberta das fontes para futuras medições. Esses ajustes não
constituem uma nova validação de execução. A suíte e o Bash não foram executados
nesta reorganização.

## Caminhos principais

| Layout anterior | Layout atual |
|---|---|
| `nucleo.py`, `identidade.py` e demais módulos | `src/blockchain_tcc/` |
| `painel/` | `src/blockchain_tcc/painel/` |
| `demo.py`, `demo_persistencia.py` | `src/blockchain_tcc/demos/` |
| `teste_*.py` | `tests/teste_*.py` |
| `experimentos.py`, `figuras_experimentos.py` | `tools/` |
| `requirements.txt` | `config/requirements.txt` |
| `requirements-experimentos.txt` | `config/requirements-graficos.txt` |
| Guias das etapas e README anterior | `docs/historico/` |
| Redação complementar e roteiro | `docs/` |
| Instalação `dados-api/` | Nova instalação padrão: `dados/apresentacao/` |

`docs/MIGRACAO.json` registra hashes e caminhos dos módulos principais antes
e depois da organização. Os resultados históricos continuam associados às
fontes originais em `resultados/proveniencia/fontes-medidas.zip`.

O `.rar` entrega o projeto inteiro, incluindo bancos sintéticos do experimento,
mas não inclui ambiente virtual, caches, pasta temporária, dados operacionais,
senhas ou chaves privadas de instalações. O ambiente é criado no computador
de destino pelo script. Resultados sintéticos não são dados operacionais.
