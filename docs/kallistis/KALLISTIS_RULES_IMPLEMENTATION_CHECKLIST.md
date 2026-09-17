# KALLISTIS — Rules Implementation Checklist

Checklist derivado exclusivamente de KALLISTIS_RULES_GUIDE.md e da auditoria do Gravewright realizada no Rules Adaptation Gate 01.

Status permitidos:

~~~
ALREADY_IMPLEMENTED  existe e atende ao contrato auditado
PARTIAL              existe parcialmente ou sem a autoridade/semântica completa
MISSING              não existe no Gravewright auditado
UNVERIFIED            não foi provado pela auditoria disponível
~~~

Nenhum item autoriza inventar regra. Todas as referências apontam para seções do guia canônico.

## CORE

- [ ] CORE-01 — Dado da Luz
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §3
  - EVIDENCE=light_die permanece numérico 1..10 e light_face identifica as faces 10/1 como Glifo da Luz/Glifo da Escuridão.
- [ ] CORE-02 — Dado da Escuridão
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §3
  - EVIDENCE=dark_die permanece numérico 1..10 e dark_face identifica as faces 10/1 como Glifo da Escuridão/Glifo da Luz.
- [ ] CORE-03 — Glifos invertidos
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §3
  - EVIDENCE=metadata de face preserva a identidade do glifo por dado, sem derivar valor globalmente; UI renderiza a identidade textual quando aplicável.
- [ ] CORE-04 — Atributo + Perícia
  - STATUS=PARTIAL
  - REF=Guia §4 e §9
  - EVIDENCE=prepare_action calcula base_modifier como atributo + perícia e o teste determinístico cobre a fórmula; autoridade server-side do actor permanece BLOCKED_BY_CHARACTER_CONTRACT porque Actor.data.runtime não possui contrato canônico completo de perícias.
- [ ] CORE-05 — Dificuldade
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §4
  - EVIDENCE=validação aceita dificuldade numérica e DIFFICULTY_PRESETS cobre 10, 12, 15, 18, 21, 24, 27 e 30; valor customizado acima de 30 também é coberto deterministicamente.
- [ ] CORE-06 — Margem
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §4
  - EVIDENCE=margem é total - dificuldade, sem arredondamento, com boundaries -6, -5, -4, -1, 0, 4, 5, 9, 10 e 11 cobertos deterministicamente.
- [ ] CORE-07 — Grau de resultado
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §4
  - EVIDENCE=faixa de grau e grade são verificadas nos cinco intervalos canônicos, incluindo todos os boundaries do guia; success permanece margin >= 0.
- [ ] CORE-08 — Predominância
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §5
  - EVIDENCE=predominância compara exclusivamente light_die e dark_die; casos Luz, Escuridão e igualdade estão cobertos deterministicamente.
- [ ] CORE-09 — Intensidade da Predominância
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §5
  - EVIDENCE=predominance_delta e faixas 0, 1–2, 3–5, 6–8 e 9 estão cobertos em todos os boundaries, incluindo interação numérica dos glifos.
- [ ] CORE-10 — Ressonâncias 1–10
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §6
  - EVIDENCE=valores 1–10 possuem nomes e openings canônicos; o resultado informa a abertura sem automatizar os efeitos narrativos ou mecânicos ainda UNSPECIFIED.
- [ ] CORE-11 — Classificação crítica por igualdade
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §6
  - EVIDENCE=igualdade de light_die e dark_die registra critical=true e critical_type=resonance; não igualdade registra false/null, sem sucesso/falha automático ou efeito extra.
- [ ] CORE-12 — Impulso
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §8
  - EVIDENCE=prepare_action valida o nível contextual 0..2, aplica +2 por ponto, limita o bônus normal a +4 e preserva o valor auditável no JSON da action; a matriz 0/0, 1/0, 2/0, 0/1, 0/2, 1/1, 2/1, 1/2 e 2/2 é determinística. SOURCE=VALIDATED_CLIENT_INPUT; Impulso é contexto da ação, não valor de ficha.
- [ ] CORE-13 — Pressão
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §8
  - EVIDENCE=prepare_action valida o nível contextual 0..2, aplica -2 por ponto, limita a penalidade normal a -4 e preserva o valor auditável no JSON da action; a matriz determinística cobre cancelamento com Impulso e os limites normais. SOURCE=VALIDATED_CLIENT_INPUT; Pressão é contexto da ação, não valor de ficha.

