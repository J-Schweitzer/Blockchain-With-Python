# Análise da base e plano de desenvolvimento do TCC

Data: 21 de outubro de 2026.

Este arquivo preserva a análise da base e a evidência da etapa 1. A conclusão
da etapa 2 está em [ETAPA_2.md](ETAPA_2.md). A API, os sensores simulados e
o resultado da etapa 3 estão em [ETAPA_3.md](ETAPA_3.md). O painel visual e
o resultado de 110 testes estão em [ETAPA_4.md](ETAPA_4.md). Os experimentos
e a conclusão das cinco etapas técnicas estão em [ETAPA_5.md](ETAPA_5.md).

Base inspecionada: `C:\Users\gabri\OneDrive\Desktop\Blockchain-With-Python-main`.
Desenvolvimento: `C:\Users\gabri\OneDrive\Documentos\ChatGPT\TCC João\blockchain-tcc`.

Documento de referência: seção 5, páginas 7 a 10, de
`Blockchain_Pública_e_Privada_em_Ambientes_IoT___TCC_v2__Copy___Copy_ (1).pdf`,
na Área de Trabalho.

## Parecer de coerência

A base corresponde à implementação descrita na seção 5. Essa seção documenta
o protótipo existente e suas limitações; não define todos os requisitos da
futura versão de apresentação. O sistema definitivo do TCC precisa, portanto,
ter suas evoluções registradas junto das mudanças no código.

| Seção | Requisito ou descrição | Evidência na base |
|---|---|---|
| 5.1 | Execução local e leituras simuladas | `demo.py` cria um sensor e três autoridades no mesmo processo |
| 5.1 e 5.3 | Gênese, pendências e hashes encadeados | `Cadeia`, `Bloco`, `HASH_ZERO` e referência ao bloco anterior |
| 5.2 | Dispositivo, valor textual, timestamp e assinatura | `Transacao`; JSON com chaves ordenadas e UTF-8 |
| 5.3 | SHA-256 e assinatura do hash do bloco | `Bloco.calcular_hash()` e assinatura Ed25519 pelo produtor |
| 5.3 e 5.6 | Validação e consulta de histórico | `Cadeia.validar()` e `Cadeia.historico()` |
| 5.4 | Identidades e papéis em memória | `Identidade` e `Registro` em `identidade.py` |
| 5.5 | Blocos em SQLite e validação na recuperação | `Armazenamento` e construtor de `Cadeia` |
| 5.8 e 5.9 | Ausência de rede, anti-replay e validação física | Confirmada na leitura dos seis arquivos da base |

O encadeamento protege a representação dos blocos; a assinatura vincula o
conteúdo a uma chave. O rodízio apenas seleciona o produtor permitido para
cada índice. A implementação não reproduz o consenso do Ethereum nem a
arquitetura distribuída do Fabric. O registro local também não emite
certificados nem equivale funcionalmente a toda a infraestrutura de identidade
do Fabric, embora cumpra uma função didática de autorização.

## Problemas adicionais encontrados na base

1. **Produção com chave falsa:** `produzir_bloco` conferia o nome no rodízio,
   mas anexava o bloco sem verificar a chave do produtor. A assinatura falsa
   era detectada apenas ao chamar `validar()`. Isso precisava ser fortalecido
   para cumprir a autorização antes da gravação indicada nas seções 5.4 e 5.6.
2. **Falha de persistência:** as pendências eram apagadas e o bloco já estava
   em memória quando a gravação podia falhar. O processo ficava com um estado
   diferente do SQLite, sem preservar as pendências para repetição.
3. **Gênese reescrito:** um novo conteúdo do bloco zero, acompanhado de hash
   recalculado, passava na verificação quando a cadeia tinha somente o gênese.
4. **Revalidação de pendências:** alterações nas pendências ou revogação do
   sensor depois da submissão não eram verificadas antes da produção.
5. **Estruturas inválidas:** uma cadeia sem gênese retornava válida. Algumas
   estruturas malformadas geravam exceções internas; blocos não iniciais sem
   transações e timestamps não finitos também podiam ser aceitos.
6. **Índice da persistência:** o carregamento ignorava a diferença entre a chave
   primária SQL e o índice armazenado no JSON.
7. **Documentação do código:** README e comentários apresentavam o rodízio
   como consenso com finalidade definitiva. O PDF delimita melhor esse mecanismo.

Os itens 1 a 6 foram corrigidos nesta primeira etapa, e o README passou a
descrever o mecanismo local. O formato dos registros válidos foi preservado.

## Evidência da etapa 1

- Os 13 testes originais passaram antes das alterações.
- Foram escritos 11 cenários de regressão para os problemas encontrados.
  Todos reproduziram falhas na implementação original: 8 falhas de expectativa
  e 3 exceções não tratadas.
