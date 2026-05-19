# silo-automacao

Projeto Python para converter ordens de compra em PDF para arquivos TXT no padrao NeoGrid, com foco em importacao no ERP e operacao futura em servidor Windows.

## Visao Geral

O projeto recebe ordens de compra em PDF, interpreta os dados do documento, cruza os itens com uma tabela de produtos do ERP, aplica regras de conversao comercial e gera um arquivo TXT no layout NeoGrid.

Hoje o projeto ja cobre:

- extracao de texto de PDFs
- parse de uma ou mais OCs por arquivo
- tratamento da tabela de produtos
- De/Para por similaridade
- conversoes de quantidade e valor
- validacoes antes da geracao do TXT
- geracao de relatorios Excel
- geracao do TXT NeoGrid
- processamento em lote de uma pasta de PDFs

Tambem ja existe documentacao para a proxima etapa de implantacao automatica no servidor Windows.

## Objetivo

Automatizar a conversao de ordens de compra em PDF para TXT no padrao NeoGrid, reduzindo digitacao manual, padronizando a integracao com o ERP e preparando o processo para rodar de forma autonoma no servidor da empresa.

## Escopo Atual

O pipeline atual executa as seguintes etapas:

1. Carrega a tabela de produtos.
2. Trata duplicatas e inconsistencias do cadastro.
3. Extrai o texto do PDF.
4. Interpreta os dados da OC.
5. Identifica os produtos na tabela do ERP.
6. Aplica regras de conversao de quantidade, embalagem e valor.
7. Gera um relatorio de conversao.
8. Valida os dados processados.
9. Gera o TXT NeoGrid.

## Estrutura Do Projeto

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
|  |- campos_mapeados.md
|  |- desenho_tecnico_automacao_servidor.md
|  |- layout_neogrid.md
|  |- prompts_etapa_automacao_servidor.md
|  |- regras_conversao.md
|  |- resumo_andamento_projeto.md
|  \- tratamento_duplicatas.md
|- src/
|  |- config.py
|  |- extrair_pdf.py
|  |- gerar_txt_neogrid.py
|  |- main.py
|  |- parser_oc.py
|  |- produtos_depara.py
|  |- relatorio_processamento.py
|  |- tratar_duplicatas.py
|  \- validar_txt.py
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

## Arquivos De Apoio

Arquivos necessarios para a operacao atual:

- PDFs das ordens de compra
- tabela de produtos do ERP
- documento de layout NeoGrid
- exemplos de TXT para comparacao e homologacao

Localizacao atual no projeto:

- PDFs de entrada: `data/entrada/ordens_pdf`
- tabela de produtos: `data/apoio/Tabela de produtos.xlsx`
- layout NeoGrid: `data/apoio/NeoGrid PEDIDOS.pdf`
- exemplo de TXT: `data/exemplos/txt_exemplo_neogrid.txt`

## Instalacao

Crie um ambiente virtual e instale as dependencias:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Dependencias principais:

- `pandas`
- `openpyxl`
- `pdfplumber`
- `rapidfuzz`
- `python-dotenv`
- `pytest`

## Como Executar

### Processar um PDF especifico

```powershell
python -m src.main "data/entrada/ordens_pdf/ordem_compra.pdf"
```

### Processar todos os PDFs de uma pasta

```powershell
python -m src.main "data/entrada/ordens_pdf"
```

## Saidas Geradas

O processamento gera:

- TXT final em `data/saida/txt_gerados`
- relatorio de conversao em `data/saida/relatorios`
- relatorio de duplicatas em `data/saida/relatorios`

Padroes de nome:

- TXT: `OC_<numero_oc>.txt`
- relatorio de conversao: `relatorio_conversao_OC_<numero_oc>.xlsx`

## Modulos Principais

### `src/extrair_pdf.py`

Responsavel por:

- abrir o PDF com `pdfplumber`
- extrair o texto de todas as paginas
- preservar a estrutura das linhas
- salvar um `.txt` de apoio quando necessario

### `src/parser_oc.py`

Responsavel por interpretar o texto da ordem de compra.

Capacidades atuais:

- extrai cabecalho, itens e totais
- reconstrui descricoes quebradas em varias linhas
- suporta mais de uma OC dentro do mesmo PDF

### `src/tratar_duplicatas.py`

Responsavel por limpar a tabela de produtos.

Regras atuais:

- normaliza os textos
- cria `item_normalizado`
- remove duplicatas exatas
- separa casos para revisao
- gera arquivos de apoio em `data/saida/relatorios`

### `src/produtos_depara.py`

Responsavel por:

- carregar a tabela tratada
- validar colunas obrigatorias
- buscar produtos por correspondencia exata ou aproximada
- aplicar regras de conversao de embalagem, unidade e valor

### `src/relatorio_processamento.py`

Responsavel por gerar um DataFrame com o resultado da conversao item a item, incluindo:

- item encontrado
- codigo silo
- descricao ERP
- quantidade original
- quantidade convertida
- valor unitario convertido
- valor total convertido
- score
- status

### `src/validar_txt.py`

Responsavel por validar:

- produtos convertidos
- consistencia dos totais
- estrutura do TXT gerado

