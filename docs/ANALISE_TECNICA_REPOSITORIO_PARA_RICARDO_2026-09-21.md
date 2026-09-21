# Análise técnica do repositório — Gravewright × KALLISTIS

Data: 2026-09-21  
Destinatário principal: Ricardo Tristão Porfirio  
Repositório analisado: `NomosLudens/gravewright`  
Branch: `master`

## 1. Objetivo desta análise

Esta análise não pretende avaliar o Gravewright upstream como produto. O objetivo é mostrar, de forma objetiva, o que foi construído no fork KALLISTIS, onde houve extensão do core, quais decisões arquiteturais foram tomadas e quais pontos merecem revisão do mantenedor do Gravewright.

O repositório completo está em:

- https://github.com/NomosLudens/gravewright

O percurso detalhado do trabalho está em:

- https://github.com/NomosLudens/gravewright/blob/master/docs/GRAVEWRIGHT_KALLISTIS_PERCURSO_COMPLETO_2026-09-21.md

## 2. Relação com o upstream

A base comum verificada é a release oficial `v0.1.1`, commit:

`04a1b666119dc42db755126c61a764097ad5fc24`

No momento desta análise:

- o fork `NomosLudens/gravewright:master` está 48 commits à frente dessa base e 0 atrás;
- o `main` atual de `Gravewright/gravewright` está 1 commit à frente da mesma base;
- portanto existe um commit novo do upstream ainda não integrado ao fork.

O commit atual do upstream introduz, entre outras coisas:

- diretórios padrão `extensions/django` e `extensions/api`;
- configuração explícita para apps Django confiáveis externos;
- melhorias no fluxo de módulos/sistemas;
- mudanças de Runner e configuração associadas.

Isso é especialmente relevante porque parte do KALLISTIS hoje está implementada diretamente no core do fork.

## 3. O que o fork acrescentou

As mudanças KALLISTIS não são apenas visuais. Elas atravessam vários domínios.

### 3.1 Regras

Há uma camada server-side própria em:

- `gravewright/rules/kallistis_runtime.py`
- `gravewright/dice/kallistis.py`
- `gravewright/actors/runtime.py`
- integrações em `gravewright/combat/services.py`

O runtime cobre, em diferentes graus:

- resolução Luz/Escuridão;
- Atributo + Perícia;
- dificuldade, margem e grau;
- predominância e ressonância;
- Impulso e Pressão;
- recursos;
- condições;
- economia de ações;
- combate;
- magia;
- evocações;
- Merge;
- Coro/Ressonância Coletiva;
- Sombra;
- Fendas;
- Fulgor;
- validações de progressão.

A decisão principal foi manter a resolução mecânica autoritativa no servidor, sem depender do cliente para resultados que alteram estado.

### 3.2 Identidade e autenticação

O fork acrescentou:

- `KallistisIdentity`;
- `KallistisPlayerAccess`;
- login por frase;
- provisionamento de jogadores;
- acesso administrativo pelo mesmo mecanismo;
- rate limiting;
- armazenamento por digest de lookup + hash Django, sem frases em texto claro.

Arquivos centrais:

- `gravewright/accounts/models.py`
- `gravewright/accounts/services.py`
- `gravewright/accounts/provisioning.py`
- `gravewright/accounts/management/commands/provision_kallistis_players.py`

O fluxo atual de produto usa frase como credencial humana persistente. Houve anteriormente uma tentativa de SSO/handoff automático, que permanece em partes do histórico/código, mas não é o caminho principal atual.

### 3.3 Campanha e personagem

Foram criados dois vínculos específicos:

- `KallistisCampaignLink`
- `KallistisCharacterLink`

O caminho atual de personagem é deliberadamente explícito:

KALLISTIS exporta JSON → Gravewright faz preview → Mestre escolhe campanha/jogador → confirmação transacional → Actor + link.

Arquivo central:

- `gravewright/actors/kallistis_import.py`

Características relevantes:

- schema versionado;
- validação de tamanho/profundidade;
- rejeição de campos sensíveis;
- preview sem escrita;
- `transaction.atomic()`;
- prevenção de duplicação por ID KALLISTIS;
- Actor criado com permissão `owner` para o jogador selecionado.

### 3.4 Realtime

O fork também alterou `gravewright/realtime/consumers.py` e testes relacionados.

Durante a convergência do ruleset apareceram duas falhas reais:

- heartbeat/idle socket em testes de secret roll;
- corrida de limpeza de presença.

Ambas foram tratadas na camada de transporte/teste, e a suíte daquele gate foi fechada em 360/360 sem remoção de testes.

### 3.5 Interface e identidade visual

Foram alterados:

- templates de painel e mesa;
- assets;
- tema KALLISTIS;
- ficha/controles de Actor;
- tray e resultados de dados;
- módulos JS da mesa.

Isso funcionou como produto, mas aumenta o acoplamento do fork com a UI interna do Gravewright.

## 4. Qualidades técnicas observadas

### 4.1 Autoridade server-side

A maior parte das decisões mecânicas relevantes foi deslocada para o servidor. Isso reduz divergência entre clientes e evita confiar no browser para estado de jogo.

### 4.2 Persistência e idempotência

Os gates foram desenhados para verificar:

- escrita real;
- readback;
- persistência;
- idempotência;
- ausência de duplicação;
- rollback em erro;
- deltas explícitos de banco.

### 4.3 Segurança do login por frase

A implementação não persiste as frases em claro. O registro usa:

- digest HMAC para lookup;
- hash de senha do Django para verificação;
- revogação;
- rate limiting;
- sessão Django normal após autenticação.

### 4.4 Importação transacional

O importador de personagem é uma das partes mais isoladas e claras do fork. Ele separa preview e commit, exige autorização de GM e mantém um vínculo externo único.

### 4.5 Disciplina de testes

Foram adicionadas suítes específicas para:

- ruleset;
- dice;
- actor runtime;
- combat;
- phrase access;
- campaign mapping;
- character read;
- provisioning;
- character import.

Além disso, foi criada em 2026-09-21 uma CI própria:

`.github/workflows/kallistis-ci.yml`

Ela roda em `master`/PR para `master` e executa:

- `manage.py check`;
- `makemigrations --check --dry-run`;
- testes KALLISTIS direcionados;
- suíte Django completa.

A CI herdada de automatic updates também foi adaptada no fork de `main` para `master`.

A primeira execução da nova CI ainda deve ser considerada pendente de observação; esta análise não assume PASS sem resultado real do GitHub Actions.

## 5. Pontos de acoplamento que merecem revisão

Este é provavelmente o principal ponto para análise do mantenedor.

O KALLISTIS hoje toca diretamente:

- `accounts`;
- `campaigns`;
- `actors`;
- `dice`;
- `combat`;
- `realtime`;
- `table`;
- `web`;
- `modules`;
- `pdf_system`;
- templates e JS internos.

Isso tornou possível entregar o produto rapidamente e com autoridade correta, mas aumenta o custo de sincronização futura com o upstream.

A pergunta arquitetural principal é:

> Quanto desse código deveria permanecer como patch do core e quanto pode migrar para um app Django externo e/ou módulo de sistema suportado pelo Gravewright atual?

O novo upstream já documenta:

- `GRAVEWRIGHT_SERVER_APPS`;
- `GRAVEWRIGHT_SERVER_APP_PATHS`;
- `gravewright_urlconf`;
- diretório padrão `extensions/django`;
- sistemas/módulos de browser com superfícies como `actor.sheet`, `token.sheet`, `scene.controls`, `combat.tracker` e `table.interface`.

Isso parece abrir uma rota para reduzir divergência futura, mas não foi feita uma refatoração apenas por existir essa possibilidade. Seria útil uma avaliação do Ricardo sobre a fronteira correta.

## 6. Dívida técnica / pontos abertos

### 6.1 Duas arquiteturas de integração coexistem

O repositório contém vestígios da primeira estratégia:

- SSO/handoff;
- provisionamento server-to-server;
- campaign mapping;

e da estratégia atual:

- login por frase;
- exportação/importação manual de personagem.

Isso é compreensível historicamente, mas pode ser simplificado depois que o fluxo atual estiver definitivamente fechado.

