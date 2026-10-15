# Gravewright Tactics — G5 Batalha de Knossos

**Estado geral: PARTIAL — G5 não aprovado.** Em 15/10/2026, a vitória foi jogada com duas sessões locais autenticadas, mas a segunda execução de derrota não chegou a ACTIVE. KALLISTIS federado segue fora da prova.

## Autoridade e cenário

- Checkout de implementação: `/home/tonyus-dev/Portifolio/gravewright`.
- Branch: `feat/tactics-godot-transport-20261014`.
- HEAD inicial solicitado: `478b93be191479f45f074183da4cdee9ac96be23`.
- G4.2 foi consolidado no commit `2795989` (relatório e evidências). O diretório local `tactics/godot/.godot/` permanece fora do Git.
- Documento fundador consultado no Google Drive: `GRAVEWRIGHT_TACTICS_DOCUMENTO_FUNDADOR_VERTICAL_SLICE_01_KNOSSOS_2026-10-14.md` (ID `1rN1NcpeViQ6qFzPpNFkp0lCkdpbVeiYP`). Ele define a operação como proposta de missão, sem converter o conflito Silmari ou planos de sessão em fatos canônicos.
- Técnica escolhida para implementação: **Emboscada**, KALLISTIS Regras Freeze v1.3, Batedor, Técnica da Trilha, Nível I. O texto canônico consultado declara custo de 1 Fôlego e efeito no primeiro ataque contra alvo que ainda não agiu: Nível I, dano-base ×2 e condição Exposto.
- Personagens de campanha 002, 003 e Nestor não são escalados automaticamente. A composição esperada é três aliados, três Silmari e um Nomos evacuando. Todos devem ser atores/tokens persistidos criados pelos fluxos autorizados da campanha.

## Gates

| Gate | Estado | Evidência e pendências |
|---|---|---|
| G5.0 — consolidação e desenho executável | **PASS** | G4.2 foi consolidado no commit `2795989`. Contratos do combate existente, modelo da missão, origem de Emboscada e critérios de preparação estão identificados. |
| G5.1 — missão e regras no servidor | **PASS local QA / KALLISTIS UNVERIFIED** | O roster local NÃO CANÔNICO passou pelos serviços oficiais e foi persistido; a vitória e regras de combate/Emboscada foram exercitadas. Não há vínculo canônico KALLISTIS e nenhum foi falsificado. |
| G5.2 — cliente jogável | **PASS no fluxo de vitória** | Dois clientes autenticados jogaram a missão no Godot: movimento, Emboscada, ataque, dano do servidor, resposta inimiga pelo GM, turnos, evacuação e reload. Não implica PASS do ciclo de derrota. |
| G5.3 — Knossos e QA final | **PARTIAL** | Vitória, persistência e leitura do estado terminal pelos dois navegadores foram verificadas. A segunda instância independente contém sete participantes e chegou a READY, mas a derrota, reconexão durante ACTIVE e conferência visual final dessa segunda execução não foram concluídas. |

## Contrato persistente introduzido

- `MissionDefinition` separa o conteúdo reutilizável do estado de uma partida.
- `MissionInstance` registra campanha, cena, encontro, objetivo, resultado, estado, versão e horários.
- `MissionParticipant` conecta a missão a `Actor` e `Token` reais; o Nomos evacuando precisa ter povo `nomos` no runtime KALLÍSTIS.
- `MissionEvent` registra uma sequência auditável associada à instância.
- A definição inicial `knossos-evacuation` é semeada pela migração `gravewright/combat/migrations/0002_missiondefinition_missioninstance_missionevent_and_more.py`. O conteúdo marca explicitamente a batalha como proposta não canônica.
- Preparar a missão exige grade tática persistida 16×16, as cotas 0 e 1, escada persistida entre cotas, obstáculo intransponível, parede persistida, zona de extração dentro da grade e sete participantes. Os seis combatentes e o Nomos entram no encontro existente; a iniciativa segue a alternância de lados existente.
- `mission.start` exige a missão READY e `Encounter.active`. Ao alcançar uma célula da zona, o servidor registra VICTORY e encerra o encontro; o runtime KALLÍSTIS pode registrar DEFEAT quando a Permanência do Nomos chegar a `TERMINAL`. Encerramento do mestre resulta em ABORTED e não é apresentado como vitória.
- Após estado terminal, novos comandos de movimento e combate são recusados. A repetição do mesmo request continua atendida pelo recibo de idempotência já existente na mesa.
- Em cenas com `TacticalTerrain`, ataque Corpo/Agilidade + Combate exige ativação atual, atacante controlado, dois tokens persistidos no mesmo encontro, adjacência ortogonal e linha de efeito desobstruída. Cenas legadas sem terreno tático preservam o fluxo existente. Alcance de ataque à distância permanece sem contrato e é recusado em cena tática.
- Emboscada exige vínculo canônico aprovado, snapshot ativo Batedor com Marco 2 e técnica aprendida, alvo ainda não ativado na rodada, ação e Fôlego disponíveis; aplica Exposto e persiste metadados de dano-base ×2 no evento de ataque. Ao mestre aplicar dano, o servidor carrega esse perfil salvo, calcula a fórmula Freeze v1.3 via runtime KALLÍSTIS e rejeita `rawDamage`/multiplicador enviados pelo cliente. Evento duplicado é idempotente; um segundo evento de dano para o mesmo ataque é recusado.
- O perfil de dano usa a arma confirmada da ficha KALLÍSTIS aprovada, catálogo Freeze v1.3, Potente/Corpo limitado a +3, grau da margem, Proteção e Perfurante. O cliente só seleciona uma resolução bem-sucedida ainda sem dano.

