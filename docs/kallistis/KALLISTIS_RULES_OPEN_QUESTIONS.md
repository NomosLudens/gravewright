# KALLISTIS — Open Questions

Questões derivadas de KALLISTIS_RULES_GUIDE.md. Este arquivo separa regra já definida, implementação ausente e decisão ainda necessária. Não cria regra nova.

## Q-01 — Efeito mecânico extra do crítico

STATUS=RULE_DEFINED_EXTRA_EFFECT_UNSPECIFIED

REF=Guia §6

Definido: quando light_die == dark_die, ocorre Ressonância e o resultado é crítico. A classificação crítica é Ressonância.

Não definido: qualquer efeito mecânico adicional além da Ressonância por valor.

Não implementar sem decisão autoral: dano dobrado, dano máximo, reroll, bônus, sucesso automático ou falha automática.

## Q-02 — Forma interna da face

STATUS=RULE_DEFINED_IMPLEMENTATION_UNSELECTED

REF=Guia §3 e §13

Definido: os glifos substituem visualmente 1 e 10, mantêm seus valores matemáticos e são invertidos entre os dois dados.

Em aberto: se o Gravewright usará objeto de face, token tipado ou outra representação equivalente. A escolha não pode perder numeric_value, glyph ou die.

## Q-03 — Efeitos mecânicos individuais de 1-1 a 10-10

STATUS=RULE_PARTIALLY_DEFINED

REF=Guia §6

Definido: cada igualdade possui valor, nome e abertura narrativa; Ressonância segue a regra geral de sucesso/falha.

Ausente no corpus: efeito numérico obrigatório específico para a maioria das dez Ressonâncias. Os exemplos são aberturas para a condução, não bônus automáticos.

Decisão necessária antes de automatizar: quais, se houver, efeitos devem ser campos executáveis em vez de texto narrativo.

## Q-04 — Fonte autoritativa de Atributo e Perícia

STATUS=RULE_DEFINED_IMPLEMENTATION_CLOSED_FOR_LINKED_ACTOR

REF=Guia §9, §13 e §14

Definido: o teste usa Atributo + Perícia e a ficha possui valores próprios.

Implementado e provado: quando actor_id existe, o Gravewright resolve os seis Atributos e as 15 Perícias no Actor.data.runtime após validar campanha e controle; valores numéricos do payload não são autoridade.

Contrato preservado: action sem actor ligado continua aceitando o caminho genérico explícito; action KALLISTIS vinculada a actor usa exclusivamente a ficha server-side.

## Q-05 — Registro formal do ruleset

STATUS=RULE_DEFINED_IMPLEMENTATION_OPTIONAL

REF=Guia §14 e §15

Definido: KALLISTIS possui sistema, atributos, perícias e procedimentos próprios.

Gap atual: a lógica KALLISTIS está hard-coded em dice/kallistis.py e combat.services, não registrada no catálogo de rulesets.

Decisão necessária: o produto precisa selecionar KALLISTIS como Campaign.system formal ou basta a integração nativa existente? Não criar Package/Module sem essa necessidade.

## Q-06 — Conteúdo canônico ainda não modelado

STATUS=RULE_DEFINED_IMPLEMENTATION_MISSING

REF=Guia §9, §11, §12 e §16

Há regras definidas, mas sem implementação auditada completa para personagem, magia, Tecelão, Evocação, Velarim, Merge, Coro, progressão e procedimentos completos de GM.

Esta é uma lacuna de implementação, não uma regra ausente. Cada domínio deve ser tratado em gate próprio, sem ampliar o escopo do núcleo de dados.
