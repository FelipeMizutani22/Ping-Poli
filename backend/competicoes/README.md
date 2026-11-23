# API de campeonatos (D4)

Base: `/api/v1/`. Leitura exige conta ativa; escrita exige diretor ativo.

| Método | Rota | Resultado |
|---|---|---|
| GET | `campeonatos/?status=` | Lista sem paginação, por início decrescente |
| GET | `campeonatos/{id}/` | Detalhe com categorias |
| POST | `campeonatos/` | Criação atômica com categorias; 201 |
| PATCH | `campeonatos/{id}/` | Edição parcial; 200 |
| POST | `campeonatos/{id}/cancelar/` | Cancelamento com `motivo` de 10 a 300 caracteres; 200 |

A saída segue o objeto Campeonato do contrato. `inscrito` considera apenas inscrições
ativas do usuário autenticado. `vagas_restantes` desconta apenas inscrições ativas;
vale `null` quando não há limite.

## Entrada e edição

- Criação exige pelo menos uma categoria: `categorias: [{"nome": "Livre", "vagas": null}]`.
- `anunciar` é opcional, padrão `true` na criação: publica um aviso de campeonato.
  A edição não republica o aviso.
- Mesmo nome e data inicial retornam 409 `possivel_duplicada`, com `campeonato_id`.
  Reenviar com `confirmar_duplicada: true` permite confirmar a duplicidade.
- Omitir `categorias` no PATCH preserva todas. Se enviada, a lista representa o conjunto
  completo desejado: informe `id` e `nome` para preservar cada categoria existente;
  itens sem `id` criam categorias. `vagas` ausente ou `null` significa sem limite.
- A remoção de categoria com qualquer inscrição (inclusive cancelada) ou partida é
  bloqueada com 409 `categoria_vinculada`, para preservar histórico. Essa proteção é
  mais restritiva que o UC12-h, que menciona apenas inscrições ativas.
- Vagas não podem ficar abaixo do número de inscrições ativas. Nomes e ids não podem
  se repetir. Categoria de outro campeonato é rejeitada.
- Datas são validadas também no PATCH parcial. O encerramento pode ocorrer no próprio
  dia de início, considerando Brasília, pois o campeonato não possui horário de início.
- `PATCH {"status": "inscricoes_abertas"}` antecipa a abertura de um planejado;
  `PATCH {"status": "inscricoes_encerradas"}` antecipa o encerramento de um aberto.
  A data correspondente é ajustada para agora e revalidada. Não há regressão de status.
- Cancelamento mantém categorias e inscrições e registra motivo/autor na auditoria.
  Repetir o cancelamento não repete o envio. Finalizados não podem ser cancelados.
- Alterações de datas/local e cancelamento enviam e-mail aos inscritos ativos, uma vez
  por atleta, após confirmar a transação. No ambiente local, os e-mails saem no console.

## Status automático

`competicoes.servicos.sincronizar_status(agora=None)` retorna o número de campeonatos
alterados e é chamado após autenticação/permissão no início das views. Pode ser usado
pelo futuro comando `executar_rotinas` (A11).

Abre no instante de abertura, encerra no instante do prazo e finaliza no dia seguinte
ao término em Brasília. Recupera etapas atrasadas, preserva cancelados/finalizados e
não duplica notificações em chamadas repetidas. Abertura notifica atletas ativos;
finalização notifica diretores ativos. Não anuncia abertura cujo prazo já expirou.
Status e notificações no banco são atômicos: em caso de falha, a transação é desfeita
para permitir nova tentativa consistente.

## Escopo

D5 implementará as telas de gestão; D6, as operações de inscrição; D8, resultados.
DELETE/PUT não são expostos, seguindo as rotas do contrato. A rotina agendada A11
não faz parte desta tarefa. Não há alteração de modelos ou migrações.

Teste: `python manage.py test competicoes` dentro de `backend`.


## D6 — inscrições próprias

- `POST /api/v1/inscricoes/`: categorias (IDs únicos do mesmo campeonato), observacoes (até 300 caracteres), ciencia_regulamento=true. Retorna 201 com a lista de inscrições.
- `GET /api/v1/inscricoes/minhas/`: histórico exclusivamente do usuário autenticado, incluindo canceladas.
- `DELETE /api/v1/inscricoes/{id}/`: cancelamento lógico da própria inscrição, durante a janela de inscrições; 204. Diretores seguem as mesmas regras para inscrições próprias.
- Erros 409: inscricoes_fechadas, ja_inscrito, sem_vagas (categorias_esgotadas contém IDs numéricos). Entradas inválidas: 400; inscrição alheia: 404.
- Uma transação valida todas as categorias antes de reservar vagas. Bloqueio do campeonato seguido das categorias em ordem de ID. SQLite adquire bloqueio de escrita antes das leituras, pois ignora select_for_update; outros bancos usam os bloqueios de linha.
- Reinscrição reativa a mesma linha. Cancelamento libera a vaga e mantém o histórico. E-mails são disparados após o commit; no ambiente local usam o backend configurado de console.
- Interface: inscrição no detalhe do campeonato e `/inscricoes` para histórico/cancelamento. Trocas utilizam cancelamento e nova inscrição separados, sujeitos à disponibilidade; não há endpoint de troca atômica no contrato D6.
- Nenhuma migração ou recriação de dados é necessária.
