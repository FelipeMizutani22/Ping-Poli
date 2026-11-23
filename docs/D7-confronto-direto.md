# D7 — Confronto direto (UC19)

`GET /api/v1/desempenho/confronto/?a=<id>&b=<id>&periodo=tudo`

O atleta comum sempre ocupa o lado A; o parâmetro `a` é ignorado para esse perfil. Diretores podem selecionar ambos os atletas. A consulta aceita adversários Poli inativos, mas requer uma conta ativa autenticada. B é obrigatório e deve ser diferente de A.

Todo o histórico é o padrão. Períodos personalizados incluem as duas datas e rejeitam datas finais futuras ou anteriores à inicial. Os períodos 3m, 6m e 12m e o filtro competicao também são aceitos pela API.

O retrospecto, os destaques, a lista e o acumulado usam somente partidas confirmadas entre o par. Os indicadores gerais consideram todas as partidas confirmadas de cada atleta no período, inclusive adversários externos. Pendências são contadas à parte; partidas contestadas, removidas e futuras não entram nos cálculos.

A lista mantém a ordem por data e ID, com placar na perspectiva de A. Para atender ao placar set a set do UC19, cada item de `partidas` acrescenta o campo `sets` (numero, pontos_atleta, pontos_adversario), também na perspectiva de A. Os demais campos do contrato são preservados.

A tela `/confronto` está acessível pelo dashboard e pelos adversários mais enfrentados. Inclui seleção por nome/NUSP, período personalizado, retrospecto, destaques, gráfico acumulado, lista cronológica, indicadores gerais, estados vazio/carregamento/erro e nova tentativa. Resultados anteriores são mantidos e identificados em caso de falha.

Validação: testes de API para permissões, orientações dos placares, histórico completo, indicadores gerais, datas, entradas inválidas, inativos, consultas sem crescimento por partida e pendências antigas. Conferência local no Chrome: diretora selecionou Ana Lima × Bruno Kato; 5 × 2 vitórias, sete partidas e uma pendência, com indicadores gerais de 35 e 17 jogos.

Não há migrações nem alterações nos dados existentes.