### 6.2 UI KALLISTIS está bastante integrada ao core

Branding e superfícies específicas foram alterados em templates e estáticos internos. Funciona, mas é uma área provável de conflito em merges futuros.

### 6.3 Regras estão parcialmente isoladas e parcialmente integradas

`gravewright/rules/kallistis_runtime.py` é uma boa fronteira, mas vários pontos ainda exigem alterações em `dice`, `combat`, `actors` e UI.

Seria útil saber se o padrão desejado pelo Gravewright é:

- uma engine de regras externa chamada pelo core;
- um sistema/módulo instalado;
- um app Django confiável;
- ou alguma combinação dessas opções.

### 6.4 Documentos históricos ainda referenciam infraestrutura antiga

Alguns documentos de gates preservam referências históricas a ambientes já desativados. Eles são úteis para auditoria, mas precisam ser lidos como histórico e não como topologia atual.

### 6.5 CI nova ainda não foi validada por run observado

A configuração foi criada e versionada, mas o resultado da primeira execução ainda não foi confirmado nesta análise.

## 7. Estado do produto no momento

O fork já possui, no repositório:

- ruleset KALLISTIS server-side;
- autenticação por frase;
- provisionamento de 25 jogadores + administrador no runtime real;
- identidade visual;
- campanha e memberships reais;
- exportação/importação de personagem;
- prevenção de import duplicado;
- testes específicos e documentação extensa;
- CI própria recém-adicionada.

O fluxo E2E de personagem ainda estava em fechamento operacional fora do GitHub no momento desta análise. O último bloqueio observado no runtime era o transporte CSRF do browser no importador. Esse patch não deve ser confundido com o estado publicado do repositório até que seja validado e commitado.

## 8. Questões objetivas para o Ricardo

1. A atual separação entre `kallistis_runtime.py` e os patches em Actor/Dice/Combat está alinhada com a arquitetura que você imagina para systems complexos?
2. O KALLISTIS deveria migrar progressivamente para um `GRAVEWRIGHT_SERVER_APP` externo?
3. Quais partes da UI específica fariam mais sentido como módulo de browser/system package, em vez de alteração de templates internos?
4. `KallistisIdentity` e `KallistisPlayerAccess` deveriam continuar dentro do app accounts ou existir em uma extensão?
5. O vínculo `KallistisCharacterLink` é uma modelagem adequada para identidade externa de Actor?
6. Há alguma API/extensão atual do Gravewright que substitua nossos patches em Dice/Combat/Actor sem perda de autoridade server-side?
7. Quais mudanças do commit atual de `main` você considera prioritárias para incorporarmos antes de continuar?
8. Você vê algum ponto do fork que possa ser generalizado e eventualmente retornar ao Gravewright upstream?

## 9. Arquivos que recomendo inspecionar primeiro

Para uma leitura eficiente:

1. `docs/GRAVEWRIGHT_KALLISTIS_PERCURSO_COMPLETO_2026-09-21.md`
2. `gravewright/rules/kallistis_runtime.py`
3. `gravewright/actors/runtime.py`
4. `gravewright/dice/kallistis.py`
5. `gravewright/actors/kallistis_import.py`
6. `gravewright/accounts/services.py`
7. `gravewright/accounts/models.py`
8. `gravewright/realtime/consumers.py`
9. `.github/workflows/kallistis-ci.yml`

## 10. Síntese

O fork já passou do estágio de experimento. Ele opera como uma adaptação funcional do Gravewright para um sistema específico, com decisões server-side, persistência, realtime, autenticação e fluxo de personagem.

O principal risco técnico não parece ser falta de funcionalidade, mas manutenção da divergência: o KALLISTIS cresceu atravessando o core exatamente ao mesmo tempo em que o upstream começou a oferecer mecanismos formais de extensão.

Por isso, a revisão mais valiosa agora não é “o código funciona?”, e sim:

> qual é a melhor fronteira para manter o KALLISTIS funcional sem transformar o fork em uma linha permanentemente difícil de sincronizar com o Gravewright?

Essa é a questão que gostaríamos que o mantenedor analisasse.
