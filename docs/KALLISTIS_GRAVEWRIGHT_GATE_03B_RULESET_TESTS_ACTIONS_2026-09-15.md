# Gate 03B — Testes e ações KALLISTIS

Data: 2026-09-15
Ambiente: Baby, `/srv/gravewright/app`
Campanha: `GATE 02 QA CAMPAIGN` (`c143d6c3-c0eb-41f9-bcc6-147d3e3ce176`)

## Resultado

```text
GATE_03B=PASS
SERVER_ACTION=PASS
ACTION_INPUTS_PERSISTED=PASS
CIRCUMSTANCE_NET_ZERO=PASS
OPPOSED_SERVER=PASS
OPPOSED_PERSISTED=PASS
OPPOSED_REAL_SUBMISSIONS=2
OPPOSED_TEST_ID_STABLE=YES
CLIENT_A_RECEIVED=PASS
CLIENT_B_RECEIVED=PASS
REFRESH_REQUIRED=NO
QA_CLEANUP=PASS
SOURCE_CHANGED_DURING_FINAL_PROOF=NO
NEXT_EXACT_ACTION=GATE_03C_RESOURCES_AND_CONDITIONS
```

## Prova de ação

Os dois clientes autenticados permaneceram simultaneamente na mesma campanha, com `Participants: 2`.

```text
ACTION_LABEL=Examinar inscrição Gate 03B
ATTRIBUTE=Intelecto 3
SKILL=Conhecimento 2
BASE_MODIFIER=5
IMPULSE=1 / +2 / Pista relevante
PRESSURE=1 / -2 / Tempo limitado
HELPERS=0
CIRCUMSTANCE_MODIFIER=0
SERVER_TOTAL_MODIFIER=5
LIGHT=9
DARK=3
NATURAL_TOTAL=12
TOTAL=17
DIFFICULTY=15
MARGIN=+2
GRADE=success
PREDOMINANCE=light
RESONANCE=false
CLIENT_A_AND_B_VALUES_IDENTICAL=YES
RECEIVED_WITHOUT_REFRESH=YES
```

O registro persistido confirmou os mesmos campos de entrada e o mesmo resultado calculado pelo servidor. A submissão foi idempotente e identificada por `71723abc-25ed-474b-b87f-91ff7a179b62` durante a prova.

## Prova opposed

Uma única submissão do fluxo real criou duas submissões KALLISTIS reais, uma para cada lado. Os dois clientes receberam as duas mensagens sem refresh.

```text
OPPOSED_TEST_ID=e4a311ed-5442-5f87-8dcc-70b296120200
SIDE_A_SUBMISSION=4ef12f1a-051c-4178-8f23-70d29af9f342
SIDE_B_SUBMISSION=e9677802-7369-55aa-8f0a-8250395c44e2
SIDE_A_TOTAL=10
SIDE_B_TOTAL=16
RESOLUTION=SIDE_B_WINS
TIE_POLICY=TIE_REQUIRES_CONTEXT
CLIENT_A_RECEIVED_BOTH=PASS
CLIENT_B_RECEIVED_BOTH=PASS
```

## Validação automática

```text
MANAGE_CHECK=PASS
TARGETED_TESTS=22 passed
FULL_TEST_SUITE=320 passed
TRAY_JS_SYNTAX=PASS
```

## Limpeza

Foram removidos somente os três `Message` e os três `Submission` criados nesta prova: ação `31` e opposed `32–33`. A verificação final confirmou zero remanescentes para esses IDs. Nenhuma conta QA foi criada ou removida, e nenhuma senha foi registrada neste relatório.

## Encerramento

```text
GATE_03B=PASS
NEXT_EXACT_ACTION=GATE_03C_RESOURCES_AND_CONDITIONS
```
