# Gravewright × KALLISTIS — percurso de integração, customização e estado atual

*Documento de apresentação para Ricardo — do upstream oficial ao fork KALLISTIS em produção*

> Versão Google Docs: https://docs.google.com/document/d/115OZj3ObMwLWAgHJyuKK_uTK2UeoF5a2rRX64vub_08/edit?usp=drivesdk
> Snapshot documental versionado em 2026-09-21. O código continua sendo autoridade operacional; este arquivo registra o percurso, decisões e estado observado.

Este documento registra o caminho técnico e arquitetural percorrido para transformar o Gravewright no runtime VTT do KALLISTIS sem romper a relação com o projeto upstream. Ele reúne decisões, gates, falhas, correções, mudanças de infraestrutura, integração de regras, autenticação, importação de personagens e o estado exato do repositório hoje.

## 1. Resumo executivo

O trabalho não partiu da ideia de substituir ou reescrever o Gravewright. A estratégia foi manter o projeto oficial como base e acrescentar, de forma controlada, as necessidades específicas do KALLISTIS. O resultado atual é um fork funcional, publicado em GitHub, que permanece descendente direto do upstream Gravewright v0.1.1 e adiciona uma camada extensa de regras, identidade, integração, UI e operação real.

- O upstream oficial continua sendo a referência estrutural do VTT.
- O KALLISTIS é a autoridade de cânone, personagem, identidade e progressão; o Gravewright é o runtime de campanha, cena, mapa, token, chat, rolagens, recursos, combate e realtime.
- O fork atual no GitHub está 43 commits à frente da tag oficial v0.1.1 e 0 commits atrás dela; a tag upstream atual é ancestral direta do nosso master.
- As regras centrais do KALLISTIS foram implementadas server-side, testadas, persistidas e validadas em realtime.
- O acesso por frase KALLISTIS está em produção no Gravewright com 25 jogadores e 1 acesso administrativo, sem armazenar frases em texto claro.
- O importador de ficha KALLISTIS já existe no repositório, com preview, confirmação transacional, vínculo de personagem e prevenção de duplicatas.
- O fluxo E2E de importação está hoje bloqueado somente no transporte CSRF executado pelo navegador público; o banco permanece intacto e nenhum Actor KALLISTIS foi criado durante as tentativas bloqueadas.
- Existe neste momento um patch CSRF local na Mini ainda não commitado nem enviado ao GitHub; o master público permanece em 79c301d.
## 2. Repositórios e relação com o upstream

A política adotada desde cedo foi tratar o Gravewright oficial como upstream e o fork KALLISTIS como uma extensão controlada. Atualizações do upstream não são aplicadas diretamente em produção: primeiro são comparadas, testadas e só então convergidas para o master do fork.

- Upstream oficial: Gravewright/gravewright, branch principal main.
- Fork KALLISTIS: NomosLudens/gravewright, branch de produção master.
- Tag upstream v0.1.1 atual: commit 04a1b666119dc42db755126c61a764097ad5fc24.
- Master KALLISTIS no GitHub: commit 79c301d07caf7307948dd0f49894e01e199cd1c6.
- Comparação verificada: ahead_by=43, behind_by=0, merge base=04a1b666.
- A release v0.1.1 foi republicada pelo projeto oficial sem mudança do número de versão; nosso histórico já contém exatamente o commit atualmente apontado pela tag.
Essa relação é importante porque o fork não está solto nem baseado em uma fotografia antiga: ele continua assentado sobre o mesmo commit que hoje define a release oficial v0.1.1, com as customizações KALLISTIS empilhadas depois dele.

## 3. Primeira fase: estabilizar o Gravewright como runtime real

Antes da integração profunda, o objetivo foi provar que o VTT funcionava como produto real: serviço ativo, campanha, mapa, atores, tokens, persistência, Redis e realtime. Os primeiros gates aconteceram na infraestrutura Baby, hoje desativada; posteriormente o runtime autoritativo foi migrado para kaline-mini.

