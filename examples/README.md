# Exemplos e demonstrações

Após instalar o projeto, as demonstrações podem ser chamadas como módulos:

```bash
python -m blockchain_tcc.demos.demo
python -m blockchain_tcc.demos.demo_persistencia criar dados/exemplo
python -m blockchain_tcc.demos.demo_persistencia continuar dados/exemplo
python -m blockchain_tcc.demos.demo_persistencia verificar dados/exemplo
```

Use o Python da `.venv`, conforme o guia em `docs/GUIA_EXECUCAO.md`.
O primeiro exemplo é em memória. O segundo preserva estado, exige senha para
criar/continuar e recusa reutilizar uma pasta já existente na criação.

Para apresentar o sistema com interface, execute `bash executar.sh` e siga
`docs/ROTEIRO_DEFESA.md`. Os códigos das demonstrações ficam em
`src/blockchain_tcc/demos/`, dentro do pacote instalado.