- Depois das correções, foram acrescentados mais 5 cenários para assinatura
  histórica falsa, banco real, rollback, JSON inválido e divergência de índice.
- A suíte final executou **29 testes, todos aprovados**: 13 da base e 16 regressões.
- A demonstração criou três blocos, retornou cadeia válida e detectou a
  alteração posterior da leitura do bloco 1.
- Ambiente observado: Python 3.12.14, cryptography 50.0.2, SQLite 3.53.1,
  Windows AMD64. Os testes foram executados com `python -m unittest -v` e a
  demonstração com `python demo.py`, usando o Python disponível no ambiente.
- O diretório temporário dos testes foi direcionado para a pasta do projeto
  porque o SQLite não conseguiu abrir arquivos no TEMP padrão do ambiente
  isolado. Essa restrição foi contornada antes de validar a suíte original.

O teste antigo que aceitava a produção com chave falsa para depois detectá-la
foi atualizado para exigir rejeição antecipada. Um teste separado verifica
a detecção de assinatura falsa em bloco já existente.

Essas verificações avaliam casos funcionais e falhas selecionadas. Não medem
TPS, latência de transações, disponibilidade ou resistência a ataques distribuídos.

## Evolução por etapas

| Etapa | Entrega | Critério de conclusão |
|---|---|---|
| 1 - Núcleo consistente | Rejeição antes da gravação, gênese fixo, transações SQLite e erros controlados | Concluída; 29 testes aprovados e demonstração executada |
| 2 - Estado recuperável e identidades | Persistência de membros e validadores; gestão de chaves; política de revogação histórica; anti-replay com formato versionado | Concluída; 62 testes no total, reinício e demonstração verificados; detalhes em ETAPA_2.md |
| 3 - Aplicação e simulador | Serviço Python para envio assinado, produção, consulta e validação; simulador com leituras, unidades e identificação | Concluída; 95 testes no total, incluindo Waitress e sensor em processo separado; detalhes em ETAPA_3.md |
| 4 - Apresentação visual | Painel para acompanhar sensores simulados, pendências, validadores, blocos, histórico e verificação de integridade | Concluída; 110 testes no total e revisão no navegador em desktop/celular; detalhes em ETAPA_4.md |
| 5 - Experimentos e documentação final | Carga controlada, repetições, latência, throughput, consumo e comparação com SQLite equivalente | Concluída no escopo local; 24 execuções finais, dados brutos, figuras, protocolo, texto complementar e roteiro de defesa; detalhes em ETAPA_5.md |

A API e o painel são evoluções propostas para a apresentação. A seção 5
do PDF registra explicitamente que eles não existem na versão analisada.
A comunicação entre múltiplos nós e o consenso distribuído constituem uma
etapa adicional de pesquisa, caso sejam exigidos pelo escopo final do TCC.

Na etapa 2, cada bloco passou a assinar o hash da versão de cadastro vigente
na sua altura de confirmação. Revogações e trocas de chaves entram em vigor
no próximo bloco, conforme o cadastro local persistido. O relógio declarado
pelo dispositivo não altera essa autorização. A política e seus limites estão
detalhados em ETAPA_2.md.

## Limitações ao encerrar a etapa 1 (registro histórico)

- Sem registro persistente de identidades, configuração persistida ou
  armazenamento cifrado de chaves privadas.
- Sem anti-replay, schema versionado ou metadados de medição completos.
- Revogação ou substituição de chave ainda pode invalidar registros anteriores.
- Blocos e pendências são estruturas acessíveis em memória; o código detecta
  alterações nos cenários testados, sem impedir acesso administrativo ao processo.
- Sem recuperação de pendências após queda de processo ou proteção contra
  truncamento do final do ledger mediante checkpoint confiável externo.
- Sem rede distribuída, protocolo de consenso, sensor físico ou benchmark.
- Sem comprovação de veracidade física dos dados, conforme o problema do oráculo.
- A validação integral antes de produzir cada bloco aumenta o custo com o
  tamanho do histórico; deverá ser considerada nos experimentos de desempenho.

## Atualizações necessárias no manuscrito após esta etapa

As seções 5.3, 5.5 e 5.6 devem refletir a validação anterior à gravação e a
ordem de persistência. A seção 6 e a Tabela 4 devem distinguir os 13 testes
da base dos 29 testes da versão evoluída, atualizar o caso de chave falsa e
identificar o novo ambiente de execução. Os números descritos para Linux no
PDF pertencem à execução anterior e não devem ser substituídos sem contexto.

As limitações ainda existentes devem continuar documentadas. O número de
testes aprovados não deve ser convertido em alegação de cobertura integral,
segurança formal ou desempenho de uma blockchain distribuída.
