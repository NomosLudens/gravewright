













(function () {
    const FALLBACK_LABELS = {
        start: "Start combat",
        end: "End combat",
        empty: "No combat is active in this table.",
        noCombatants: "Nobody in the order yet.",
        inactive: "Out of combat",
        waitingGm: "Waiting for the GM.",
        round: "Round",
        turn: "Turn",
        initiative: "Side initiative",
        friendly: "Friendly side",
        hostile: "Hostile side",
        unassigned: "Assign side",
        activations: "Activations per round",
        rollSides: "Roll side representatives",
        chooseFirst: "Winner: choose which side acts first",
        firstFriendly: "Friendly side first",
        firstHostile: "Hostile side first",
        representatives: "Representatives",
        winner: "Initiative winner",
        sideScore: "Side total",
        rollOne: "Roll this side representative",
        setInitiative: "Side initiative",
        previousTurn: "Previous turn",
        nextTurn: "Next turn",
        previousRound: "Previous round",
        nextRound: "Next round",
        addSelected: "Add selected tokens",
        actions: "Combatant actions",
        centerToken: "Center token",
        openSheet: "Open sheet",
        setTurn: "Give the turn",
        remove: "Remove from combat",
        hide: "Hide from players",
        reveal: "Show to players",
        markDefeated: "Mark as defeated",
        clearDefeated: "Clear defeated",
        nextUp: "Next",
        moveUp: "Move up",
        moveDown: "Move down",
    };

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text != null) node.textContent = String(text);
        return node;
    }

    function icon(name) {
        const source=document.querySelector("#combat-icons")?.content.querySelector(`[data-combat-icon="${safeIcon(name)}"] svg`);
        const node=source?source.cloneNode(true):el("span");
        node.setAttribute("aria-hidden", "true");
        return node;
    }

    function safeIcon(value) {
        const text = String(value || "").trim().toLowerCase();
        const prefixed = text.startsWith("ph-") ? text : `ph-${text}`;
        const clean = prefixed.replace(/[^a-z0-9-]/g, "").slice(0, 48);
        return clean.length > 3 ? clean : "ph-dice-five";
    }



    function labelsFor(panel) {
        const data = panel?.dataset || {};
        const out = { ...FALLBACK_LABELS };
        Object.keys(FALLBACK_LABELS).forEach((key) => {
            const value = data[`label${key.charAt(0).toUpperCase()}${key.slice(1)}`];
            if (value) out[key] = value;
        });
        return out;
    }

    function systemId(state) {
        return String(state?.config?.system_id || "");
    }

    function dispatch(state, name, payload) {
        return window.GravewrightCombat?.dispatch?.(systemId(state), name, payload);
    }

    function slot(state, name, payload) {
        return window.GravewrightCombat?.renderSlot?.(systemId(state), name, payload) || [];
    }

    function initiativeLabel(state, L) {
        return state?.config?.label || L.initiative;
    }

    function initiativeIcon(state) {
        return safeIcon(state?.config?.icon || "ph-dice-five");
    }

    function button(action, iconName, title, { primary = false, danger = false, disabled = false, data = {} } = {}) {
        const btn = el("button", "gw-combat-icon"
            + (primary ? " gw-combat-icon--primary" : "")
            + (danger ? " gw-combat-icon--danger" : ""));
        btn.type = "button";
        btn.title = title;
        btn.setAttribute("aria-label", title);
        btn.disabled = disabled;
        btn.dataset.combatAction = action;
        Object.entries(data).forEach(([key, value]) => { btn.dataset[key] = String(value); });
        btn.appendChild(icon(iconName));
        return btn;
    }

    function menuItem(action, iconName, text, { danger = false, data = {} } = {}) {
        const btn = el("button", "gw-combat-menu-item" + (danger ? " gw-combat-menu-item--danger" : ""));
        btn.type = "button";
        btn.dataset.combatAction = action;
        Object.entries(data).forEach(([key, value]) => { btn.dataset[key] = String(value); });
        btn.append(icon(iconName), el("span", null, text));
        return btn;
    }

    function portrait(combatant) {
        const wrap = el("span", "gw-combat-combatant__portrait");
        if (combatant.portrait_url) {
            const img = document.createElement("img");
            img.src = combatant.portrait_url;
            img.alt = "";
            img.loading = "lazy";
            wrap.appendChild(img);
        } else {
            const initial = String(combatant.name || "?").trim().charAt(0).toUpperCase() || "?";
            wrap.appendChild(el("span", "gw-combat-combatant__initial", initial));
        }
        if (combatant.defeated) {
            const defeated=icon('ph-skull');
            defeated.classList.add('gw-combat-combatant__defeated-icon');
            wrap.appendChild(defeated);
        }
        return wrap;
    }




    function resourceBar(bar) {
        if (!bar) return null;
        const percent = bar.percent == null ? 0 : Math.max(0, Math.min(100, Number(bar.percent) || 0));
        const level = percent <= 25 ? "is-critical" : (percent <= 50 ? "is-wounded" : "is-healthy");
        const wrap = el("div", `gw-combat-bar ${level}`);
        const track = el("span", "gw-combat-bar__track");
        const fill = el("span", "gw-combat-bar__fill");
        fill.style.width = `${percent}%`;
        track.appendChild(fill);
        wrap.append(track, el("span", "gw-combat-bar__value", `${bar.value ?? "-"}/${bar.max ?? "-"}`));
        return wrap;
    }



    function initiativeCell(combatant, state, isGm, L) {
        const wrap = el("div", "gw-combat-combatant__side-config");
        const side = isGm ? document.createElement("select") : el("span", "gw-combat-combatant__score");
        if (isGm) {
            side.setAttribute("aria-label", `${L.initiative}: ${combatant.name}`);
            side.disabled = !!state.active;
            side.dataset.combatSide = combatant.id;
            [["", L.unassigned], ["friendly", L.friendly], ["hostile", L.hostile]].forEach(([value, label]) => {
                const option = document.createElement("option"); option.value = value; option.textContent = label; side.append(option);
            });
            side.value = combatant.side || "";
        } else {
            side.textContent = combatant.side === "friendly" ? L.friendly : combatant.side === "hostile" ? L.hostile : L.unassigned;
        }
        const score = el("span", "gw-combat-combatant__score", combatant.side_score == null ? "–" : String(combatant.side_score));
        score.title = `${L.sideScore}: ${combatant.side === "friendly" ? L.friendly : L.hostile}`;
        wrap.append(side, score);
        if (isGm) {
            const activations = document.createElement("input");
            activations.type = "number"; activations.min = "1"; activations.max = "12"; activations.step = "1";
            activations.value = String(combatant.activations || 1); activations.disabled = !!state.active;
            activations.title = L.activations; activations.setAttribute("aria-label", `${L.activations}: ${combatant.name}`);
            activations.dataset.combatActivations = combatant.id;
            wrap.append(activations);
        }
        return wrap;
    }

    function combatantMenu(combatant, state, isGm, L) {
        const wrap = el("div", "gw-combat-combatant__actions");
        slot(state, "combatantActions", { combatant, state, isGm }).forEach((node) => wrap.appendChild(node));

        const menu = el("details", "gw-combat-menu");
        const trigger = el("summary", "gw-combat-menu__trigger");
        trigger.title = L.actions;
        trigger.setAttribute("aria-label", L.actions);
        trigger.appendChild(icon("ph-dots-three-outline-vertical"));
        menu.appendChild(trigger);

        const list = el("div", "gw-combat-menu__list");
        if (combatant.token_id) {
            list.append(
                menuItem("token/focus", "ph-crosshair", L.centerToken, { data: { tokenId: combatant.token_id } }),
                menuItem("token/sheet", "ph-identification-card", L.openSheet, { data: { tokenId: combatant.token_id } }),
            );
        }
        if (isGm) {
            const id = { combatantId: combatant.id };
            if (combatant.can_move_up) {
                list.appendChild(menuItem("order/up", "ph-arrow-up", L.moveUp, { data: id }));
            }
            if (combatant.can_move_down) {
                list.appendChild(menuItem("order/down", "ph-arrow-down", L.moveDown, { data: id }));
            }
            list.append(
                menuItem("turn/set", "ph-flag", L.setTurn, { data: id }),
                menuItem(
                    "flags/hidden",
                    combatant.hidden ? "ph-eye" : "ph-eye-slash",
                    combatant.hidden ? L.reveal : L.hide,
                    { data: { ...id, value: combatant.hidden ? "0" : "1" } },
                ),
                menuItem(
                    "flags/defeated",
                    combatant.defeated ? "ph-arrow-counter-clockwise" : "ph-skull",
                    combatant.defeated ? L.clearDefeated : L.markDefeated,
                    { data: { ...id, value: combatant.defeated ? "0" : "1" } },
                ),
                menuItem("combatants/remove", "ph-x", L.remove, { danger: true, data: id }),
            );
        }
        if (list.children.length) menu.appendChild(list); else return wrap;
        wrap.appendChild(menu);
        return wrap;
    }

    function combatantRow(combatant, state, isGm, L) {
        const row = el("article", "gw-combat-combatant");
        if (combatant.is_current) row.classList.add("is-current");
        if (combatant.is_next) row.classList.add("is-next");
        if (combatant.has_acted) row.classList.add("has-acted");
        if (combatant.defeated) row.classList.add("is-defeated");
        if (combatant.hidden) row.classList.add("is-hidden-combatant");
        row.dataset.combatantId = combatant.id;
        row.dataset.tokenId = combatant.token_id || "";

        row.append(el("span", "gw-combat-combatant__position", combatant.position), portrait(combatant));

        const main = el("div", "gw-combat-combatant__main");
        main.appendChild(el("span", "gw-combat-combatant__name", combatant.name || "???"));

        const meta = [];
        if (combatant.conditions_count) meta.push(`${combatant.conditions_count} ⊘`);
        if (combatant.effects_count) meta.push(`${combatant.effects_count} ✦`);
        const extra = dispatch(state, "combatantMeta", { combatant, state, isGm });
        (Array.isArray(extra) ? extra : [extra]).forEach((item) => {
            const text = String(item || "").trim();
            if (text) meta.push(text);
        });
        if (meta.length) main.appendChild(el("span", "gw-combat-combatant__meta", meta.join(" · ")));

        const bar = resourceBar(combatant.bar);
        if (bar) main.appendChild(bar);
        row.appendChild(main);

        row.append(initiativeCell(combatant, state, isGm, L), combatantMenu(combatant, state, isGm, L));
        return row;
    }

    function header(state, L, active) {
        const wrap = el("header", "gw-combat-header");
        if (!active) {
            wrap.appendChild(el("strong", "gw-combat-header__title", L.inactive));
            return wrap;
        }
        wrap.appendChild(el("strong", "gw-combat-header__title", `${L.round} ${state.round}`));
        const current = state.current_name || "-";
        wrap.appendChild(el("span", "gw-combat-header__current", current));
        if (state.next_name && state.next_name !== current) {
            wrap.appendChild(el("span", "gw-combat-header__next", `${L.nextUp}: ${state.next_name}`));
        }
        return wrap;
    }

    function toolbar(panel, state, L, active) {
        const selected = Number(panel.dataset.selectedTokenCount || 0);
        const bar = el("div", "gw-combat-toolbar");
        bar.append(
            button(active ? "end" : "start", active ? "ph-stop" : "ph-play", active ? L.end : L.start, { disabled: !active && !state?.config?.first_side }),
            button("combatants/add-selected", "ph-plus-circle",
                selected ? `${L.addSelected} (${selected})` : L.addSelected, { disabled: selected < 1 }),
            button("turn/previous", "ph-caret-left", L.previousTurn, { disabled: !active }),
            button("turn/next", "ph-caret-right", L.nextTurn, { primary: true, disabled: !active }),
            button("combatants/add-actor", "ph-user-plus", "Add actor"),
            button("round/previous", "ph-arrow-counter-clockwise", L.previousRound, { disabled: !active || state.round <= 1 }),
            button("round/next", "ph-arrow-clockwise", L.nextRound, { disabled: !active }),
        );
        slot(state, "toolbar", { panel, state, isGm: true }).forEach((node) => bar.appendChild(node));
        return bar;
    }


    function initiativeSetup(state, L, isGm) {
        const setup = el("section", "gw-combat-initiative-setup");
        const roster = Array.isArray(state?.combatants) ? state.combatants : [];
        const representatives = el("div", "gw-combat-initiative-setup__representatives");
        representatives.appendChild(el("strong", null, L.representatives));
        for (const side of ["friendly", "hostile"]) {
            const select = document.createElement("select");
            select.dataset.initiativeRepresentative = side;
            const rows = roster.filter((row) => row.side === side && !row.defeated);
            rows.forEach((row) => {
                const option = document.createElement("option");
                option.value = row.id; option.textContent = row.name; select.append(option);
            });
            select.disabled = !isGm || !!state.active || !rows.length;
            select.setAttribute("aria-label", side === "friendly" ? L.friendly : L.hostile);
            representatives.appendChild(select);
        }
        if (isGm && !state.active) {
            setup.append(representatives, button("initiative/roll-sides", "ph-dice-five", L.rollSides, {
                primary: true,
                disabled: !roster.some((row) => row.side === "friendly" && !row.defeated) || !roster.some((row) => row.side === "hostile" && !row.defeated),
            }));
        }
        const result = state?.config?.side_initiative;
        if (result?.totals) {
            setup.appendChild(el("p", "gw-combat-initiative-setup__result",
                `${L.friendly}: ${result.totals.friendly} · ${L.hostile}: ${result.totals.hostile} · ${L.winner}: ${result.winner === "friendly" ? L.friendly : L.hostile}`));
            if (isGm && !state.active) {
                setup.appendChild(el("p", null, L.chooseFirst));
                setup.append(
                    button("initiative/first-side", "ph-arrow-right", L.firstFriendly, { data: { side: "friendly" } }),
                    button("initiative/first-side", "ph-arrow-right", L.firstHostile, { data: { side: "hostile" } }),
                );
            }
            if (result.firstSide) setup.appendChild(el("p", "gw-combat-initiative-setup__result",
                `First: ${result.firstSide === "friendly" ? L.friendly : L.hostile}`));
        }
        return setup;
    }

    function activationSequence(state) {
        const sequence = Array.isArray(state?.turn_order) ? state.turn_order : [];
        if (!state?.active || !sequence.length) return null;
        const strip = el("div", "gw-combat-activation-sequence");
        sequence.forEach((slot, index) => {
            const item = el("span", "gw-combat-activation-sequence__item", `${index + 1}. ${slot.name}`);
            item.classList.toggle("is-current", !!slot.current);
            item.classList.add(slot.side === "friendly" ? "is-friendly" : "is-hostile");
            strip.appendChild(item);
        });
        return strip;
    }

    function renderPanel(panel, state) {
        const target = panel.querySelector("[data-combat-state]");
        if (!target) return;
        const L = labelsFor(panel);
        const isGm = panel.dataset.isGm === "true";
        const active = !!state?.active;
        const combatants = Array.isArray(state?.combatants) ? state.combatants : [];

        dispatch(state, "beforeRender", { panel, state, isGm });
        target.innerHTML = "";
        target.classList.toggle("is-active", active);
        if (state?.config?.accent) target.style.setProperty("--gw-combat-accent", state.config.accent);

        target.appendChild(header(state, L, active));
        const sequence = activationSequence(state);
        if (sequence) target.appendChild(sequence);
        if (isGm) {
            target.appendChild(toolbar(panel, state, L, active));
            if (!active) target.appendChild(initiativeSetup(state, L, isGm));
        }

        const list = el("div", "gw-combat-list");
        if (!combatants.length) {
            const empty = el("div", "tool-empty gw-combat-empty");
            empty.appendChild(icon("ph-sword"));
            empty.appendChild(el("p", null, active ? L.noCombatants : (isGm ? L.empty : L.waitingGm)));
            list.appendChild(empty);
        } else {
            combatants.forEach((combatant) => list.appendChild(combatantRow(combatant, state, isGm, L)));
        }
        target.appendChild(list);

        dispatch(state, "afterRender", { panel, state, target, isGm });
    }


    if (!window.GravewrightCombatPanel) {
        window.GravewrightCombatPanel = { renderPanel };
    }
})();