- O serviço atual é gravewright.service em kaline-mini, executando o checkout /home/tonyus-dev/gravewright.
- A origem local é 127.0.0.1:3000 e a superfície pública é gravewright.kallistis.app.
- O banco de runtime é SQLite, preservando campanha, atores, vínculos e estado de sessão.
- O realtime usa Channels e Redis.
- Um incidente de compatibilidade entre channels-redis e redis-py foi isolado e corrigido no commit bf5d951, fixando o cliente Redis compatível em vez de mascarar o problema.
Essa fase consolidou uma regra operacional que continuou valendo durante todo o trabalho: build e testes não bastam. Sempre que possível, o gate precisa chegar ao produto real, ao navegador real, ao banco real, ao realtime real e a uma prova de rollback ou ausência de dano.

## 4. Implementação das regras KALLISTIS no Gravewright

A integração começou pelo núcleo mecânico, não pela aparência. O objetivo era transformar o Gravewright em um executor server-side das regras do KALLISTIS, mantendo as decisões canônicas fora do cliente.

### 4.1 Resolução e dados

- Commit 3f4261e — add KALLISTIS core roll.
- Commit 94f940e — add KALLISTIS dice semantics.
- Dado da Luz e Dado da Escuridão com semântica própria dos glifos 1 e 10.
- Atributo + Perícia + modificadores legítimos calculados no servidor.
- Dificuldade, margem, grau do resultado, predominância e intensidade da predominância.
- Ressonância pela igualdade dos dados, com tabela canônica de 1–1 a 10–10.
- Persistência e retransmissão dos mesmos resultados para múltiplos clientes sem refresh.
### 4.2 Ações, oposição, recursos e combate

- Commit 34122e5 — testes e ações KALLISTIS.
- Commit fd3c53c — recursos de runtime e condições.
- Commit 16c30c4 — runtime mínimo de combate.
- Impulso e Pressão foram testados com cancelamento e limites.
- Testes opostos passaram a criar e persistir as duas submissões reais.
- Recursos como Vitalidade, Lucidez, Fluxo, Fôlego e Determinação passaram a residir no runtime do Actor.
- O fluxo de dano e combate passou a delegar ao runtime canônico em vez de duplicar regra no cliente.
### 4.3 Autoridade do Actor e expansão do ruleset

- Commit c5e2023 — rolagens KALLISTIS vinculadas a Actor tornadas server-authoritative.
- Commit 3e47700 — runtime autoritativo dos Povos.
- A camada de regras cresceu para ação, movimento, reação, condições, magia, evocações, Merge, Coro, Sombra, Fendas, equipamentos, artefatos, Fulgor e validação de progressão.
- O trabalho foi consolidado em gravewright/rules/kallistis_runtime.py e gravewright/actors/runtime.py, com integração em dice, combat, UI e realtime.
- A matriz completa do ruleset encerrou a fase de convergência com 360/360 testes após correções reais de realtime e presença, sem remover ou pular testes.
Essa etapa é importante para entender o repositório atual: o Gravewright não recebeu apenas um tema visual KALLISTIS. Ele ganhou um runtime de regras substancial, integrado aos próprios domínios nativos de Actors, Dice, Combat, Realtime e Table.

## 5. A primeira arquitetura de ponte: SSO, handoff e provisionamento

Depois do ruleset, tentamos aproximar os dois produtos por uma ponte automática. A ideia original era o usuário autenticado no KALLISTIS receber um handoff temporário e entrar no Gravewright sem uma segunda autenticação.

- Commit d9e2ecb — KALLISTIS SSO handoff.
- Commit 7b946f5 — provisionamento Gravewright a partir do handoff.
- Commit 2390a9a — provisionamento assinado, com autenticação server-to-server.
- Foi criado suporte a KallistisIdentity e KallistisCampaignLink.
- Foram implementadas superfícies para listar campanhas Gravewright existentes e vinculá-las a uma Mesa KALLISTIS, evitando criar campanha nova por engano.
- A integração chegou a validar partes do fluxo, mas a fronteira de autenticação entre sessão KALLISTIS, cookie, handoff, provisionamento e sessão Gravewright aumentou muito a complexidade operacional.
O ponto de decisão foi pragmático: o bridge automático estava consumindo muito tempo para resolver identidade e sessão antes de entregar a necessidade real da mesa. A arquitetura não foi apagada; ela foi classificada como deferred e saiu do caminho crítico.

