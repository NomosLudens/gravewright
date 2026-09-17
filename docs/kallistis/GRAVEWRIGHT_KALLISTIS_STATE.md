# Gravewright × KALLISTIS — Estado Autoritativo

## Baseline

Host: kallistiswright
Repository: /home/nomosludens/gravewright
Branch: master
HEAD: 3e47700280c53a4f99e865b6d4f4a2e743acd000
Origin master: 3e47700280c53a4f99e865b6d4f4a2e743acd000
Worktree: CLEAN

## Runtime

gravewright.service: active
Redis: active
HTTP /: 200
HTTP /login: 200

## Test baseline

Official suite:
- total: 345
- passed: 345
- failed: 0
- errors: 0

## KALLISTIS rules implementation

### Completed

- CORE-01 — Dado da Luz
- CORE-02 — Dado da Escuridão
- CORE-03 — Glifos invertidos
- CORE-04 — Atributo + Perícia — matemática verificada
- CORE-05 — Dificuldade
- CORE-06 — Margem
- CORE-07 — Grau de resultado
- CORE-08 — Predominância
- CORE-09 — Intensidade da Predominância
- CORE-10 — Ressonâncias 1–10 — nomes e openings canônicos verificados
- CORE-11 — Classificação crítica por igualdade — critical/critical_type verificados
- CORE-12 — Impulso — escala, limites e cancelamento verificados
- CORE-13 — Pressão — escala, limites e cancelamento verificados
- CHARACTER-01 — Seis Atributos — runtime canônico verificado
- CHARACTER-02 — Perícias 0–5 — runtime canônico verificado
- CHARACTER-03 — Povo: Traço, Dom, Herança e Dissonância — contrato canônico recuperado e runtime verificado
- CHARACTER-07 — Autoridade server-side do actor — rolagem vinculada verificada
- RESOURCES-01..07 — recursos, reservas e Defesas — fórmulas, limites e persistência verificadas
- COMBAT-01..03 — ataques corpo a corpo, distância e magia — resolução server-side verificada

### Known blockers

Não há blocker de autoridade para Atributo/Perícia em rolagens KALLISTIS
vinculadas a Actor: Actor.data/runtime é a fonte server-side provada.
O contrato de Povo foi recuperado do Livro III e CHARACTER-03 foi fechado no runtime. Ofício, Origem e vínculos permanecem pendentes.
Iniciativa continua sem fórmula canônica automática e será tratada como ordem manual enquanto o GUIDE não definir fórmula. Dano completo,
ataque de área e procedimento de cena permanecem fora do núcleo fechado deste pacote.

### Pending
- CHARACTER-04..06 — ficha canônica ainda não modelada
- COMBAT-04..08 — empate contextual, dano completo, cobertura, área e procedimento de combate
- CONDITIONS-01..05 — condições, queda, morte e Sombra
- MAGIC-01..06 — magia
- WEAVER-01..03 — Tecelão
- EVOCATION-01..04 — Evocação
- VELARIM-01..05 — Velarim
- MERGE-01..05 — Merge
- RESONANCE_COLLECTIVE-01..07 — Ressonância Coletiva
- PROGRESSION-01..04 — progressão
- GM-01..06 — condução de Mestre
- UI-01..05 — exposição de regras na UI
- PERSISTENCE-01..04 — persistência completa
- REALTIME-01..04 — realtime completo

## Dice contract

Dado da Luz:

- 10 = Glifo da Luz
- 9..2 = números
- 1 = Glifo da Escuridão

Dado da Escuridão:

- 10 = Glifo da Escuridão
- 9..2 = números
- 1 = Glifo da Luz

Glyph identity != numeric value.

## Resolution contract

light_die + dark_die + attribute + skill + legitimate modifiers

margin = total - difficulty

Predominance:
- light > dark → Luz
- dark > light → Escuridão
- equality → Ressonância

## Resonance contract

light_die == dark_die
→ resonance=true
→ critical=true
→ critical_type=resonance

Critical extra mechanical effect remains UNSPECIFIED.

1-1 a 10-10 possuem Ressonâncias canônicas próprias; o resultado informa
nome e opening sem automatizar efeitos narrativos ou mecânicos.

## Persistence and realtime

- Message.roll persistence: PASS
- WebSocket broadcast: PASS
- CLIENT_A: PASS
- CLIENT_B: PASS

## Database

Production database changed by rules gates: NO
Fake runtime data created: NO

## Documentation authority

- docs/kallistis/KALLISTIS_RULES_GUIDE.md
- docs/kallistis/KALLISTIS_RULES_IMPLEMENTATION_CHECKLIST.md
- docs/kallistis/KALLISTIS_RULES_OPEN_QUESTIONS.md

## Last completed gate

Gate: D — CHARACTER-03 — Povo, Traço, Dom, Herança e Dissonância
Commit: 3e47700280c53a4f99e865b6d4f4a2e743acd000
Date: 2026-09-17T16:44:08+00:00
Verdict: PASS

## Next exact action

Executar o próximo gate autorizado para CHARACTER-04 — Ofício, Papel, Trilha e Chave.
