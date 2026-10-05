# GRAVEWRIGHT / KALLISTIS
## Transição controlada do upstream oficial v0.1.1 → v0.1.3

**Projeto:** KALLISTIS / Gravewright<br>
**Fork:** `NomosLudens/gravewright`<br>
**Upstream oficial:** `Gravewright/gravewright`<br>
**Branch de integração:** `chore/upstream-gravewright-v0.1.3`<br>
**Baseline do fork:** `73a8462cd5bce911ef89de34f27f4625d66d14b3`<br>
**Tag upstream alvo:** `v0.1.3`<br>
**Commit upstream v0.1.3:** `e5ae9d5fb09f8c31a3cfc7b6583004e715de9224`<br>
**Estado final da validação:** `PASS_INTEGRATION_READY`<br>
**Produção alterada durante a integração:** **NÃO**<br>
**Estado registrado na auditoria funcional:** merge ainda não commitado<br>
**Fechamento posterior:** commit de integração `d289b8784396de87824ea11f4c43a5543b40699f` criado em `chore/upstream-gravewright-v0.1.3`<br>
**Produção/deploy:** **NÃO**

> As seções 48–53 registram o estado ao fim da auditoria funcional, antes da revisão final do merge. A atualização pós-commit está na seção 54.

---

# 1. Objetivo deste documento

Este documento registra integralmente a transição do Gravewright usado pelo KALLISTIS, partindo da linhagem oficial **v0.1.1** e incorporando o upstream oficial até **v0.1.3**, com preservação das customizações KALLISTIS.

O objetivo não foi simplesmente “atualizar a versão”.

O processo foi tratado como uma integração controlada porque o fork KALLISTIS já havia divergido fortemente do upstream, com dezenas de commits próprios e alterações em autenticação, campanhas, actors, regras, combate, dice, realtime, tokens, UI, assets, compêndios e integrações específicas.

Foram aplicados os seguintes princípios:

- não atualizar produção cegamente;
- não tratar build/lint/teste automatizado como prova de produto funcional;
- preservar o `master`;
- trabalhar em branch isolada;
- evitar refatorações laterais;
- não introduzir mocks/fallbacks para “fazer passar”;
- comparar falhas com o baseline;
- exigir smoke real com dados reais;
- manter rollback possível;
- interromper imediatamente diante de qualquer risco de escrita na produção;
- só aceitar `PASS` com evidência funcional.

---

# 2. Linha oficial do upstream

## 2.1 v0.1.1

Commit oficial de referência:

```text
04a1b666119dc42db755126c61a764097ad5fc24
```

Essa era a linhagem base da qual o fork KALLISTIS havia partido.

Quando a auditoria foi iniciada, o fork já possuía **73 commits adicionais** em relação a essa base.

O HEAD conhecido do fork era:

```text
73a8462cd5bce911ef89de34f27f4625d66d14b3
fix: preserve file input identity across section navigation
```

---

## 2.2 Caminho oficial v0.1.1 → v0.1.3

A diferença oficial entre v0.1.1 e v0.1.3 era de quatro commits:

```text
04a1b666...  v0.1.1 lineage
    ↓
c2e3ef15...  Add local module installation and marketplace setup
    ↓
165f4dab...  Separate Windows installer and add updates with rollback
    ↓
811c7455...  Release 0.1.2 with Django marketplace apps and managed rollback
    ↓
e5ae9d5f...  Release 0.1.3 fixing local ZIP package installation
```

---

# 3. O que mudou no upstream

## 3.1 v0.1.2 — mudança estrutural

A verdadeira mudança arquitetural estava em **v0.1.1 → v0.1.2**.

A v0.1.2 incorporou:

- instalação de apps Django confiáveis;
- marketplace assinado;
- instalação local por ZIP;
- módulos Django exibidos como `Django · Server`;
- preparação de ambiente Python isolado;
- instalação de dependências pinadas sem substituir dependências travadas do core;
- verificação do Django;
- migrations;
- `collectstatic`;
- reinício controlado;
- rollback em caso de falha;
- preservação de apps Django e dependências durante atualizações;
- novo fluxo de installer/runner;
- atualização gerenciada de arquivos;
- remoção de arquivos obsoletos;
- regeneração de launcher;
- preservação de dados pessoais;
- snapshot `.old` opcional para rollback;
- tratamento de caminhos longos do Windows;
- documentação e testes correspondentes.

### Observação importante

Para uma instalação oficial antiga v0.1.1, a atualização para v0.1.2 exigia atenção especial ao launcher antigo.

No fork KALLISTIS, entretanto, não se optou por executar o updater oficial diretamente em produção. A integração foi feita no repositório, em branch isolada.

---

## 3.2 v0.1.3 — correção específica

A v0.1.3 foi uma mudança pequena quando comparada à v0.1.2.

O objetivo principal foi corrigir o fluxo:

```text
Install from ZIP
```

O bug fazia o sistema exibir incorretamente:

```text
Select a ZIP file.
```

mesmo quando um arquivo válido já havia sido escolhido.

### Causa

O formulário entrava em busy state e os inputs eram desabilitados antes da captura adequada do `FormData`.

### Correção

O `FormData` passou a ser capturado **antes** de os inputs serem desabilitados.

Isso preserva:

- o arquivo selecionado;
- o tipo do pacote;
- a instalação local por ZIP.

A v0.1.3 também adicionou cobertura browser para:

- instalação de módulo;
- instalação de sistema;
- arquivo vazio;
- limite de tamanho;
- atualização da biblioteca real.

---

# 4. Verificação do upstream oficial

Foi verificado o repositório oficial:

```text
Gravewright/gravewright
```

A release mais recente encontrada foi:

```text
v0.1.3
```

Commit:

```text
e5ae9d5fb09f8c31a3cfc7b6583004e715de9224
```

A release era:

```text
prerelease = NO
```

Asset oficial observado:

```text
Gravewright-0.1.3-django.zip
```

Digest publicado:

```text
sha256:94af735526537da22886773589c8896334e3a3fcc2c64f6e1cbcb05a504ffec4
```

A comparação oficial confirmou:

```text
v0.1.1 → v0.1.3 = 4 commits
v0.1.2 → v0.1.3 = 1 commit
```

Portanto:

```text
0.1.2 = mudança estrutural
0.1.3 = patch pequeno do ZIP
```

---

# 5. Estado inicial do fork KALLISTIS

Fork:

```text
NomosLudens/gravewright
```

Branch:

```text
master
```

HEAD esperado:

```text
73a8462cd5bce911ef89de34f27f4625d66d14b3
```

O fork possuía diversas alterações próprias, incluindo:

- autenticação KALLISTIS;
- campanhas;
- integração/importação de actors;
- runtime de regras;
- combate;
- dice;
- realtime;
- tokens;
- assets próprios;
- tema/UI KALLISTIS;
- compêndios;
- NPCs;
- permissões Mestre/Jogador;
- integrações adicionais do produto.

Por isso, foi rejeitada qualquer atualização direta em produção.

---

# 6. Primeiro bloqueio — checkout errado

A primeira tentativa de integração foi executada no diretório errado:

```text
/home/tonyus-dev/Documents/ChatGPT/GRAVEWRIGHT
```

Esse diretório apresentava:

```text
branch master sem commits
origin = inexistente
HEAD = ausente
worktree = dirty
```

Arquivos não rastreados encontrados:

```text
.tmp-velarim-audit.ts
docs/
kallistis-identidades-permissoes-preview.png
kallistis-identidades-permissoes.xlsx
kallistis-identidades-permissoes.xlsx.inspect.ndjson
scripts/
```

Veredito:

```text
VERDICT=BLOCKED
```

Nenhuma alteração foi realizada.

---

# 7. Localização do checkout autoritativo

Foi executada uma busca controlada por checkouts Gravewright/KALLISTIS.

Foram encontrados dois candidatos principais.

## Candidato incorreto

```text
/home/tonyus-dev/Documents/ChatGPT/GRAVEWRIGHT
```

Estado:

```text
origin=NONE
master sem commits
HEAD=ABSENT
WORKTREE=DIRTY
```

## Checkout autoritativo

```text
/home/tonyus-dev/Portifolio/gravewright
```

Estado:

```text
origin=https://github.com/NomosLudens/gravewright.git
branch=master
HEAD=73a8462cd5bce911ef89de34f27f4625d66d14b3
WORKTREE=CLEAN
EXPECTED_COMMIT_PRESENT=YES
```

Veredito:

```text
VERDICT=PASS_CHECKOUT_FOUND
```

---

# 8. Preparação da integração

Com o checkout correto identificado:

```text
REPO=/home/tonyus-dev/Portifolio/gravewright
BRANCH=master
HEAD=73a8462...
WORKTREE=CLEAN
```

Foi confirmado o remote oficial e buscada a tag:

```text
v0.1.3
```

Commit resolvido:

```text
e5ae9d5fb09f8c31a3cfc7b6583004e715de9224
```

Foi criada a branch isolada:

```text
chore/upstream-gravewright-v0.1.3
```

---

# 9. Merge upstream

O merge foi executado como:

```bash
git merge --no-ff --no-commit v0.1.3
```

Resultado:

```text
MERGE_APPLIED=YES
MERGE_CONFLICTS=NONE
COMMIT_CREATED=NO
```

O merge permaneceu preparado para revisão.

Delta observado:

```text
74 arquivos
+2672
-344
```

Houve sobreposição lógica em arquivos que o KALLISTIS também modificava, incluindo:

- `.env.example`;
- workflows;
- `config/settings.py`;
- `pyproject.toml`;
- `uv.lock`;
- administração;
- `management.js`;
- templates;
- infraestrutura de módulos.

Apesar da sobreposição, o Git aplicou o merge sem conflito textual.