## 6. Mudança de estratégia: produto utilizável antes da automação perfeita

A estratégia foi então simplificada em duas frentes independentes: uma credencial humana estável para entrar no Gravewright e um pacote manual, explícito e auditável para transferir ficha do KALLISTIS para o runtime.

- Identidade: acesso por frase/palavra, reutilizável em qualquer navegador, sem depender de cookie como identidade.
- Personagem: exportação JSON manual do KALLISTIS e importação manual no Gravewright.
- KALLISTIS continua sendo a fonte canônica; o Gravewright recebe uma cópia de runtime.
- A sessão Gravewright pode desaparecer e ser recriada pela mesma frase sem criar outro usuário.
- A ficha pode ser importada sem expor senha KALLISTIS, cookie, token Supabase ou segredo do serviço.
## 7. Acesso por frase KALLISTIS

O repositório hoje contém um mecanismo completo de autenticação por frase no Gravewright. Ele foi criado para aproveitar a lógica humana de acesso por palavras já conhecida no ecossistema KALLISTIS, sem armazenar as frases reais no código.

- Commit 6185c2a — add KALLISTIS player phrase access.
- Commit bab5572 — allow admin phrase access.
- Modelo KallistisPlayerAccess com player_code, digest de lookup, hash de verificação e revogação.
- Normalização de frase com strip + casefold.
- Digest HMAC para localizar o registro e hash Django para confirmar a frase.
- Rota /login/player e endpoint /api/auth/player-login.
- 25 acessos de jogadores e 1 acesso administrativo provisionados no banco real.
- As contas criadas para esse fluxo podem ter senha inutilizável; email não é exigido na UI.
- Tentativa inválida ou frase revogada recebe invalid_credentials sem revelar se o usuário existe.
- A sessão final é uma sessão Django normal; a frase é a credencial para recriar a identidade, não o ID primário.
O fluxo administrativo foi provado em navegador real, incluindo reload da sessão. A mesma infraestrutura atende participantes e proprietário, evitando um segundo mecanismo de login apenas para o Mestre.

## 8. Identidade visual KALLISTIS dentro do Gravewright

Depois da base mecânica e de identidade, o Gravewright recebeu a camada visual KALLISTIS sem transformar conteúdo de cena em tema.

- Commit 678bc68 — identidade visual KALLISTIS aplicada ao Gravewright.
- Commit 155801c — atualização de branding do painel.
- Commit 2aa9578 — paleta KALLISTIS efetivamente carregada na mesa.
- Logo, hero, favicon, apple-touch icon e metadados de compartilhamento foram integrados.
- A UI passou a usar os tokens roxos do KALLISTIS.
- A arte dourada observada na cena Gate 03C foi preservada porque pertence ao conteúdo da cena, não ao chrome do VTT.
## 9. Transferência manual de personagem

O KALLISTIS ganhou uma exportação explícita para runtime Gravewright e o Gravewright ganhou o importador correspondente. O contrato foi desenhado para permitir inclusive uma ficha válida ainda não publicada, sem transformar a cópia de runtime em versão canônica.

### 9.1 Contrato de exportação

- schema = kallistis.gravewright.character
- schema_version = 1
- export_mode = manual_runtime_snapshot
- source_state preservado exatamente como no KALLISTIS
- canonical = false permitido
- player.email pode ser null
- kallistis_character_id é preservado como chave externa
- campos sensíveis são rejeitados; senha, token, cookie e segredo não fazem parte do pacote
A ficha real usada para a prova atual é 'esquecido', ID KALLISTIS cmu657xqwme2tl, source_state=submitted, canonical=false, Mesa de origem AMIGOS ONLINE.

### 9.2 Importador Gravewright

- gravewright/actors/kallistis_import.py valida schema, tamanho, profundidade e presença de campos sensíveis.
- GET /api/kallistis/import/options lista apenas campanhas em que o usuário autenticado é GM e seus memberships de jogadores ativos.
- POST /api/kallistis/import/preview valida o JSON sem escrever no banco.
- POST /api/kallistis/import/confirm executa a criação em transaction.atomic().
- KallistisCharacterLink mantém vínculo único entre kallistis_character_id e Actor.
- O Actor recebe permission owner para o jogador selecionado.
- A segunda importação do mesmo kallistis_character_id é rejeitada como already_imported.
- Os testes existentes cobrem rollback transacional, duplicata, autorização de GM, jogador fora da campanha, canonical=false e email nulo.
## 10. Estado do E2E de personagem

