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
- erros ficam visiveis em pasta, relatorio e log, sem depender de aviso por e-mail neste primeiro momento

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
- arquivos ainda em copia podem aparecer aqui temporariamente e devem ser ignorados ate ficarem prontos

### `processando`

Recebe temporariamente os PDFs que ja foram capturados pelo processo automatico.

Regra:

- um arquivo deve sair de `entrada` e ir para `processando` antes do processamento real
- isso evita duplicidade e reduz risco de pegar arquivo ainda em copia

### `processados`

Recebe os PDFs processados com sucesso.

Regra:

- o arquivo deve ser renomeado com o numero da OC
- padrao:
  - `OC_<numero_oc>.pdf`
- em caso de conflito de nome:
  - `OC_<numero_oc>_1.pdf`
  - `OC_<numero_oc>_2.pdf`

Observacao:

- como os PDFs devem ser mantidos, essa pasta vira o historico operacional
- se um PDF tiver mais de uma OC, ele sera arquivado uma vez com o primeiro numero de OC e as demais ficarao registradas no log

### `erro`

Recebe PDFs que nao puderam ser processados.

Casos esperados:

- produto nao encontrado
- item com revisao manual
- falha de leitura do PDF
- erro de validacao de totais
- problema de acesso a arquivo
- falha de leitura da tabela de produtos

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

### `apoio`

Recebe os arquivos necessarios para a automacao funcionar.

Arquivos previstos:

- `Tabela de produtos.xlsx`
- `NeoGrid PEDIDOS.pdf`

### `logs`

Recebe os logs tecnicos da execucao automatica.

Arquivos previstos:

- `automacao_oc_YYYY-MM-DD.log`
- `.automacao_oc.lock`

## Fluxo Tecnico Da Automacao

### Fluxo Principal

1. O Agendador de Tarefas do Windows dispara a automacao.
2. O runner tenta adquirir uma trava de execucao para impedir concorrencia.
3. A automacao varre a pasta `entrada`.
4. O sistema tenta carregar e preparar a tabela de produtos do servidor.
5. Cada PDF encontrado passa pela validacao de arquivo pronto.
6. Arquivos ainda em copia sao ignorados naquela rodada e permanecem em `entrada`.
7. Cada PDF elegivel e movido para `processando`.
8. O sistema extrai o texto do PDF.
9. O sistema parseia uma ou mais ordens de compra.
10. O sistema gera o relatorio de conversao.
11. O sistema valida produtos, totais e estrutura de saida.
12. Se estiver tudo correto, gera o TXT NeoGrid.
13. O PDF e movido para `processados` com nome padrao por OC.
14. Se houver erro, o PDF vai para `erro`.
15. O log da execucao e gravado em `logs`.
16. Ao final, a trava de execucao e liberada.

## Componentes De Software

### `src/config.py`

Responsabilidades:

- definir pasta raiz da automacao
- apontar `entrada`, `processando`, `processados`, `erro`, `saida`, `apoio` e `logs`
- localizar a tabela de produtos no servidor
- expor o caminho da trava de execucao
- expor os parametros da checagem de arquivo pronto

Configuracoes importantes:

- `AUTOMACAO_OC_ROOT`
- `AUTOMACAO_OC_READY_CHECK_INTERVAL_SECONDS`
- `AUTOMACAO_OC_READY_STABLE_CHECKS`

### `src/main.py`

Ponto central do processamento de um PDF.

Responsabilidades:

- preparar a tabela de produtos
- processar um PDF individual
- retornar status, relatorio, caminho do TXT e erros
- manter o caminho do TXT informado mesmo em falha final, permitindo limpeza segura de saida parcial pelo runner

### `src/auto_processar_pasta.py`

Runner automatico do servidor.

Responsabilidades:

- localizar novos PDFs em `entrada`
- validar se o arquivo esta pronto para leitura
- mover para `processando`
- chamar o pipeline do projeto
- mover para `processados` ou `erro`
- renomear PDF com numero da OC
- remover TXT parcial em caso de falha
- diferenciar erro tecnico de erro de negocio
- impedir duas execucoes simultaneas com arquivo `.lock`
- registrar logs

### Logging

Sugestao adotada:

- usar o modulo `logging` do Python
- salvar log em arquivo no servidor
- registrar:
  - inicio da execucao
  - fim da execucao
  - quantidade de PDFs encontrados
  - arquivos ignorados por ainda estarem em copia
  - PDFs processados com sucesso
  - PDFs com erro
  - numero das OCs geradas
  - caminho dos TXTs
  - bloqueio por concorrencia
  - erro de inicializacao da tabela de produtos
  - motivo do erro quando houver

## Regras Operacionais

### Regra De Captura Segura Do Arquivo

Antes de processar um PDF:

- verificar se o arquivo pode ser aberto
- verificar se o tamanho do arquivo estabilizou em mais de uma leitura
- usar intervalo configuravel entre leituras
- mover o arquivo para `processando` somente quando estiver pronto

Configuracoes atuais:

- `AUTOMACAO_OC_READY_CHECK_INTERVAL_SECONDS`
- `AUTOMACAO_OC_READY_STABLE_CHECKS`

### Regra De Concorrencia

Antes de iniciar o lote:

- o runner cria uma trava `.automacao_oc.lock`
- se a trava ja existir, a execucao deve registrar o bloqueio no log e encerrar com seguranca
- a trava deve ser removida ao final da execucao, inclusive quando houver erro controlado

### Regra De Renomeacao Do PDF Processado

PDFs processados com sucesso devem ser renomeados para:

- `OC_<numero_oc>.pdf`

Se houver conflito de nome:

- `OC_<numero_oc>_1.pdf`
- `OC_<numero_oc>_2.pdf`

### Regra De Erro

Se a automacao falhar:

- nao gerar TXT parcial
- remover qualquer TXT parcial que tenha sido criado antes da falha final
- salvar relatorio quando possivel
- mover o PDF para `erro`
- registrar o motivo no log

Classificacao esperada:

- erro tecnico:
  - problema de acesso a arquivo
  - falha ao ler a tabela de produtos
  - excecao inesperada no processamento
- erro de negocio:
  - produto nao encontrado
  - item para revisao manual
  - validacao bloqueando geracao do TXT

### Regra De Reprocessamento

Neste primeiro momento:

- um arquivo que entrou em `erro` nao deve ser reprocessado automaticamente
- o reprocessamento pode ser manual depois de ajuste no arquivo ou na tabela

## Tratamento De Multiplas OCs No Mesmo PDF

O parser atual ja suporta mais de uma ordem no mesmo arquivo.

Para a automacao no servidor:

- gerar um TXT por OC encontrada
- gerar um relatorio por OC encontrada
- manter um unico PDF original arquivado
- renomear o PDF com o primeiro numero de OC
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

### Tabela De Produtos No Servidor

A tabela de produtos e um ponto critico de inicializacao.

Cuidados:

- o arquivo nao deve ficar bloqueado por uso manual no Excel no momento da execucao
- erros de acesso devem aparecer como erro tecnico no log
- se a tabela nao puder ser carregada, o lote deve encerrar sem processar PDFs daquela rodada

## Estrategia De Agendamento

Recomendacao inicial:

- usar o Agendador de Tarefas do Windows
- executar a cada 5 minutos
- configurar para nao iniciar nova instancia

Comando esperado:

`python -m src.auto_processar_pasta`

## Etapas De Implantacao

### Etapa 1

Adaptar configuracao do projeto para caminhos do servidor.

### Etapa 2

Criar o runner automatico de pasta com movimentacao de arquivos.

### Etapa 3

Adicionar logs, trava de concorrencia e regras de arquivamento.

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
- execucoes simultaneas indevidas sao bloqueadas
- arquivos ainda em copia sao ignorados e tentados novamente na proxima rodada
