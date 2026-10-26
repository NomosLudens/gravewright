# Gravewright Tactics — Gate 4 QA

**Status: PASS — G4 is approved.** G4.2 completed authenticated, two-way PixiJS/Godot movement with persisted reload readback, then uploaded and rendered a QA-only raster with aligned grid and token overlay. Evidence and final regression results are recorded in `docs/evidence/gravewright-g4.2-2026-10-15/`.

## Preserved checkout

- Checkout: `/home/tonyus-dev/Portifolio/gravewright`
- Branch: `feat/tactics-godot-transport-20261014`
- Starting HEAD: `3820dd5dfccdac4786ec32a162ba4d0a593e2fa5`
- Remote branch was still at `30617b4ceb5d7aabf1d3465973157632045710e4` when checked; local branch had the two G0/G2/G3 commits ahead of it.
- Existing Godot source WIP and `.godot/` export/cache were retained. No operational campaign data, merge, or deployment was used.
- QA SQLite and media were isolated under `/tmp/gravewright-tactics-qa-20261015/`; `data/gravewright.sqlite3` was not opened for QA or modified. QA campaign and account identifiers, passwords, and cookies are omitted.

## Implementation and automated evidence

- Added scene-owned `TacticalTerrain`, `TerrainCell`, and `TerrainConnection` models with schema and terrain revisions. Initialization creates persisted cells; the only terrain values are KALLÍSTIS `NORMAL`, `DIFICIL`, `SEVERO`, and `INTRANSPONIVEL`.
- GM edits use the existing idempotent `maps.command` path, validate expected versions, persist, and trigger the existing authorized layer refresh. The public projection includes cells, movement costs, elevation, and connections; `canEdit` is role-scoped.
- Terrain-backed movement validates every orthogonal step and occupied footprint, passability, wall crossing, destination terrain cost, and every floor-height transition. The transition needs a persisted stair or ramp connection. KALLÍSTIS movement multipliers are reused by combat allowance accounting. Scenes without tactical terrain keep the prior movement contract.
- Floor elevation and token elevation are related as `Token.elevation = floor elevation + existing offset above floor`; only moves on opted-in tactical scenes adjust token elevation. Explicit GM wall overrides are stored in the command receipt.
- Focused map/token/combat run: **14 tests passed**.
- Full Django suite: **405 tests passed**. The warning `post-session backup failed: backup_drive_upload_failed` is the expected failure-path test in `gravewright/administration/test_post_session_backup.py`; the test deliberately injects that error and asserts the response.
- `manage.py check`: passed. `makemigrations --check --dry-run`: no changes detected. Godot 4.6.3 Web Compatibility export completed after the final GDScript projection adjustment. `git diff --check`: passed.

## Authenticated QA protocol proof

- QA origin: `http://127.0.0.1:3001`.
- Authenticated route: `/game/<authorized-campaign-id>/tactics/`. Both GM and player HTTP logins returned 200 and the authorized export route returned 200; anonymous route access redirected to login (302). The traditional campaign route returned HTTP 200 for the player.
- Separate GM and player sessions connected to the running Daphne WebSocket. Both received `table.joined`, `maps.state`, and `tokens.state`; the scene projection contained 256 persisted cells.
- Player move request `d43ff476-e750-4536-9bab-63fd411216d6` received `tokens.ack`. Both live sessions observed the token at `(2,1)`. A newly authenticated WebSocket session read the same position and token revision 3 after reconnect.
- GM terrain edit request `19b4f5d8-d44f-4e49-93e0-725e3151ce7c` was acknowledged. The player received terrain version 8 with 256 cells. Database readback confirmed the token at `(2,1)`, elevation `0`, revision `3`, and the edited `DIFICIL` cell cost `2`.
- Automated negative checks cover uncontrolled movement, off-turn movement, excess movement allowance, impassable terrain, missing height connection, wall crossing without explicit GM override, stale token/terrain revisions, unauthorized scene access, player terrain edits, duplicate requests, and rollback of rejected moves.

## Evidência histórica do bloqueio inicial

No primeiro registro de G4, `cua_repl` não encontrou browser e a política externa falhou com HTTP 403 antes da navegação. G4.1 superou esse bloqueio usando Chrome local com Playwright; os resultados atuais e as pendências estão documentados abaixo.

## G4.1 — validação visual local sem CUA (15/10/2026)

