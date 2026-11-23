# D8 — Gestão de inscrições e resultados (UC14)

Somente diretores ativos podem consultar e alterar a gestão de inscrições. O detalhe do campeonato oferece o acesso a `/campeonatos/:id/inscricoes`.

## API

- `GET campeonatos/{id}/inscricoes/`: campeonato, permissão temporal para resultados e categorias com total, vagas restantes e inscrições ativas. Cada inscrição contém atleta (id, nome, NUSP e curso), data, observações, colocação e destaque.
- `PATCH inscricoes/{id}/resultado/`: colocacao (inteiro de 1 a 32767 ou null), destaque (até 50 caracteres, vazio para limpar), confirmar_empate (opcional). Mantém campos omitidos.
- `PATCH campeonatos/{id}/resultados/`: extensão para salvar o formulário inteiro atomicamente: `{resultados: [{id, colocacao, destaque}], confirmar_empate: false}`.
- `POST campeonatos/{id}/inscricoes/`: inclusão manual `{atleta, categorias: [ids], observacoes}`. Atleta deve estar ativo. A diretoria pode incluir fora do prazo, mas respeita capacidade e não duplica inscrições. Campeonato cancelado é recusado. Reativa registro cancelado, com autoria do diretor.
- `POST inscricoes/{id}/remover/`: remoção lógica com `{motivo}` de 10 a 300 caracteres. Libera a vaga, audita e comunica o motivo por e-mail; repetição não envia nova mensagem.

Resultados são permitidos a partir da data inicial, inclusive em campeonatos finalizados, mas nunca em cancelados ou inscrições canceladas. A auditoria registra diretor, data/hora, valores anteriores e novos. A resposta 409 `confirmar_empate` exige confirmação explícita quando uma alteração produz colocações repetidas na mesma categoria. O conjunto final é validado antes de qualquer gravação, permitindo trocar posições em lote sem falso empate.

As extensões acima preservam a API de inscrições próprias da D6. Transações usam a mesma ordem de bloqueio campeonato/categorias; no SQLite, adquirem bloqueio de escrita antes das leituras. Os resultados ativos alimentam a consulta já existente do dashboard.

## Exportação

A tela exporta CSV com UTF-8/BOM, campos entre aspas e neutralização de fórmulas. Exporta apenas os dados já salvos. O botão “Imprimir / salvar PDF” abre o diálogo de impressão do navegador, com layout próprio agrupado por categoria; escolha “Salvar como PDF” para obter o arquivo. Nenhum serviço externo recebe a lista.

## Validação

Testes de permissões, agrupamento, vagas, inclusão fora do prazo, duplicidade, inativos, remoção motivada, reinscrição, datas/status, validação, empates, troca de posições, auditoria, rollback do lote e integração com dashboard. A exportação não requer dependências adicionais.

Não há migrações nem necessidade de recriar os dados.

Validação final: 386 testes aprovados e build de produção aprovado. No Chrome, a lista do JUSP 2026 e seus campos foram conferidos sem alterar resultados existentes. As gravações, empates e remoções foram verificados no banco isolado de testes; a impressão/PDF não foi conferida visualmente.
