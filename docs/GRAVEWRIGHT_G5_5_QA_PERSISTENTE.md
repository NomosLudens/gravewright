# Gravewright — G5.5 QA persistente

**Relatório técnico | 19 de outubro de 2026**  
**Resultado geral: PARTIAL**

A infraestrutura QA foi transferida para armazenamento persistente do usuário, com serviço controlado pelo systemd de usuário, SQLite isolado e backup/restauração verificados. O G5.4 permanece `PASS_HISTORICAL`; seu combate não foi repetido.

A instância autenticou Mestre e jogador e serviu o export Godot atual. Um registro de QA criado pelo WebSocket oficial sobreviveu à parada e à inicialização controlada do backend. Os dois clientes foram fechados e abertos novamente, autenticaram-se e acessaram o mesmo tabuleiro e a missão persistida.

A missão está em `PREPARING`, sem participantes, e não está apta a playtest. A única tentativa de criar uma fixture oficial foi recusada pelo próprio guard do projeto (`qa_fixtures_disabled`): `gravewright/actors/provenance.py` exige que a raiz de fixture, banco e mídia resolvam sob `/tmp`. Isso conflita com a exigência G5.5 de não usar `/tmp` para dados persistentes. A guarda não foi contornada e nenhuma identidade, regra ou resultado foi fabricado.

## Ambiente recuperado

| Item | Estado verificado |
|---|---|
| Checkout | `/home/tonyus-dev/Portifolio/gravewright` |
| Branch / HEAD | `feat/tactics-godot-transport-20261014` / `b4d737bbbc66e608f5743853a8915dce5bac912e` |
| QA persistente | `/home/tonyus-dev/.local/share/gravewright/playtest-g5/` em ext4 montado `rw`; 263 GB livres na verificação |
| SQLite QA | `database/gravewright.sqlite3`; `integrity_check=ok`, 73 migrations, 2 contas, 1 missão |
| Configuração | `config/qa_settings_g5.py`; aponta banco e mídia exclusivamente para o diretório QA |
| Serviço | `gravewright-g5-qa.service`, systemd de usuário, habilitado e ativo; `linger=yes`; bind em `127.0.0.1:3001` |
| Export Godot | Servido pelo endpoint autenticado; SHA-256 de `index.html`: `8d8ecb91e3cf57957ca4fa1e2b593d5c152463cb5627ef9ee6431f7363711be1` |
| Contas | Mestre `owner` e jogador `participant`, autenticados; senhas recuperáveis em arquivo privado com modo `0600`, fora do repositório |
| Cena e missão | Cena `Knossos — G5.5 QA` e definição versionada `knossos-evacuation v1`; estado persistido `PREPARING` |

O SQLite do produto (`/home/tonyus-dev/Portifolio/gravewright/data/gravewright.sqlite3`) permaneceu fora da configuração e dos comandos de QA; seu timestamp observado permaneceu em 14/09/2026. Nenhum arquivo de produto ou código foi alterado.

## Gates executados

| Gate | Resultado | Evidência da execução |
|---|---|---|
| P1 — Inicialização | **PARTIAL** | Serviço HTTP `200`; migrações oficiais; duas contas autenticadas; ambos acessaram a cena e missão real. A missão continua `PREPARING`, pois o guard bloqueou a roster fixture. Ver `evidence/p1-identities.json`, `evidence/mission-ready.json` não foi produzido; bloqueio bruto em `evidence/fixture-gate-blocked.txt`. |
| P2 — Persistência | **PASS** | `chat.say` criou uma mensagem-probe descartável pelo WebSocket autenticado. Após `stop`/`start`, a mensagem voltou em `chat.history` e existe uma linha na tabela QA `gravewright_chat_message`. Ver `evidence/continuity-p2-p4.json`. |
| P3 — Continuidade operacional | **PASS** para a missão persistida em `PREPARING` | Os contextos e o processo Chromium foram encerrados. Dois novos clientes autenticaram-se, carregaram a mesma cena e obtiveram `GET /api/maps/<scene>/manifest = 200`; ambos receberam a mensagem persistida. Capturas `04` e `05`. Não significa missão pronta para combate. |
| P4 — Backup/restauração | **PASS** | Backup SQLite consistente; integridade `ok`; 73 migrations; hash SHA-256 do backup e da restauração secundária idênticos: `9396b36d6663ef594fbcaec48ed762c73887ec939b254b9d582c2ab3b7b8e0f6`. Restore ocorreu em `backups/restore-20261019T124548Z/`, sem substituir a instância principal. |
| P5 — Sobrevivência a reboot real | **UNVERIFIED** | Nenhum reboot foi executado. A unidade está habilitada e o user manager tem `linger=yes`; isso não substitui o teste pós-reboot. |

## Operação e recuperação

O controle persistente fica em:

`/home/tonyus-dev/.local/share/gravewright/playtest-g5/runtime/qa-control`

Use `start`, `stop`, `restart`, `status`, `logs`, `backup` ou `restore <arquivo-de-backup>`. O restore sempre cria uma cópia secundária isolada em `backups/restore-<timestamp>/`; não sobrescreve o banco ativo. Para recuperar acesso, consultar o arquivo privado `config/credentials.private.json` no host QA e autenticar pelas telas usuais `/login` e `/register`. Ele está fora do checkout e com permissão `0600`; não copiar credenciais para relatórios.

Para uma verificação pós-reboot autorizada, executar `qa-control status`, conferir `systemctl --user is-active gravewright-g5-qa.service`, `qa_db_tool.py check ...`, autenticar as duas contas e reabrir a URL local da campanha. O sistema não foi reiniciado nesta missão.

## Capturas e limitações

Índice: `/home/tonyus-dev/.local/share/gravewright/playtest-g5/evidence/SCREENSHOTS_INDEX.md`  
Capturas originais: `/home/tonyus-dev/.local/share/gravewright/playtest-g5/evidence/screenshots/`  
Manifesto de dimensões e hashes: `evidence/screenshots-manifest.json`.

As capturas pós-reinício mostram o tabuleiro real renderizado no cliente Mestre e no cliente jogador, com missão `PREPARING`. A interface do Mestre apresenta sobreposição de controles e rótulos nessa resolução. Isso é observação visual; não foi corrigido nesta missão. As capturas iniciais dos dois clientes mostram a tela sem mapa ativo e não são usadas como prova de missão funcional.

## Conclusão e próxima ação

**A persistência operacional do QA está recuperada:** serviço de usuário reproduzível, duas contas recuperáveis, persistência após reinício do backend e backup/restauração validados. **O ambiente ainda não está pronto para convidados de playtest**, pois não há participantes na missão e ela não alcançou `READY`.

Próxima ação única: ajustar, em missão separada e autorizada, a guarda de fixtures para aceitar uma raiz QA persistente do usuário com os mesmos requisitos de isolamento; então repetir somente a criação dos sete participantes e a transição da missão para `READY`. Alternativa válida: fornecer um fluxo oficial de roster canônico que não dependa das fixtures. Não repetir P2–P4 sem alteração relevante e não iniciar combate antes de comprovar `READY`.

**Escopo de mudança:** somente este relatório foi criado no repositório; nenhum arquivo de produto foi alterado. Nenhum commit ou push foi feito. Nenhum reboot, deploy ou acesso à produção ocorreu.

---

## Atualização G5.5 — correção do guard e preparação da missão

**Execução:** 19 de outubro de 2026, UTC 13:17–13:21  
**Branch / HEAD:** `feat/tactics-godot-transport-20261014` / `b4d737bbbc66e608f5743853a8915dce5bac912e` (inalterados)  
**Resultado:** `PARTIAL` — guard corrigido; missão `READY` e persistente; visualização do jogador não comprovou o roster no tabuleiro.

### Causa e correção

O guard em `gravewright/actors/provenance.py` aceitava somente raiz de fixtures sob `/tmp`. A configuração G5.5 já apontava banco, banco de testes e mídia para a raiz persistente autorizada, mas a condição fixa do guard recusava essa raiz com `qa_fixtures_disabled`. A configuração sozinha não podia resolver a incompatibilidade.

A alteração mantém uma lista fechada de layouts: a raiz G5.5 autorizada e a raiz legada G5.3 em `/tmp`. Para a raiz persistente, banco ativo, banco de testes e mídia precisam corresponder aos caminhos exatos dentro dela. O guard valida caminhos absolutos canônicos, recusa componentes com symlink ou `..`, exige SQLite, `DEBUG` local, hosts de loopback e integrações externas desativadas. Não há autorização para raízes persistentes arbitrárias.

Arquivos alterados nesta execução:

- `gravewright/actors/provenance.py` — allowlist de raiz/layout e validação segura dos caminhos.
- `gravewright/actors/tests_provenance.py` — oito casos de fronteira do guard, positivos e negativos.
- `docs/GRAVEWRIGHT_G5_5_QA_PERSISTENTE.md` — este adendo ao histórico existente.

O teste oficial existente também confirmou que as sete fixtures são criadas como registros não canônicos e que a operação é idempotente. O teste focado final executou 12 casos e terminou `OK`. Uma primeira execução apontou um caminho de banco de teste legado incorreto no novo caso de teste; o próprio caso foi corrigido e a suíte passou na repetição. Não houve alteração de regras ou da cena Godot.

Comando final: `DJANGO_SETTINGS_MODULE=qa_settings_g5 PYTHONPATH=<config QA>:<checkout> <venv>/bin/python manage.py test gravewright.actors.tests_provenance --noinput`. Saída final: `Ran 12 tests`; `OK`; `System check identified no issues (0 silenced)`.