## CHARACTER

- [ ] CHARACTER-01 — Seis Atributos
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §9
  - EVIDENCE=Actor.data.runtime persiste e projeta Corpo, Agilidade, Intelecto, Presença, Vontade e Sintonia; os seis identificadores e valores canônicos foram verificados após reload.
- [ ] CHARACTER-02 — Perícias 0–5
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §9
  - EVIDENCE=Actor.data.runtime persiste as 15 Perícias canônicas com validação server-side de 0 a 5; todos os identificadores, zero e máximo 5 foram cobertos.
- [ ] CHARACTER-03 — Povo: Traço, Dom, Herança e Dissonância
  - STATUS=MISSING
  - REF=Guia §9 e §16
  - EVIDENCE=não há contrato canônico KALLISTIS equivalente no actor runtime.
- [ ] CHARACTER-04 — Ofício, Papel, Trilha e Chave
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=não há implementação KALLISTIS comprovada.
- [ ] CHARACTER-05 — Origem cosmológica
  - STATUS=MISSING
  - REF=Guia §2 e §9
  - EVIDENCE=Criado na Luz, Escuridão, Trocado e Outro não são campos canônicos do actor atual.
- [ ] CHARACTER-06 — Vínculos, Promessa, Ferida e Pergunta
  - STATUS=MISSING
  - REF=Guia §9
  - EVIDENCE=não há modelo/runtime auditado para esses elementos.
- [ ] CHARACTER-07 — Autoridade server-side do actor
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §13 e §14
  - EVIDENCE=quando actor_id está vinculado, dice roll e combate substituem valores numéricos do cliente pelos valores do Actor após validação de campanha e controle; payload 999/999, actor inexistente, outra campanha e actor read-only foram rejeitados ou neutralizados.

## RESOURCES

- [ ] RESOURCES-01 — Vitalidade
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §9
  - EVIDENCE=max=10+Corpo×3, current separado e limitado a 0..max; gasto, dano, recuperação, persistência e reload foram verificados.
- [ ] RESOURCES-02 — Lucidez
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §9
  - EVIDENCE=max=8+Vontade×3, current separado e limitado a 0..max; transição a zero preserva somente o marcador documentado para resolução posterior.
- [ ] RESOURCES-03 — Fluxo
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §9
  - EVIDENCE=max=3+Sintonia+ceil(Marco/2), current separado e limitado a 0..max; alteração de derivação não redefine current e Fraturado bloqueia Pausa Segura conforme runtime existente.
- [ ] RESOURCES-04 — Guarda
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §9
  - EVIDENCE=combat.services.defenses resolve server-side Guarda=10+Agilidade+Proteção; fórmula e valor foram verificados com Actor runtime.
- [ ] RESOURCES-05 — Fortitude
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §9
  - EVIDENCE=combat.services.defenses resolve server-side Fortitude=10+Corpo+Vontade; fórmula foi verificada com Actor runtime.
- [ ] RESOURCES-06 — Integridade
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §9
  - EVIDENCE=combat.services.defenses resolve server-side Integridade=10+Vontade+Sintonia; fórmula foi verificada com Actor runtime.
- [ ] RESOURCES-07 — Fôlego e Determinação
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §9
  - EVIDENCE=Fôlego max=3 e retorna na Pausa Segura; Determinação inicia em 1, teto normal 3 e é consumida uma vez no reroll persistido, sem alterar dados naturais de forma indevida.

## COMBAT

- [ ] COMBAT-01 — Ataque corpo a corpo
  - STATUS=PARTIAL
  - REF=Guia §10
  - EVIDENCE=combat resolve ação KALLISTIS, mas o contrato integral de ficha/defesa não está fechado.
- [ ] COMBAT-02 — Ataque à distância
  - STATUS=PARTIAL
  - REF=Guia §10
  - EVIDENCE=estrutura de combate existe; cobertura completa não foi provada.
- [ ] COMBAT-03 — Ataque mágico contra Defesa
  - STATUS=MISSING
  - REF=Guia §10 e §16
  - EVIDENCE=DSL genérico não equivale à magia KALLISTIS.
