# Roteiro da demonstração e defesa

## Antes da apresentação

Prepare uma pasta nova, evitando o histórico usado para os experimentos. Na
pasta do projeto:

```powershell
.\.venv\Scripts\python.exe -m blockchain_tcc.preparar_demo_api .\dados\defesa
.\.venv\Scripts\python.exe -m blockchain_tcc.iniciar_api .\dados\defesa --apresentacao
```

O preparador solicita a senha das chaves; a API solicita essa mesma senha e um
token administrativo. Guarde ambos durante a sessão. Abra
`http://127.0.0.1:5000/painel` e informe o token. Consulte os requisitos de senha
e token em `ETAPA_4.md`. Ao reutilizar uma instalação preparada, execute apenas
o segundo comando. Não execute novamente o preparador na mesma pasta.

## Sequência sugerida (8 a 10 minutos)

1. **Problema e escopo (1 min).** Explique integridade e rastreabilidade de
   leituras IoT. Identifique o protótipo como processo local com identidades
   autorizadas, usando dados simulados. A comparação de plataformas do TCC é
   bibliográfica; o protótipo não reproduz uma rede Ethereum ou Fabric.
2. **Identidades (1 min).** Mostre sensores, chave pública e autoridades.
   Explique que o sensor assina a leitura, a autoridade assina o bloco e o
   administrador local mantém o cadastro.
3. **Do dado ao bloco (2 min).** Gere leituras, mostre a fila, produza um bloco
   e abra os detalhes. Destaque unidade, ID, timestamp, hash anterior e assinatura.
   Produza outro bloco para mostrar a mudança da autoridade da vez.
4. **Rastreabilidade (1 min).** Abra o histórico de um sensor e relacione uma
   leitura com seu bloco. Explique que o timestamp é declarado pelo emissor.
5. **Integridade (2 min).** Altere uma leitura na cópia do laboratório. Mostre
   a incompatibilidade de hash. Repita com recálculo e mostre a assinatura
   inválida. Verifique novamente o original para confirmar que continua íntegro.
6. **Resultados (1 min).** Apresente a figura e a tabela de
   `resultados/execucao-final/`. Defina confirmação, agrupamento e três repetições.
   Explique os custos adicionais frente ao controle SQLite e a revalidação histórica.
7. **Conclusão e limites (1 min).** Separe autoria, integridade e veracidade
   física. Registre ausência de rede distribuída e limites das medições.

## Perguntas prováveis

**Por que SQLite se existe uma blockchain?** SQLite é o armazenamento local
dos blocos. Encadeamento, assinaturas e regras de autorização são verificações
do programa. A persistência, isoladamente, não cria consenso distribuído.

**São três nós?** São três identidades de autoridade em um único processo.
O rodízio não fornece votação, replicação ou tolerância a falhas de nós.

**O administrador consegue alterar dados?** Quem controla processo, banco e
chaves possui poderes relevantes. O protótipo detecta inconsistências nos
cenários implementados; não impede reescrita completa por um administrador
com todas as chaves nem detecta todo truncamento sem uma referência externa.

**Por que o SQLite convencional é mais rápido?** Ele armazena JSON assinado,
mas não executa o conjunto de validações e blocos do ledger. O experimento
compara esses conjuntos de operações; não atribui todo o custo a uma assinatura.

**Revogar apaga leituras antigas?** Não. O cadastro é versionado por altura
de bloco. Eventos anteriores usam a versão histórica e novas operações do
sensor revogado são recusadas.

**Um sensor pode mentir?** Pode assinar um valor fisicamente falso. A assinatura
vincula conteúdo e chave, sem verificar o fenômeno físico ou calibração.

**O benchmark mede o painel?** Não. Mede o núcleo com persistência, em carga
sequencial. HTTP, navegador e descriptografia de chaves ficam fora da janela.

## Se houver falha durante a demonstração

- API indisponível: confira o terminal e o endereço/porta; recarregue e conecte
  novamente. Recarregar remove o token da memória da aba.
- Fila com leitura de sensor revogado: use o descarte explícito daquela pendência
  ou prepare uma nova pasta em outro nome. Não altere o banco manualmente.
- Para mostrar persistência: encerre a API e reabra com a mesma pasta e senha;
  defina o token da nova sessão. Somente blocos confirmados são recuperados.
- Se precisar mostrar os resultados sem executar carga, use os arquivos e as
  figuras já entregues. Não é necessário rodar o benchmark durante a defesa.
