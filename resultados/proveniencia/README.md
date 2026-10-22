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

Não houve nova coleta ou execução dos testes após a reorganização. Para novas
medições, utilize `tools/experimentos.py` após instalar o pacote e escolha
uma pasta de resultados nova. Os resultados históricos não devem ser
apresentados como medição de Bash, instalação ou funcionamento do novo pacote.