## Verificação local até agora

- `manage.py check`: PASS.
- `makemigrations --check --dry-run`: PASS, nenhuma migração pendente.
- Migração G5.1 aplicada ao SQLite QA `/tmp/gravewright-tactics-qa-20261015/gravewright.sqlite3`: PASS.
- Testes focados `gravewright.combat.tests_missions`: **7/7 PASS** usando o banco de teste isolado `/tmp/gravewright-tactics-qa-20261015/test-gravewright.sqlite3`. Incluem fórmula de arma Potente, bônus de Corpo, Proteção e rejeição de dano falsificado/duplicado. Dados e vínculos canônicos sintéticos existem apenas nas fixtures do teste, não no banco QA de produto.
- Regressão Django completa (`config gravewright`): **412/412 PASS** no banco de teste isolado `/tmp/gravewright-tactics-qa-20261015/test-gravewright.sqlite3`; caminhos do DB ativo, `MEDIA_ROOT` e DB de teste foram impressos e conferidos antes da execução. O runner imprimiu `post-session backup failed: backup_drive_upload_failed`, mas concluiu com `OK`.
- Godot 4.6.3 headless import: PASS; export Web Compatibility: PASS, saída em `/tmp/gravewright-tactics-qa-20261015/godot/`. `git diff --check`: PASS.
- O banco QA de produto continua sem instâncias de missão, possui zero `KallistisCharacterLink` canônicos aprovados, zero `KallistisIdentity` e zero `KallistisPlayerAccess`. Há dois usuários locais, dois atores e três tokens persistidos, insuficientes para o elenco de sete; não temos credenciais para autenticar essas contas em duas sessões. Nenhum ator, vínculo, login, vitória ou derrota foi fabricado para preencher esse gate.
- Browser autenticado com mestre/jogador, vitória e derrota jogadas, reload/reconexão e ausência de regressão PixiJS **UNVERIFIED**. A execução permanece bloqueada nesses gates até existir identidade/acesso KALLÍSTIS de QA e sete fichas aprovadas que possam ser sincronizadas pelos serviços oficiais.

## INCIDENTE de isolamento do runner

A primeira invocação de `manage.py test --keepdb` foi interrompida como evidência ao observar que o runner escolhia `data/test-gravewright.sqlite3`, pois `config/settings.py` fixa esse nome em `DATABASES.TEST.NAME` e ignora `GRAVEWRIGHT_DATABASE` para o banco de teste. Essa execução aplicou a migração G5 nesse arquivo de teste ignorado pelo Git e falhou em um fixture incompleto. Nenhum banco operacional (`data/gravewright.sqlite3`) foi selecionado. As execuções seguintes passaram a apontar explicitamente `DATABASES.default.TEST.NAME` para `/tmp/gravewright-tactics-qa-20261015/test-gravewright.sqlite3`; nenhum outro teste deve usar o arquivo `data/test-gravewright.sqlite3` nesta missão.

## Execução G5.3 de 15/10/2026

