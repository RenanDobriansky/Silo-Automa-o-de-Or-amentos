# Resumo Do Andamento Do Projeto

Este arquivo consolida o que ja foi definido, implementado e validado no projeto `silo-automacao` ate o momento.

## Objetivo Do Projeto

Converter ordens de compra em PDF para arquivos TXT no padrao NeoGrid, para posterior importacao no ERP.

O fluxo atual do projeto cobre:

- leitura da tabela de produtos
- tratamento de duplicatas
- extracao de texto dos PDFs
- parse das ordens de compra
- cruzamento de produtos via De/Para
- aplicacao de regras de conversao
- validacoes antes da geracao
- geracao do TXT NeoGrid
- salvamento de relatorios de apoio

## Estrutura Ja Montada

O projeto foi estruturado com as pastas:

- `data/entrada/ordens_pdf`
- `data/saida/txt_gerados`
- `data/saida/relatorios`
- `data/apoio`
- `data/exemplos`
- `docs`
- `src`
- `tests`

Tambem foram criados:

- `README.md`
- `requirements.txt`
- `.gitignore`

## Dependencias Definidas

O projeto usa:

- `pandas`
- `openpyxl`
- `pdfplumber`
- `rapidfuzz`
- `python-dotenv`
- `pytest`

## Modulos Implementados

### `src/tratar_duplicatas.py`

Responsavel por limpar a tabela de produtos.

Regras implementadas:

- normalizacao de textos
- criacao de `item_normalizado`
- remocao de duplicatas exatas
- separacao de casos para revisao
- geracao de:
  - `produtos_unicos.xlsx`
  - `produtos_duplicados_para_revisao.xlsx`

Depois, a logica foi evoluida para escolher automaticamente o melhor cadastro por similaridade entre `Item` e `DESCRICAO`, mantendo sinalizacao de revisao quando necessario.

### `src/produtos_depara.py`

Responsavel por:

- carregar a tabela tratada
- validar colunas obrigatorias
- bloquear conflitos de `item_normalizado` com codigos diferentes
- buscar produto por correspondencia exata ou aproximada
- aplicar regras de conversao de quantidade/unidade

Status possiveis da busca:

- `encontrado_exato`
- `encontrado_aproximado`
- `revisar`
- `nao_encontrado`

## Regras De Conversao Definidas

Com a nova tabela de produtos, foi incluida uma coluna `CONVERSAO`.

As regras implementadas hoje sao:

- conversao numerica com arredondamento sempre para cima
  - exemplo: `130` com regra `50` vira `3`
- regras textuais de divisao, tambem arredondando para cima
- regra dos filmes PVC:
  - exemplo: pedido `3` de rolos `500m` vira `2` no sistema quando a regra indica que duas unidades de `500` equivalem a uma de `1000`
- excecao dos guardanapos:
  - nesse caso nao dividimos pela embalagem
  - a quantidade e arredondada para o proximo multiplo do fardo
  - exemplo: `90` guardanapos vira `144` no sistema quando a regra for `ARREDONDAR MULTIPLO DE 72`

## `src/extrair_pdf.py`

Responsavel por:

- abrir o PDF com `pdfplumber`
- extrair texto de todas as paginas
- preservar a estrutura das linhas
- salvar um `.txt` de apoio quando necessario

## `src/parser_oc.py`

Responsavel por interpretar o texto extraido da ordem de compra.

Campos ja tratados:

- fornecedor
- numero da OC
- CNPJ do fornecedor
- comprador
- condicao de pagamento
- endereco de entrega
- endereco de faturamento
- CNPJ de faturamento
- data de entrega
- itens
- total da unidade
- total do fornecedor

Regras importantes:

- reconstrucao de descricoes quebradas em varias linhas
- suporte a mais de uma ordem de compra dentro do mesmo PDF
- compatibilidade com o fluxo atual do projeto

## `src/relatorio_processamento.py`

Responsavel por gerar o relatorio da conversao dos itens antes do TXT final.

Colunas principais do relatorio:

- `numero_oc`
- `sequencia`
- `item_pdf`
- `item_encontrado_tabela`
- `codigo_silo`
- `descricao_erp`
- `quantidade_original`
- `quantidade`
- `unidade`
- `valor_unitario`
- `valor_total`
- `regra_conversao`
- `criterio_conversao`
- `score`
- `status`

Tambem controla se o TXT pode ou nao ser gerado automaticamente.

## `src/gerar_txt_neogrid.py`

Responsavel pela geracao do TXT no layout NeoGrid.

Registros implementados:

- `019`
- `024`
- `040`
- `090`

Regras atuais:

- um item da ordem gera uma linha `040`
- o codigo do item vem do `COD. SILO` retornado pelo De/Para
- o `090` soma os valores dos itens
- campos ainda nao mapeados completamente permanecem com zeros ou espacos fixos, conforme placeholder do layout

## `src/validar_txt.py`

Responsavel pelas validacoes antes e depois da geracao do TXT.

Validacoes implementadas:

- bloqueio se houver item com `revisar`
- bloqueio se houver item com `nao_encontrado`
- comparacao entre total dos itens e total do fornecedor com tolerancia de `0.01`
- verificacao estrutural das linhas do TXT

## `src/main.py`

Responsavel pela orquestracao do processamento completo.

Fluxo atual:

1. recebe um PDF ou uma pasta com PDFs
2. trata a tabela de produtos
3. carrega a tabela limpa
4. extrai o texto do PDF
5. parseia a ordem
6. gera o relatorio de conversao
7. valida produtos e totais
8. gera o TXT NeoGrid
9. salva o relatorio em Excel
10. mostra no terminal o resumo do processamento

Tambem foi ajustado para processar todos os PDFs dentro de `data/entrada/ordens_pdf`.

## Arquivos De Apoio

Na pasta `data/apoio`, passamos a trabalhar com:

- `Tabela de produtos.xlsx`
- `NeoGrid PEDIDOS.pdf`

Posteriormente a tabela foi substituida por uma nova versao com coluna adicional de conversao.

## Ajustes De Documentacao E Publicacao

Ja foram atualizados:

- `README.md`
- `.gitignore`

O `.gitignore` foi preparado para nao subir:

- ambientes virtuais
- caches
- PDFs de entrada reais
- arquivos operacionais de `data/apoio`
- saidas geradas em `data/saida`

## Testes Automatizados

Foram criados testes para:

- tratamento de duplicatas
- De/Para de produtos
- extracao de PDF
- parser da OC
- relatorio de processamento
- geracao do TXT
- validacoes
- fluxo principal

Ultima validacao registrada:

- `35 passed`

## Teste Real Com Os PDFs Da Pasta

Foi executado o processamento real da pasta `data/entrada/ordens_pdf`.

Resultado:

- 8 PDFs processados com sucesso
- 8 relatorios gerados
- 8 arquivos TXT gerados

OCs processadas com status `ok`:

- `623986`
- `626856`
- `626855`
- `632917`
- `632916`
- `626677`
- `624063`
- `621860`

## Situacao Atual

O projeto esta funcional ponta a ponta para os exemplos atuais.

Ja existe:

- pipeline completo
- tabela de produtos substituida
- regras de conversao ajustadas
- testes automatizados passando
- geracao real de TXT para as OCs de exemplo

## Pontos Que Ainda Podem Evoluir

- refino fino da tabela de produtos conforme revisoes manuais
- revisao detalhada de todos os campos do layout NeoGrid
- ampliacao das regras de conversao para novos casos da tabela
- validacoes adicionais de negocio
- melhoria dos relatorios para auditoria operacional

