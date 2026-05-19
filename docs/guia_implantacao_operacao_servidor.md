# Guia Resumido De Implantacao E Operacao No Servidor

## Objetivo

Este documento resume o passo a passo para colocar a automacao de OCs em funcionamento no servidor Windows e orienta como deve ser a operacao no dia a dia.

O objetivo da automacao e:

- ler PDFs de ordens de compra colocados em uma pasta de rede
- converter os dados para o layout NeoGrid
- gerar os arquivos TXT para importacao no ERP
- arquivar os PDFs processados
- registrar erros em pasta, relatorio e log

## Visao Geral Do Processo

O fluxo operacional esperado e:

1. O usuario coloca o PDF na pasta `entrada`.
2. O Agendador de Tarefas do Windows dispara o runner automatico.
3. O sistema verifica se o arquivo esta pronto para uso.
4. O sistema processa a OC.
5. Se der certo:
   - gera o TXT
   - gera o relatorio
   - move o PDF para `processados`
6. Se der erro:
   - nao deixa TXT parcial
   - move o PDF para `erro`
   - registra o motivo no log

## Estrutura De Pastas No Servidor

Pasta raiz:

- `\\Servidor\arquivos rede\AUTOMAÇÃO OC`

Pastas esperadas:

- `entrada`
- `processando`
- `processados`
- `erro`
- `saida\txt_gerados`
- `saida\relatorios`
- `apoio`
- `logs`

Finalidade:

- `entrada`: recebe os PDFs novos
- `processando`: guarda temporariamente o PDF durante a execucao
- `processados`: recebe PDFs processados com sucesso
- `erro`: recebe PDFs que falharam
- `saida\txt_gerados`: recebe os TXTs finais
- `saida\relatorios`: recebe os relatorios Excel
- `apoio`: guarda tabela de produtos e documentos de referencia
- `logs`: guarda log da execucao e trava de concorrencia

## Arquivos Necessarios No Servidor

Dentro de `apoio`, manter:

- `Tabela de produtos.xlsx`
- `NeoGrid PEDIDOS.pdf`

Tambem e necessario:

- codigo do projeto no servidor
- Python instalado
- dependencias instaladas com `pip install -r requirements.txt`

## Passo A Passo De Implantacao

### 1. Preparar o servidor

Validar:

- servidor Windows ativo
- acesso ao compartilhamento de rede
- usuario tecnico ou de servico definido para a tarefa
- permissao de leitura e escrita nas pastas da automacao

### 2. Copiar o projeto para o servidor

Opcoes comuns:

- clone do repositorio Git no servidor
- copia da pasta do projeto para um caminho fixo do servidor

Recomendacao:

- usar um caminho estavel, sem mudar o nome da pasta depois

### 3. Instalar Python e dependencias

Na pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configurar variaveis de ambiente

Variavel principal:

- `AUTOMACAO_OC_ROOT`

Valor esperado:

```text
\\Servidor\arquivos rede\AUTOMAÇÃO OC
```

Variaveis opcionais para checagem de arquivo ainda em copia:

- `AUTOMACAO_OC_READY_CHECK_INTERVAL_SECONDS`
- `AUTOMACAO_OC_READY_STABLE_CHECKS`

Exemplo:

```text
AUTOMACAO_OC_READY_CHECK_INTERVAL_SECONDS=1.5
AUTOMACAO_OC_READY_STABLE_CHECKS=2
```

### 5. Validar manualmente antes do agendamento

Executar na raiz do projeto:

```powershell
.venv\Scripts\python.exe -m src.auto_processar_pasta
```

Confirmar:

- criacao do log
- leitura da tabela de produtos
- leitura dos PDFs
- geracao do TXT
- geracao do relatorio
- movimentacao correta do PDF

### 6. Configurar o Agendador de Tarefas

Executar:

```powershell
.venv\Scripts\python.exe -m src.auto_processar_pasta
```

Configuracoes recomendadas:

- repetir a cada 5 minutos
- executar com usuario tecnico
- executar mesmo sem logon
- nao iniciar nova instancia se a tarefa ja estiver em execucao
- iniciar na pasta raiz do projeto

Se preferir, criar um `.bat` para encapsular a execucao.

Exemplo:

```bat
@echo off
set "AUTOMACAO_OC_ROOT=\\Servidor\arquivos rede\AUTOMAÇÃO OC"
set "AUTOMACAO_OC_READY_CHECK_INTERVAL_SECONDS=1.5"
set "AUTOMACAO_OC_READY_STABLE_CHECKS=2"
cd /d C:\caminho\do\projeto\silo-automacao
call .venv\Scripts\python.exe -m src.auto_processar_pasta
```