**Status: PARTIAL — a validação visual Godot passou no ambiente QA; a validação integral PixiJS e o movimento reverso válido continuam pendentes.** O Chrome local foi controlado com Playwright em dois contextos independentes, sem usar `cua_repl`, sem expor o Daphne fora de `127.0.0.1:3001` e sem abrir o banco operacional.

- Checkout/branch/HEAD verificados: `/home/tonyus-dev/Portifolio/gravewright`, `feat/tactics-godot-transport-20261014`, `fe1108911833c7a7e955b64b9c4d08eacf4fd4e6`.
- O fluxo anterior com login normal de GM e jogador carregou a rota autorizada `/game/<campanha-QA>/tactics/` e recebeu estado real pelo WebSocket: `table.joined`, `maps.state`, `maps.layers`, `tokens.state`, `maps.ack` e `session.ping`/`session.pong`. A projeção contém 256 células; GM recebeu `canEdit=true` e jogador `canEdit=false`.
- As capturas foram inspecionadas visualmente. O tabuleiro isométrico mostra células coloridas, faces de desnível, conexões em escada, obstáculos/paredes, seleção e tokens. O clique em pisos elevados e a seleção do token elevado funcionaram. Edição visual do GM foi projetada no jogador e sobreviveu ao reload.
- Movimento Godot real anterior recebeu `tokens.ack`, foi observado no outro contexto autenticado e persistiu após reload. O estado QA foi reutilizado e acumulou mudanças em execuções anteriores; no momento do último registro, o token controlado estava em `(5,2)`, elevação 4, versão 7, com o orçamento de movimento da ativação já consumido.
- No PixiJS, rota autorizada `/game/<campanha-QA>/` carregou e `tokens.state` correspondeu ao token de Godot. O arrasto real em direção à célula `(4,2)` enviou request `4311efa8-b738-4272-a64e-46609feb2ba6`, token versão 7, com caminho ortogonal inteiro `[(5,2),(4,2)]`. O backend respondeu `tokens.error: movement_exceeded`; posição e revisão persistidas permaneceram inalteradas. A leitura do QA SQLite confirmou `(5,2)`, elevação `4`, revisão `7`, terreno versão `78`, `movement_used=6`, combate ativo na rodada `1`, turno `0`. Antes da correção, os pontos fracionários do arrasto eram incompatíveis com a validação de célula tática. A correção converte o caminho apenas em cenas com `tacticalTerrain.initialized`; cenas legadas preservam o caminho anterior.
- Limitação Pixi: o mapa QA não tem imagens raster de fundo, portanto os pedidos de tiles retornam 404; a grade e os tokens são renderizados no canvas. Esse 404 do fixture QA não é erro WebSocket, mas impede atestar visualmente a compatibilidade de textura da mesa tradicional.
- Evidências: [diretório de capturas e logs](evidence/gravewright-g4.1-2026-10-15/), em especial `godot-gm-levels-and-stair.png`, `godot-player-selected-raised-token.png`, `godot-player-reload.png`, `pixijs-before-drag-patched.png`, `pixijs-after-drag-patched.png`, `browser-results.json` e `pixi-patched-drag-results.json`.

### Correções desta validação

- Godot agora seleciona polígonos de terreno na mesma ordem de desenho, incluindo elevações sobrepostas, e atinge tokens pela caixa visual projetada. Limpar a seleção anterior ao alternar o modo de conexão evita reutilizar um ponto antigo como origem da escada.
- PixiJS arredonda pontos de arrasto para células e interpola passos ortogonais no cliente tático. O servidor continua autoridade sobre movimento, turno e orçamento; a rejeição `movement_exceeded` confirma que a tentativa não alterou o estado.
- O roteiro Playwright usa contextos separados e login normal, evita repetir edições já persistidas, distingue ausência de tiles do fixture QA e não navega por controles auxiliares que abriam preferências.

### G4.2 — integração PixiJS ↔ Godot concluída (15/10/2026)

**Status: PASS.** A validação usou exclusivamente o SQLite isolado `/tmp/gravewright-tactics-qa-20261015/gravewright.sqlite3`, a campanha `Knossos QA - G4`, login normal e dois contextos autenticados independentes. O Daphne ficou limitado a `127.0.0.1:3001`; a porta operacional `3000` e o banco operacional não foram usados.