---

# 10. Inspeção especial do `management.js`

O arquivo:

```text
gravewright/web/static/gravewright_web/inside/management.js
```

era crítico porque continha customizações KALLISTIS e também a correção upstream v0.1.3.

Foi comprovado que a correção upstream foi incorporada semanticamente:

```text
selecionar ZIP
→ capturar FormData
→ ativar busy state
→ manter File + package kind
```

O arquivo não foi substituído cegamente pelo upstream.

---

# 11. Testes automatizados iniciais

## 11.1 Suíte Django focada

Resultado:

```text
175 executados
171 passaram
4 falharam
```

As quatro falhas foram reproduzidas no commit-base.

Logo:

```text
NEW_REGRESSIONS_FROM_MERGE=NO
```

---

## 11.2 JavaScript

Resultado:

```text
21 passed
```

---

## 11.3 Marketplace E2E

```text
tests/e2e/marketplace.py
```

Resultado:

```text
PASS
```

Cobriu:

- upload ZIP;
- módulo;
- sistema;
- arquivo vazio;
- tamanho;
- atualização da biblioteca.

---

## 11.4 Django marketplace E2E

```text
tests/e2e/django_marketplace.py
```

Resultado:

```text
PASS
```

Cobriu:

- ativação;
- dependências;
- rotas;
- migrations;
- rollback;
- desativação.

---

# 12. Automatic updates — ajuste do fixture

O E2E de atualização automática inicialmente falhou.

Problema:

o ZIP de teste incluía arquivos versionados sob:

```text
data/vtt/compendiums/kallistis-npcs/
```

O updater corretamente rejeitou dados persistentes dentro de um pacote de release.

Foi ajustado somente o fixture para excluir:

```text
data/
```

Também foi corrigida uma comparação de caminho Python para comparar o caminho resolvido.

Resultado:

```text
automatic_updates.py --runner = PASS
```

A adaptação foi posteriormente auditada:

```text
AUTOMATIC_UPDATES_FIXTURE_CHANGE_VALID=YES
ASSERTIONS_RELAXED=NO
PRODUCTION_CODE_CHANGED_FOR_TEST=NO
```

O arquivo permaneceu em estado:

```text
MM tests/e2e/automatic_updates.py
```

porque parte vinha do merge upstream e parte era adaptação local ainda não stageada.

---

# 13. Falhas preexistentes detectadas

A suíte ampla terminou com:

```text
TOTAL=421
PASSED=414
FAILED=7
```

Os sete casos foram reproduzidos também no baseline.

## 13.1 Combate

Falhas preexistentes:

```text
test_effect_clock_expires_before_periodic_damage_and_is_bounded
test_periodic_damage_is_idempotent_and_previous_preserves_identity
test_roster_changes_preserve_current_identity
```

## 13.2 Upload de actors

Falhas:

```text
test_pdf_upload_and_delete_repair_all_sheet_sources
test_upload_csrf_private_images_and_file_cleanup
```

Causa observada:

```text
AttributeError: 'UUID' object has no attribute 'pk'
```

O callback de `transaction.on_commit` passava UUID para código que esperava objeto com `.pk`.

Não foi corrigido nesta integração.

## 13.3 Backup pós-sessão

Falhas:

```text
test_owner_success_contains_snapshot_media_manifest_and_cleans_temp
test_upload_failure_keeps_only_encrypted_retry_artifact
```

Problema observado:

```text
backup_commit_unavailable
```

Também havia caminho rígido:

```text
/home/tonyus-dev/gravewright
```

inadequado para o checkout usado.

Não foi corrigido.

---

# 14. `management.py`

Execução:

```bash
uv run --locked python tests/e2e/management.py
```

Resultado:

```text
FAIL
```

A mesma falha foi reproduzida no baseline.

O erro envolvia a localização do título:

```text
database
```

Classificação:

```text
MANAGEMENT_BASELINE=FAIL
MANAGEMENT_INTEGRATED=FAIL
NEW_REGRESSION=NO
```

Por isso, deixou de ser considerado bloqueador específico da integração.

---

# 15. Necessidade de smoke real

Apesar dos testes automatizados, não foi aceito `PASS_INTEGRATION_READY`.

Era necessário validar:

- AMIGOS ONLINE;
- Mestre;
- Jogador;
- cena real;
- mapa;
- tokens;
- realtime;
- persistência;
- ficha;
- file input.

O banco local do checkout continha apenas:

```text
BASELINE GRAVEWRIGHT 0.1.0
```

e não possuía AMIGOS ONLINE.

---

# 16. Localização da instância real

Foi encontrada a instalação real no Mini:

```text
HOST=kaline-mini
SERVICE=gravewright.service
```

Banco:

```text
/home/tonyus-dev/gravewright-runtime/data/gravewright.sqlite3
```

Foi confirmada a presença de:

```text
AMIGOS ONLINE
5 cenas
2 tokens
10 atores
1 vínculo de personagem KALLISTIS
```

