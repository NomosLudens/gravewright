# Gravewright — KALLISTIS ruleset implementation checkpoint

Source authority: `/home/tonyus-dev/Downloads/KALLISTIS_LIVRO_III_SISTEMA_INTEGRADO_MANIFESTACAO_FULGOR.md`

Source SHA-256: `599b018e70865a3105d8b65d5dfbe683b4acd595939f22503916a088cea69eaa`

Physical source lines: `3267` (the supplied gate text expected 3268 logical lines; the verified file hash is the authority).

Production was not used as a development target. All changes below are in the Mini worktree `rules/full-kallistis-canon-2026-09-18`, based on production SHA `6ed37aa334078668674978b311f3b09f20f94c97`.

## Authority boundary

| Rule ID | Domain | Responsibility | Implementation status |
|---|---|---|---|
| RES | universal resolution | Gravewright executes; KALLISTIS supplies character facts | one server-side Light/Dark 2d10 path, margin, grade, predominance, resonance and capped circumstances |
| RES-CRIT | resonance naming | Gravewright executes | equality is Ressonância, not a critical hit; payload/tests migrated |
| ACT | action economy | Gravewright executes | action, movement, reaction, round reset, run and terrain cost |
| RESOURCES | session resources | Gravewright executes | Vitality, Lucidity, Flow, Breath and Determination persisted in actor runtime JSON |
| CONDITIONS | temporary consequences | Gravewright executes | all ten Livro III conditions represented with duration/effect metadata |
| COMBAT | combat resolution | Gravewright executes | existing damage path delegates to canonical runtime damage application |
| TECH | techniques | Gravewright executes; KALLISTIS owns acquisition | generic execution contract with Marco, action and scene-frequency gates |
| MAGIC | ordinary/epic magic | Gravewright executes; KALLISTIS owns repertoire | grades G0–G6, costs, concentration and G7 rejection |
| EVO | evocations | Gravewright executes; KALLISTIS owns bond/form | minor, standard and major profiles, instability, cost and scene duration |
| MERGE | Merge | Gravewright executes; KALLISTIS owns identity facts | consent/mode boundary, cost, test, active state and two-benefit limit |
| CORO | collective resonance | Gravewright executes | shared pulses/bars, eligibility and role/level activation bounds |
| SHADOW | Sombra | Gravewright executes | bounded 0–6 state and state-name transitions |
| FISSURE | Fendas/travessias | Gravewright executes | state DC, destination/anchor/cost preconditions and 3-before-2 sequence |
| EQUIP | equipment | Gravewright executes; KALLISTIS owns acquisition | catalog constants, load and frequency primitives |
| ART | artifacts | Gravewright executes; KALLISTIS owns identity/bond | activation-frequency gate without duplicating ownership |
| FULGOR | Fulgor | Gravewright executes; KALLISTIS owns identity/Legado | 0–5, Fulgor Pleno and reset; visible in runtime dialog |
| PROG | progression | KALLISTIS authority read-only | Marco contract validator; M16 is history-only |
| MAP | map/token | existing Gravewright subsystem | orthogonal-grid motor preserved; rules movement primitive isolated |
| UI | session controls | Gravewright executes | actor dialog displays action economy, Coro, Sombra and Fulgor and invokes bounded commands |
| REALTIME | transport | Gravewright executes | existing authorized actor command/realtime channel reused |
| PERSIST | persistence | Gravewright executes | runtime state remains in actor JSON through the existing idempotent command path |

## Implementation files

- `gravewright/rules/kallistis_runtime.py`: framework-free runtime rule layer.
- `gravewright/actors/runtime.py`: persisted actor command integration.
- `gravewright/dice/kallistis.py`: resonance is no longer labelled a critical hit.
- `gravewright/combat/services.py`: damage delegates to the canonical runtime layer.
- `gravewright/actors/jinja2/gravewright_actors/workspace.html`: runtime rules surface.
- `gravewright/actors/static/gravewright_actors/workspace.js`: state display and bounded session commands.

## Baseline and validation

Baseline used the official Django runner:

```text
Found 345 test(s)
Ran 345 tests in 881.848s
FAILED (failures=1)
BASELINE_PASS=344
BASELINE_FAIL=1
```

The deterministic baseline failure was `gravewright.dice.tests.test_rolls.DiceTests.test_secret_roll_is_filtered_live_and_in_history`, a pre-existing realtime secret-roll/chat projection failure reproduced in a targeted run before code changes. It was not silently reclassified as a ruleset failure.

