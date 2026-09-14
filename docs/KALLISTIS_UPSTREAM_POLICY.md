# KALLISTIS upstream policy

The official Gravewright project is the upstream source of the fork baseline.

```text
UPSTREAM=Gravewright/gravewright
UPSTREAM_BRANCH=main

ORIGIN=NomosLudens/gravewright
PRODUCTION_BRANCH=master
PRODUCTION_HOST=BABY

DIRECT_UPSTREAM_DEPLOY=FORBIDDEN
AUTO_UPSTREAM_DEPLOY=NO
```

Upstream changes are handled through this controlled flow:

```text
fetch upstream
→ sync/upstream-X.Y.Z
→ divergence review
→ tests
→ real browser proof
→ merge master
→ deploy Baby
```

Baby consumes only `origin/master`. It never pulls `upstream/main` directly.

KALLISTIS customization priority:

```text
1. Gravewright module
2. Official API
3. External bridge
4. Core patch
```

Core patches are the last resort. Keep custom behavior isolated to minimize
future upstream conflicts. The Gravewright updater may report and stage
releases, but it does not authorize automatic upstream deployment.
