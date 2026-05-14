# Tratamento de Duplicatas

O modulo `src/tratar_duplicatas.py` consolida itens repetidos antes da geracao do TXT.

## Chave de consolidacao

Itens sao considerados duplicados quando compartilham:

- codigo NeoGrid;
- descricao final;
- unidade;
- preco unitario.

## Comportamento

- A quantidade e somada.
- O menor numero de linha de origem e preservado como referencia.
- O objetivo e evitar repeticao desnecessaria no TXT final.
