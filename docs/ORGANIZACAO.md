# Organização e migração

A distribuição está em `Prototipo/Blockchain-With-Python/`. As fontes usadas nas medições anteriores estão em `resultados/proveniencia/fontes-medidas.zip`.

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
subprocesso e descoberta das fontes para futuras medições. A suíte funcional foi executada após a reorganização. As medições de desempenho continuam associadas à versão arquivada.

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

Os bancos em `resultados/` contêm dados sintéticos da pesquisa. O ambiente virtual e os dados da demonstração são preparados localmente.