- [ ] COMBAT-04 — Testes opostos
  - STATUS=PARTIAL
  - REF=Guia §10
  - EVIDENCE=opposed dice existe; empate e resolução completa precisam de reconciliação.
- [ ] COMBAT-05 — Dano, margem e potência
  - STATUS=PARTIAL
  - REF=Guia §10
  - EVIDENCE=combat possui dano; regras completas de potência/margem não estão centralizadas.
- [ ] COMBAT-06 — Grade, zonas, Movimento e cobertura
  - STATUS=PARTIAL
  - REF=Guia §9 e §10
  - EVIDENCE=mapa/tokens existem; contrato mecânico completo não foi provado.
- [ ] COMBAT-07 — Ataque de área: uma rolagem, Defesas separadas
  - STATUS=MISSING
  - REF=Guia §10
  - EVIDENCE=não há prova de implementação desta regra KALLISTIS.
- [ ] COMBAT-08 — Objetivo de cena, fases e ação anunciada
  - STATUS=MISSING
  - REF=Guia §10 e §16
  - EVIDENCE=procedimento de condução não está representado como runtime canônico.

## CONDITIONS

- [ ] CONDITIONS-01 — Abalado, Exposto, Lento e Sangrando
  - STATUS=PARTIAL
  - REF=Guia §10
  - EVIDENCE=conditions runtime existe; cobertura e duração canônicas são incompletas.
- [ ] CONDITIONS-02 — Dissonante, Fraturado e Corrompido
  - STATUS=PARTIAL
  - REF=Guia §10
  - EVIDENCE=modificadores de condição existem; semântica completa não está fechada.
- [ ] CONDITIONS-03 — Caído e Teste de Permanência
  - STATUS=PARTIAL
  - REF=Guia §10
  - EVIDENCE=estado de queda existe; procedimento completo não foi provado.
- [ ] CONDITIONS-04 — Ferimento Grave e dano excedente
  - STATUS=MISSING
  - REF=Guia §10
  - EVIDENCE=não há contrato KALLISTIS equivalente auditado.
- [ ] CONDITIONS-05 — Morte, Lucidez zero e Sombra
  - STATUS=PARTIAL
  - REF=Guia §10 e §2
  - EVIDENCE=alguns estados existem; consequências canônicas completas não estão implementadas.

## MAGIC

- [ ] MAGIC-01 — Estrutura Nome/Tradição/Grau/Ação/Alvo
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=não há schema KALLISTIS de magia auditado.
- [ ] MAGIC-02 — Graus 0–3 e acesso por Marco
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=DSL de fórmula não representa esse contrato.
- [ ] MAGIC-03 — Magias conhecidas e limite de Sintonia
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=não há repertório canônico auditado.
- [ ] MAGIC-04 — Custo, Fluxo, concentração e consequência
  - STATUS=MISSING
  - REF=Guia §9 e §16
  - EVIDENCE=integração KALLISTIS não foi provada.
- [ ] MAGIC-05 — Teste mágico
  - STATUS=PARTIAL
  - REF=Guia §10 e §16
  - EVIDENCE=generic formula path existe, mas não carrega o contrato KALLISTIS.
- [ ] MAGIC-06 — Área, resistência e dano mágico
  - STATUS=PARTIAL
  - REF=Guia §10 e §16
  - EVIDENCE=há componentes genéricos; semântica KALLISTIS completa não está centralizada.

## WEAVER

- [ ] WEAVER-01 — Tradições, Formas e Grau do Tecelão
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=não há runtime KALLISTIS específico.
- [ ] WEAVER-02 — Forma Estável, Chaves e progressão de repertório
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=não há modelo auditado.
- [ ] WEAVER-03 — Limites de Velarim e Magia do Tecelão
  - STATUS=MISSING
  - REF=Guia §12 e §16
  - EVIDENCE=não há implementação comprovada.

## EVOCATION

- [ ] EVOCATION-01 — Âncora, Forma, Impulso e Pacto
  - STATUS=MISSING
  - REF=Guia §12 e §16
  - EVIDENCE=não há contrato KALLISTIS de vínculo persistido.
- [ ] EVOCATION-02 — Portes Menor, Padrão, Maior e Instável
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=não há runtime específico auditado.
- [ ] EVOCATION-03 — Convocar, manter e comandar
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=não há pipeline KALLISTIS comprovado.
- [ ] EVOCATION-04 — Consciência e recusa compatível com Pacto
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=não há representação auditada.

