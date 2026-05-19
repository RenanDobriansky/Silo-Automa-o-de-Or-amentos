# Checklist De Homologacao Da Automacao De OCs

## Objetivo

Validar no servidor se a automacao de ordens de compra esta funcionando corretamente do ponto de vista operacional, tecnico e funcional.

Este checklist foi pensado para a equipe testar a automacao diretamente no ambiente do servidor Windows.

## Dados Do Ambiente

Preencher antes de iniciar a homologacao:

- Servidor:
- Usuario que executa a tarefa:
- Data do teste:
- Responsavel pelo teste:
- Pasta raiz:
  - `\\Servidor\arquivos rede\AUTOMAÇÃO OC`

## Estrutura Esperada

Confirmar se as pastas abaixo existem:

- `entrada`
- `processando`
- `processados`
- `erro`
- `saida\txt_gerados`
- `saida\relatorios`
- `apoio`
- `logs`

Status:

- [ ] ok
- [ ] pendente ajuste

Observacoes:

---

## Pre-Requisitos

### 1. Python e ambiente

Validar:

- [ ] Python instalado no servidor
- [ ] dependencias do projeto instaladas
- [ ] projeto acessivel no servidor
- [ ] tarefa do Windows criada ou runner executavel manualmente

Observacoes:

---

### 2. Arquivos de apoio

Validar:

- [ ] `Tabela de produtos.xlsx` presente em `apoio`
- [ ] `NeoGrid PEDIDOS.pdf` presente em `apoio`
- [ ] tabela de produtos abre normalmente
- [ ] usuario da tarefa tem permissao de leitura em `apoio`
- [ ] a tabela nao esta bloqueada por outro usuario no momento do teste

Observacoes:

---

## Cenarios De Homologacao

## Cenario 1. Leitura Dos PDFs Da Pasta De Entrada

Objetivo:

Validar se o processo identifica corretamente novos PDFs colocados em `entrada`.

Passos:

1. Colocar um PDF valido em `entrada`.
2. Executar a automacao manualmente ou aguardar o agendamento.
3. Confirmar que o arquivo foi reconhecido pelo processo.

Validar:

- [ ] o PDF foi encontrado pela automacao
- [ ] o nome do arquivo apareceu no log
- [ ] a automacao nao tentou processar arquivos que nao sao PDF

Status:

- [ ] aprovado
- [ ] reprovado

Observacoes:

---

## Cenario 2. Leitura Da Tabela De Produtos No Servidor

Objetivo:

Validar se a automacao esta lendo a tabela de produtos diretamente da pasta `apoio`.

Passos:

1. Confirmar que a tabela esta no caminho esperado.
2. Rodar a automacao com um PDF valido.
3. Verificar se o processamento avanca normalmente sem erro de acesso a planilha.

Validar:

- [ ] a tabela foi localizada sem ajuste manual
- [ ] nao houve erro de permissao ou caminho
- [ ] o De/Para foi executado normalmente

Status:

- [ ] aprovado
- [ ] reprovado

Observacoes:

---

## Cenario 3. Movimentacao Entre Pastas Em Caso De Sucesso

Objetivo:

Validar o fluxo correto de sucesso.

Passos:

1. Colocar um PDF valido em `entrada`.
2. Rodar a automacao.
3. Acompanhar a movimentacao do arquivo.

Validar:

- [ ] o PDF saiu de `entrada`
- [ ] o PDF passou por `processando`
- [ ] ao final o PDF foi movido para `processados`
- [ ] o PDF nao ficou parado em `processando`

Status:

- [ ] aprovado
- [ ] reprovado

Observacoes:

---

## Cenario 4. Movimentacao Para Pasta De Erro

Objetivo:

Validar o fluxo quando houver falha no processamento.

Sugestao de teste:

- usar um PDF com item nao encontrado
- ou provocar erro de negocio conhecido

Passos:

1. Colocar o PDF de teste em `entrada`.
2. Rodar a automacao.
3. Verificar destino final do arquivo.

Validar:

- [ ] o PDF saiu de `entrada`
- [ ] o PDF passou por `processando`
- [ ] o PDF foi movido para `erro`
- [ ] o motivo do erro apareceu no log

Status:

- [ ] aprovado
- [ ] reprovado

Observacoes:

---

## Cenario 5. Geracao Dos TXTs

Objetivo:

Validar se o TXT NeoGrid esta sendo gerado corretamente.

Passos:

1. Processar um PDF valido.
2. Verificar a pasta `saida\txt_gerados`.

Validar:

- [ ] o TXT foi criado
- [ ] o nome segue o padrao `OC_<numero_oc>.txt`
- [ ] o TXT possui registros `019`, `024`, `040` e `090`
- [ ] nao foi gerado TXT parcial em caso de erro
- [ ] se houve falha apos tentativa de geracao, o TXT parcial foi removido

Status:

- [ ] aprovado
- [ ] reprovado

Observacoes:

---

## Cenario 6. Geracao Dos Relatorios

Objetivo:

Validar a geracao dos relatorios Excel da conversao.

Passos:

1. Processar um PDF valido.
2. Verificar a pasta `saida\relatorios`.

Validar:

- [ ] o relatorio foi criado
- [ ] o nome segue o padrao `relatorio_conversao_OC_<numero_oc>.xlsx`
- [ ] o relatorio contem itens, status, quantidades e valores
- [ ] em caso de falha, o relatorio foi mantido quando possivel

Status:

- [ ] aprovado
- [ ] reprovado

Observacoes:

---

## Cenario 7. Renomeacao Do PDF Pelo Numero Da OC

Objetivo:

Validar a regra de arquivamento do PDF processado.

Passos:

1. Processar um PDF com sucesso.
2. Abrir a pasta `processados`.

