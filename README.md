# Blockchain privada (protótipo didático)

Marcos implementados: **I1** (núcleo) e **I2** (permissão e consenso).

| Arquivo | Função |
|---|---|
| `nucleo.py` | `Transacao`, `Bloco`, `Cadeia`, hash SHA-256, validação da cadeia, consenso Proof of Authority em rodízio |
| `identidade.py` | Chaves Ed25519, assinatura e `Registro` de membros autorizados (papel da CA) |
| `armazenamento.py` | Persistência dos blocos em SQLite |
| `teste_i1_i2.py` | 13 testes automatizados |
| `demo.py` | Demonstração em terminal |

## Executar

```bash
pip install cryptography
python demo.py
python -m unittest -v
```

## Decisões de projeto

- **Hash do bloco:** SHA-256 sobre JSON canônico (chaves ordenadas) do cabeçalho: índice, timestamp, transações, hash anterior e validador.
- **Permissão:** só dispositivos cadastrados com papel `dispositivo` gravam transações; só validadores cadastrados produzem blocos. A assinatura é conferida na entrada e de novo em `validar()`.
- **Consenso (PoA):** o bloco de índice *i* é do validador `validadores[(i-1) % n]`. Bloco fora da vez é recusado. A finalidade é determinística.
- **Rastreabilidade:** `Cadeia.historico(dispositivo)` devolve todas as leituras com o bloco de origem.

## Limitações assumidas (citar na defesa)

- Sem rede P2P: um único nó mantém a cadeia.
- Sem tolerância a falhas bizantinas: PoA assume validadores honestos.
- Sem proteção contra repetição (*replay*) de transações.
- O problema do oráculo permanece: um sensor autorizado que envia dado falso tem o dado registrado com assinatura válida.
- As chaves privadas vivem em memória; a persistência guarda só os blocos.

## Próximos marcos

- **I3:** API Flask (`/transacao`, `/cadeia`, `/validar`, `/historico/<dispositivo>`) e simulador de sensores.
- **I4:** testes de adulteração via API e medição de TPS e latência.