O E2E já avançou além da autenticação: um jogador real entrou com frase, acessou a campanha correta e o Mestre chegou ao upload da ficha real. O primeiro bloqueador observado foi CSRF antes do preview.

- Jogador real testado: JOGADOR-15.
- User Gravewright resolvido: 279aa2d5-7e22-459e-859b-525eaa08610c.
- Campanha alvo: Gate 03B Mesa KALLISTIS, ID d366d443-2ca0-4ce3-9c5b-e5638d312266.
- Membership alvo validado: 16.
- A ficha real 'esquecido' chegou ao fluxo de upload.
- Nenhum Actor ou KallistisCharacterLink foi criado durante as tentativas bloqueadas.
- Contagem preservada no último gate: 2 Actors e 0 links KALLISTIS.
### 10.1 Incidente CSRF atual

O primeiro diagnóstico encontrou um mismatch real: em HTTPS o cookie se chama __Host-gravewright-csrf, enquanto o JS antigo procurava gravewright-csrf. A correção foi aplicada para obter o token pelo endpoint oficial GET /api/security/csrf, sem desabilitar o middleware nem usar csrf_exempt.

- O módulo público atual já aponta para workspace.js?v=20260921-csrf4.
- O arquivo público servido contém a nova chamada /api/security/csrf e não contém o lookup antigo no handler de importação.
- Mesmo assim, a sessão de navegador usada no gate continuou disparando diretamente o POST antigo e recebeu 403 invalid_csrf_token.
- Não foi encontrado service worker, navigator.serviceWorker, Cache Storage ou PWA cache no repositório.
- O próximo passo correto é testar um contexto de navegador realmente limpo e, se o GET continuar ausente, capturar o Initiator e call stack do POST 403 para descobrir qual código efetivamente está executando.
- Não há autorização técnica para continuar criando versões csrf5, csrf6 ou novos patches sem essa evidência.
Importante: esse patch CSRF está hoje somente no checkout autoritativo da Mini. Ele passou nos testes direcionados, Django check, migration check e JS check, mas ainda não foi commitado nem enviado. O GitHub continua em 79c301d até que o E2E real passe.

## 11. Estrutura do repositório KALLISTIS/Gravewright

Os principais pontos do fork podem ser inspecionados diretamente no repositório. O código KALLISTIS não está concentrado em um único 'plugin'; ele atravessa os domínios nativos onde a responsabilidade realmente pertence.

- gravewright/accounts/ — autenticação, frase KALLISTIS, identity, handoff e provisionamento.
- gravewright/accounts/kallistis.py — contratos de integração e leitura KALLISTIS.
- gravewright/accounts/management/commands/provision_kallistis_players.py — provisionamento controlado dos acessos por frase.
- gravewright/accounts/migrations/0004_kallistisidentity.py, 0005_kallistisplayeraccess.py e 0006_admin_phrase_access.py — persistência de identidade e acesso.
- gravewright/campaigns/migrations/0004_kallistiscampaignlink.py — vínculo de campanha da fase de integração automática.
- gravewright/actors/kallistis_import.py — contrato de importação de ficha.
- gravewright/actors/migrations/0004_kallistischaracterlink.py — vínculo único ficha KALLISTIS ↔ Actor.
- gravewright/actors/runtime.py — estado e comandos persistidos do runtime KALLISTIS.
- gravewright/rules/kallistis_runtime.py — camada central de regras.
- gravewright/dice/kallistis.py — resolução Luz/Escuridão, predominância e ressonância.
- gravewright/combat/services.py — integração do combate com runtime canônico.
- gravewright/realtime/ — transporte, presença e provas multi-cliente.
- gravewright/web/ e gravewright/table/ — identidade visual, superfícies e carregamento dos módulos.
- docs/kallistis/ — guia de regras, checklist, questões abertas e estado autoritativo.
- docs/KALLISTIS_RULESET_FULL_MATRIX_2026-09-18.md — matriz de convergência do ruleset.
- docs/RELATORIO-KALLISTIS-GRAVEWRIGHT-2026-09-20.md — relatório da entrega de acesso por frase e identidade visual.
## 12. Marcos de commit que contam a história

- bf5d951 — compatibilidade Redis/Channels.
- 3f4261e — core roll KALLISTIS.
- 94f940e — semântica completa dos dados.
- 34122e5 — testes e ações.
- d9e2ecb — SSO handoff.
- fd3c53c — recursos e condições.
- 16c30c4 — combate mínimo.
- 7b946f5 — provisionamento a partir do handoff.
- 2390a9a — assinatura server-to-server.
- c5e2023 — Actor como autoridade server-side das rolagens.
- 3e47700 — runtime autoritativo dos Povos.
- 678bc68 — identidade visual KALLISTIS.
- f2bd2c9 — fechamento da convergência do ruleset.
- 6185c2a — acesso por frase dos jogadores.
- bab5572 — acesso administrativo por frase.
- 155801c — branding do painel.
- 2aa9578 — paleta aplicada à mesa.
- 79c301d — relatório de entrega versionado.
## 13. O que tentamos, o que abandonamos e por quê

O percurso teve mudanças de estratégia importantes. Elas não são dívida escondida; fazem parte do aprendizado arquitetural e estão preservadas no histórico.

- SSO/handoff automático: implementado parcialmente e preservado, mas retirado do caminho crítico porque sessão, cookie, identity, provisionamento e Mesa formavam uma cadeia operacional muito frágil para a necessidade imediata.
- Provisionamento automático de campanha: substituído, no fluxo atual, por seleção de campanha existente e importação explícita; evitamos duplicar campanhas e memberships silenciosamente.
- Google OAuth: considerado como identidade durável, mas descartado por aumentar a complexidade e introduzir dependência desnecessária.
- Pacote de ativação preso ao navegador: descartado por não ser uma identidade sustentável entre dispositivos.
- Frase KALLISTIS: escolhida por ser humana, estável, independente de navegador e compatível com contas Gravewright sem senha utilizável.
- Exportação manual de ficha: escolhida como caminho robusto e auditável enquanto a sincronização automática permanece opcional e futura.
## 14. Relação com a release oficial v0.1.1

A release oficial v0.1.1 merece destaque porque foi republicada mantendo o mesmo número de versão. A tag atual aponta para 04a1b666 e inclui, entre outras mudanças, sheets de sistemas integradas à janela nativa, ativação do sistema da mesa, suporte explícito a apps Django externos confiáveis, correções ASGI e controles independentes de textos traduzidos.

Nosso master contém esse commit como ancestral direto. Portanto não há uma atualização v0.1.1 faltando para instalar. Pelo contrário: o fork atual está 43 commits à frente dessa base. Por isso o atualizador interno do Gravewright não deve ser usado cegamente no runtime KALLISTIS; qualquer nova release upstream deve seguir o fluxo controlado de comparação, testes, prova real e merge.

Um ponto interessante para o futuro é GRAVEWRIGHT_SERVER_APPS / GRAVEWRIGHT_SERVER_APP_PATHS. O upstream agora oferece uma extensão server-side oficial para apps Django confiáveis. Isso abre uma rota possível para isolar partes da ponte KALLISTIS do core em uma refatoração futura, sem necessidade de fazer isso durante o fechamento do E2E atual.

## 15. Princípios arquiteturais que ficaram consolidados

- KALLISTIS continua sendo a autoridade do jogo; Gravewright executa a sessão.
- Atributos, perícias, recursos e efeitos que participam da resolução não podem depender do cliente.
- O browser não é prova suficiente quando o banco, realtime e permissões ainda não foram verificados.
- Migrations e vínculos externos devem ser aditivos e idempotentes.
- Não esconder falhas por mocks, fixtures artificiais ou fallbacks que não existam no produto.
- Não aplicar upstream diretamente no runtime customizado.
- Preferir módulos e APIs oficiais antes de core patches sempre que a arquitetura permitir.
- Uma correção só fecha quando o fluxo humano real funciona; teste estático sozinho não encerra o gate.
- Quando a complexidade de integração ameaça bloquear o produto, preservar autoridade e escolher um caminho manual explícito pode ser superior a uma automação incompleta.
## 16. Estado atual — o que está fechado e o que ainda falta

