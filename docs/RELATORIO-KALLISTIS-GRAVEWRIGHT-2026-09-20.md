# Relatório completo — Gravewright × KALLISTIS

Data da verificação: 2026-09-20
Runtime autoritativo: `kaline-mini:/home/tonyus-dev/gravewright`
Serviço: `gravewright.service`
Repositório: `github.com/NomosLudens/gravewright`
Branch: `master`

## Resultado executivo

`PASS` para os objetivos concluídos nesta intervenção:

- o administrador Tony entra no Gravewright usando somente a frase de acesso;
- o login por e-mail/senha não é utilizável para essa conta;
- as 25 frases de acesso dos jogadores foram provisionadas sem registrar frases em texto claro;
- a frase administrativa foi separada do slot do jogador 15;
- o fluxo real autenticado chegou ao painel `/inside` e permaneceu autenticado após reload;
- a identidade visual KALLISTIS foi aplicada ao painel e à mesa;
- o repositório autoritativo foi publicado no GitHub;
- nenhum mapping, handoff, DNS, Tunnel, Cloudflare ou código do KALLISTIS foi alterado nesta etapa visual/authenticated.

O dourado ainda visível na imagem da mesa não pertence ao tema do Gravewright: está incorporado na arte da cena `Gate 03C`, renderizada em canvas. A paleta da interface foi alterada para roxo KALLISTIS; a arte da cena foi preservada como dado de conteúdo.

## Autoridade e estado final

Toda alteração foi feita no checkout efetivamente usado por `gravewright.service`:

```text
Host: kaline-mini
WorkingDirectory: /home/tonyus-dev/gravewright
ExecStart: /home/tonyus-dev/gravewright/.venv/bin/daphne -b 127.0.0.1 -p 3000 config.asgi:application
Service: active
```

Estado Git final:

```text
HEAD: 2aa9578 fix: apply kallistis palette to table
origin/master: 2aa9578
WORKTREE: clean
```

O GitHub confirmou o mesmo SHA em `refs/heads/master`.

## Histórico de commits desta intervenção

### `6185c2a` — `feat: add KALLISTIS player phrase access`

Implementou o primeiro fluxo de acesso por frase:

- modelo `KallistisPlayerAccess`;
- digest HMAC para localizar o acesso;
- hash Django para verificar a frase;
- rota web `/login/player`;
- endpoint `/api/auth/player-login`;
- formulário sem campos de e-mail e senha;
- provisionamento controlado das 25 identidades;
- testes para login, revogação, ausência de plaintext e sessão.

### `bab5572` — `feat: allow admin phrase access`

Estendeu o mesmo fluxo para o proprietário sem criar um segundo mecanismo:

- código interno `ADMIN-TONY` permitido pela constraint;
- migration `0006_admin_phrase_access`;
- teste de login por frase de um usuário `owner`;
- textos da interface alterados de “jogador” para “frase de acesso”.

### `155801c` — `feat: refresh kallistis panel branding`

Aplicou o logo fornecido:

- novo asset `hero-logo.png`;
- logo no cabeçalho do painel;
- hero padrão nas capas de mesas sem imagem;
- favicon e apple-touch icon;
- metadados Open Graph/Twitter para miniatura;
- remoção do wordmark/cristal visual antigo;
- cache-busting visual.

### `2aa9578` — `fix: apply kallistis palette to table`

Corrigiu a última divergência de cache na página da mesa:

- `/table/jinja2/gravewright_table/page.html` passou a carregar `kallistis-theme.css?v=20260920-hero`;
- isso faz a mesa usar efetivamente os tokens roxos publicados, em vez do tema dourado cacheado.

## Autenticação por frase

### Contrato final

O administrador utiliza a superfície pública:

```text
/login/player
```

O formulário contém somente o campo de frase de acesso. O fluxo real observado foi:

```text
frase de acesso
→ sessão Gravewright
→ /inside
→ painel administrativo
```

Após recarregar a página, a URL permaneceu em `/inside` e o painel continuou disponível.

### Segurança do armazenamento

- nenhuma frase real foi adicionada ao Git;
- nenhuma frase real foi adicionada ao relatório;
- a tabela guarda somente digest de lookup e hash de verificação;
- a conta administrativa ficou sem senha utilizável;
- o e-mail da conta permanece apenas como identificador interno obrigatório do modelo e não é campo nem requisito do login por frase;
- nenhum cookie, token, Authorization ou segredo foi publicado.

### Identidades provisionadas

```text
KALLISTIS_PLAYER_ACCESS_COUNT=26
JOGADORES=25
ADMIN=1
ADMIN_ROLE=owner
ADMIN_GM_MEMBERSHIP=preserved
PLAYER_15_ADMIN_PHRASE_COLLISION=NO
```

O registro de proprietário sintético existente foi reutilizado para Tony, preservando o vínculo GM da mesa, porque o modelo permite apenas um proprietário ativo.

## Banco e dados reais

Migration aplicada no banco autoritativo:

```text
gravewright_accounts.0005_kallistisplayeraccess [X]
gravewright_accounts.0006_admin_phrase_access [X]
```