Post-change targeted evidence:

```text
gravewright.rules.tests.test_kallistis_runtime: 15 tests, OK
gravewright.dice.tests.test_kallistis + test_rolls: 29 tests, OK
gravewright.actors.tests_runtime + gravewright.combat.tests_gate03d: 14 tests, OK
```

Structural check: `PASS`.

Full suite after implementation:

```text
Found 360 test(s)
Ran 360 tests in 803.154s
FAILED (failures=2)
PASS=358
FAIL=2
```

The two failures are the pre-existing secret-roll/history socket failure and a presence cleanup failure in the full-suite ordering. The presence test passes when run in isolation; the secret-roll failure reproduces in isolation. Isolated runtime smoke: login page HTTP 200 on `127.0.0.1:3100`; authenticated table smoke was not claimed because no canonical account/campaign fixture was invented.

No production deploy, merge, push, service restart, migration or external-host mutation was performed.

## Previous checkpoint verdict

`PARTIAL_RULESET_IMPLEMENTATION`

The backend execution layer and persisted command surface are implemented and targeted-tested. A final `RULESET_FULL_IMPLEMENTATION_PASS` is not claimed until the entire suite, isolated runtime smoke and the remaining UI flows for every runtime contract are observed end-to-end. The pre-existing realtime failure remains an explicit blocker to a clean full-suite verdict.

## Gate 358/360 -> 360/360 closure

VERDICT=RULESET_TEST_CLOSURE_PASS_360_OF_360

PRODUCTION_HEAD=6ed37aa334078668674978b311f3b09f20f94c97
PRODUCTION_WORKTREE=CLEAN
PRODUCTION_SERVICE=active
PRODUCTION_LOGIN_HTTP=200

RULES_BRANCH=rules/full-kallistis-canon-2026-09-18
RULES_HEAD=6ed37aa334078668674978b311f3b09f20f94c97
RULES_WORKTREE_STATUS=DIRTY_EXPECTED_ISOLATED_CHANGES

FAILURE_1_TEST=gravewright.dice.tests.test_rolls.DiceTests.test_secret_roll_is_filtered_live_and_in_history
FAILURE_1_ROOT_CAUSE=The shared WebSocket fixture did not service heartbeat pongs for idle sockets; the idle participant expired before receiving the public marker. This was transport/fixture timing, not secret-data leakage: the persisted recipient audience and room_message authorization already filtered the secret roll.
FAILURE_1_FIX=The fixture now renews only previously observed peer sockets before waiting for an event, and session.pong is excluded from the command rate-limit bucket so the real browser heartbeat cannot consume command capacity.
FAILURE_1_STATUS=FIXED

FAILURE_2_TEST=gravewright.realtime.tests.test_sockets.SocketTests.test_presence_deduplicates_tabs_and_removes_last_connection
FAILURE_2_ROOT_CAUSE=Presence lease removal depended on a later disconnect callback; close paths could race with teardown and leave a PresenceConnection row behind.
FAILURE_2_FIX=TableConsumer now releases presence idempotently at close and disconnect, clears the connection id before awaiting database work, guards partial-handshake teardown, and avoids duplicate group publication.
FAILURE_2_STATUS=FIXED

FULL_SUITE_TOTAL=360
FULL_SUITE_PASS=360
FULL_SUITE_FAIL=0

DJANGO_CHECK=PASS
DIFF_CHECK=PASS
MIGRATION_CHECK=PASS
ISOLATED_LOGIN_HTTP=200

FILES_CHANGED_THIS_GATE=gravewright/realtime/consumers.py; gravewright/realtime/tests/test_sockets.py

TESTS_REMOVED=0
TESTS_SKIPPED_NEW=0
XFAIL_ADDED=0

PRODUCTION_CHANGED=NO
PUSH_EXECUTED=NO
MERGE_EXECUTED=NO
DEPLOY_EXECUTED=NO
PRODUCTION_RESTARTED=NO

STATE_CHANGED=YES_ISOLATED_RULES_WORKTREE_ONLY
NEXT_EXACT_ACTION=CONTROLLED_CONVERGENCE_OF_VALIDATED_RULESET_TO_AUTHORITATIVE_MASTER

The convergence action is intentionally not executed in this gate.
