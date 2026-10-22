# Dados operacionais

O Bash prepara a instalação em `apresentacao/` dentro desta pasta na primeira
execução. Cada instalação contém o SQLite, configuração e chaves cifradas.
Uma pasta existente nunca é apagada ou substituída automaticamente.

Os dados operacionais não acompanham a distribuição e são ignorados pelo Git.
Para outra instalação independente, use `bash executar.sh --dados ./dados/defesa`.
Faça backup da instalação e mantenha a senha sob sua responsabilidade.