## VELARIM

- [ ] VELARIM-01 — Catálogo autorizado de Silmain com 76 glifos
  - STATUS=MISSING
  - REF=Guia §12
  - EVIDENCE=o catálogo editorial não está integrado ao Gravewright.
- [ ] VELARIM-02 — Analisar
  - STATUS=MISSING
  - REF=Guia §12
  - EVIDENCE=não há comando/resultado específico auditado.
- [ ] VELARIM-03 — Pronunciar
  - STATUS=MISSING
  - REF=Guia §12
  - EVIDENCE=não há comando/resultado específico auditado.
- [ ] VELARIM-04 — Inscrever
  - STATUS=MISSING
  - REF=Guia §12
  - EVIDENCE=não há comando/resultado específico auditado.
- [ ] VELARIM-05 — Traduzir com alternativas e certeza
  - STATUS=MISSING
  - REF=Guia §12
  - EVIDENCE=não há modelo de proveniência linguística auditado.

## MERGE

- [ ] MERGE-01 — Consentimento, limites, duração e saída
  - STATUS=MISSING
  - REF=Guia §12
  - EVIDENCE=não há fluxo KALLISTIS de consentimento.
- [ ] MERGE-02 — Âncora e custo de 1 Fluxo por participante
  - STATUS=MISSING
  - REF=Guia §12
  - EVIDENCE=não há procedimento persistido.
- [ ] MERGE-03 — Teste contra Dificuldade 15
  - STATUS=MISSING
  - REF=Guia §12
  - EVIDENCE=não há entrypoint específico.
- [ ] MERGE-04 — Dois benefícios em sucesso
  - STATUS=MISSING
  - REF=Guia §12
  - EVIDENCE=não há resolução específica.
- [ ] MERGE-05 — Fusão forçada e Merge corrompido como violência
  - STATUS=MISSING
  - REF=Guia §12
  - EVIDENCE=não há estado/efeito específico auditado.

## RESONANCE_COLLECTIVE

- [ ] RESONANCE_COLLECTIVE-01 — Medidor compartilhado de Pulsos e Barras
  - STATUS=MISSING
  - REF=Guia §11
  - EVIDENCE=combat reage narrativamente ao Coro, mas não há medidor canônico.
- [ ] RESONANCE_COLLECTIVE-02 — Limites por tamanho do grupo
  - STATUS=MISSING
  - REF=Guia §11
  - EVIDENCE=não há estado persistido auditado.
- [ ] RESONANCE_COLLECTIVE-03 — Geração de no máximo 1 Pulso por personagem/rodada
  - STATUS=MISSING
  - REF=Guia §11
  - EVIDENCE=não há regra executável auditada.
- [ ] RESONANCE_COLLECTIVE-04 — Ativação Nível I/II/III
  - STATUS=MISSING
  - REF=Guia §11
  - EVIDENCE=não há comando específico auditado.
- [ ] RESONANCE_COLLECTIVE-05 — Papéis Vanguarda, Artilharia, Amparo e Bastião
  - STATUS=MISSING
  - REF=Guia §11
  - EVIDENCE=não há contrato de Papel do actor.
- [ ] RESONANCE_COLLECTIVE-06 — Uma ativação por rodada
  - STATUS=MISSING
  - REF=Guia §11
  - EVIDENCE=não há enforcement auditado.
- [ ] RESONANCE_COLLECTIVE-07 — Persistência entre cenas e reset
  - STATUS=MISSING
  - REF=Guia §11
  - EVIDENCE=não há modelo de Coro auditado.

## PROGRESSION

- [ ] PROGRESSION-01 — Marcos 1–10
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=não há progressão KALLISTIS comprovada.
- [ ] PROGRESSION-02 — Ganhos por Marco e limites de Atributo
  - STATUS=MISSING
  - REF=Guia §9 e §16
  - EVIDENCE=não há regra de progressão no actor runtime.
- [ ] PROGRESSION-03 — Legado e Marcos 11–15
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=não há camada épica auditada.
- [ ] PROGRESSION-04 — M16 histórico e não jogável
  - STATUS=UNVERIFIED
  - REF=Guia §16
  - EVIDENCE=não houve prova de modelagem desse limite no produto.