- Pela interface de combate do mestre, o comando `combat/next-round` recebeu o request ID `aa1c8947-fed4-4498-a9a1-defe05428f8b`. A leitura posterior confirmou combate ativo, rodada 2, turno 0, Batedor QA como ativação atual, controle do jogador e orçamento `0/6`. A ordem friendly/hostile existente permaneceu intacta.
- No PixiJS, um arrasto real moveu o Batedor de `(5,2)`, elevação 4, revisão 8, para `(4,2)`, elevação 3, revisão 9. O caminho foi um passo ortogonal pela escada persistida, custo 1; o request `fc36654f-0886-4c2a-842f-a8cfa26586d2` recebeu `tokens.ack`. O Godot do mestre conectado mostrou a nova posição sem reload. O Pixi e o Godot recuperaram essa posição após reload.
- No sentido inverso, o jogador controlou o Batedor no Godot e o moveu de `(4,2)`, elevação 3, revisão 9, para `(3,2)`, elevação 2, revisão 10. A escada, o piso transitável e o custo 1 foram validados pelo servidor. O request `7dc3fb5b-ee55-439a-aef5-f1e51bb22c75` recebeu `tokens.ack`; o Pixi do mestre observou a atualização ao vivo. Ambos recarregaram em `(3,2)`. O gasto total ficou em `2/6`; o limite não foi alterado.
- O raster foi enviado pelo formulário autenticado `/api/containers/12279004-3006-48e4-8a28-95e62aea9465/scene-upload`, HTTP 201. A cena `G4 QA raster - NOT CANON` (`fdbb3ac5-5580-47f8-b76d-94f613b44fc2`) contém a imagem explicitamente marcada QA-only, 1120×1120, grade 70 px e 14 tiles persistidas nos LODs 0–2. O manifesto e os tiles responderam HTTP 200; 18 requisições de tile observadas após ativar a cena terminaram em 200. O Pixi exibiu raster, grade e token Batedor QA, colocado pelo arrasto real da ficha no diretório de personagens; o segundo contexto autenticado viu o mesmo token. O console não registrou erros na validação final do par raster.
- O mapa de combate original não tinha tiles e produziu 404 esperados antes do upload. Nenhuma tile da cena raster produziu 404. A cena raster e seu token continuam preservados na campanha descartável, fora do broadcast.
- O broadcast retornou à cena `Knossos - invasão Silmari (QA)` pela interface: navegar até a cena original e então usar `Activate`. O `maps.ack` `67ed9eac-266b-4fc1-ba18-836895671a7e` e a leitura do banco confirmaram o broadcast original.
- Incidente de calibração: dois cliques feitos no Godot com sessão de mestre foram interpretados como comandos de edição de terreno. As revisões avançaram de 78 a 80, mas comparação de células e conexões confirmou conteúdo idêntico. Nenhum movimento ou regra foi forçado, nenhuma economia de movimento mudou e nenhum dado fora da campanha QA foi tocado.

**Regressão final:** Django completo **405/405**; conjunto focado de referência em terreno, tokens e combate **14/14**; o mesmo conjunto mais o teste de upload/entrega de tiles raster autorizada **15/15**. Godot `4.6.3.stable.official.7d41c59c4` importou em modo headless e exportou Web Compatibility; `git diff --check` passou. A execução focada inicial foi cancelada quando Django pediu confirmação para substituir o banco de testes existente; foi repetida com `--keepdb`, preservando-o. Nenhum código de produto mudou nesta etapa.

Evidências detalhadas, capturas, IDs e a leitura final do ambiente estão em `docs/evidence/gravewright-g4.2-2026-10-15/`. **G5 — Vertical Slice 01: Batalha de Knossos** está pronto para iniciar; esta validação não antecipou sua implementação.

### Pendências registradas em G4.1 — encerradas por G4.2

- A evidência Pixi comprovou recepção do estado e envio do formato de caminho compatível, mas não um movimento aceito no Pixi: o orçamento da ativação já estava esgotado. É necessária uma ativação QA com orçamento disponível para confirmar `tokens.ack`, sincronização reversa com Godot, persistência e reload via Pixi.
- Abrir uma cena QA com textura raster real (ou gerar esse asset pela UI autorizada) para conferir a sobreposição Pixi com o tabuleiro texturizado. Não foi fabricada imagem para mascarar a ausência do asset.
- Regressão após as correções: Django completo **405/405**, conjunto focado **14/14**, Godot 4.6.3 export Web Compatibility concluído, e `git diff --check` sem apontamentos.
- O script `tests/e2e/tactics_g4_1_visual.py` foi reexecutado com as duas sessões reais e sem reaplicar alterações já persistidas. Confirmou reloads e comparação Pixi/Godot; não repetiu o movimento bloqueado nem converteu `movement_exceeded` em sucesso.