### Fechado / provado

- Fork alinhado à release upstream v0.1.1 atual e 43 commits à frente.
- Runtime Gravewright funcional na Mini e superfície pública respondendo.
- Ruleset KALLISTIS convergido e suíte completa fechada no respectivo gate.
- Autenticação por frase de jogadores e administrador.
- 25 memberships de jogadores e GM preservado na campanha de prova.
- Identidade visual KALLISTIS.
- Exportação manual KALLISTIS em schema v1.
- Importador Gravewright implementado e testado.
- Vínculo KallistisCharacterLink e proteção contra duplicação.
- Nenhuma corrupção ou mutação parcial causada pelos gates de importação bloqueados.
### Aberto imediatamente

- Provar o handler CSRF novo em um contexto de navegador realmente limpo.
- Se ainda houver POST direto sem GET /api/security/csrf, capturar Initiator e call stack antes de qualquer novo patch.
- Obter preview 200 do JSON real de 'esquecido'.
- Confirmar importação real uma única vez e verificar Actor + KallistisCharacterLink + owner correto.
- Reentrar como JOGADOR-15 pela mesma frase e provar visibilidade, controle e persistência do Actor.
- Somente depois do PASS E2E: commit da correção CSRF e push.
### Possíveis passos posteriores, não bloqueadores

- Isolar a ponte KALLISTIS em um GRAVEWRIGHT_SERVER_APP, se isso reduzir manutenção futura.
- Revisar e eventualmente remover superfícies antigas de SSO/handoff que permanecerem sem uso.
- Preparar o fork para abertura pública somente após auditoria de segredos, dados reais e histórico Git.
- Manter uma política explícita de sincronização com novas releases upstream.
## 17. Como eu sugeriria ao Ricardo inspecionar o trabalho

Para entender rapidamente a extensão do trabalho sem ler o histórico inteiro, a melhor ordem é:

- Abrir o fork NomosLudens/gravewright e comparar seu master com a tag upstream v0.1.1.
- Ler docs/RELATORIO-KALLISTIS-GRAVEWRIGHT-2026-09-20.md para o estado de autenticação e branding.
- Ler docs/KALLISTIS_RULESET_FULL_MATRIX_2026-09-18.md para a visão de regras, testes e limites de autoridade.
- Ler docs/KALLISTIS_UPSTREAM_POLICY.md para entender como tratamos atualizações oficiais.
- Inspecionar gravewright/rules/kallistis_runtime.py, gravewright/actors/runtime.py e gravewright/dice/kallistis.py para o núcleo mecânico.
- Inspecionar gravewright/accounts/services.py e KallistisPlayerAccess para o login por frase.
- Inspecionar gravewright/actors/kallistis_import.py e KallistisCharacterLink para o fluxo de personagem.
## 18. Links principais

[Repositório KALLISTIS/Gravewright no GitHub](https://github.com/NomosLudens/gravewright)

[Upstream oficial do Gravewright](https://github.com/Gravewright/gravewright)

[Release oficial Gravewright v0.1.1](https://github.com/Gravewright/gravewright/releases/tag/v0.1.1)

[Instância pública do Gravewright KALLISTIS](https://gravewright.kallistis.app)

## 19. Encerramento

O ponto principal deste percurso é que a integração deixou de ser uma prova conceitual. Existe um fork real, derivado do upstream atual, com regras server-side, realtime, identidade por frase, UI KALLISTIS, contratos de importação e documentação de gates. Também existe um histórico explícito das abordagens que não valeram o custo operacional e foram conscientemente retiradas do caminho crítico.

O único fechamento imediato ainda pendente é provar, em navegador limpo, o caminho CSRF já corrigido no código e então concluir o E2E frase → jogador → ficha → Actor → controle → persistência. Até esse ponto passar, a correção permanece local e o master público continua estável em 79c301d.

A intenção deste documento é permitir que Ricardo veja tanto o resultado quanto o processo: onde o Gravewright oficial foi preservado, onde o KALLISTIS precisou estendê-lo, quais decisões foram revertidas e quais partes hoje já são produto funcional.
