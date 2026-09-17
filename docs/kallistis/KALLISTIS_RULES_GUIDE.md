# KALLISTIS — Guia Mecânico Canônico para o Gravewright

Status: referência de desenvolvimento. Este documento não é uma implementação das regras.

## 1. Proveniência e precedência

Fonte analisada nesta sessão:

~~~
KALLISTIS_livros_editor_oral.zip
SHA-256: 197ed07cd3daf19d0aa76822d24105f7ae8a26151501b00f7e24438db47cb5b2
~~~

Arquivos lidos integralmente:

~~~
livros/00_ABERTURA.md
livros/01_LIVRO_I_HISTORIA.md
livros/02_LIVRO_II_ATLAS.md
livros/03_LIVRO_III_SISTEMA.md
livros/04_LIVRO_IV_NARRANDO_O_JOGO.md
livros/05_APENDICES.md
~~~

Para mecânicas, 03_LIVRO_III_SISTEMA.md tem precedência. O Livro IV acrescenta condução, bestiário e encontros; os demais livros fixam cosmologia e terminologia. A regra adicional dos glifos, na seção 3, foi declarada diretamente pelo autor e é canônica mesmo quando não aparece nos livros.

Campos não definidos pelo corpus são UNSPECIFIED. Interpretação narrativa não vira bônus, dano ou sucesso automático sem regra explícita.

## 2. Vocabulário operacional

| Termo | Significado |
|---|---|
| Luz / manesh | manifestação, forma, presença e ordem cosmológicas |
| Escuridão / thuvel | profundidade, silêncio, memória, repouso e potencial |
| Sombra / kav | assimilação, falsificação e apagamento da diferença |
| Ressonância | igualdade dos dois dados naturais; também há Ressonância Coletiva e Ressonância em Merge |
| Predominância | qual dos dois dados naturais foi maior |
| Coro | nome de mesa da Ressonância Coletiva; recurso compartilhado |
| Mirveth | contraparte cosmológica integral, não metade ou propriedade |
| Vethari | Merge legítimo com identidade, autonomia e consentimento |
| Fenda | ruptura intermundos que reage a condições, linguagem e relações |
| Velarim | língua relacional herdada da realidade anterior à Fratura |
| Silmain | escrita nativa de Velarim; catálogo vigente com 76 glifos |

Ressonância dos dados, Coro e Merge são mecanismos distintos.

## 3. Dados e glifos

KALLISTIS usa dois d10 distintos. Cada dado possui os dois glifos, mas a posição é invertida.

### Dado da Luz

| Valor matemático | Face visual |
|---:|---|
| 10 | Glifo da Luz |
| 9 | 9 |
| 8 | 8 |
| 7 | 7 |
| 6 | 6 |
| 5 | 5 |
| 4 | 4 |
| 3 | 3 |
| 2 | 2 |
| 1 | Glifo da Escuridão |

### Dado da Escuridão

| Valor matemático | Face visual |
|---:|---|
| 10 | Glifo da Escuridão |
| 9 | 9 |
| 8 | 8 |
| 7 | 7 |
| 6 | 6 |
| 5 | 5 |
| 4 | 4 |
| 3 | 3 |
| 2 | 2 |
| 1 | Glifo da Luz |

Resumo canônico das faces:

~~~
DADO DA LUZ:        10 = Glifo da Luz; 9–2 = números; 1 = Glifo da Escuridão
DADO DA ESCURIDÃO:  10 = Glifo da Escuridão; 9–2 = números; 1 = Glifo da Luz
~~~

A representação visual não altera o valor matemático. O contrato interno deve preservar, por dado:

~~~
die: light | dark
numeric_value: 1..10
glyph: light | dark | null
~~~

O nome concreto do objeto é decisão de implementação. Não substituir o glifo por outro número nem perder a face visual depois da soma.

## 4. Núcleo de resolução

Só há teste quando a ação pode alterar a situação e existe risco, pressão, custo ou incerteza. Sem isso, a ação acontece.

~~~
Dado da Luz + Dado da Escuridão + Atributo + Perícia = total
margem = total - dificuldade
~~~

O total determina se o objetivo foi alcançado. Os valores naturais determinam como o resultado entra no mundo.

### Dificuldades

| Nome | Valor |
|---|---:|
| Baixa | 10 |
| Favorável | 12 |
| Incerta | 15 |
| Difícil | 18 |
| Severa | 21 |
| Extrema | 24 |
| Lendária | 27 |
| Épica | 30 |

Dificuldades acima de 30 representam fenômenos cosmológicos e devem crescer em passos aproximados de 3.

### Graus

| Margem | Grau | Efeito |
|---:|---|---|
| -5 ou menos | Falha severa | piora significativa |
| -1 a -4 | Falha | não consegue ou paga custo alto |
| 0 a +4 | Sucesso | realiza o objetivo |
| +5 a +9 | Sucesso forte | realiza e obtém benefício |
| +10 ou mais | Sucesso extraordinário | altera a situação além do esperado |

## 5. Predominância

Compare os dados naturais antes dos modificadores:

| Condição | Valor | Leitura |
|---|---|---|
| Luz maior | light | direto, material, público ou imediatamente perceptível |
| Escuridão maior | dark | contextual, relacional, profundo, discreto ou posterior |
| Iguais | resonance | as duas forças encontram a mesma frequência |

Predominância não converte sucesso em falha ou falha em sucesso.

| Diferença | Intensidade |
|---:|---|
| 0 | Ressonância |
| 1–2 | Sutil |
| 3–5 | Clara |
| 6–8 | Intensa |
| 9 | Absoluta |

Normalmente aplica-se um efeito principal do dado predominante. Em sucesso extraordinário, falha severa ou Predominância intensa, o Mestre pode combinar dois efeitos relacionados. O dado menor acrescenta no máximo uma nuance.

## 6. Ressonância dos dados

Valores naturais iguais produzem Ressonância. O total continua determinando sucesso ou falha.

Em sucesso, a Ressonância pode ampliar o efeito, reduzir custo, abrir oportunidade para aliado, recuperar 1 Fluxo, preencher 1 Pulso dentro dos limites ou revelar relação oculta pertinente.

Em falha, pode revelar verdade útil, impedir a pior consequência, abrir tentativa imediata, converter dano em condição, marcar recuperação ou gerar 1 Pulso por resistência coletiva.

Igualdade dos valores naturais também classifica o resultado como crítico. A classificação crítica é a própria Ressonância; ela não altera, por si só, o sucesso, a falha ou o grau.

Essas são permissões condicionadas à ficção, não efeitos automáticos. Ressonância não retira autonomia, não impõe Merge e não inventa informação.

### Matriz de Ressonâncias

| Valor | Nome | Abertura canônica | Efeito mecânico específico |
|---:|---|---|---|
| 1-1 | Ressonância Frágil | algo pequeno sobrevive, começa ou recusa desaparecer | UNSPECIFIED; exemplos: 1 Vitalidade, objeto funciona uma vez, memória breve ou rota por segundos |
| 2-2 | Ressonância do Eco | pista, som, memória ou padrão retorna | UNSPECIFIED |
| 3-3 | Ressonância da Forma | algo recebe estrutura ou significado | UNSPECIFIED |
| 4-4 | Ressonância da Passagem | rota, deslocamento ou transição torna-se possível | UNSPECIFIED |
| 5-5 | Ressonância do Espelho | relação, correspondência ou identidade é revelada | UNSPECIFIED; não força Merge |
| 6-6 | Ressonância do Acorde | aliados, forças ou intenções coordenam-se | UNSPECIFIED |
| 7-7 | Ressonância da Fratura | defesa, mentira, barreira ou padrão rompe-se | UNSPECIFIED; não destrói chefe automaticamente |
| 8-8 | Ressonância do Vínculo | relação restaura-se, transforma-se ou é posta à prova | UNSPECIFIED |
| 9-9 | Ressonância da Convergência | várias contribuições produzem mudança coletiva | UNSPECIFIED; pode equivaler a dois benefícios básicos relacionados |
| 10-10 | Ressonância Plena | Luz e Escuridão alteram a cena em escala excepcional | UNSPECIFIED; não mata chefe, força Merge, remove toda Sombra ou resolve a campanha |

O gatilho de crítico é definido pela regra canônica adicional do autor:

~~~
CRITICAL_TRIGGER = DEFINED
condition = light_die == dark_die
RESONANCE_TRIGGER = DEFINED
condition = light_die == dark_die
CRITICAL_CLASSIFICATION = RESSONÂNCIA
CRITICAL_AUTOMATIC_SUCCESS = NO
CRITICAL_AUTOMATIC_FAILURE = NO
CRITICAL_EXTRA_MECHANICAL_EFFECT = UNSPECIFIED
~~~

Não inventar dano dobrado, dano máximo, reroll, bônus, sucesso automático ou falha automática.

## 7. Leituras naturais

As leituras orientam a consequência; não são bônus numéricos automáticos.

### Luz

| Valor | Princípio | Sucesso | Falha ou custo |
|---:|---|---|---|
| 1 | Centelha | efeito começa, pequeno ou incompleto | intenção, esforço ou hesitação |
| 2 | Vestígio | pista, marca ou evidência útil | rastros ou sinais indesejados |
| 3 | Forma | contorno, função, posição ou definição | forma instável ou limitada |
| 4 | Movimento | posição, ritmo ou direção mudam | posição desfavorável |
| 5 | Exposição | alvo, fraqueza, mentira ou passagem visível | alguém ou recurso exposto |
| 6 | Abertura | oportunidade imediata | oposição recebe abertura |
| 7 | Impacto | interrupção, quebra, deslocamento ou força | recuo, dano colateral ou reação |
| 8 | Testemunho | ação reconhecida, vista ou registrada | autoridade ou julgamento |
| 9 | Transformação | mudança duradoura | alteração indesejada |
| 10 | Manifestação plena | efeito incontestável | consequência imediata e visível |

### Escuridão

| Valor | Princípio | Sucesso | Falha ou custo |
|---:|---|---|---|
| 1 | Sussurro | intuição ou sinal aparece | ambiguidade |
| 2 | Eco | passado ou outra cena retorna | eco falso ou perturbador |
| 3 | Contexto | conexão histórica ou institucional | peça faltante e interpretação errada |
| 4 | Caminho | rota alternativa ou solução indireta | custo, atraso ou desvio |
| 5 | Vínculo | relação fortalece-se ou transforma-se | tensão, dívida ou distância |
| 6 | Segredo | algo oculto fica acessível | segredo parcial ou perigoso |
| 7 | Memória | passado retorna de modo útil | lembrança dolorosa ou distorcida |
| 8 | Possibilidade | opção futura torna-se real | oportunidade da oposição ou preço |
| 9 | Profundidade | causa, estrutura ou identidade revelada | desestabilização |
| 10 | Origem | ação toca a raiz da relação ou fenômeno | dívida, eco ou consequência duradoura |

## 8. Modificadores

Impulso e Pressão são circunstanciais:

~~~
1 ponto = 2 no resultado
Impulso máximo normal = +4
Pressão máxima normal = -4
~~~

Eles se anulam. A mesma justificativa não concede dois benefícios. Ajuda competente concede +2 por aliado, máximo de dois aliados, usando Ação e compartilhando risco.

## 9. Atributos, perícias e defesas

### Atributos

~~~
Corpo       força, resistência, vigor, impacto
Agilidade   precisão, velocidade, equilíbrio, reflexo
Intelecto   análise, conhecimento, técnica, planejamento
Presença    influência, liderança, expressão, intimidação
Vontade     disciplina, coragem, identidade, resistência mental
Sintonia    magia, Ressonância, Fendas, Velarim e Evocações
~~~

Valores iniciais: 3, 2, 2, 1, 1, 0. O bônus do teste é o próprio valor.

Perícias: Atletismo, Combate, Pontaria, Furtividade, Percepção, Sobrevivência, Investigação, Conhecimento, Ofício, Influência, Empatia, Cuidado, Magia, Evocação e Velarim. Variam de 0 a 5.

~~~
Vitalidade  = 10 + Corpo × 3
Lucidez     = 8 + Vontade × 3
Fluxo       = 3 + Sintonia + ceil(Marco / 2)
Guarda      = 10 + Agilidade + Proteção
Fortitude   = 10 + Corpo + Vontade
Integridade = 10 + Vontade + Sintonia
~~~

Guarda, Fortitude e Integridade são Defesas estáticas. Movimento normal é 6 na grade e 2 zonas em zonas.

Fôlego tem máximo 3 e retorna na Pausa Segura. Determinação começa cada sessão em 1, tem teto normal 3 e pode repetir os dois dados, evitar queda a 0 Vitalidade, recusar controle ou declarar vínculo/preparação plausível.

## 10. Oposição, combate e condições

Testes opostos usam 2d10 + Atributo + Perícia para cada lado. O maior vence; empate usa posição estabelecida, relação mais específica ou impasse.

~~~
corpo a corpo: 2d10 + Corpo ou Agilidade + Combate contra Guarda
distância:     2d10 + Agilidade + Pontaria contra Guarda
magia:         2d10 + Sintonia + Magia contra Guarda, Fortitude ou Integridade
~~~

Dano final é (dano-base × multiplicador) + margem + modificadores fixos + Corpo quando Potente - Proteção. Só o dano-base é multiplicado. Sucesso forte dá +2 dano; extraordinário dá +4.

Condições relevantes: Abalado (-2 no próximo teste), Exposto (+2 contra ataques), Lento, Sangrando (-2 Vitalidade no fim do turno), Dissonante (-2 em Sintonia/Velarim/Merge/Evocação), Fraturado (não recupera Fluxo), Corrompido (Pressão 1 nos testes afetados) e Caído.

Caído realiza 2d10 + Corpo + Atletismo contra Dificuldade 12 no início do turno. Três sucessos estabilizam; três falhas produzem morte ou consequência terminal conforme o acordo da campanha.

## 11. Coro / Ressonância Coletiva

~~~
1 Barra = 4 Pulsos
1–2 personagens: máximo 1 Barra
3–4 personagens: máximo 2 Barras
5 ou mais: máximo 3 Barras
~~~

Uma personagem gera no máximo 1 Pulso por rodada. Ressonância, Promessa sob risco, vínculo reparado, consequência aceita ou ação de Papel que mude a posição coletiva podem gerar Pulso quando houver risco e contribuição reais.

Uma Barra ativa Nível I, duas ativam Nível II e três ativam Nível III. Há no máximo uma ativação por rodada e um efeito por Ação ou Reação. Vanguarda, Artilharia e Amparo usam Ação; Bastião usa Reação. Não existe Nível IV ordinário.

O Coro é do grupo, não de um personagem. Não é crítico individual.

## 12. Fendas, Merge e Velarim

### Fendas

| Estado | Dificuldade |
|---|---:|
| Latente | 21 |
| Ressonante | 15 |
| Aberta | 12 |
| Fraturada | 18 e consequência |
| Corrompida | 21 e risco de Sombra |

Travessia exige destino, Âncora, estado, teste coletivo e custo concreto. Três sucessos antes de duas falhas atravessam com estabilidade. Cada contribuição usa 2d10 + Atributo + Perícia.

### Merge

Merge legítimo exige consentimento, limites, duração, direito de saída, Âncora e 1 Fluxo por participante. Role:

~~~
2d10 + Sintonia + Empatia, Magia, Evocação ou Velarim contra Dificuldade 15
~~~

Fusão forçada é violência; Merge corrompido é assimilação. Nenhum deles é uma ação neutra.

### Velarim

~~~
Analisar:   2d10 + Intelecto + Velarim
Pronunciar: 2d10 + Sintonia + Velarim
Inscrever: 2d10 + Intelecto ou Sintonia + Ofício ou Velarim
Traduzir:   teste prolongado, preservando alternativas e certeza
~~~

Forma, sentido e relação concreta são necessários. Léxico sem autoridade não deve ser inventado em cena.

## 13. Contrato de desenvolvimento para o VTT

Esta seção é proposta técnica, não regra adicional.

~~~
{
  "system": "kallistis",
  "mode": "single|action|opposed",
  "request_id": "uuid",
  "attribute": {"name": "Corpo", "value": 0},
  "skill": {"name": "Combate", "value": 0},
  "difficulty": 15,
  "modifier": 0
}
~~~

Resultado mínimo:

~~~
{
  "system": "kallistis",
  "light_die": {"numeric_value": 1, "glyph": "dark"},
  "dark_die": {"numeric_value": 1, "glyph": "light"},
  "natural_total": 2,
  "modifier": 0,
  "total": 2,
  "difficulty": 15,
  "margin": -13,
  "degree": "failure_severe",
  "predominance": "resonance",
  "critical": true,
  "resonance": {
    "value": 1,
    "name": "Ressonância Frágil",
    "effect": "UNSPECIFIED"
  }
}
~~~

Message.roll já pode armazenar esse JSON; Submission e request_id já cobrem reserva e idempotência; Recipient cobre rolls secretos; o WebSocket e o dispatch pós-commit já cobrem realtime.

## 14. Mapeamento para o Gravewright

Já compatível:

- dice.services reserva antes da aleatoriedade, reautoriza e persiste depois.
- dice.kallistis mantém light_die e dark_die separados.
- Message.roll já carrega resultado, dificuldade, ação, oposição e metadados.
- Chat, template, WebSocket, Channels/Redis e dispatch já estão prontos para transportar o resultado.

Gaps comprovados:

- _die() atual produz somente inteiros 1–10; não preserva glifo.
- A UI exibe Luz/Escuridão como números, sem face visual.
- O engine ainda não classifica explicitamente a igualdade como crítico; hoje registra apenas resonance.
- Ação sem actor ligado mantém o caminho genérico explícito; quando actorId está presente, atributo e perícia são resolvidos server-side a partir de Actor.data.runtime.
- KALLISTIS está hard-coded em dice/kallistis.py e no combate, não registrado como ruleset no catálogo.
- combat.formula_engine é genérico e não deve substituir o engine KALLISTIS.

## 15. Conflitos e decisões

| Situação | Impacto | Decisão |
|---|---|---|
| Glifos do autor versus engine numérico | face visual perdida | estender o engine KALLISTIS, sem mudar valor matemático |
| Ressonância versus critical | igualdade precisa preservar classificação e semântica própria | marcar critical quando os valores forem iguais; manter efeito extra como UNSPECIFIED |
| Ressonância versus grau | interpretação poderia mudar sucesso/falha | total, margem e grau continuam soberanos |
| Ressonância, Coro e Merge | termos podem ser misturados | namespaces distintos |
| Payload versus ficha do actor | valores podem ser forjados | usar ficha server-side quando houver actor ligado |
| Sistema versus catálogo | campanha não seleciona KALLISTIS formalmente | registrar somente se a ativação de ruleset exigir |

## 16. Menor plano de adaptação futura

1. Estender apenas gravewright/dice/kallistis.py para face visual + valor numérico.
2. Testar as duas orientações de glifo e os dez valores de Ressonância.
3. Atualizar template/estilos para mostrar valor e glifo.
4. Manter Submission, Message.roll, Recipient, chat, realtime e dispatch.
5. Resolver atributo/perícia pela ficha quando actorId estiver presente — concluído no Gate A.
6. Registrar KALLISTIS no catálogo somente se a campanha precisar de seleção formal.
7. Implementar somente a classificação crítica por igualdade; manter efeito mecânico extra como UNSPECIFIED.

## 17. Fontes internas

~~~
Livro III, §§ 3–10       núcleo, Dificuldade, Grau, Predominância e Ressonância
Livro III, §§ 11–14      Atributos, Perícias, Defesas e Reservas
Livro III, §§ 24–33      Técnicas e Magia
Livro III, §§ 34–52      Evocações, Velarim e Merge
Livro III, §§ 53–66      Combate, condições, queda e morte
Livro III, §§ 67–79      Coro / Ressonância Coletiva
Livro III, §§ 101–104    Fendas e travessias
Livro IV, §§ 1–8         condução, consequências e bestiário
Apêndices, Glossário     terminologia operacional
~~~

Conclusão: a adaptação cabe no pipeline existente. Os gaps técnicos mínimos são a extensão do resultado KALLISTIS para faces semanticamente etiquetadas e a classificação crítica da igualdade como Ressonância, preservando a projeção numérica. Nenhum efeito mecânico adicional de crítico está definido.

### Povos

Fonte canônica: Livro III, seção **Povos**, subseção **Regras dos Povos**, do corpus vigente. Cada Povo oferece um Traço, um Dom, uma Herança escolhida durante a criação e uma Dissonância. O Traço expressa uma característica constante; o Dom acrescenta uma capacidade ativa com limite próprio; a Herança é escolhida entre duas opções; e a Dissonância mostra como uma virtude do Povo pode ser deformada pela Sombra.

Traço e Dom pertencem ao Núcleo permanente e continuam disponíveis independentemente da Trilha de Ofício ativa. Uma Herança muda apenas por transformação narrativa real, normalmente durante um Marco ou arco dedicado. A Dissonância produz pressão e consequência, enquanto o controle da personagem permanece com o jogador dentro do acordo de mesa. Alinhamento, profissão, personalidade, mundo de criação, lealdade e capacidade intelectual pertencem à história da personagem.

#### Aelvari

**Traço — Memória Estratificada.** Ao investigar lugar, objeto ou tradição com vínculo histórico, receba +2. Em sucesso forte, também pode descobrir o que aconteceu, quem tentou ocultá-lo ou qual versão foi descartada.

**Dom — Eco Paralelo.** Uma vez por cena, depois de uma rolagem, substitua um dado pelo valor natural do outro. Se os dois passarem a mostrar o mesmo valor, ocorre Ressonância. Depois, sofra 1 Pressão no próximo teste de Intelecto ou Vontade.

**Heranças:** Cronista (Conhecimento +1; pode registrar uma memória de cena como evidência resistente a alteração comum) ou Vidente Cauteloso (uma vez por cena, perguntar qual consequência imediata parece mais provável se a ação continuar).

**Dissonância — Sobrecarga Temporal.** Ao falhar usando memória ancestral, o Mestre pode oferecer confusão entre passado e possibilidade, perda temporária de uma lembrança atual ou a condição Abalado.

#### Kragor

**Traço — Força de Comunidade.** Enquanto estiver adjacente ou na mesma zona que um aliado consciente, receba +1 Fortitude e +1 dano corpo a corpo.

**Dom — Juramento Operante.** Durante uma Pausa Segura, formule um juramento específico com outro personagem que consinta. Enquanto ambos o cumprem, cada um pode conceder +2 ao outro uma vez por cena. Quebrar conscientemente o juramento causa Dissonante até existir reparação.

**Heranças:** Escudo do Clã (usar a Reação para receber metade do dano destinado a um aliado próximo) ou Voz da Assembleia (ao liderar ação coletiva, dois aliados podem ajudar sem gastar suas ações completas).

**Dissonância — Honra Fechada.** Quando a proteção da comunidade se transforma em exclusão, aceitar o apagamento da autonomia de alguém “pelo grupo” marca 1 Sombra.

#### Draken

**Traço — Corpo Elemental.** Escolha uma Afinidade entre brasa, frio, tormenta, pedra, maré ou vento. Reduza em 2 o dano proveniente dessa Afinidade.

**Dom — Manifestação Elemental.** Gaste 1 Fluxo para acrescentar +3 de dano elemental, alterar o terreno de uma zona, resistir automaticamente a um perigo ambiental da Afinidade ou produzir efeito narrativo equivalente que respeite a escala da cena.

**Heranças:** Soberania (+2 contra coerção e medo) ou Condutor (ao usar magia elemental, um aliado na mesma zona recebe +1 Guarda até o próximo turno).

**Dissonância — Hýbris.** Quando o poder elemental for usado para impor obediência sem necessidade, o Mestre pode oferecer 1 Fluxo em troca de 1 Sombra.

#### Nomos

**Traço — Chassi Modular.** Escolha dois módulos: Visão ampliada (+2 Percepção uma vez por cena contra distância, ocultação ou cobertura); Ferramenta integrada (ferramenta adequada sem ocupar espaço); Compartimento protegido (+2 espaços de Carga); Blindagem leve (+1 Proteção, sem acúmulo com outra Blindagem); Interface de dados (+2 Investigação ou Conhecimento uma vez por cena ao lidar com dispositivo, registro ou padrão); ou Membros adaptáveis (ignora uma penalidade de Movimento ou manuseio por turno). Trocar módulo exige oficina e Descanso Completo. Os bônus respeitam Impulso e a economia normal de ações.

**Dom — Lei Interior.** Uma vez por cena, quando uma regra externa tentar controlar sua ação, declare sua Lei Interior. Sua Integridade aumenta em +4 contra esse efeito. Se a rolagem do agente falhar contra sua Integridade, recupere 1 Lucidez.

**Heranças:** Reparador (usar Ofício no lugar de Cuidado ao tratar Nomos e dispositivos) ou Processador (uma vez por cena, transformar pergunta de Investigação em cálculo imediato dos padrões presentes).

**Dissonância — Otimização Absoluta.** Quando remover a escolha de alguém for apresentada como solução perfeita, resistir exige recordar um vínculo. Sem vínculo relevante, sofra -2 Integridade.

#### Livres

**Traço — Aprendizagem Cruzada.** Escolha uma Perícia fora do Ofício e aumente-a em +1. Depois de cada Marco, essa Perícia pode ser trocada.

**Dom — Solução Improvisada.** Uma vez por cena, declare uso inesperado de objeto, contato, costume ou fragmento de conhecimento. Receba +2 e ignore a falta de ferramenta básica apropriada.

**Heranças:** Comunidade Escolhida (ao ajudar um vínculo, a ajuda concede +3) ou Múltiplos Caminhos (aprender uma Técnica inicial de outro Ofício, respeitando pré-requisitos narrativos).

**Dissonância — Identidade Oferecida.** A Sombra pode oferecer identidade livre de dúvida. Aceitar essa certeza concede sucesso automático imediato e marca 2 Sombra.

#### Dóreos

**Traço — Memória da Matéria.** Ao tocar obra, ferramenta ou estrutura, role 2d10 + Sintonia + Ofício. Em sucesso, descubra seu propósito original, um reparo relevante, uma promessa quebrada ou seu último uso significativo.

**Dom — Inscrição de Promessa.** Durante uma Pausa Segura, inscreva uma promessa em um objeto. Uma vez, o portador pode receber +3 em ação coerente com a promessa, impedir a destruição do objeto ou revelar quem violou sua função. Depois do uso, a inscrição precisa ser renovada.

**Heranças:** Forjador (fabricar equipamento de qualidade sem oficina completa) ou Guardião de Obra (+2 Guarda ao defender estrutura, Artefato ou pessoa sob responsabilidade formal).

**Dissonância — Permanência Rígida.** Quando preservar uma obra exigir sacrificar pessoas ou escolhas presentes, insistir sem negociação marca 1 Sombra.

#### Teriantes

**Traço — Aspecto Faunístico.** Escolha um Aspecto e um sentido associado: felinos/visão e equilíbrio, lupinos/cheiro e cooperação, avianos/distância e orientação, reptilianos/calor e imobilidade ou aquáticos/vibração e água. Outro Aspecto pode ser criado com aprovação do grupo. Receba +2 Percepção quando o sentido escolhido for relevante.

**Dom — Instinto Inteiro.** Uma vez por cena, antes de rolar, pergunte qual saída parece mais segura, quem demonstra ameaça, o que está fora de lugar ou qual movimento preserva o bando. A resposta é verdadeira, embora possa ser incompleta.

**Heranças:** Caçador (+1 dano contra alvo rastreado) ou Protetor de Bando (aliados próximos recebem +1 contra medo e emboscada).

**Dissonância — Redução ao Impulso.** A Sombra pode pressionar o instinto até transformá-lo em perda de escolha. Quando um aliado chama a personagem pelo nome e pelo vínculo compartilhado, receba +2 Integridade para resistir.

#### Nimari

Nimari são o povo pequeno das rotas. Sua baixa estatura não modifica alcance ou deslocamento por si só; Passo Liminal, Fortuna e Herança expressam mecanicamente sua forma de atravessar o mundo.

**Traço — Passo Liminal.** Uma vez por turno, atravesse espaço ocupado ou terreno difícil sem custo adicional. Barreiras sólidas continuam exigindo uma passagem real.

**Dom — Dado da Fortuna.** Uma vez por cena, depois de qualquer rolagem visível, aumente ou reduza em 1 o valor natural de um dado, respeitando o intervalo de 1 a 10. A mudança pode criar ou desfazer uma dupla. Descreva qual possibilidade foi desviada.

**Heranças:** Cartógrafo de Frestas (+2 Sobrevivência ao procurar rotas, portais e saídas) ou Negociador de Risco (ao aceitar uma consequência antes do teste, recebe +3 em vez de +2).

**Dissonância — Caminho Sem Compromisso.** Abandonar um vínculo para evitar todo risco recupera 1 Fôlego, mas marca uma Ruptura nesse vínculo. Três Rupturas encerram o vínculo até existir reparação.

#### Vitrálios

**Traço — Corpo Harmônico.** Escolha uma frequência dominante entre calor, som, emoção, luz física, vibração ou magia. Perceba sem teste mudanças relevantes nessa frequência quando próximas.

**Dom — Ressonância Prismática.** Gaste 1 Fluxo para refletir magia de alvo único com efeito reduzido, emitir luz ou som estruturado, compartilhar emoção verdadeira com consentimento ou conceder +2 a teste de Sintonia de aliado.

**Resistência Vitrália.** Resistência a uma condição concede Impulso 1 nos testes feitos especificamente para evitá-la, resistir a ela ou removê-la. Durante Pausa Segura, a Herança pode permitir trocar a condição protegida.

**Reflexão Vitrália.** O novo alvo precisa ser válido e estar no alcance funcional. Ampliações pagas pelo conjurador original permanecem no efeito original. Dano refletido usa grau de potência abaixo do original, mínimo ×1; outro valor numérico é reduzido aproximadamente à metade, arredondando para baixo; sem escala numérica, duração ou intensidade cai um passo coerente. A reflexão preserva ou reduz a potência recebida.

**Heranças:** Lapidador de Si (durante Pausa Segura, trocar a resistência a uma condição por outra até a próxima Pausa Segura) ou Coro Vitrálio (quando outro personagem gerar Ressonância, recuperar 1 Lucidez, uma vez por cena).

**Dissonância — Quebra Frequencial.** Ao sofrer dano de Lucidez igual ou superior à Vontade, escolha tornar a emoção visível, perder temporariamente acesso ao Dom ou sofrer Fraturado.

**Trocados e identidade.** Em Vitrálio Trocado, escolha Luz ou Escuridão antes da rolagem. Role um segundo d10 dessa identidade, mantenha um dos dois dados dela e preserve o dado da outra identidade. Predominância e Ressonância usam os dois dados mantidos.