### `src/gerar_txt_neogrid.py`

Responsavel por gerar o TXT NeoGrid com registros:

- `019`
- `024`
- `040`
- `090`

### `src/main.py`

Responsavel pela orquestracao do fluxo completo.

## Regra De De/Para De Produtos

A descricao do item no PDF e cruzada com a coluna `Item` da tabela de produtos. A partir disso, o sistema retorna:

- `COD. SILO`
- `DESCRIÇÃO`
- regra de conversao, quando existir

O processo usa:

- correspondencia exata por `item_normalizado`
- correspondencia aproximada com `rapidfuzz`

## Status Possiveis Do Produto

- `encontrado_exato`
- `encontrado_aproximado`
- `revisar`
- `nao_encontrado`

Regra de liberacao:

- o TXT so pode ser gerado quando todos os itens estiverem em `encontrado_exato` ou `encontrado_aproximado`

## Tratamento De Duplicatas

Regras atuais:

- duplicatas exatas sao removidas automaticamente
- itens iguais com codigos diferentes sao separados para revisao
- a tabela tratada gera arquivos auxiliares para auditoria

Arquivos gerados:

- `produtos_unicos.xlsx`
- `produtos_duplicados_para_revisao.xlsx`

## Regras De Conversao Ja Implementadas

O projeto ja possui conversoes comerciais importantes, incluindo:

- divisao por embalagem com arredondamento sempre para cima
- arredondamento para multiplos fixos
- conversao de filme PVC de `500m` para `1000m`
- regra especial da Farinha de Rosca vendida em pacotes de `5KG`
- conversoes de docinhos por caixa de `50`, `150` e `160`
- excecoes em que a quantidade no sistema precisa ser lancada por multiplo de pacote fechado

### Exemplos de regras suportadas

- `130` unidades com regra `50` vira `3` caixas
- `151` unidades com regra `150` vira `2` caixas
- `130` unidades com regra `160` vira `1` caixa
- `90` guardanapos com multiplo `72` vira `144`
- `13` Fibraço Verde Grosso com multiplo `10` vira `20`
- `12 KG` de Farinha de Rosca vira `3` pacotes de `5KG`

## Regra De Valor Nas Conversoes

Quando a conversao representa troca de unidade comercial:

- a quantidade e convertida
- o valor unitario e ajustado para a nova unidade de venda
- o valor total e recalculado com base na quantidade convertida

Exemplo:

- `151` doces a `0,37` com conversao `150`
- resultado:
  - `2` caixas
  - `valor_unitario = 55,50`
  - `valor_total = 111,00`

## Validacoes Atuais

Antes de gerar o TXT, o sistema valida:

- se todos os produtos foram convertidos
- se nao ha itens para revisao manual
- se nao ha itens nao encontrados
- se o total dos itens bate com o total da OC
- se o TXT gerado possui estrutura minima esperada

## Testes

Para rodar a suite de testes:

```powershell
python -m pytest -q
```

Cobertura atual por modulo:

- extracao de PDF
- parser de OC
- tratamento de duplicatas
- De/Para de produtos
- relatorio de conversao
- validacao do TXT
- geracao do TXT
- fluxo principal

## Estado Atual Do Projeto

O projeto ja esta funcional ponta a ponta para os exemplos atualmente trabalhados.

Ja foram validados:

- processamento de OCs reais em PDF
- aplicacao das principais regras de conversao
- geracao dos TXTs NeoGrid
- geracao dos relatorios Excel
- processamento de uma pasta com varias OCs

## Proxima Etapa: Automacao No Servidor

O proximo objetivo e tirar a execucao da maquina local e colocar o processo para rodar automaticamente no servidor Windows da empresa.

Decisoes ja definidas:

- o servidor roda Windows
- a automacao usara a pasta de rede:
  - `\\Servidor\arquivos rede\AUTOMAÇÃO OC`
- a tabela de produtos ficara no servidor
- os PDFs processados devem ser mantidos
- os PDFs processados devem ser renomeados com o numero da OC
- neste primeiro momento, erros serao tratados por pasta e relatorio

Estrutura prevista no servidor:

- `entrada`
- `processando`
- `processados`
- `erro`
- `saida\txt_gerados`
- `saida\relatorios`
- `apoio`
- `logs`

## Documentacao Da Etapa Do Servidor

Arquivos ja criados para apoiar essa implantacao:

- [desenho_tecnico_automacao_servidor.md](docs/desenho_tecnico_automacao_servidor.md)
- [prompts_etapa_automacao_servidor.md](docs/prompts_etapa_automacao_servidor.md)
- [resumo_andamento_projeto.md](docs/resumo_andamento_projeto.md)

## Publicacao E Versionamento

Para revisar o status local:

```powershell
git status
```

Para rodar os testes antes de subir alteracoes:

```powershell
python -m pytest -q
```

## Observacoes Importantes

- a qualidade da tabela de produtos influencia diretamente a qualidade do De/Para
- novas regras comerciais podem exigir novos tratamentos em `src/produtos_depara.py`
- o layout NeoGrid ainda pode receber refinamentos conforme homologacao com o ERP
- a etapa de servidor sera implementada sobre o pipeline atual, nao em paralelo separado

