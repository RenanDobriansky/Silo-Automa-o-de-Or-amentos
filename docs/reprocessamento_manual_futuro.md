# Planejamento De Reprocessamento Manual Futuro

## Objetivo

Desenhar uma solucao simples para reprocessar manualmente PDFs que foram parar na pasta `erro`, sem implementar essa funcionalidade agora.

O foco desta proposta e:

- permitir reprocessamento controlado
- evitar duplicidade de TXT
- manter rastreabilidade
- facilitar a operacao para a equipe

## Contexto Atual

Hoje, quando um PDF falha:

- ele vai para a pasta `erro`
- o motivo fica registrado no log
- o relatorio pode ser mantido quando possivel
- o arquivo nao e reprocessado automaticamente

Isso e bom para seguranca operacional, mas no futuro sera util oferecer um jeito simples de reprocessar depois que:

- a tabela de produtos for ajustada
- o PDF for corrigido
- uma regra de conversao for atualizada
- um erro tecnico pontual for resolvido

## Proposta De Solucao Simples

Sugestao principal:

- criar uma pasta dedicada para reenvio manual

Exemplo de nova pasta futura:

- `\\Servidor\arquivos rede\AUTOMAÇÃO OC\reprocessar`

Fluxo desejado:

1. A equipe analisa o PDF que foi para `erro`.
2. Se decidir tentar novamente, copia ou move o PDF para `reprocessar`.
3. O runner automatico passa a olhar tambem essa pasta.
4. O arquivo e processado com prioridade ou de forma separada.
5. O resultado vai para:
   - `processados`, se der certo
   - `erro`, se falhar novamente
6. O log registra claramente que se tratava de um reprocessamento.

## Como Selecionar Um PDF Com Erro

Forma mais simples:

- a equipe navega na pasta `erro`
- localiza o PDF desejado
- usa o log e o relatorio para entender a falha

Critrios de selecao mais comuns:

- erro de negocio corrigido na tabela de produtos
- PDF ajustado pelo fornecedor ou area responsavel
- falha tecnica pontual que nao se repetira

Arquivos de apoio para decisao:

- log em `logs`
- relatorio em `saida\relatorios`
- proprio PDF em `erro`

## Como Reenviar Para Processamento

### Opcao 1. Pasta `reprocessar`

Esta e a opcao mais recomendada.

Fluxo:

- o operador move o PDF de `erro` para `reprocessar`
- o processo automatico cuida do restante

Vantagens:

- separa claramente entrada normal de reprocessamento
- facilita logs e auditoria
- reduz risco de misturar arquivos novos com arquivos antigos

### Opcao 2. Reenviar para `entrada`

Fluxo:

- o operador move o PDF de `erro` de volta para `entrada`

Vantagens:

- implementacao mais simples

Desvantagens:

- perde a distincao entre arquivo novo e reprocessado
- dificulta auditoria
- aumenta risco de confusao operacional

Conclusao:

- preferir pasta `reprocessar`

## Como Evitar Duplicidade De TXT

Esse e o ponto mais importante do reprocessamento.

Antes de reprocessar um PDF, o processo futuro deve verificar:

- se ja existe TXT gerado para a mesma OC
- se ja existe PDF arquivado em `processados` para a mesma OC
- se aquele arquivo ja foi reprocessado anteriormente

### Regra recomendada

Se ja existir um TXT da mesma OC:

- nao sobrescrever automaticamente
- mover o novo resultado para uma pasta de revisao
- ou gerar com nome alternativo apenas se isso for desejado e seguro

Sugestao conservadora:

- bloquear o reprocessamento automatico quando a OC ja tiver TXT em producao
- exigir validacao manual para sobrescrever

### Alternativas futuras

1. Bloquear e registrar no log
2. Gerar TXT com sufixo:
   - `OC_<numero_oc>_reprocessado.txt`
3. Mover o TXT anterior para historico antes de gerar o novo

Recomendacao inicial:

- bloquear por padrao

## Como Registrar Isso Em Log

O reprocessamento precisa ficar muito claro nos logs.

O log futuro deve registrar:

- que o arquivo veio de reprocessamento
- data e hora do reprocessamento
- nome do PDF original
- motivo anterior da falha, quando possivel
- resultado do novo processamento
- OCs encontradas
- caminho do novo TXT, se gerado
- bloqueio por duplicidade, se ocorrer

Exemplos de mensagens desejadas:

- `Inicio de reprocessamento manual do arquivo X`
- `Arquivo identificado como reprocessamento`
- `OC 625684 reprocessada com sucesso`
- `Reprocessamento bloqueado: TXT da OC 625684 ja existe`
- `Reprocessamento falhou novamente por erro de negocio`

## Comportamento Recomendado Em Caso De Nova Falha

Se o arquivo falhar novamente:

- voltar para `erro`
- opcionalmente com marca de tentativa
- manter log do novo evento

Exemplo de nomes futuros:

- `arquivo_original.pdf`
- `arquivo_original_reprocessado_1.pdf`

Ou simplesmente:

- manter mesmo nome
- registrar numero da tentativa apenas no log

Recomendacao inicial:

- controlar tentativas via log
- evitar complicar o nome do arquivo cedo demais

## Modelo Operacional Futuro

### Fluxo sugerido

1. Operador abre a pasta `erro`.
2. Consulta log e relatorio.
3. Corrige a causa da falha.
4. Move o PDF para `reprocessar`.
5. O agendador executa o runner.
6. O runner detecta que e reprocessamento.
7. O runner valida duplicidade antes de gerar TXT.
8. O resultado e registrado em log.

## Melhor Caminho Para Implementacao Futura

Quando essa fase entrar no codigo, a implementacao mais simples seria:

### Nova pasta

- `reprocessar`

### Novo comportamento no runner

- varrer primeiro `reprocessar`
- depois `entrada`

### Nova marcacao no resultado

- `origem_processamento = entrada`
- `origem_processamento = reprocessar`

### Nova validacao

- verificar duplicidade de OC antes de gravar TXT

### Novo log

- deixar explicito quando o processamento veio de reenvio manual

## Recomendacao Final

A melhor solucao futura, mantendo simplicidade e seguranca, e:

- criar pasta `reprocessar`
- tratar reprocessamento como fluxo separado
- bloquear sobrescrita automatica de TXT ja existente
- registrar tudo em log

Assim a equipe ganha um mecanismo operacional simples, sem abrir risco de sobrescrever arquivos validos de forma silenciosa.