- Checkout `/home/tonyus-dev/Portifolio/gravewright`, branch `feat/tactics-godot-transport-20261014`, HEAD inicial `be05989213e3ebd9a700b93a8b55f53f5d54e30d`. Sem merge, deploy ou segundo checkout.
- Banco de execução: `/tmp/gravewright-tactics-qa-20261015/g5.3/gravewright.sqlite3`; mídia: `/tmp/gravewright-tactics-qa-20261015/g5.3/media`; configuração ativa `config.qa_settings`. A configuração impõe SQLite temporário, integrações externas desativadas e fixtures QA opt-in.
- A sessão QA criou sete atores e tokens através de serviços de campanha. Três aliados têm permissão de controle do jogador local autenticado; três Silmari são NPCs sob GM; o Nomos é unidade de cenário. `qa_fixture`/`scenario_npc` e autoridade `NON_CANONICAL` permanecem explícitos. Nenhum `KallistisIdentity` ou `KallistisCharacterLink` aprovado foi criado. Autenticação federada KALLISTIS: **UNVERIFIED**.
- Vitória: campanha `Knossos G5.3 QA`, cena `058a24fd-1b06-4d94-a7f1-52e706521c07`, missão `cf855d57-bd30-4d25-929e-f14ce799e92e`; estado persistido `VICTORY`, razão `nomos_extracted`, sete participantes, 45 eventos. Sequência final: evento 44 `mission.ended`; evento 45 `objective.resolved`. Nomos evacuado em `(14,14)`.
- Emboscada usou ataque real da ficha QA Batedora com Faca; o servidor registrou `resolutionId=cb96b1a6-f2f4-4183-bd72-8c9b84d72d06`, gasto de 1 Fôlego e multiplicador-base ×2 no perfil salvo. O GM aplicou dano usando somente resolução/alvo/evento; o backend calculou raw 6, proteção 0, final 6 e Vitalidade do Silmari de 19 para 13. Não houve dano bruto ou multiplicador recebido do cliente.
- A resposta do contra-ataque Silmari foi autorizada pelo GM e registrada por resolução/dano. Dois combatentes aliados sofreram reduções válidas de Vitalidade. Cliques durante ACTIVE que chegaram à ferramenta de edição de terreno não alteraram a posição; foram impedidos depois da correção que desativa edição de terreno em missão ativa. O teste apontou e corrigiu também a validação que comparava recursos atuais com valores iniciais após dano/consumo.
- GM e jogador usaram sessões independentes e autenticadas no Gravewright. Ambos receberam o estado terminal `VICTORY` após reload; o jogador recebeu `maps.state`, `tokens.state` com sete tokens, `resources.state` e `mission.result`. Capturas estão em `/tmp/gravewright-tactics-qa-20261015/g5.3/` (`gm-victory-reload.png`, `player-victory-reload.png`, `player-ambush.png`, `gm-h3-damage.png`, `pixi-combat-active.png`).
- PixiJS abriu para GM/jogador. A cena Pixi da segunda instância foi inspecionada; a lista de combatentes estava vazia antes de iniciar a segunda execução. Não foi reivindicada equivalência visual dos controles táticos no PixiJS.
- Segunda instância: campanha `Knossos QA Derrota G5.3`, cena `79cd2ea9-af72-42bc-8b42-56e485fcda1c`, missão `e6ebd0b3-e550-4926-950b-b1b6585b80e2`, sete participantes e terreno persistido; estado final desta sessão de trabalho `READY`, nove eventos. Nenhum estado, Vitalidade ou Permanência foi alterado diretamente no banco para fabricar derrota. **Derrota legítima, comandos posteriores bloqueados após derrota e reconexão durante ACTIVE: NÃO COMPROVADOS.**
- A execução completa encontrou um ponto visual que bloqueava cliques nos quadrados de extração sob o HUD Godot. O painel agora permite passagem de mouse e `H` oculta/mostra o HUD. O modo de edição de terreno também não captura mais comandos durante missão ACTIVE.
- Regressão final nesta revisão: suíte Django `config gravewright` **416/416 PASS** em 76,016 s, com `config.qa_settings`, banco ativo e mídia impressos e isolados sob `/tmp/gravewright-tactics-qa-20261015/g5.3/`. Testes focados de proveniência/combate **11/11 PASS**; `makemigrations --check --dry-run` **PASS** (`No changes detected`); Godot **4.6.3 import + export Web PASS**; `git diff --check` **PASS**. O runner registrou `post-session backup failed: backup_drive_upload_failed`, sem falhar os testes.
- `gh pr view 2` e a busca de PRs pela branch retornaram que não há PR #2 correspondente no repositório configurado. O commit `42a0a43` foi enviado em fast-forward para `origin/feat/tactics-godot-transport-20261014`; nenhuma PR nova foi criada, não houve merge nem deploy. A exigência de manter a PR #2 draft permanece **UNVERIFIED / PR não encontrada**.
- Evidências gráficas são QA local e não foram adicionadas ao Git; `.godot/` permanece local e não deve ser staged.

## Estado de produto

O estado comprova uma vitória jogada por mestre/jogador locais autenticados com sete fichas QA mecanicamente válidas, Emboscada, dano autoritativo, movimento, turnos, evacuação, resultado persistido e reload. O resultado não valida identidade federada ou proveniência canônica, não conclui a execução independente de derrota e não prova reconexão do WebSocket durante combate ACTIVE. **G5 permanece PARTIAL** até concluir a derrota legítima e reconexão, ou registrar um impedimento concreto se houver bloqueio técnico.
