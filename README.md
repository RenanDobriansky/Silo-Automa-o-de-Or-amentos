# silo-automacao

Projeto Python para converter ordens de compra em PDF para arquivos TXT no padrao NeoGrid, para importacao no ERP.

## Objetivo

O objetivo do projeto e converter ordens de compra em PDF para TXT no padrao NeoGrid para importacao no ERP.

## Estrutura de Pastas

```text
silo-automacao/
|- README.md
|- requirements.txt
|- .gitignore
|- data/
|  |- entrada/
|  |  \- ordens_pdf/
|  |- saida/
|  |  |- txt_gerados/
|  |  \- relatorios/
|  |- apoio/
|  |  |- Tabela de produtos.xlsx
|  |  \- NeoGrid PEDIDOS.pdf
|  \- exemplos/
|     |- ordem_compra_exemplo.pdf
|     \- txt_exemplo_neogrid.txt
|- docs/
|  |- layout_neogrid.md
|  |- regras_conversao.md
|  |- campos_mapeados.md
|  \- tratamento_duplicatas.md
|- src/
|  |- main.py
|  |- config.py
|  |- extrair_pdf.py
|  |- parser_oc.py
|  |- produtos_depara.py
|  |- tratar_duplicatas.py
|  |- gerar_txt_neogrid.py
|  |- validar_txt.py
|  \- relatorio_processamento.py
\- tests/
   |- test_extrair_pdf.py
   |- test_gerar_txt.py
   |- test_main.py
   |- test_parser_oc.py
   |- test_produtos_depara.py
   |- test_relatorio_processamento.py
   |- test_tratar_duplicatas.py
   \- test_validar_txt.py
```

## Instalacao de Dependencias

```bash
pip install -r requirements.txt
```

## Como Executar

Para processar um PDF:

```bash
python -m src.main "data/entrada/ordens_pdf/ordem_compra.pdf"
```

O `main.py` tambem aceita uma pasta com varios PDFs.

## Arquivos Necessarios

- PDFs das ordens de compra
- `tabela_produtos.xlsx`
- TXT exemplo NeoGrid
- documento de layout NeoGrid

No projeto atual, esses arquivos ficam principalmente em:

- `data/entrada/ordens_pdf/`
- `data/apoio/Tabela de produtos.xlsx`
- `data/exemplos/txt_exemplo_neogrid.txt`
- `data/apoio/NeoGrid PEDIDOS.pdf`

## Regra de De/Para de Produtos

A descricao do item no PDF sera cruzada com a coluna `Item` da tabela de produtos, retornando `COD. SILO` e `DESCRIÇÃO`.

## Tratamento de Duplicatas

- Duplicatas exatas serao removidas automaticamente.
- Itens iguais com codigos diferentes serao enviados para revisao.
- Enquanto houver duplicatas criticas, o TXT nao sera gerado.

## Status Possiveis dos Produtos

- `encontrado_exato`
- `encontrado_aproximado`
- `revisar`
- `nao_encontrado`

## Saidas Geradas

- TXT final em `data/saida/txt_gerados`
- relatorio de conversao em `data/saida/relatorios`
- relatorio de duplicatas em `data/saida/relatorios`
