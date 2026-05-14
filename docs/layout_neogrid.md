# Layout NeoGrid

Este documento descreve o layout inicial adotado pelo projeto para gerar arquivos TXT em um formato NeoGrid simplificado.

## Estrutura base

- `H|numero_pedido|fornecedor|cnpj|data_entrega`
- `D|sequencia|codigo_produto|descricao|quantidade|unidade|preco_unitario`

## Observacoes

- O layout atual e um ponto de partida tecnico para desenvolvimento e testes.
- A estrutura pode ser ajustada quando o layout oficial do parceiro ou do ERP estiver consolidado.
- O modulo `src/validar_txt.py` valida apenas a consistencia basica desse formato inicial.
