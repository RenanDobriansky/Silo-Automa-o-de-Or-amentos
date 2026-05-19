# Agendamento No Windows Para A Automacao De OCs

## Objetivo

Configurar o Agendador de Tarefas do Windows para executar automaticamente a automacao de ordens de compra em PDF, sem necessidade de abrir terminal ou rodar comandos manualmente.

O processo deve:

- varrer a pasta de entrada no servidor
- processar os PDFs encontrados
- gerar os TXTs NeoGrid
- gerar os relatorios
- mover os PDFs para `processados` ou `erro`
- gravar logs em `logs`

## Contexto Da Implantacao

Servidor:

- Windows

Pasta raiz da automacao:

- `\\Servidor\arquivos rede\AUTOMAÇÃO OC`

Runner automatico do projeto:

- `src/auto_processar_pasta.py`

Comando principal previsto:

- `python -m src.auto_processar_pasta`

Frequencia recomendada:

- a cada 5 minutos

## Pre-Requisitos

Antes de configurar a tarefa, confirmar:

### 1. Python instalado no servidor

Validar se o Python esta disponivel no servidor.

Exemplo de verificacao:

```powershell
python --version
```

Ou, se necessario, usar o caminho completo do executavel:

```powershell
"C:\Python312\python.exe" --version
```

### 2. Projeto disponivel no servidor

O codigo-fonte do projeto deve estar acessivel no servidor.

Exemplos de localizacao valida:

- pasta local do servidor
- clone do repositorio em disco local
- pasta sincronizada pela TI

Importante:

- o projeto deve estar em um caminho estavel
- o runner deve conseguir importar `src.auto_processar_pasta`

### 3. Dependencias instaladas

As bibliotecas do projeto precisam estar instaladas no Python usado pela tarefa.

Exemplo:

```powershell
pip install -r requirements.txt
```

### 4. Estrutura de pastas criada

Confirmar que as pastas do servidor existem:

- `entrada`
- `processando`
- `processados`
- `erro`
- `saida\txt_gerados`
- `saida\relatorios`
- `apoio`
- `logs`

### 5. Arquivos de apoio disponiveis

Confirmar a existencia em `apoio` de:

- `Tabela de produtos.xlsx`
- `NeoGrid PEDIDOS.pdf`

## Usuario E Permissoes Necessarias

A tarefa do Windows deve rodar com um usuario que tenha permissao de:

- leitura em `\\Servidor\arquivos rede\AUTOMAÇÃO OC\entrada`
- leitura em `\\Servidor\arquivos rede\AUTOMAÇÃO OC\apoio`
- escrita em:
  - `processando`
  - `processados`
  - `erro`
  - `saida\txt_gerados`
  - `saida\relatorios`
  - `logs`

Recomendacao:

- usar um usuario de servico ou um usuario tecnico da empresa
- evitar usar um usuario pessoal

Tambem e importante:

- marcar a tarefa para executar mesmo sem logon interativo
- garantir que esse usuario tem acesso ao caminho UNC da rede

## Variaveis De Ambiente Recomendadas

O projeto suporta configuracao da raiz operacional e da checagem de arquivo pronto por variavel de ambiente:

- `AUTOMACAO_OC_ROOT`
- `AUTOMACAO_OC_READY_CHECK_INTERVAL_SECONDS`
- `AUTOMACAO_OC_READY_STABLE_CHECKS`

Valor esperado da raiz:

```text
\\Servidor\arquivos rede\AUTOMAÇÃO OC
```

Recomendacao:

- definir essas variaveis no ambiente do servidor
- ou defini-las no script de chamada da tarefa

Exemplo:

```text
AUTOMACAO_OC_READY_CHECK_INTERVAL_SECONDS=1.5
AUTOMACAO_OC_READY_STABLE_CHECKS=2
```

Se a rede for mais lenta ou os arquivos forem maiores, esses parametros podem ser ajustados.

## Comando Completo Recomendado

### Opcao 1: chamada direta do Python

Exemplo com caminho completo do Python:

```powershell
C:\Python312\python.exe -m src.auto_processar_pasta
```

### Opcao 2: usando ambiente virtual do projeto

Exemplo:

```powershell
C:\caminho\do\projeto\.venv\Scripts\python.exe -m src.auto_processar_pasta
```

Essa opcao costuma ser a mais segura, porque garante uso do ambiente certo.

## Directorio Inicial Da Tarefa

No Agendador de Tarefas, o campo de inicio em deve apontar para a raiz do projeto.

Exemplo:

```text
C:\caminho\do\projeto\silo-automacao
```

Isso e importante para:

- imports do modulo `src`
- carga correta do `.env`
- execucao consistente do runner

## Script Recomendado Para Chamada

Em muitos casos, vale a pena criar um `.bat` ou `.cmd` para encapsular a execucao.

Exemplo de script `executar_automacao_oc.bat`:

```bat
@echo off
set "AUTOMACAO_OC_ROOT=\\Servidor\arquivos rede\AUTOMAÇÃO OC"
set "AUTOMACAO_OC_READY_CHECK_INTERVAL_SECONDS=1.5"
set "AUTOMACAO_OC_READY_STABLE_CHECKS=2"
cd /d C:\caminho\do\projeto\silo-automacao
call .venv\Scripts\python.exe -m src.auto_processar_pasta
```