---

# 17. Primeiro snapshot real

Foi criado snapshot seguro usando API SQLite:

```text
Connection.backup
```

com conexão de origem:

```text
mode=ro
```

Snapshot:

```text
/tmp/gravewright-kallistis-v013-smoke/gravewright.sqlite3
```

SHA-256:

```text
96e1fa0c76e34ebc6f5250a1514ec01d08eb47d4a61c73bf9b59210ba6744b4c
```

Mídia:

```text
/tmp/gravewright-kallistis-v013-smoke/media
```

Resultado:

```text
77/77 arquivos
39.744.662 bytes
```

Sem `.env` ou chaves.

---

# 18. Incidente aparente de credenciais

No primeiro runtime isolado, o usuário não conseguiu autenticar.

Inicialmente levantou-se suspeita de alteração de credenciais.

Foi aberto diagnóstico somente leitura.

Resultado:

```text
INCIDENT_SCOPE=ISOLATED_SNAPSHOT
PRODUCTION_AUTH_IMPACT=NO
ISOLATION_BREACH=NO
```

Foi comprovado:

```text
USER_PRESENT_SOURCE=YES
USER_PRESENT_SNAPSHOT=YES
IDENTIFIER_MATCH=YES
EMAIL_MATCH=YES
ROLE_MATCH=YES
PASSWORD_HASH_MATCH=YES
ACTIVE_STATUS_MATCH=YES
```

---

# 19. Causa real do login inválido

A autenticação de jogadores por frase KALLISTIS depende da:

```text
SECRET_KEY
```

O snapshot local usava uma `SECRET_KEY` diferente da instalação real.

Consequência:

```text
frase válida
→ digest calculado com chave diferente
→ invalid_credentials
```

Nenhuma senha, frase ou hash real havia sido modificado.

A única escrita foi no snapshot:

```text
gravewright_accounts_authattempt
```

Quatro tentativas de login incrementaram o limitador.

Produção permaneceu intacta.

---

# 20. Nova estratégia de autenticação segura

Foi decidido:

- não copiar a `SECRET_KEY` para fora do Mini;
- executar o smoke isolado no próprio Mini;
- usar a `SECRET_KEY` já existente no host;
- apontar o runtime de smoke apenas para banco e mídia copiados;
- usar porta separada;
- manter `gravewright.service` intacto.

Contrato:

```text
SECRET_KEY_SOURCE=existing Mini runtime
SECRET_KEY_EXPOSED=NO
SECRET_KEY_COPIED_OFF_HOST=NO

SMOKE_DB=SNAPSHOT
SMOKE_MEDIA=SNAPSHOT
SMOKE_SERVICE=SEPARATE
PRODUCTION_SERVICE_MODIFIED=NO
```

---

# 21. Runtime isolado no Mini

Runtime:

```text
BIND=127.0.0.1
PORT=4173
```

Código:

```text
/tmp/gravewright-v013-final-smoke/app-exact
```

Banco:

```text
/tmp/gravewright-v013-final-smoke/data/gravewright.sqlite3
```

Mídia:

```text
/tmp/gravewright-v013-final-smoke/media-campaign
```

Foi comprovado:

```text
WORKTREE_COPY_MATCH=YES
SMOKE_DATABASE_IS_SOURCE_DB=NO
SMOKE_MEDIA_IS_SOURCE_MEDIA=NO
SMOKE_CODE_IS_PRODUCTION_CODE=NO
```

---

# 22. Primeiro smoke parcial

Foi confirmado:

```text
MASTER_LOGIN=PASS
INSIDE_OPEN=PASS
AMIGOS ONLINE visível
```

Entretanto, inicialmente:

```text
PLAYER_LOGIN=UNVERIFIED
MAP=UNVERIFIED
TOKENS=UNVERIFIED
REALTIME=UNVERIFIED
```

O usuário não lembrava inicialmente uma identidade de jogador.

---

# 23. Cena alvo real

O snapshot identificou:

```text
A Fratura — Praça do Cristálio
```

com:

```text
11 tiles
2 tokens
```

Tokens observados:

```text
token 1: posição 5,9 / versão 8
token 2: posição 11,6 / versão 5
```

---

# 24. “Table unreachable”

Em uma execução, a interface terminou em:

```text
Table unreachable
```

Foi planejado A/B:

```text
A = baseline 73a8462
B = integração v0.1.3
```

---

# 25. Baseline não executável

No A/B, o baseline falhou antes de iniciar.

Erro:

```text
ImportError: gravewright.realtime.apps não contém RealtimeConfig
```

Foi constatado:

```text
gravewright/realtime/apps.py = 0 bytes
config/settings.py referencia gravewright.realtime.apps.RealtimeConfig
```

Consequência:

```text
BASELINE_EXECUTABLE=NO
```

Logo, o A/B direto ficou inconclusivo.

---

# 26. Runtime integrado conectou corretamente

Na branch integrada:

```text
MASTER_LOGIN=PASS
INSIDE_OPEN=PASS
AMIGOS_ONLINE_OPEN=PASS
TABLE_CONNECTION=PASS
```

Daphne registrou:

```text
WSCONNECTING
WSCONNECT
WSDISCONNECT
```

Endpoint:

```text
ws://127.0.0.1:4173/ws/tables/9df58f5d-50cc-4fc0-91d1-b430a10ffb3f/
```

Logo:

```text
REALTIME_HANDSHAKE=PASS
```

---

# 27. Investigação da tela vazia

Apesar do WebSocket funcionar, em uma execução a UI mostrou:

```text
No map has been drawn
```

Foi aberto diagnóstico do pipeline:

```text
SQLite
→ ORM
→ backend
→ transporte
→ browser
→ estado JS
→ renderer
```

---

# 28. Evidências do pipeline da cena

Cena:

```text
A Fratura — Praça do Cristálio
SCENE_ID=4ee2c0be-7e78-451d-9f02-f49c4b25e792
```

Banco:

```text
DB_TILE_COUNT=11
DB_TOKEN_COUNT=2
```

Mídia:

```text
TILE_MEDIA_REFERENCES_TOTAL=11
TILE_MEDIA_REFERENCES_FOUND=11
TILE_MEDIA_REFERENCES_MISSING=0
```

ORM:

```text
ORM_SCENE_FOUND=YES
ORM_TILE_COUNT=11
ORM_TOKEN_COUNT=2
```

Backend:

```text
tokens.state = 2 tokens
scene viewport candidates = 8 tiles LOD 0 para a região observada
```

Em execução válida da branch integrada:

```text
MAP_RASTER_VISIBLE=PASS
VISIBLE_TOKEN_OBJECTS=2
```

Logo:

```text
DATA_CORRUPTION_DETECTED=NO
V0_1_3_REGRESSION_DETECTED=NO
```

A tela vazia anterior não foi reproduzida.

---

# 29. `Module recovery required`

Foi observado em uma execução:

```text
Module recovery required
TransportError: unreachable
```

Origem:

```text
gravewright/modules/static/gravewright_modules/workspace.js
gravewright/modules/static/gravewright_modules/fetch-http-transport.js
```

Relacionava-se a:

```text
GET /api/tables/{campaign_id}/modules
GET /api/module-packages
```

Entretanto, na execução que renderizou corretamente a cena, o erro não bloqueou mapa/tokens.

Portanto:

```text
MODULE_RECOVERY_AS_ROOT_CAUSE=NOT_DEMONSTRATED
```

---

# 30. Smoke completo Mestre + Jogador

Posteriormente, as credenciais de Mestre e Jogador estavam disponíveis.

Foi executado smoke com duas sessões independentes.

Resultado final dos fluxos principais:

```text
MASTER_LOGIN=PASS
PLAYER_LOGIN=PASS
INSIDE_OPEN=PASS
AMIGOS_ONLINE_OPEN=PASS
TABLE_ENTRY=PASS
```

---

# 31. Fluxo correto de abertura da campanha

Uma execução intermediária aparentou falhar em:

```text
Open AMIGOS ONLINE
```

O diagnóstico mostrou que o fluxo é em duas etapas:

```text
/inside
→ Open AMIGOS ONLINE
→ prévia da campanha
→ Enter table
→ /game/<campaign_id>
```

Elementos observados:

```text
control:
#campaign-9df58f5d-50cc-4fc0-91d1-b430a10ffb3f button.gw-campaign__cover
```

A prévia era aberta via Datastar:

```text
GET /inside/dialog/preview/9df58f5d-50cc-4fc0-91d1-b430a10ffb3f
```

O botão `Enter table` executava navegação para:

```text
/game/9df58f5d-50cc-4fc0-91d1-b430a10ffb3f
```

Resultado:

```text
CAMPAIGN_OPEN_GATE=PASS
```

A falha anterior foi reclassificada como erro de interpretação do fluxo de smoke.

---

# 32. Painel Scenes

Após entrar corretamente na mesa:

```text
SCENES_PANEL_OPEN=PASS
VISIBLE_SCENE_COUNT=5
TARGET_SCENE_VISIBLE_IN_PANEL=YES
TARGET_SCENE_SELECTABLE=PASS
```

Cena selecionada:

```text
A Fratura — Praça do Cristálio
```

ID:

```text
4ee2c0be-7e78-451d-9f02-f49c4b25e792
```

---

# 33. Mapa e tokens

Com a cena alvo selecionada:

```text
MAP_VISIBLE=PASS
TOKEN_RENDER=PASS
TOKEN_COUNT_OBSERVED=2
```

---

# 34. Fluxo Mestre

Resultado:

```text
MASTER_FLOW=PASS
```

Foram comprovados:

- entrada na campanha;
- painel Scenes;
- cena correta;
- mapa;
- tokens;
- controles de Mestre.

---

