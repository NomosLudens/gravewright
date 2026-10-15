# Gravewright Tactics — G5 Batalha de Knossos

**Estado geral: PARTIAL — G5 não aprovado.** Este relatório acompanha a implementação incremental. O encontro ainda não foi jogado por dois usuários no Godot/browser.

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
| G5.1 — missão e regras no servidor | **PARTIAL** | Definição reutilizável, instância, participantes, eventos, estados terminais, autorização de GM, transição de extração, ataque espacial corpo a corpo e validação/efeito de Emboscada estão implementados. A resolução do multiplicador ×2 no fluxo de dano e o roteiro completo ainda não estão provados. |
| G5.2 — cliente jogável | **PARTIAL** | Godot agora expõe comandos de missão, seleção de movimento/ataque/Emboscada, próximo turno, registro de tokens, controle básico de dano pelo mestre e feedback de confirmação/erro. Ainda faltam apresentação e inspeção completas do fluxo de dano/resolução e prova em navegador. |
| G5.3 — Knossos e QA final | **NOT STARTED** | Ainda não há prova manual de dois navegadores para vitória, derrota, técnica, reload e ausência de regressões PixiJS. |

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
- Emboscada exige vínculo canônico aprovado, snapshot ativo Batedor com Marco 2 e técnica aprendida, alvo ainda não ativado na rodada, ação e Fôlego disponíveis; aplica Exposto e persiste metadados de dano-base ×2 no evento de ataque. A multiplicação não é aplicada automaticamente à operação `damage`, cuja autorização segue separada pelo mestre. Portanto, custo e condição estão integrados, mas a consequência de dano ×2 ainda não percorre o fluxo de dano e permanece pendente.

## Verificação local até agora

- `manage.py check`: PASS.
- `makemigrations --check --dry-run`: PASS, nenhuma migração pendente.
- Migração G5.1 aplicada ao SQLite QA `/tmp/gravewright-tactics-qa-20261015/gravewright.sqlite3`: PASS.
- Testes focados `gravewright.combat.tests_missions`: **6/6 PASS** usando o banco de teste isolado `/tmp/gravewright-tactics-qa-20261015/test-gravewright.sqlite3`. Cobrem definição/não-canonicidade, roster, início pelo Encounter existente, evacuação com token real e persistência de vitória, autorização de GM, repetição idempotente, ataque espacial/linha bloqueada e custo/Exposto de Emboscada.
- `manage.py check`: PASS; `makemigrations --check --dry-run`: PASS; regressão Django completa: **411/411 PASS**; `gravewright.combat.tests_missions`: **6/6 PASS**; Godot 4.6.3 headless import: PASS; export Web Compatibility: PASS; `git diff --check`: PASS.
- A regressão imprimiu o aviso `post-session backup failed: backup_drive_upload_failed`, mas concluiu com `OK` (411 testes). Isso não foi tratado como prova ou falha de fluxo de jogo.
- Playwright de batalha, console autenticado, prova de dois navegadores, ataque/dano/Emboscada no browser, derrota independente, reconexão e reload de desfecho ainda não executados.

## INCIDENTE de isolamento do runner

A primeira invocação de `manage.py test --keepdb` foi interrompida como evidência ao observar que o runner escolhia `data/test-gravewright.sqlite3`, pois `config/settings.py` fixa esse nome em `DATABASES.TEST.NAME` e ignora `GRAVEWRIGHT_DATABASE` para o banco de teste. Essa execução aplicou a migração G5 nesse arquivo de teste ignorado pelo Git e falhou em um fixture incompleto. Nenhum banco operacional (`data/gravewright.sqlite3`) foi selecionado. As execuções seguintes passaram a apontar explicitamente `DATABASES.default.TEST.NAME` para `/tmp/gravewright-tactics-qa-20261015/test-gravewright.sqlite3`; nenhum outro teste deve usar o arquivo `data/test-gravewright.sqlite3` nesta missão.

## Estado de produto

O estado atual comprova persistência e vitória por evacuação em teste de serviço, validação espacial de combate corpo a corpo, custo/condição de Emboscada, painel Godot compilado/exportado e regressão completa. Não comprova uma batalha jogada por mestre e jogador. O SQLite QA tem apenas dois atores e dois tokens na cena Knossos; a missão exige sete participantes. Não há servidor local autenticado ativo nem sessão do mestre disponível para completar a preparação pelos fluxos normais. O roster não foi fabricado nem escrito no banco. A interface tem um controle básico para o mestre declarar dano, mas não apresenta ainda o fluxo completo com inspeção de proteção e condições; o multiplicador x2 também não é consumido pela operação autorizada `damage`. Os resultados de combate/reload não foram verificados no browser. Portanto, **G5 permanece PARTIAL; não declarar a batalha jogável ou aprovada**.
