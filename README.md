# silo-automacao

Automacao de ordens de compra em PDF para arquivos TXT no padrao NeoGrid, com integracao ao ERP e operacao automatica no servidor Windows.

## Visao Geral

O projeto executa o fluxo completo abaixo:

1. le o PDF da ordem de compra
2. extrai e interpreta cabecalho, itens e totais
3. cruza os itens com a tabela de produtos do ERP
4. aplica regras de conversao comercial
5. valida o resultado
6. gera o TXT NeoGrid
7. gera relatorios de apoio
8. processa automaticamente os arquivos no servidor

Hoje o projeto ja esta funcionando no servidor com agendamento automatico.

## O Que O Projeto Entrega

| Etapa | Descricao |
| --- | --- |
| Extracao | Leitura de PDFs com `pdfplumber` |
| Parser | Interpretacao de uma ou mais OCs no mesmo PDF |
| De/Para | Busca exata e aproximada na tabela de produtos |
| Conversoes | Ajuste de quantidade, embalagem e valor |
| Validacao | Bloqueio por revisao, nao encontrado e divergencia de total |
| Saida | Geracao do TXT NeoGrid e relatorio de conversao |
| Operacao | Processamento manual, em lote e automatico no servidor |

## Fluxo Rapido

```text
PDF da OC
  -> extrair_pdf.py
  -> parser_oc.py
  -> tratar_duplicatas.py
  -> produtos_depara.py
  -> relatorio_processamento.py
  -> validar_txt.py
  -> gerar_txt_neogrid.py
  -> TXT NeoGrid + relatorios
```

## Estrutura Do Projeto

```text
silo-automacao/
|- README.md
|- requirements.txt
|- .gitignore
|- rodar_automacao_oc.bat
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
|  |- desenho_tecnico_automacao_servidor.md
|  |- agendamento_windows_automacao_oc.md
|  |- checklist_homologacao_automacao_oc.md
|  |- guia_implantacao_operacao_servidor.md
|  |- prompts_etapa_automacao_servidor.md
|  |- layout_neogrid.md
|  |- regras_conversao.md
|  |- tratamento_duplicatas.md
|  \- resumo_andamento_projeto.md
|- src/
|  |- auto_processar_pasta.py
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
   |- test_auto_processar_pasta.py
   |- test_config.py
   |- test_extrair_pdf.py
   |- test_gerar_txt.py
   |- test_main.py
   |- test_parser_oc.py
   |- test_produtos_depara.py
   |- test_relatorio_processamento.py
   |- test_tratar_duplicatas.py
   \- test_validar_txt.py
```

## Arquivos Necessarios

Arquivos essenciais para o funcionamento:

- PDFs das ordens de compra
- `Tabela de produtos.xlsx`
- `NeoGrid PEDIDOS.pdf`
- TXT de exemplo para homologacao, quando necessario

Localizacao padrao no projeto:

- PDFs de entrada: `data/entrada/ordens_pdf`
- tabela de produtos: `data/apoio/Tabela de produtos.xlsx`
- layout NeoGrid: `data/apoio/NeoGrid PEDIDOS.pdf`
- exemplo de TXT: `data/exemplos/txt_exemplo_neogrid.txt`

## Instalacao Local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
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

### Rodar o runner automatico manualmente

```powershell
python -m src.auto_processar_pasta
```

## Saidas Geradas

| Tipo | Local | Padrao de nome |
| --- | --- | --- |
| TXT final | `data/saida/txt_gerados` | `OC_<numero_oc>.txt` |
| Relatorio de conversao | `data/saida/relatorios` | `relatorio_conversao_OC_<numero_oc>.xlsx` |
| Relatorio de duplicatas | `data/saida/relatorios` | `produtos_unicos.xlsx` e `produtos_duplicados_para_revisao.xlsx` |

## Modulos Principais

### `src/extrair_pdf.py`

- extrai o texto bruto do PDF
- preserva a estrutura das linhas
- pode salvar um `.txt` de apoio

### `src/parser_oc.py`

- interpreta cabecalho, itens e totais
- recompõe descricoes quebradas em varias linhas
- suporta mais de uma OC no mesmo PDF

### `src/tratar_duplicatas.py`

- limpa a tabela de produtos
- normaliza textos
- remove duplicatas exatas
- separa casos para revisao

### `src/produtos_depara.py`

- carrega a tabela tratada
- busca produtos por correspondencia exata ou aproximada
- aplica regras de conversao de quantidade, embalagem e valor

### `src/relatorio_processamento.py`

- gera o relatorio item a item da conversao
- registra score, status, quantidade e valor convertidos

### `src/validar_txt.py`

- valida produtos convertidos
- valida totais
- valida estrutura do TXT

### `src/gerar_txt_neogrid.py`

- monta os registros `019`, `024`, `040` e `090`
- gera o TXT no layout NeoGrid

### `src/main.py`

- orquestra o fluxo completo de processamento
- suporta um PDF ou uma pasta com varios PDFs

### `src/auto_processar_pasta.py`

- runner do servidor Windows
- processa automaticamente a pasta de entrada
- move arquivos entre `entrada`, `processando`, `processados` e `erro`
- registra logs da execucao

## Regra De De/Para De Produtos

O item do PDF e cruzado com a coluna `Item` da tabela de produtos. A partir disso, o sistema retorna:

- `COD. SILO`
- `DESCRICAO`
- regra de conversao, quando existir

O processo usa:

- correspondencia exata por `item_normalizado`
- correspondencia aproximada com `rapidfuzz`

