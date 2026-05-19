# Desenho Tecnico Da Automacao No Servidor

## Objetivo

Executar a automacao de forma continua no servidor Windows, sem necessidade de interacao manual com Python ou terminal.

O comportamento esperado e:

- o usuario adiciona PDFs de ordens de compra em uma pasta de entrada
- o processo automatizado detecta os novos arquivos
- os PDFs sao processados
- os arquivos TXT NeoGrid sao gerados automaticamente
- os relatorios sao salvos
- os PDFs originais sao arquivados na pasta de processados com o numero da OC no nome
- erros ficam visiveis em pasta e relatorio, sem depender de aviso por e-mail neste primeiro momento

## Ambiente

- Sistema operacional do servidor: Windows
- Pasta raiz da automacao na rede:
  - `\\Servidor\arquivos rede\AUTOMAÇÃO OC`

## Estrutura De Pastas No Servidor

Pasta raiz:

- `\\Servidor\arquivos rede\AUTOMAÇÃO OC\entrada`
- `\\Servidor\arquivos rede\AUTOMAÇÃO OC\processando`
- `\\Servidor\arquivos rede\AUTOMAÇÃO OC\processados`
- `\\Servidor\arquivos rede\AUTOMAÇÃO OC\erro`
- `\\Servidor\arquivos rede\AUTOMAÇÃO OC\saida\txt_gerados`
- `\\Servidor\arquivos rede\AUTOMAÇÃO OC\saida\relatorios`
- `\\Servidor\arquivos rede\AUTOMAÇÃO OC\apoio`
- `\\Servidor\arquivos rede\AUTOMAÇÃO OC\logs`

## Finalidade De Cada Pasta

### `entrada`

Recebe os PDFs novos enviados pelos usuarios.

Regra:

- somente arquivos ainda nao processados devem ficar aqui

### `processando`

Recebe temporariamente os PDFs que ja foram capturados pelo processo automatico.

Regra:

- um arquivo deve sair de `entrada` e ir para `processando` antes do processamento real
- isso evita duplicidade e reduz risco de pegar arquivo ainda em copia

### `processados`

Recebe os PDFs processados com sucesso.

Regra:

- o arquivo deve ser renomeado com o numero da OC
- padrao sugerido:
  - `OC_<numero_oc>.pdf`
- em caso de mais de uma OC no mesmo PDF:
  - `OC_<numero_oc>_origem_<nome_original>.pdf`
  - ou manter o PDF unico com nome do primeiro pedido e registrar os demais no log

Observacao:

- como os PDFs devem ser mantidos, essa pasta vira o historico operacional

### `erro`

Recebe PDFs que nao puderam ser processados.

Casos esperados:

- produto nao encontrado
- item com revisao manual
- falha de leitura do PDF
- erro de validacao de totais
- problema de acesso a arquivo

### `saida\txt_gerados`

Recebe os arquivos TXT prontos para importacao no ERP.

Padrao de nome:

- `OC_<numero_oc>.txt`

### `saida\relatorios`

Recebe os relatorios Excel da conversao e outros artefatos de apoio.

Arquivos esperados:

- `relatorio_conversao_OC_<numero_oc>.xlsx`
- `produtos_unicos.xlsx`
- `produtos_duplicados_para_revisao.xlsx`
- possivel relatorio consolidado de execucao no futuro

### `apoio`

Recebe os arquivos necessarios para a automacao funcionar.

Arquivos previstos:

- `Tabela de produtos.xlsx`
- `NeoGrid PEDIDOS.pdf`

### `logs`

Recebe os logs tecnicos da execucao automatica.

Arquivos previstos:

- `automacao_oc_YYYY-MM-DD.log`
- ou `execucao_YYYYMMDD_HHMMSS.log`

## Fluxo Tecnico Da Automacao

### Fluxo Principal

1. O agendador do Windows dispara a automacao.
2. A automacao varre a pasta `entrada`.
3. Cada PDF elegivel e movido para `processando`.
4. O sistema carrega a tabela de produtos do servidor.
5. O sistema trata duplicatas e carrega o De/Para.
6. O sistema extrai o texto do PDF.
7. O sistema parseia uma ou mais ordens de compra.
8. O sistema gera o relatorio de conversao.
9. O sistema valida produtos, totais e estrutura de saida.
10. Se estiver tudo correto, gera o TXT NeoGrid.
11. O PDF e movido para `processados` com nome padrao por OC.
12. Se houver erro, o PDF vai para `erro`.
13. O log da execucao e gravado em `logs`.