# 35. Fluxo Jogador

Resultado:

```text
PLAYER_FLOW=PASS
PLAYER_CAN_ACCESS_CAMPAIGN=YES
PLAYER_CAN_SEE_SCENE=YES
PLAYER_CAN_SEE_MAP=YES
PLAYER_CAN_SEE_TOKENS=YES
PLAYER_HAS_GM_CONTROLS=NO
```

Logo, a separação Mestre/Jogador permaneceu correta.

---

# 36. Realtime com duas sessões

Token usado:

```text
813cede37e104562a7966a0446db11b7
```

Antes:

```text
POSITION_BEFORE=5,9
VERSION_BEFORE=8
```

Movimento pelo Mestre:

```text
POSITION_AFTER_MASTER_MOVE=7,9
VERSION_AFTER_MASTER_MOVE=9
```

Jogador observou sem reload:

```text
POSITION_OBSERVED_BY_PLAYER=7,9
```

Resultado:

```text
REALTIME_TWO_CLIENTS=PASS
```

---

# 37. Persistência

Após reload:

```text
POSITION_AFTER_RELOAD=7,9
```

Resultado:

```text
PERSISTENCE_RELOAD=PASS
```

Depois o token foi restaurado:

```text
POSITION_RESTORED=5,9
```

A alteração ocorreu apenas no snapshot isolado.

---

# 38. Personagem KALLISTIS

O ator vinculado:

```text
esquecido
```

abriu corretamente.

Resultado:

```text
KALLISTIS_CHARACTER_OPEN=PARTIAL
```

Limitações observadas:

- leitura canônica indisponível para aquela conta;
- ficha PDF sem asset;
- ator sem mídia associada.

Essas limitações eram dos dados/permissões do snapshot, não regressões do v0.1.3.

Classificação final:

```text
KALLISTIS_CHARACTER_OPEN=PASS_WITH_DATA_LIMITATIONS
V0_1_3_CHARACTER_REGRESSION=NO
```

---

# 39. Gate final — identidade do file input

O último gate estava relacionado ao próprio commit-base:

```text
73a8462
fix: preserve file input identity across section navigation
```

Arquivo de teste:

```text
/home/tonyus-dev/Portifolio/gravewright/.training/kallistis/sessao-01/kallistis-system-0.0.1.zip
```

Primeira execução:

```text
FILE_SELECTED=YES
FILE_COUNT_BEFORE=1
FILE_NAME_BEFORE=kallistis-system-0.0.1.zip

Settings → Administration

SAME_INPUT_IDENTITY=NO
FILE_COUNT_AFTER=0
FILE_NAME_AFTER=NONE
```

Resultado:

```text
KALLISTIS_FILE_INPUT_IDENTITY=FAIL
VERDICT=INCIDENT
```

---

# 40. Causa raiz do file input

Diagnóstico final:

```text
Ao navegar para Settings, o patch Datastar substituía o shell e removia a seção Administration do DOM.
```

Quando o usuário retornava:

```text
novo HTML
→ nova seção Administration
→ novo <input type=file>
→ FileList vazio
```

Logo, apenas adicionar um `id` estável ao input, como feito no `73a8462`, não era suficiente.

O `id` permite preservar um elemento apenas quando esse elemento também está presente no HTML recebido.

Na resposta de `Settings`, o input não existia.

---

# 41. Arquivos relacionados ao bug

Origem do patch:

```text
gravewright/web/inside.py::inside_response()
```

Renderização:

```text
shell.html
→ SSE.patch_elements()
```

Template principal:

```text
gravewright/web/jinja2/gravewright_web/inside/shell.html
```

Form/input:

```text
gravewright/web/jinja2/gravewright_web/inside/administration.html
```

---

# 42. Relação com upstream v0.1.3

Foi concluído:

```text
UPSTREAM_V0_1_3_CAUSED_FILE_INPUT_BUG=NO_DEMONSTRATED
```

As alterações upstream de administração/`management.js` cuidavam de módulos, updater e instalação ZIP.

A falha de preservação do input estava no comportamento da navegação KALLISTIS/shell.

Portanto, a causa foi uma insuficiência do mecanismo do próprio fork:

```text
73a8462 adicionava id
mas shell removia completamente o elemento
```

---

# 43. Correção cirúrgica

Foram alterados:

```text
gravewright/web/jinja2/gravewright_web/inside/shell.html
gravewright/web/jinja2/gravewright_web/inside/administration.html
```

Foi criado:

```text
tests/e2e/file_input_identity.py
```

A solução manteve a seção Administration presente no DOM, porém oculta quando outra seção está ativa.

Com isso:

```text
o mesmo elemento real permanece no DOM
→ FileList permanece associado ao mesmo input
```

Não foi feita cópia artificial de `FileList`.

---

# 44. Teste de regressão do file input

Antes da correção:

```text
REGRESSION_TEST_BEFORE_FIX=FAIL
```

Depois:

```text
REGRESSION_TEST_AFTER_FIX=PASS
```

Smoke manual:

```text
FILE_SELECTED=YES
FILE_COUNT_BEFORE=1
FILE_NAME_BEFORE=kallistis-system-0.0.1.zip

NAVIGATION_EXECUTED=YES
NAVIGATION_PATH=Settings → Administration

SAME_INPUT_IDENTITY=YES
FILE_COUNT_AFTER=1
FILE_NAME_AFTER=kallistis-system-0.0.1.zip

UPLOAD_SUBMITTED=NO
IMPORT_CAMPAIGN_CLICKED=NO
NETWORK_UPLOAD_REQUEST_SENT=NO
```

Resultado:

```text
KALLISTIS_FILE_INPUT_IDENTITY=PASS
VERDICT=PASS_FILE_INPUT_FIX
```

---

# 45. Estado funcional final

Após todos os gates:

```text
MASTER_FLOW=PASS
PLAYER_FLOW=PASS

CAMPAIGN_OPEN=PASS
TABLE_ENTRY=PASS

SCENES_PANEL_OPEN=PASS
TARGET_SCENE_SELECTABLE=PASS

MAP_VISIBLE=PASS
TOKEN_RENDER=PASS

REALTIME_TWO_CLIENTS=PASS
PERSISTENCE_RELOAD=PASS

KALLISTIS_CHARACTER_OPEN=PASS_WITH_DATA_LIMITATIONS
KALLISTIS_FILE_INPUT_IDENTITY=PASS

DIFF_AUDIT=PASS
NEW_AUTOMATED_REGRESSIONS=0

UPSTREAM_ZIP_FIX_AUTOMATED=PASS
UPSTREAM_MARKETPLACE_FIXTURE=PASS

DATA_CORRUPTION_DETECTED=NO
V0_1_3_REGRESSION_DETECTED=NO

PRODUCTION_MODIFIED=NO
ISOLATION_BREACH=NO
```

Veredito consolidado:

```text
VERDICT=PASS_INTEGRATION_READY
```

---

# 46. Produção durante todo o processo

A produção não foi usada como ambiente de escrita do smoke.

Serviço observado:

```text
gravewright.service
```

PID persistente observado em diversas missões:

```text
2332177
```

Foi repetidamente comprovado:

```text
PRODUCTION_SERVICE_UNCHANGED=YES
SMOKE_WRITE_PATH_TO_PRODUCTION_DB=NO
ISOLATION_BREACH=NO
```

Em algumas janelas o arquivo SQLite de produção mudou de tamanho/hash devido a atividade real de autenticação na própria publicação.

Essas mudanças não foram atribuídas ao smoke sem evidência.

Classificação usada:

```text
PRODUCTION_DB_CHANGED_DURING_WINDOW=YES quando observado
SMOKE_CAUSATION=NOT_DEMONSTRATED
```

No smoke final:

```text
PRODUCTION_DB_CHANGED_DURING_WINDOW=NO
```

---

# 47. Erros observados mas não bloqueantes

## `/sw.js`

Foi observado:

```text
GET /sw.js → 404
```

Não houve evidência de impacto funcional nos gates validados.

---

## `media-workspace.js`

Foi observado em smoke anterior:

```text
TypeError ao ler "x"
```

Não bloqueou os fluxos finais validados.

Permanece como débito observado, não regressão comprovada do v0.1.3.

---

## Module recovery

Erro observado:

```text
TransportError: unreachable
```

na recuperação de módulos/workspace.

Não bloqueou:

- campanha;
- cena;
- mapa;
- tokens;
- realtime;
- persistência.

Logo, não foi usado para reprovar a integração.

---

# 48. Estado Git ao final da validação

Até o encerramento deste processo:

```text
BRANCH=chore/upstream-gravewright-v0.1.3
HEAD=73a8462cd5bce911ef89de34f27f4625d66d14b3
```

O merge seguia sem commit.

Estado relevante:

```text
74 entradas staged da integração upstream
tests/e2e/automatic_updates.py = MM
```

Após a correção do file input também existiam:

```text
gravewright/web/jinja2/gravewright_web/inside/shell.html
gravewright/web/jinja2/gravewright_web/inside/administration.html
tests/e2e/file_input_identity.py
```

Nenhum commit final havia sido criado ainda.

Também:

```text
PUSH_EXECUTED=NO
PR_CREATED=NO
DEPLOY_EXECUTED=NO
MASTER_MODIFIED=NO
```

---

# 49. O que deve entrar no commit final

O commit final de integração deve conter conscientemente:

## Upstream oficial

```text
v0.1.1 → v0.1.2 → v0.1.3
```

incluindo:

- Django marketplace;
- instalação ZIP;
- lifecycle de apps Django;
- updater;
- rollback;
- launcher/runner;
- patch v0.1.3 de FormData.

## Ajuste local do teste

```text
tests/e2e/automatic_updates.py
```

Ajustes já auditados:

- excluir `data/` persistente do ZIP de fixture;
- resolver caminho Python antes da comparação;
- sem relaxar assertions;
- sem alterar código de produção.

## Correção local KALLISTIS

```text
shell.html
administration.html
tests/e2e/file_input_identity.py
```

Objetivo:

```text
preservar o input real e seu FileList durante navegação interna
```

---

# 50. O que não deve ser misturado nesse commit

Não incorporar como “correção da integração”:

- 7 falhas automatizadas preexistentes;
- bug UUID nos uploads de actors;
- backup pós-sessão;
- `management.py`;
- `/sw.js`;
- `media-workspace.js`;
- `Module recovery required`;
- outros débitos históricos.

Esses itens devem continuar registrados separadamente.

---

# 51. Próximo passo recomendado

A integração está funcionalmente aprovada.

O próximo processo deve ser somente:

```text
1. git status completo
2. revisar staged
3. revisar unstaged
4. revisar automatic_updates.py
5. revisar shell.html
6. revisar administration.html
7. revisar file_input_identity.py
8. confirmar ausência de arquivos acidentais
9. stagear conscientemente o delta final
10. revisar diff final
11. criar um único commit de integração
12. revisar o commit criado
13. somente depois decidir merge no master
14. deploy deve ser uma missão separada
```

Não repetir os smokes funcionais já encerrados sem regressão nova observada.

---

# 52. Resumo executivo

## Origem

```text
UPSTREAM_START=v0.1.1
UPSTREAM_TARGET=v0.1.3
```

## Mudança oficial

```text
v0.1.2 = arquitetura de apps Django + updater/rollback
v0.1.3 = correção de instalação ZIP/FormData
```

## Fork

```text
KALLISTIS_FORK_AHEAD_OF_V0_1_1=73 commits no início da auditoria
```

## Integração

```text
MERGE_CONFLICTS=0
DIFF_AUDIT=PASS
NEW_AUTOMATED_REGRESSIONS=0
```

## Produto real

```text
MASTER=PASS
PLAYER=PASS
CAMPAIGN=PASS
SCENES=PASS
MAP=PASS
TOKENS=PASS
REALTIME=PASS
PERSISTENCE=PASS
CHARACTER=PASS_WITH_DATA_LIMITATIONS
FILE_INPUT=PASS após correção cirúrgica
```

## Segurança

```text
PRODUCTION_MODIFIED=NO
ISOLATION_BREACH=NO
SECRET_KEY_EXPOSED=NO
SECRET_KEY_COPIED_OFF_HOST=NO
```

## Git

```text
COMMIT_CREATED=NO
PUSH_EXECUTED=NO
PR_CREATED=NO
DEPLOY_EXECUTED=NO
```

## Veredito final

```text
PASS_INTEGRATION_READY
```

---

# 53. Conclusão

A transição do Gravewright oficial **v0.1.1 → v0.1.3** foi tratada como integração controlada, não como atualização automática.

A branch integrada:

- incorporou o salto arquitetural da v0.1.2;
- incorporou o patch ZIP da v0.1.3;
- preservou as customizações KALLISTIS;
- não introduziu nova regressão automatizada detectada;
- passou por smoke real com dados da campanha AMIGOS ONLINE;
- comprovou Mestre e Jogador;
- comprovou mapa e tokens;
- comprovou realtime entre duas sessões;
- comprovou persistência;
- comprovou separação de permissões;
- preservou a produção;
- detectou e corrigiu uma falha real do file input do próprio fork;
- terminou com o merge ainda não commitado, permitindo revisão final antes da entrada no `master`.

O estado consolidado é:

```text
VERDICT=PASS_INTEGRATION_READY
```

A próxima ação correta é **finalizar o merge de forma controlada**, revisar o commit resultante e só depois decidir a entrada em `master` e eventual deploy.

# 54. Fechamento controlado do merge — 2026-10-05

Após a auditoria funcional, foi executada a revisão final do merge no checkout autoritativo:

```text
REPOSITORY=/home/tonyus-dev/Portifolio/gravewright
BRANCH=chore/upstream-gravewright-v0.1.3
COMMIT=d289b8784396de87824ea11f4c43a5543b40699f
PARENT_FORK=73a8462cd5bce911ef89de34f27f4625d66d14b3
PARENT_UPSTREAM=e5ae9d5fb09f8c31a3cfc7b6583004e715de9224
FILES=76
DIFF=+2822/-346
WORKTREE=CLEAN
DEPLOY_EXECUTED=NO
```

O commit `d289b87` é o merge commit que une o baseline KALLISTIS e o upstream oficial v0.1.3. A revisão não repetiu os gates funcionais já encerrados. O painel Administration oculto faz a leitura administrativa `GET /api/admin/status`; a rota não iniciou importação, upload nem atualização.

Este fechamento registra o commit local da integração. A entrada em `master` e o deploy continuam fora do escopo desta integração e devem ser tratados como etapas separadas.