Dados observados após o provisionamento:

```text
CAMPAIGN=Gate 03B Mesa KALLISTIS
CAMPAIGN_ID=d366d443-2ca0-4ce3-9c5b-e5638d312266
PLAYER_MEMBERSHIPS=25
OWNER_GM_MEMBERSHIP=YES
MAPPING_WRITE=NO
HANDOFF=NO
```

As únicas mutações de dados foram as autorizadas para provisionar os acessos por frase e atualizar a identidade do proprietário existente. Não houve alteração de personagem, mapping ou campanha.

## Identidade visual KALLISTIS

### Painel

O painel agora usa o logo fornecido como:

- marca do rail lateral;
- hero padrão de mesa sem capa;
- favicon;
- apple-touch icon;
- miniatura de compartilhamento via Open Graph/Twitter.

O wordmark antigo e o cristal anterior deixaram de ser usados pelos seletores principais do tema.

### Mesa

O tema efetivamente carregado no navegador foi verificado com:

```text
THEME_URL_SUFFIX=20260920-hero
ACCENT=#a980f4
GAME_LAYER_ACCENT_RGB=169, 128, 244
```

Isso cobre barra superior, abas de camada, dock, painéis, foco, bordas, presença e controles. A imagem da cena não foi filtrada nem sobrescrita porque o dourado observado nela faz parte do conteúdo visual da própria cena.

## Validação executada

### Código e migration

```text
TARGETED_TESTS=47 passed
MANAGE_CHECK=PASS
MAKEMIGRATIONS_CHECK=PASS
GIT_DIFF_CHECK=PASS
MIGRATIONS=0005 and 0006 applied
```

### Runtime

```text
SERVICE=active
LOCAL /login/player=200
PUBLIC /login/player=200
```

Houve um `502` transitório imediatamente após um restart; a origem local já respondia `200` e o endpoint público se estabilizou em `200` sem qualquer alteração de Tunnel, DNS ou Cloudflare.

### Browser real

Fluxo comprovado no navegador interno autenticado:

```text
LOGIN_BY_PHRASE=PASS
FINAL_URL=/inside
OWNER_NAME_VISIBLE=Tony
ADMIN_TABLE_VISIBLE=YES
RELOAD_SESSION=PASS
EMAIL_FIELD_ON_PHRASE_PAGE=NO
PASSWORD_FIELD_ON_PHRASE_PAGE=NO
```

Não foi usado mock, placeholder, fallback falso, dados hardcoded para simular login ou chamada HTTP anônima como substituto do fluxo.

## Arquivos principais alterados

### Autenticação

- `gravewright/accounts/models.py`
- `gravewright/accounts/migrations/0006_admin_phrase_access.py`
- `gravewright/accounts/tests/test_kallistis_player_access.py`
- `gravewright/accounts/messages.json`

### Identidade visual

- `gravewright/web/static/gravewright_web/assets/kallistis/hero-logo.png`
- `gravewright/web/jinja2/gravewright_web/base.html`
- `gravewright/web/jinja2/gravewright_web/inside/shell.html`
- `gravewright/web/jinja2/gravewright_web/inside/card.html`
- `gravewright/web/static/gravewright_web/css/kallistis-theme.css`
- `gravewright/web/static/gravewright_web/css/index.css`
- `gravewright/web/static/gravewright_web/css/blocks/campaign-card.css`
- `gravewright/table/jinja2/gravewright_table/page.html`

## Escopo explicitamente não alterado

```text
KALLISTIS_SOURCE_CODE=UNCHANGED
KALLISTIS_DEPLOY=NOT_TOUCHED
CLOUDFLARE=NOT_TOUCHED
DNS=NOT_TOUCHED
TUNNEL=NOT_TOUCHED
R2=NOT_TOUCHED
SUPABASE=NOT_TOUCHED
HYPERDRIVE=NOT_TOUCHED
GRAVEWRIGHT_DATABASE_SCHEMA_OUTSIDE_AUTH=UNCHANGED
CAMPAIGN_MAPPING=UNCHANGED
```

## Limite conhecido e próximo passo exato

Se a intenção for também recolorir o dourado que pertence à arte da cena `Gate 03C`, isso deve ser tratado como edição separada do asset/conteúdo da cena, com backup e validação visual próprios. A alteração atual deliberadamente não mascara nem deforma esse conteúdo.

Para o estado entregue, o próximo passo é apenas usar a mesa normalmente. Nenhum deploy adicional é necessário para os commits acima.

## Veredicto final

```text
REPOSITORY_UPDATED=YES
GITHUB_PUSH=YES
AUTHORITATIVE_RUNTIME=PASS
PHRASE_ONLY_ADMIN_LOGIN=PASS
REAL_BROWSER_FLOW=PASS
KALLISTIS_PURPLE_THEME=PASS
SCENE_ART_RECOLOR=NOT_EXECUTED_BY_DESIGN
MAPPING_DELTA=0
MOCKS_OR_FAKE_FALLBACKS=NONE
FINAL_STATUS=PASS_WITH_SCENE_ART_LIMITATION
```