## Componentes De Software Previsto

### `src/config.py`

Devera suportar configuracao por ambiente para caminhos do servidor.

Responsabilidades:

- definir pasta raiz da automacao
- apontar `entrada`, `processando`, `processados`, `erro`, `saida`, `apoio` e `logs`
- localizar a tabela de produtos no servidor

### `src/main.py`

Pode continuar como ponto central do processamento de um PDF ou de uma pasta, mas deve ser chamado internamente pelo runner automatico.

### Novo runner automatico

Sugestao de novo modulo:

- `src/auto_processar_pasta.py`

Responsabilidades:

- localizar novos PDFs em `entrada`
- validar se o arquivo esta pronto para leitura
- mover para `processando`
- chamar o pipeline do projeto
- mover para `processados` ou `erro`
- renomear PDF com numero da OC
- registrar logs

### Logging

Sugestao:

- usar o modulo `logging` do Python
- salvar log em arquivo no servidor
- registrar:
  - inicio da execucao
  - quantidade de PDFs encontrados
  - PDFs processados com sucesso
  - PDFs com erro
  - numero das OCs geradas
  - caminho dos TXTs
  - motivo do erro quando houver

## Regras Operacionais

### Regra De Captura Segura Do Arquivo

Antes de processar um PDF:

- verificar se o arquivo nao esta em uso
- verificar se o tamanho do arquivo estabilizou
- mover o arquivo para `processando`

Isso reduz risco de processar arquivo ainda em copia.

### Regra De Renomeacao Do PDF Processado

PDFs processados com sucesso devem ser renomeados para:

- `OC_<numero_oc>.pdf`

Se houver conflito de nome:

- `OC_<numero_oc>_1.pdf`
- `OC_<numero_oc>_2.pdf`

### Regra De Erro

Se a automacao falhar:

- nao gerar TXT parcial
- salvar relatorio quando possivel
- mover o PDF para `erro`
- registrar o motivo no log

### Regra De Reprocessamento

Neste primeiro momento:

- um arquivo que entrou em `erro` nao deve ser reprocessado automaticamente
- o reprocessamento pode ser manual depois de ajuste no arquivo ou na tabela

## Estrategia De Agendamento

Recomendacao inicial:

- usar o Agendador de Tarefas do Windows
- executar a cada 5 minutos

Comando esperado:

- chamar o Python do servidor
- executar um runner automatico dedicado

Exemplo conceitual:

`python -m src.auto_processar_pasta`

## Tratamento De Multiplas OCs No Mesmo PDF

O parser atual ja suporta mais de uma ordem no mesmo arquivo.

Para a automacao no servidor, a regra precisa ser explicita:

- gerar um TXT por OC encontrada
- gerar um relatorio por OC encontrada
- manter um unico PDF original arquivado

Sugestao de comportamento:

- mover o PDF para `processados`
- renomear com o primeiro numero de OC
- registrar no log os demais numeros encontrados no mesmo arquivo

## Riscos E Cuidados

### Permissoes

O usuario ou servico do Windows que executa a tarefa precisa ter permissao de:

- leitura em `entrada` e `apoio`
- escrita em `processando`, `processados`, `erro`, `saida` e `logs`

### Caminhos UNC

O projeto precisa ser testado diretamente com o caminho UNC:

- `\\Servidor\arquivos rede\AUTOMAÇÃO OC`

Isso e importante porque caminhos de rede podem ter comportamento diferente de pastas locais.

### Nomes Com Espacos E Acentos

Como a pasta de rede possui espacos e acento, todos os caminhos devem ser tratados com `pathlib.Path` ou string bruta equivalente.

## Etapas De Implantacao

### Etapa 1

Adaptar configuracao do projeto para caminhos do servidor.

### Etapa 2

Criar o runner automatico de pasta com movimentacao de arquivos.

### Etapa 3

Adicionar logs e regras de arquivamento.

### Etapa 4

Testar manualmente no servidor com alguns PDFs.

### Etapa 5

Configurar o Agendador de Tarefas.

### Etapa 6

Homologar com operacao real.

## Resultado Esperado Da Nova Etapa

Ao final dessa fase, o processo deve funcionar assim:

- o usuario solta o PDF em `entrada`
- a automacao processa sozinha
- o TXT aparece em `saida\txt_gerados`
- o relatorio aparece em `saida\relatorios`
- o PDF vai para `processados`
- se houver erro, o PDF vai para `erro`
- a equipe acompanha tudo por pasta e log, sem precisar abrir terminal ou executar comandos manualmente

