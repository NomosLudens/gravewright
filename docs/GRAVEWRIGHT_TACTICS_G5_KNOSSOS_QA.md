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
| G5.1 — missão e regras no servidor | **PARTIAL** | Definição reutilizável, instância, participantes, eventos, estados terminais, autorização de GM, transição de extração, ataque espacial corpo a corpo, validação/efeito de Emboscada e cálculo de dano conectado ao ataque salvo estão implementados. A validação automatizada usa fixtures sintéticas; ainda não há elenco KALLÍSTIS aprovado para uma sessão real. |
| G5.2 — cliente jogável | **PARTIAL** | O Godot seleciona um ataque bem-sucedido e pede ao servidor para aplicar o dano derivado, sem enviar dano bruto/multiplicador do cliente. Importação e exportação Web passaram. Ainda falta abrir e jogar o fluxo em navegador autenticado. |
| G5.3 — Knossos e QA final | **UNVERIFIED** | Ainda não há prova manual de dois navegadores para vitória, derrota, técnica, reload e ausência de regressões PixiJS; não existe no QA um vínculo/identidade KALLÍSTIS aprovado para preparar o elenco por fluxo oficial. |

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

## Estado de produto

O estado atual comprova vitória por evacuação em teste de serviço, validação espacial de combate corpo a corpo, custo/condição de Emboscada, cálculo de dano derivado do ataque no servidor, Godot exportado e regressão completa. Não comprova uma batalha jogada por mestre e jogador. O banco QA não possui vínculo canônico KALLÍSTIS aprovado, identidade ou acesso de jogador sincronizado; os dois atores existentes e três tokens não formam o elenco sete. O roster não foi fabricado nem escrito diretamente no banco. Portanto, **G5 permanece PARTIAL**. Próximo insumo necessário: identidade de QA autenticável no KALLÍSTIS e sete fichas completas aprovadas, incluindo um Batedor com Emboscada e um Nomos, para sincronização pelos serviços oficiais e continuação em duas sessões independentes.