## GM

- [ ] GM-01 — Objetivo, oposição, risco e consequência de cena
  - STATUS=UNVERIFIED
  - REF=Guia §4 e §16
  - EVIDENCE=há documentação de condução, mas não foi provado runtime de GM.
- [ ] GM-02 — Testes prolongados e relógios
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=não há serviço KALLISTIS auditado.
- [ ] GM-03 — Bloco de adversário com Ofensiva +X
  - STATUS=PARTIAL
  - REF=Guia §10 e §16
  - EVIDENCE=combat possui adversários; contrato completo de bestiário não está integrado.
- [ ] GM-04 — Moral, rendição e fuga
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=não há procedimento específico auditado.
- [ ] GM-05 — Técnicas anunciadas e fases de chefe
  - STATUS=MISSING
  - REF=Guia §16
  - EVIDENCE=não há runtime específico.
- [ ] GM-06 — Consequência persistente pós-conflito
  - STATUS=UNVERIFIED
  - REF=Guia §16
  - EVIDENCE=Message e dados existem, mas o fluxo canônico de consequência não foi provado.

## UI

- [ ] UI-01 — Tray com seleção KALLISTIS
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §13
  - EVIDENCE=tray força 2d10 e envia modo/action/opposed.
- [ ] UI-02 — Exibir Luz e Escuridão separadamente
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §3 e §7
  - EVIDENCE=template exibe ambos os valores e leituras.
- [ ] UI-03 — Exibir glifos e valores matemáticos
  - STATUS=PARTIAL
  - REF=Guia §3 e §13
  - EVIDENCE=template exibe a identidade textual do glifo junto do valor matemático; assets visuais reais permanecem indisponíveis.
- [ ] UI-04 — Exibir classificação crítica sem sucesso automático
  - STATUS=MISSING
  - REF=Guia §6 e §13
  - EVIDENCE=não há campo critical nem apresentação correspondente.
- [ ] UI-05 — Exibir Ressonância por valor e abertura
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §6 e §7
  - EVIDENCE=template exibe nome, valor e abertura quando presentes.

## PERSISTENCE

- [ ] PERSISTENCE-01 — Reserva antes da aleatoriedade
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §13
  - EVIDENCE=Submission é criada antes da avaliação.
- [ ] PERSISTENCE-02 — Resultado JSON em Message.roll
  - STATUS=PARTIAL
  - REF=Guia §13 e §14
  - EVIDENCE=Message.roll continua sendo JSON e absorve light_face/dark_face; prova de produto ficou bloqueada pelo handshake realtime.
- [ ] PERSISTENCE-03 — Idempotência por request_id
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §13
  - EVIDENCE=Submission e Message protegem retries/replays.
- [ ] PERSISTENCE-04 — Resultado secreto e Recipient
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §13
  - EVIDENCE=Recipient define audiência de roll GM.

## REALTIME

- [ ] REALTIME-01 — WebSocket de tabela autenticado
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §13
  - EVIDENCE=TableConsumer revalida sessão e membership.
- [ ] REALTIME-02 — Avaliação server-side
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §13 e §14
  - EVIDENCE=engine KALLISTIS é executado no servidor.
- [ ] REALTIME-03 — Broadcast pós-commit
  - STATUS=ALREADY_IMPLEMENTED
  - REF=Guia §13
  - EVIDENCE=dispatch usa transaction.on_commit.
- [ ] REALTIME-04 — Transmitir glifo e critical sem perda de dados
  - STATUS=PARTIAL
  - REF=Guia §3, §6 e §13
  - EVIDENCE=o pipeline reutiliza o JSON do resultado para light_face/dark_face; teste de transporte ficou bloqueado pelo handshake realtime.

## Ordem sugerida de execução

1. CORE-01 a CORE-03 e UI-03: representação dos dois dados e glifos.
2. CORE-10 e CORE-11: Ressonância por valor e classificação crítica.
3. PERSISTENCE-02 e REALTIME-04: preservar/transmitir os novos campos.
4. CHARACTER-01, CHARACTER-02 e CHARACTER-07: autoridade do actor.
5. Os demais domínios somente após contrato funcional específico e sem duplicar o pipeline de dice.