### Ambiente e roster

Antes das fixtures, o serviço persistente estava ativo em `127.0.0.1:3001`, a configuração carregada era `qa_settings_g5`, as integrações externas estavam vazias, e o backup do SQLite QA passou `integrity=ok` com 73 migrations, dois usuários e uma missão. Foi criado backup atualizado antes do reinício pós-READY: `backups/gravewright-g5-20261019T131954Z.sqlite3`, SHA-256 `f3a561bd5ee7c8b312f995157bc2cdeb5fb091ef592ac076a2cf671f020181c6`.

Usando o Mestre autenticado no cliente Godot Web, a roster foi criada pela API/WebSocket oficial, reutilizando a campanha, cena e missão existentes. As operações `actor.qa_fixture.create`, `tokens.command` e `mission.participant.add` receberam ACKs; `mission.ready` passou pela validação oficial e retornou `READY`, versão 9, sete participantes. Distribuição persistida: 3 `ALLY`, 3 `HOSTILE` Silmari e 1 `EVACUEE` Nomos. Os três aliados têm permissão `owner` para o usuário jogador; as quatro entidades de cenário não concedem esse controle. Todos os sete tokens apontam para a cena e para o ator correspondente.

`encounter.active=0`, rodada 0 e turno 0. **Iniciativa e combate não foram iniciados.** A missão continua sendo `knossos-evacuation v1`, proposta de QA não canônica.

### Acesso, reinício e limitação visual

Mestre e jogador autenticaram-se com HTTP 200 e abriram a rota do export Godot, com canvas presente e conexão WebSocket. Após o reinício controlado do backend, ambos autenticaram-se novamente e reabriram a mesma missão. Cada cliente recebeu `READY`, os sete participantes e os sete tokens; a projeção do jogador retornou sete tokens visíveis e `canControl=true` para exatamente os três aliados. O SQLite persistente continuou íntegro após o reinício.

Na inspeção das capturas reais do Chromium executando o export, o cliente Mestre mostra as sete unidades no tabuleiro e o estado `READY`. A captura do jogador mostra apenas parte do tabuleiro, deslocada para fora do enquadramento, sem os sete marcadores visíveis. A leitura autenticada do servidor confirma os tokens e permissões do jogador; isso não substitui a prova de renderização no cliente. Portanto, o acesso de dados do jogador passou, mas a comprovação visual do tabuleiro do jogador ficou `PARTIAL` e impede o `PASS` integral do G5.5. A sobreposição de HUD previamente aceita permanece visível; não foi corrigida.

Índice das quatro capturas atuais: `evidence/g5.5-ready-20261019-run01/SCREENSHOTS_INDEX.md`. Diretório absoluto: `/home/tonyus-dev/.local/share/gravewright/playtest-g5/evidence/g5.5-ready-20261019-run01/screenshots/`. Resolução original: 1280×800. Capturas e evidências JSON são da execução atual; não foram reutilizadas capturas históricas nem alterados pixels.

| Gate | Resultado | Evidência bruta |
|---|---|---|
| Guard persistente e rejeições de caminhos não autorizados | **PASS** | Saída da suíte focada: 12 testes `OK`; `tests_provenance.py` |
| Fixture oficial e roster 3/3/1 | **PASS** | `provisioning-evidence.json`; ACKs de WebSocket e estado persistido |
| Missão `READY` sem combate | **PASS** | `mission_ready_ack` em `provisioning-evidence.json`; SQLite após reinício |
| Login e dados após reinício — Mestre e jogador | **PASS** | `after-restart-evidence.json`; HTTP 200, WebSocket, 7 tokens em cada papel |
| Renderização visual da roster — Mestre | **PASS** | `01-gm-ready.png`, `03-roster.png`, `04-after-restart.png` |
| Renderização visual da roster — jogador | **PARTIAL** | `02-player-ready.png`: canvas aberto, tabuleiro incompleto/deslocado e marcadores não visíveis |

### Primeira pendência e continuidade

`FIRST_BLOCKER=PLAYER_GODOT_TABULEIRO_NAO_MOSTRA_VISUALMENTE_A_ROSTER`. A persistência, o estado do servidor e o controle de permissões sobreviveram ao reinício, mas a captura impede alegar que o jogador vê o mesmo tabuleiro funcional. Próxima ação única: investigar, em uma missão delimitada separada, o enquadramento/sincronização de cena do cliente jogador ao abrir a missão pronta e produzir captura visual válida. Não iniciar combate antes dessa confirmação; não ampliar para refatoração ou correção de CI.

O SQLite do produto permaneceu com 1.048.576 bytes e timestamp `2026-09-14 02:10:45 -0300`; nenhum comando de QA usou esse banco. Nenhum commit ou push foi criado. `HEAD` permaneceu inalterado.