Vantagens:

- deixa a configuracao da tarefa mais simples
- centraliza variaveis de ambiente
- facilita manutencao futura

## Configuracao Recomendada No Agendador De Tarefas

### Aba Geral

Sugestao:

- Nome:
  - `Automacao OC NeoGrid`
- Descricao:
  - `Processa automaticamente PDFs de ordens de compra e gera TXT NeoGrid`
- Executar estando o usuario conectado ou nao
- Executar com privilegios mais altos
- Configurar para a versao do Windows do servidor

### Aba Disparadores

Criar um disparador:

- iniciar em um horario base
- repetir a cada `5 minutos`
- por duracao `indefinidamente`
- habilitado

### Aba Acoes

Se for usar script `.bat`:

- Programa/script:
  - caminho do `.bat`

Exemplo:

```text
C:\caminho\do\projeto\silo-automacao\executar_automacao_oc.bat
```

Se for chamar Python direto:

- Programa/script:
  - `C:\caminho\do\projeto\.venv\Scripts\python.exe`
- Adicionar argumentos:
  - `-m src.auto_processar_pasta`
- Iniciar em:
  - `C:\caminho\do\projeto\silo-automacao`

### Aba Condicoes

Recomendacoes:

- desmarcar restricoes de energia se o servidor nao depender disso
- nao exigir que o computador esteja ocioso

### Aba Configuracoes

Recomendacoes:

- permitir execucao sob demanda
- executar a tarefa o mais rapido possivel apos um agendamento perdido
- se a tarefa falhar, reiniciar a cada `5 minutos`
- tentar reiniciar ate `3 vezes`
- se a tarefa ja estiver em execucao:
  - `Nao iniciar uma nova instancia`

Essa ultima opcao e importante para evitar concorrencia entre duas execucoes simultaneas.

Observacao:

- o runner tambem cria uma trava `.automacao_oc.lock` em `logs`
- essa protecao complementa o Agendador de Tarefas e evita concorrencia mesmo se a tarefa for disparada manualmente por engano

## Cuidados Com Caminho De Rede

Como a automacao usa um caminho UNC com espacos e acento:

- `\\Servidor\arquivos rede\AUTOMAÇÃO OC`

alguns cuidados sao importantes:

### 1. Preferir `pathlib` e caminhos completos

O projeto ja foi adaptado para isso, mas a tarefa tambem deve respeitar caminhos completos.

### 2. Confirmar acesso do usuario da tarefa

O fato de funcionar manualmente com um usuario logado nao garante que funcionara via Agendador de Tarefas.

Validar especificamente:

- leitura da pasta `entrada`
- escrita em `logs`
- escrita em `saida`
- leitura da tabela em `apoio`

### 3. Evitar unidade mapeada

Nao usar letra de unidade tipo `Z:`.

Preferir sempre o caminho UNC completo:

- `\\Servidor\arquivos rede\AUTOMAÇÃO OC`

Isso reduz falhas quando a tarefa roda sem sessao interativa.

### 4. Considerar arquivos ainda em copia

O runner nao processa o PDF assim que ele aparece.

Ele valida:

- se o arquivo pode ser aberto
- se o tamanho ficou estavel em mais de uma leitura

Se o arquivo ainda estiver em copia:

- ele permanece em `entrada`
- entra no log como ignorado
- sera tentado novamente na proxima execucao

## Teste Inicial Recomendado

Antes de deixar automatico em producao:

1. Executar manualmente com o mesmo usuario da tarefa.
2. Confirmar a criacao do log.
3. Colocar um PDF de teste em `entrada`.
4. Confirmar:
   - movimento para `processando`
   - geracao do TXT
   - geracao do relatorio
   - movimento para `processados` ou `erro`
   - ausencia de TXT parcial em caso de falha
   - remocao do arquivo `.automacao_oc.lock` ao final
5. Executar a tarefa manualmente pelo Agendador de Tarefas.
6. Depois habilitar a repeticao automatica.

## Checklist Rapido De Validacao

- Python instalado no servidor
- dependencias instaladas
- projeto acessivel no servidor
- `.venv` funcional, se aplicavel
- pasta de rede acessivel pelo usuario da tarefa
- estrutura de pastas criada
- tabela de produtos presente em `apoio`
- log sendo gravado em `logs`
- tarefa configurada para nao abrir instancia concorrente
- trava `.automacao_oc.lock` criada e removida corretamente
- parametros de checagem de arquivo prontos para a realidade da rede
- execucao testada manualmente e pelo agendador

## Resultado Esperado

Depois da configuracao:

- o usuario coloca o PDF em `entrada`
- o Agendador de Tarefas dispara o runner a cada 5 minutos
- o PDF e processado automaticamente
- o TXT aparece em `saida\txt_gerados`
- o relatorio aparece em `saida\relatorios`
- o PDF vai para `processados` ou `erro`
- a equipe acompanha o que aconteceu pelos logs em `logs`
- execucoes concorrentes indevidas sao bloqueadas com seguranca
