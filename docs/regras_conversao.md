# Regras de Conversao

## Fluxo inicial

1. Extrair texto do PDF da ordem de compra.
2. Ler cabecalho da OC por linhas no formato `CHAVE: VALOR`.
3. Ler itens por linhas no formato `ITEM|codigo|descricao|quantidade|unidade|preco`.
4. Aplicar de-para de produtos a partir da planilha de apoio.
5. Consolidar duplicatas por codigo NeoGrid, unidade e preco.
6. Gerar TXT final.
7. Validar o arquivo antes de salvar.

## Regras adotadas nesta fase

- Se um produto nao existir no de-para, o codigo original e mantido.
- Se a descricao NeoGrid nao estiver mapeada, a descricao original e mantida.
- Itens duplicados sao somados por quantidade quando compartilham o mesmo codigo, unidade, preco e descricao.
- Valores numericos sao gravados com duas casas decimais.