Validar:

- [ ] o PDF foi salvo como `OC_<numero_oc>.pdf`
- [ ] se ja existia arquivo com mesmo nome, foi criado sufixo `_1`, `_2` etc
- [ ] se o PDF continha mais de uma OC, ele foi arquivado apenas uma vez
- [ ] as OCs encontradas apareceram no log

Status:

- [ ] aprovado
- [ ] reprovado

Observacoes:

---

## Cenario 8. Gravacao Dos Logs

Objetivo:

Validar a rastreabilidade da automacao.

Passos:

1. Rodar a automacao.
2. Abrir a pasta `logs`.
3. Verificar o arquivo do dia.

Validar:

- [ ] o log foi criado
- [ ] o log registra inicio da execucao
- [ ] o log registra fim da execucao
- [ ] o log registra quantidade de PDFs encontrados
- [ ] o log registra nome do arquivo processado
- [ ] o log registra OCs encontradas
- [ ] o log registra caminho do TXT gerado
- [ ] o log registra erros com detalhe
- [ ] o log registra arquivos ignorados por ainda estarem em copia
- [ ] o log registra bloqueio por concorrencia quando aplicavel
- [ ] o log registra erro de inicializacao quando a tabela nao puder ser carregada

Status:

- [ ] aprovado
- [ ] reprovado

Observacoes:

---

## Cenario 9. Comportamento Em Caso De Arquivo Ainda Em Copia

Objetivo:

Validar se a automacao ignora arquivos que ainda nao terminaram de ser copiados.

Passos sugeridos:

1. Iniciar a copia de um PDF grande ou simular um arquivo em uso.
2. Rodar a automacao durante a copia.
3. Verificar o comportamento.

Validar:

- [ ] o arquivo nao foi movido para `processando`
- [ ] o arquivo permaneceu em `entrada`
- [ ] o arquivo foi ignorado naquela execucao
- [ ] o log registrou a ocorrencia
- [ ] o arquivo foi processado normalmente em uma execucao posterior apos terminar a copia

Status:

- [ ] aprovado
- [ ] reprovado

Observacoes:

---

## Cenario 10. Diferenciacao Entre Erro Tecnico E Erro De Negocio

Objetivo:

Validar a classificacao do tipo de falha.

Exemplos:

- erro tecnico:
  - falha de leitura do arquivo
  - excecao no processamento
  - erro de acesso a tabela de produtos
- erro de negocio:
  - produto nao encontrado
  - revisao manual
  - validacao bloqueando geracao

Validar:

- [ ] o log registra `tipo_erro = tecnico` quando houver falha tecnica
- [ ] o log registra `tipo_erro = negocio` quando houver falha de negocio
- [ ] o resumo da execucao diferencia erro tecnico e erro de negocio

Status:

- [ ] aprovado
- [ ] reprovado

Observacoes:

---

## Cenario 11. Concorrencia Entre Execucoes

Objetivo:

Validar se uma segunda execucao e bloqueada quando ja existe uma automacao em andamento.

Passos:

1. Iniciar uma execucao do runner.
2. Antes da primeira terminar, disparar uma segunda execucao manualmente.
3. Verificar o comportamento.

Validar:

- [ ] a segunda execucao nao processou arquivos
- [ ] o log registrou o bloqueio por concorrencia
- [ ] o resumo da execucao marcou `bloqueado_concorrencia`
- [ ] o arquivo `.automacao_oc.lock` foi removido ao final da execucao valida

Status:

- [ ] aprovado
- [ ] reprovado

Observacoes:

---

## Cenario 12. Repeticao Da Tarefa Sem Duplicidade

Objetivo:

Validar se a tarefa pode rodar novamente sem reprocessar o que ja saiu de `entrada`.

Passos:

1. Rodar a automacao com um PDF valido.
2. Confirmar que o arquivo saiu de `entrada`.
3. Rodar a automacao novamente sem adicionar novos PDFs.

Validar:

- [ ] nenhum PDF antigo foi reprocessado
- [ ] nenhum novo TXT duplicado foi gerado
- [ ] o log da segunda execucao mostra zero ou apenas novos PDFs encontrados

Status:

- [ ] aprovado
- [ ] reprovado

Observacoes:

---

## Cenario 13. Falha De Inicializacao Da Tabela De Produtos

Objetivo:

Validar o comportamento quando a tabela de produtos nao puder ser carregada.

Sugestao de teste:

- bloquear o arquivo no Excel
- ou simular indisponibilidade temporaria da pasta `apoio`

Validar:

- [ ] a execucao nao processou PDFs daquela rodada
- [ ] o log registrou erro tecnico de inicializacao
- [ ] o resumo marcou `erro_inicializacao`
- [ ] os PDFs permaneceram em `entrada`

Status:

- [ ] aprovado
- [ ] reprovado

Observacoes:

---

## Checklist Final De Aprovacao

Marcar ao final da homologacao:

- [ ] leitura dos PDFs validada
- [ ] leitura da tabela de produtos validada
- [ ] movimentacao entre pastas validada
- [ ] geracao dos TXTs validada
- [ ] geracao dos relatorios validada
- [ ] renomeacao do PDF validada
- [ ] logs validados
- [ ] comportamento de erro validado
- [ ] comportamento com arquivo em copia validado
- [ ] concorrencia validada
- [ ] inicializacao da tabela validada
- [ ] agendamento pronto para producao

## Resultado Final

- [ ] homologado para producao
- [ ] homologado com ressalvas
- [ ] nao homologado

## Ressalvas Ou Ajustes Necessarios

Descrever aqui:

---

## Aprovacao

- Responsavel funcional:
- Responsavel tecnico:
- Data:
