# Gravewright — Mesa ASCII 2D: percurso, decisões, evidências e contrato visual

**Registro:** 29/10/2026  
**Projeto:** Gravewright × KALLÍSTIS  
**Repositório:** https://github.com/NomosLudens/gravewright  
**Estado da iniciativa:** EM DESENVOLVIMENTO; experiência visual final NÃO APROVADA  
**Natureza deste arquivo:** memória técnica e contrato de produto; não é certificado de implementação.

> Decisão do proprietário: primeiro fazer o motor ASCII funcionar e obter qualidade visual real. Somente depois desenvolver a fonte autoral e os modos Velarim. Este documento não autoriza implementação antecipada da fonte, merge, deploy ou alteração de dados reais.

## 1. Visão do produto

Transformar uma cena 2D existente do Gravewright em uma **mesa de RPG composta por caracteres**, mantendo a mesma campanha, mapa, atores, tokens, câmera, efeitos e interações do VTT. O modo ASCII é **uma representação alternativa da cena real**, não outro mapa, não um jogo 3D e não um desenho estático feito manualmente com caracteres.

O resultado visual desejado lembra a referência apresentada pelo proprietário: uma imagem legível de longe, construída de perto por milhares de **micropixels tipográficos**. Cada célula usa um glifo pequeno cuja forma comunica luminosidade, textura ou orientação, enquanto sua cor deriva daquela região da imagem real. A referência é inspiração de linguagem visual, não autorização para copiar ativos de terceiros.

O projeto deve manter a alternância **Original / Mesa ASCII**, sem regressão do renderer PixiJS.

## 2. O problema que motivou a mudança

As primeiras provas mostraram que é possível desenhar caracteres e mover tokens, mas isso não atendeu ao objetivo estético:

- As paredes apareciam como barras, linhas de cerquilhas e caracteres repetitivos.
- A grade e o fundo plano não comunicavam uma paisagem.
- A conversão de imagem detalhada gerou massas de caracteres densos e repetidos, com contornos e objetos difíceis de reconhecer.
- As cores e nuances visuais percebidas ficaram muito aquém da referência.
- Build e testes de conversor passaram mesmo quando a qualidade visual continuava insuficiente.

**Problema de produto:** não basta provar que uma imagem foi convertida em texto. O observador deve reconhecer a praça, o cristal, os materiais e os volumes a partir dos caracteres.

## 3. Histórico cronológico — o que foi relatado e comprovado

Esta cronologia reproduz os relatórios do trabalho local enviados nesta conversa. As provas são **relatadas pelo executor local**; não foram reexecutadas pelo autor deste documento. A numeração de algumas missões 06 foi reutilizada em rodadas distintas.

| Etapa | Intervenção / descoberta | Evidência e limite |
| --- | --- | --- |
| Prova inicial S02 | Extração de pixels do frame PixiJS e conversão para ASCII; alternância de renderer. | Caminho de código criado, sem prova manual suficiente naquela rodada por pendências de migração. |
| S03 | SQLite original copiado de forma consistente para ambiente isolado; migrações na cópia; abertura de BASELINE MAP. | Fluxo real abriu, porém a mesa ASCII era visualmente ilegível e o token não aparecia. |
| S04 | Token real representado de forma semântica, sem depender da amostragem de sprites ocultos. | Seleção, deslocamento e persistência passaram em verificações intermediárias; imagens de mapa ainda pobres. |
| S06 — ASCII Evaluation - Ruins | Paredes, grade discreta, token [BA] e Fireflies em movimento na cena de avaliação. | [BA] mudou de (6,8) para (7,9) e permaneceu após recarga. Veredito PARTIAL porque o chão continuou vazio e BASELINE MAP não comprovou terreno detalhado. |
| GRAVEWRIGHT_ASCII_ENGINE_FIX_06 | Imagem fratura-praca.png importada pelo Map Builder em cena privada da cópia isolada; conversão de imagem para ASCII. | Conversão real ocorreu. Captura inicial com densidade excessiva, pouca recognoscibilidade da praça/cristal. Ajuste final de amostragem compilou e 5 testes passaram, mas navegador não permitiu recaptura posterior. Veredito INCIDENT. |
| Ajuste visual subsequente | Mais diversidade de caracteres, tratamento de texturas irregulares e leve elevação de cores escuras. | Build relatado. Capturas posteriores na cena Ruins continuaram repetitivas e com poucas cores; ausência de aprovação estética. |
| Hipótese de resolução 07 | Diminuir fonte e células **junto com o aumento efetivo de linhas/colunas amostradas**. | Prompt proposto; execução e melhora em navegador não demonstradas aqui. |
| Proposta de micropixels 08 | Experimentar 6, 5 e 4 px; calibrar proporção; cor individual por glifo; capturar comparativo real. | **Definição de produto**, não entrega validada. |
| Futuro Velarim | Fonte autoral proposta com 76 glifos e possíveis modos ASCII Velarim e Híbrido. | **Ideia aprovada para depois do motor funcional**, não iniciada nem canonizada como inventário tipográfico. |

### Fontes de evidência local informadas

Os relatórios locais citaram, no notebook do proprietário:

- docs/evidence/gravewright-ascii-sandtable-06/README.md — cinco capturas reais da cena Ruins e do fluxo do token.
- docs/evidence/gravewright-ascii-engine-06/README.md — quatro capturas reais da conversão; as detalhadas precedem um ajuste posterior.
- Capturas mostradas em conversa: uma cena Ruins esparsa e outra composição excessivamente carregada de caracteres.

**Atenção:** esses arquivos foram mencionados como existentes no checkout local, mas não estavam no diretório de evidências do GitHub master no momento deste registro. Não confundir o caminho local com prova publicada.

## 4. Estado comprovado versus não comprovado

| Capacidade | Situação em 29/10/2026 | Precisão |
| --- | --- | --- |
| Renderização ASCII no navegador | COMPROVADA em fluxos anteriores | Existência funcional, não qualidade estética. |
| Extração de uma imagem importada para ASCII | COMPROVADA na cópia privada | A representação estava excessivamente densa em captura anterior ao último ajuste. |
| Atualização de efeitos dinâmicos | COMPROVADA em fluxo anterior | Glifos de Fireflies mudaram de posição; pós-ajustes não revalidado. |
| Token real selecionável e móvel | COMPROVADO na cena Ruins | [BA] (6,8) → (7,9). |
| Persistência de movimento | COMPROVADA em cena de teste anterior | Posição manteve-se depois de recarga; não comprovada sobre a imagem detalhada. |
| Token na cena detalhada fratura-praca.png | NÃO COMPROVADO | Cópia detalhada usada na prova relatada não continha token. |
| Original PixiJS após alternância | COMPROVADO anteriormente | Não foi rechecado após todo o conjunto de builds posteriores. |
| Reconhecimento visual da praça e do cristal | INSUFICIENTE / NÃO APROVADO | Objetivo de produto principal ainda aberto. |
| Células de 6/5/4 px com resolução real maior | NÃO COMPROVADO | Proposta técnica, sem captura de aceite. |
| RGB individual por glifo | DEFINIÇÃO VISUAL; resultado final NÃO COMPROVADO | Ajustes de cor anteriores não produziram fidelidade satisfatória. |
| Fonte com 76 glifos | NÃO INICIADA | Ideia futura e dependente de inventário autorizado. |
| Integridade do SQLite original | PRESERVADA nos relatórios | Hash histórico informado: aec9ec87f1a3a460327ecd3e721f2ed54bf990244ed1ef28d3eb000f3b5e1df3. Não foi aferido novamente neste registro. |

**Veredito de produto atual: INCIDENTE VISUAL / FUNCIONALIDADE PARCIAL.** Há peças reais comprovadas, mas ainda não existe prova satisfatória da mesa detalhada, colorida e jogável na **mesma cena**.

## 5. Decisões de arquitetura e escopo

1. **Fonte de verdade:** usar a composição visual real do PixiJS, seus pixels, texturas e efeitos; não substituir mapas detalhados por planta ASCII manual.
2. **Renderer alternativo:** o modo ASCII não altera as entidades persistidas nem o renderer Original.
3. **Interação real:** tokens usam identidades, coordenadas, eventos e persistência do Gravewright. Não inventar tokens em fixture para aprovar o produto.
4. **Amostragem e desenho:** uma célula corresponde a uma região real da imagem; o glifo e a cor provêm dessa região. O número de células deve aumentar quando sua dimensão visual diminui.
5. **Geometria:** medir a largura efetiva do glifo monoespaçado, altura de linha e aspect ratio; não presumir que cada célula seja quadrada.
6. **Renderização:** reutilizar o caminho gráfico já existente e evitar criar um objeto PixiJS por caractere. Otimizações adicionais apenas se medidas reais justificarem.
7. **Camadas:** glifos do ambiente podem ser microscópicos, mas tokens, seleção e rótulos precisam continuar identificáveis e clicáveis.
8. **Câmera:** Original e ASCII mantêm enquadramento, zoom e coordenadas equivalentes.
9. **Dados:** só usar cópia isolada da SQLite em experimentos; nunca executar migrações no banco original para testes visuais.
10. **Escopo:** nenhuma reescrita do VTT, dependência ou branch adicional é necessária para validar essa ideia.

### Por que diminuir só o tamanho CSS não basta

Um texto menor aplicado à mesma matriz apenas encolhe os caracteres; **não recupera detalhes ausentes**. A melhoria exige:

- Mais colunas e linhas de amostragem do frame.
- Células de desenho compatíveis com fonte e altura de linha.
- Mapeamento correto das amostras para a câmera e a cena.
- Atenção à resolução física do canvas e ao devicePixelRatio, para que a fonte minúscula não vire borrão.
- Avaliação do custo de desenhar potencialmente milhares de caracteres por atualização.

**Experimento previsto:** comparar 6 px, 5 px e 4 px na mesma cena e câmera. Escolher a melhor legibilidade e fluidez, sem prometer que o menor valor será vencedor.

## 6. Contrato de cor individual por glifo

Cada posição de caráter é definida por dois componentes independentes:

- **Forma / glifo:** escolhido segundo luminosidade, densidade local, textura e, quando útil, direção de contorno.
- **Cor / opacidade:** obtidas de pixels da própria região da imagem, com tratamento previsível de transparência.

Não colorir por linha inteira, por categoria arbitrária de caractere ou por um único tom de região extensa. A saída deve preservar os azuis do cristal, a variação cromática das pedras, luzes, sombras e efeitos.

Não usar cores aleatórias. Correções de brilho/contraste devem respeitar a composição original e não transformar áreas de penumbra em ruído luminoso. A representação pode usar buckets de cor apenas se essa aproximação for visualmente fiel e necessária ao desempenho.

**Critério visual:** a imagem reconstruída deve ter identidade cromática reconhecível quando vista no tamanho normal, e os glifos devem ser discerníveis ao aproximar.

## 7. Leitura de contornos, texturas e densidade

O incidente dos caracteres repetitivos mostrou que não basta trocar a tabela de símbolos. Em particular, contornos direcionais podem dominar a imagem inteira e substituir gradações tonais importantes.

Requisitos:

- Preservar áreas escuras sem lotá-las de glifos de alta densidade.
- Distribuir símbolos por luminância e textura de maneira consistente.
- Reservar orientação de traços para bordas suficientemente confiáveis.
- Evitar que # ou barras dominem superfícies variadas.
- Manter diferenças entre céu/escuro, piso, estrutura, água/cristal e efeitos conforme o conteúdo da imagem.
- Avaliar o resultado pela reconhecibilidade dos objetos, não pelo número bruto de símbolos.

A sequência de correção continua pequena e reversível: primeiro escala e amostragem; depois somente os ajustes de contraste ou seleção de glifos que a comparação visual indicar.

## 8. Contrato de aceitação — produto real

Um **PASS** só é aceitável quando os pontos abaixo ocorrerem no aplicativo aberto, em sequência verificável:

1. Abrir a cena detalhada derivada da imagem real fratura-praca.png no ambiente SQLite isolado.
2. Fotografar/capturar **Original** e **ASCII** no mesmo zoom e enquadramento.
3. Comparar as três densidades propostas (6/5/4 px), com número real de células indicado em cada captura.
4. Reconhecer praça, cristal e grandes massas da imagem **sem depender de legenda**.
5. Observar cores individuais coerentes com a arte original e efeitos dinâmicos alterando a saída.
6. Colocar ou usar **token real** nessa mesma cena, selecioná-lo, mover e recarregar; comprovar posição persistida.
7. Voltar para Original e confirmar que interações e renderização seguem intactas.
8. Informar desempenho medido (ex.: FPS/latência em máquina e resolução observadas), sem inventar benchmark.
9. Conferir que o SQLite original não foi alterado.

Os testes de unidade e build são auxiliares. **Não substituem essas provas.** Se a automação falhar antes da captura, marcar o item não testado. Não reutilizar captura antiga como prova de ajuste posterior.

As provas precisam comparar o mesmo mapa e o mesmo estado; misturar Ruins com cena detalhada produz conclusão enganosa.

## 9. Ideia autoral futura — ASCII Velarim / Silmain

**Status: reserva de design, não implementar agora.**

A proposta do proprietário é criar uma fonte com **76 glifos** e permitir que os cenários sejam reconstruídos em caracteres do universo KALLÍSTIS. A composição visual continuaria baseada nos pixels reais e nas cores individuais.

Modos pensados:

1. **Original:** PixiJS convencional.
2. **ASCII:** micropixels de caracteres tipográficos convencionais.
3. **ASCII Velarim:** micropixels usando conjunto autoral de glifos.
4. **Híbrido (opcional e posterior):** ASCII convencional com glifos autorais onde fizer sentido estético.

### Cuidado canônico

O material normativo disponível, *VELARIM_MANUAL_DEFINITIVO_v1.0*, identifica **Silmain** como sistema de escrita geométrica contínua de Velarim. Ele registra que o fim de um grafema consonantal inicia o seguinte, vogais são marcas ligadas e **a fonte tipográfica definitiva ainda não está fixada**. Portanto:

- **Velarim** é a língua; **Silmain** é sua escrita, conforme o manual.
- O total de **76 glifos** foi proposto pelo proprietário neste percurso; sua lista, geometria e versão canônica ainda precisam ser fornecidas ou auditadas. Não afirmar que a fonte existe.
- Converter Silmain contínuo em células independentes para arte ASCII é uma **interpretação gráfica**, não necessariamente a ortografia normativa usada para escrever frases.
- A fonte deve preservar os desenhos autorizados, sem inventar grafemas e sem quebrar o sistema linguístico.
- A tipografia pode precisar de duas soluções distintas: uma **grade visual monoespaçada** para micropixels e, se posteriormente desejado, composição contextual/ligaturas para escrita Silmain real.
- WOFF2 e TTF são formatos candidatos, sujeitos a validação visual e técnica quando o projeto for autorizado.

### Condição de entrada da fase Velarim

Não começar a fonte enquanto **ASCII convencional micropixel colorido** não obtiver aceitação visual e teste de token/persistência na cena detalhada. Essa ordem foi decidida explicitamente pelo proprietário.

## 10. Próximo trabalho autorizado como foco

**Uma frente só:** provar a hipótese de micropixels coloridos no renderer existente.

Escopo pequeno:

1. Confirmar situação exata do WIP no notebook e preservar todas as alterações alheias.
2. Ajustar densidade física e amostragem para comparação 6/5/4 px.
3. Garantir cor derivada localmente por glifo; corrigir apenas o mínimo necessário para fidelidade.
4. Testar no navegador com fratura-praca.png e token real na mesma cena.
5. Capturar resultados, comparar legibilidade, registrar desempenho e declarar PASS, PARTIAL ou INCIDENT honestamente.

**Não fazer nesta rodada:** criar fonte Velarim, inventar 76 grafemas, refatorar arquitetura, criar branch extra, migrar SQLite original, fazer merge ou deploy.

## 11. Localização e proveniência de código

Segundo os relatórios locais, as implementações e testes da mesa ASCII envolveram:

- gravewright/maps/frontend/widgets/game-board/model/ascii-sandtable.js
- gravewright/maps/frontend/widgets/game-board/model/ascii-sandtable.test.js
- gravewright/maps/frontend/widgets/game-board/lib/pixi-board-renderer.js
- gravewright/maps/static/gravewright_maps/runtime/widgets/game-board/model/ascii-sandtable.js (espelho de build)

**Importante para a retomada:** em 29/10/2026, a branch local relatada era **feat/ascii-sandtable-2d**, mas a consulta ao GitHub **não encontrou essa branch remota**, e o arquivo ascii-sandtable.js não estava presente em master. Isso impede afirmar que o código experimental já está versionado no GitHub. O presente documento é publicado em master **sem transferir nem integrar o WIP local**.

O repositório também mantém o documento de percurso geral [Gravewright × KALLÍSTIS — integração e customização](GRAVEWRIGHT_KALLISTIS_PERCURSO_COMPLETO_2026-09-21.md). Este arquivo é especificamente dedicado ao motor visual Mesa ASCII.

---

## Registro de decisão final (29/10/2026)

**Prioridade:** fazer funcionar, com imagem reconhecível, cor individual por glifo, tamanho microscópico e interação verdadeira.  
**Critério:** experiência visual e jogabilidade reais em navegador; build verde isolado nunca é PASS.  
**Futuro:** ASCII Velarim / Silmain com 76 glifos propostos, somente após validação do motor.  
**Estado:** desenvolvimento aberto; nenhuma conclusão de sucesso final.
