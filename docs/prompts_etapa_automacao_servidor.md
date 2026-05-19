# Prompts Para A Etapa De Automacao No Servidor

Este arquivo reune prompts prontos para usar durante a proxima fase do projeto.

## 1. Adaptar Configuracao Para O Servidor

```text
Adapte o projeto para rodar no servidor Windows usando a pasta de rede:
\\Servidor\arquivos rede\AUTOMAÇÃO OC

Quero que os caminhos do projeto sejam centralizados no config.py, incluindo:
- entrada
- processando
- processados
- erro
- saida/txt_gerados
- saida/relatorios
- apoio
- logs

A tabela de produtos deve ser lida do servidor.
Use pathlib e deixe o codigo preparado para caminhos UNC com espacos e acentos.
Atualize os testes necessarios.
```

## 2. Criar Runner Automatico Da Pasta

```text
Crie um novo modulo src/auto_processar_pasta.py para executar a automacao em lote no servidor.

Regras:
- ler PDFs da pasta de entrada
- mover cada arquivo para processando antes de iniciar
- processar o PDF usando o pipeline atual
- se der certo, mover o PDF para processados
- se der erro, mover para erro
- manter relatorios e TXT nas pastas de saida ja definidas

Quero funcoes pequenas, docstrings claras e testes basicos para o fluxo do runner.
```

## 3. Renomear PDFs Processados Pelo Numero Da OC

```text
Implemente a regra de arquivamento dos PDFs processados.

Quando um PDF for processado com sucesso, ele deve ser movido para a pasta processados e renomeado com o numero da OC:
- OC_<numero_oc>.pdf

Se houver conflito de nome, adicionar sufixo numerico:
- OC_<numero_oc>_1.pdf
- OC_<numero_oc>_2.pdf

Se um unico PDF tiver mais de uma OC, manter o PDF arquivado uma vez e registrar no log todas as OCs encontradas.
Atualize os testes.
```

## 4. Criar Log De Execucao

```text
Adicione logging ao processo automatico da automacao de OCs.

Quero gravar logs em:
\\Servidor\arquivos rede\AUTOMAÇÃO OC\logs

O log deve registrar:
- inicio e fim da execucao
- quantidade de PDFs encontrados
- nome de cada PDF processado
- numeros de OCs encontradas
- sucesso ou erro
- caminho dos TXTs gerados
- motivo detalhado do erro quando houver

Use o modulo logging do Python e deixe o formato do log facil de ler pela equipe.
```

## 5. Evitar Arquivo Ainda Em Copia

```text
Implemente uma validacao para evitar processar PDF ainda em copia na pasta de entrada.

Sugestao de regra:
- verificar se o tamanho do arquivo estabilizou antes do processamento
- tentar abrir o arquivo
- so depois mover para processando

Se o arquivo nao estiver pronto, ele deve ser ignorado naquela execucao e tentado novamente na proxima.
Adicione testes ou simulacoes para esse comportamento.
```

## 6. Criar Modo Seguro Para Erros

```text
Implemente tratamento operacional de erro no runner automatico.

Se qualquer PDF falhar:
- nao gerar TXT parcial
- mover o PDF para a pasta erro
- salvar relatorio se possivel
- registrar o erro no log

Quero que o fluxo diferencie erro tecnico de erro de negocio quando possivel.
```

## 7. Preparar Agendamento No Windows

```text
Crie a documentacao tecnica para configurar o Agendador de Tarefas do Windows para essa automacao.

Considere:
- servidor Windows
- execucao automatica a cada 5 minutos
- chamada do Python do servidor
- execucao do runner automatico do projeto

Inclua:
- pre-requisitos
- usuario/permissoes necessarias
- comando completo
- configuracoes recomendadas da tarefa
- cuidados com caminho de rede
```

## 8. Checklist De Homologacao

```text
Monte um checklist de homologacao para a automacao de OCs no servidor.

Quero validar:
- leitura dos PDFs da pasta de entrada
- leitura da tabela de produtos no servidor
- movimentacao correta entre entrada, processando, processados e erro
- geracao dos TXTs
- geracao dos relatorios
- renomeacao do PDF pelo numero da OC
- gravacao dos logs
- comportamento em caso de erro

Organize em formato pratico para a equipe testar no servidor.
```

## 9. Reprocessamento Manual Futuro

```text
Planeje uma solucao simples para reprocessamento manual de PDFs que foram para a pasta erro.

Nao quero implementar agora, apenas desenhar a ideia.
Considere:
- como selecionar um PDF com erro
- como reenviar para entrada ou reprocessar
- como evitar duplicidade de TXT
- como registrar isso em log
```

## 10. Revisao Tecnica Antes Da Implantacao

```text
Revise o projeto com foco na implantacao em servidor Windows com pasta UNC.

Quero que voce procure:
- pontos do codigo que ainda usam caminho local fixo
- riscos com espacos e acentos no caminho
- pontos sem tratamento de erro suficiente
- necessidades de log
- riscos de concorrencia
- possiveis problemas ao rodar automaticamente pelo Agendador de Tarefas

Liste os achados mais importantes e proponha os ajustes necessarios.
```