## Status Possiveis Do Produto

| Status | Significado |
| --- | --- |
| `encontrado_exato` | correspondencia direta encontrada |
| `encontrado_aproximado` | correspondencia aproximada aceitavel |
| `revisar` | ha indicio de correspondencia, mas exige conferencia humana |
| `nao_encontrado` | item nao foi localizado de forma segura |

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

O projeto cobre regras comerciais importantes, incluindo:

- divisao por embalagem com arredondamento sempre para cima
- arredondamento para multiplos fixos
- conversao de filme PVC de `500m` para `1000m`
- regra especial da Farinha de Rosca em pacotes de `5KG`
- conversoes de docinhos por caixa de `50`, `150` e `160`
- excecoes em que a quantidade no sistema precisa ser lancada por multiplo de pacote fechado

Exemplos:

- `130` unidades com regra `50` vira `3` caixas
- `151` unidades com regra `150` vira `2` caixas
- `130` unidades com regra `160` vira `1` caixa
- `90` guardanapos com multiplo `72` vira `144`
- `13` Fibraco Verde Grosso com multiplo `10` vira `20`
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

## Automacao No Servidor

O projeto ja esta implantado para operacao automatica no servidor Windows.

### Caminhos do servidor

Existem dois cenarios possiveis:

- caminho UNC quando acessado remotamente:
  - `\\Servidor\arquivos rede\AUTOMACAO OC`
- caminho local na propria maquina do servidor:
  - `C:\ARQUIVOS REDE\AUTOMACAO OC`

Na operacao atual do servidor, o caminho utilizado e:

- `C:\ARQUIVOS REDE\AUTOMACAO OC`

Essa definicao e controlada pela variavel:

- `AUTOMACAO_OC_ROOT`

### Estrutura operacional no servidor

- `entrada`
- `processando`
- `processados`
- `erro`
- `saida\txt_gerados`
- `saida\relatorios`
- `apoio`
- `logs`

### Protecoes operacionais implementadas

- trava de concorrencia com `.automacao_oc.lock`
- validacao de arquivo ainda em copia antes do processamento
- parametros configuraveis para intervalo e quantidade de leituras estaveis
- remocao de TXT parcial em caso de falha
- diferenciacao entre erro tecnico e erro de negocio
- arquivamento do PDF com nome `OC_<numero_oc>.pdf`

Variaveis de ambiente suportadas:

- `AUTOMACAO_OC_ROOT`
- `AUTOMACAO_OC_READY_CHECK_INTERVAL_SECONDS`
- `AUTOMACAO_OC_READY_STABLE_CHECKS`

## Execucao Pelo Agendador De Tarefas

A operacao automatica atual do servidor usa o arquivo [rodar_automacao_oc.bat](rodar_automacao_oc.bat).

Responsabilidades desse arquivo:

- define o caminho operacional do servidor
- configura os parametros de checagem de arquivo em copia
- posiciona o projeto no diretorio correto
- ajusta o `PYTHONPATH`
- chama o runner automatico
- grava um log complementar do agendador em:
  - `C:\ARQUIVOS REDE\AUTOMACAO OC\logs\agendador_execucao.log`

Trecho central da chamada:

```bat
set "AUTOMACAO_OC_ROOT=C:\ARQUIVOS REDE\AUTOMACAO OC"
set "AUTOMACAO_OC_READY_CHECK_INTERVAL_SECONDS=1.5"
set "AUTOMACAO_OC_READY_STABLE_CHECKS=2"
cd /d C:\Projetos\silo-automacao
set "PYTHONPATH=C:\Projetos\silo-automacao\src"
call C:\Projetos\silo-automacao\.venv\Scripts\python.exe -m auto_processar_pasta
```

## Testes

Para rodar a suite:

```powershell
python -m pytest -q
```

Cobertura atual:

- extracao de PDF
- parser de OC
- tratamento de duplicatas
- De/Para de produtos
- relatorio de conversao
- validacao do TXT
- geracao do TXT
- fluxo principal
- configuracao do servidor
- runner automatico da pasta

## Documentacao

Documentos principais desta etapa:

- [guia_implantacao_operacao_servidor.md](docs/guia_implantacao_operacao_servidor.md)
- [desenho_tecnico_automacao_servidor.md](docs/desenho_tecnico_automacao_servidor.md)
- [agendamento_windows_automacao_oc.md](docs/agendamento_windows_automacao_oc.md)
- [checklist_homologacao_automacao_oc.md](docs/checklist_homologacao_automacao_oc.md)
- [prompts_etapa_automacao_servidor.md](docs/prompts_etapa_automacao_servidor.md)
- [resumo_andamento_projeto.md](docs/resumo_andamento_projeto.md)

## Estado Atual

O projeto esta em um ponto maduro para:

- continuar refinando regras de conversao
- validar novos exemplos de OCs reais
- acompanhar a operacao automatica no servidor
- evoluir reprocessamento e monitoramento, se necessario

## Versionamento

Para revisar o estado local:

```powershell
git status
```

Para validar os testes antes de subir alteracoes:

```powershell
python -m pytest -q
```

## Observacoes Importantes

- a qualidade da tabela de produtos influencia diretamente o sucesso do De/Para
- novas regras comerciais podem exigir ajustes em `src/produtos_depara.py`
- o layout NeoGrid ainda pode receber refinamentos conforme homologacao com o ERP
- a operacao do servidor reutiliza o mesmo pipeline validado localmente