## Regras De Funcionamento Da Automacao

### Arquivo ainda em copia

O sistema nao processa o PDF imediatamente so porque ele apareceu em `entrada`.

Antes de processar, ele valida:

- se o arquivo pode ser aberto
- se o tamanho do arquivo ficou estavel
- se houve a quantidade minima de leituras estaveis configurada

Se o arquivo ainda nao estiver pronto:

- ele continua em `entrada`
- entra no log como ignorado
- sera tentado de novo na proxima execucao

### Concorrencia

O runner cria a trava:

- `.automacao_oc.lock`

Se ja existir uma execucao em andamento:

- a nova execucao nao processa nada
- o bloqueio fica registrado no log

### Tratamento de erros

Se houver falha:

- o PDF vai para `erro`
- o motivo entra no log
- o relatorio fica salvo quando possivel
- qualquer TXT parcial e removido

Tipos de erro:

- `tecnico`: falha de acesso a arquivo, tabela bloqueada, excecao inesperada
- `negocio`: produto nao encontrado, item para revisao, validacao bloqueando geracao

### Arquivamento do PDF processado

Quando o processamento termina com sucesso:

- o PDF vai para `processados`
- o nome fica:
  - `OC_<numero_oc>.pdf`

Se ja existir um PDF com esse nome:

- `OC_<numero_oc>_1.pdf`
- `OC_<numero_oc>_2.pdf`

Se o mesmo PDF tiver mais de uma OC:

- ele e arquivado uma vez
- o log registra todas as OCs encontradas

## Como Deve Ser A Operacao No Dia A Dia

### Para quem vai usar

O operador nao precisa abrir terminal nem rodar codigo.

Rotina esperada:

1. Colocar o PDF em `entrada`.
2. Aguardar a proxima execucao automatica.
3. Consultar o resultado nas pastas de saida.

### Quando a OC for processada com sucesso

O operador deve encontrar:

- TXT em `saida\txt_gerados`
- relatorio em `saida\relatorios`
- PDF arquivado em `processados`

### Quando houver erro

O operador deve verificar:

- PDF movido para `erro`
- log do dia em `logs`
- relatorio gerado, se aplicavel

Os casos mais comuns de erro devem ser:

- problema na tabela de produtos
- produto nao encontrado
- item que exige revisao manual
- PDF com problema de leitura

## Roteiro Rapido De Conferencia Operacional

Todo dia, ou quando necessario, conferir:

- se existem PDFs parados em `entrada`
- se existem PDFs acumulando em `erro`
- se os TXTs estao sendo gerados normalmente
- se o log do dia foi criado
- se a tabela de produtos em `apoio` esta atualizada

## O Que Fazer Em Caso De Problema

### PDF parou em `erro`

Verificar:

- log do dia em `logs`
- relatorio da OC em `saida\relatorios`
- se o problema foi tecnico ou de negocio

### Nada foi processado

Verificar:

- se o Agendador de Tarefas rodou
- se a trava `.automacao_oc.lock` ficou presa
- se o usuario da tarefa tem acesso ao caminho de rede
- se a tabela de produtos esta acessivel
- se o Python e o ambiente virtual ainda estao funcionando

### PDF ficou em `entrada`

Verificar:

- se ele ainda estava em copia
- se o tamanho do arquivo estabilizou
- se o proximo ciclo do agendador tentou novamente

## Checklist Final Antes De Entrar Em Producao

- [ ] pastas do servidor criadas
- [ ] tabela de produtos disponivel em `apoio`
- [ ] projeto copiado para o servidor
- [ ] Python instalado
- [ ] dependencias instaladas
- [ ] variavel `AUTOMACAO_OC_ROOT` configurada
- [ ] runner validado manualmente
- [ ] tarefa do Windows configurada
- [ ] log sendo criado
- [ ] PDF teste processado com sucesso
- [ ] PDF teste com erro tratado corretamente

## Documentos Complementares

Para mais detalhes, consultar:

- [desenho_tecnico_automacao_servidor.md](/C:/Users/renan/Desktop/Projetos%20BI/Silo%20Miotto%20e%20WOW/silo-automacao/docs/desenho_tecnico_automacao_servidor.md)
- [agendamento_windows_automacao_oc.md](/C:/Users/renan/Desktop/Projetos%20BI/Silo%20Miotto%20e%20WOW/silo-automacao/docs/agendamento_windows_automacao_oc.md)
- [checklist_homologacao_automacao_oc.md](/C:/Users/renan/Desktop/Projetos%20BI/Silo%20Miotto%20e%20WOW/silo-automacao/docs/checklist_homologacao_automacao_oc.md)
