# Proveniência dos resultados científicos

`../execucao-final/` conserva a coleta da etapa 5 anterior à organização em
pacote Python. O arquivo `fontes-medidas.zip` contém exatamente os arquivos
identificados em `../execucao-final/fontes_sha256.json`, com seus nomes antigos.
Essa cópia mantém a implementação medida disponível junto aos resultados.

Para recuperar aquela versão de pesquisa, extraia o ZIP em outra pasta e
utilize seu próprio ambiente virtual e instruções. Não sobreponha a aplicação
atual. Nenhuma chave privada ou senha foi incluída nessa cópia.

Os hashes científicos antigos referem-se aos arquivos dentro do ZIP, não
aos módulos reorganizados em `src/blockchain_tcc`. Os hashes da distribuição
atual estão no `MANIFESTO_SHA256.json` da raiz. `docs/MIGRACAO.json` relaciona
os módulos principais anteriores e atuais.

Após a reorganização, a verificação funcional de 2 de novembro de 2026 aprovou 113 testes. A coleta de desempenho permanece a da etapa 5. Para novas
medições, utilize `tools/experimentos.py` após instalar o pacote e escolha
uma pasta de resultados nova. Os resultados históricos não devem ser
apresentados como medição de Bash, instalação ou funcionamento do novo pacote.

O manifesto histórico da distribuição está em `MANIFESTO_DISTRIBUICAO_ANTERIOR.json`. O manifesto da raiz identifica os bytes da entrega atual. Os arquivos de texto da coleta foram restaurados com as quebras de linha que reproduzem os SHA-256 do manifesto experimental original.
