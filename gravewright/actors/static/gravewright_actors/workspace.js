import {
  beginTreeDrag,
  cancelTreeDrag,
  draggedItem,
  registerTreePreview,
} from "./tree-drag.js";
import {
  getPath,
  mergePatch,
} from "/static/gravewright_web/vendor/datastar-1.0.3.js";
import { directoryView } from "/static/gravewright_maps/directory.js";
import { openSheet } from "/static/gravewright_pdf_system/sheet.js";
export const clone = (id) =>
  document.getElementById(id).content.firstElementChild.cloneNode(true);
export const icon = (name) =>
  document
    .querySelector("#actor-icons")
    .content.querySelector(`[data-icon="${name}"]`)
    .firstElementChild.cloneNode(true);
const show = (el, on) => el.toggleAttribute("hidden", !on);
let menu;
export function context(event, items, label = "Directory actions") {
  event.preventDefault();
  event.stopPropagation();
  menu?.remove();
  const el = document.createElement("menu");
  menu = el;
  el.className = "gw-folder-menu directory-context-menu";
  el.setAttribute("role", "menu");
  el.setAttribute("aria-label", label);
  Object.assign(el.style, {
    position: "fixed",
    left: event.clientX + "px",
    top: event.clientY + "px",
    zIndex: 1500,
  });
  for (const item of items) {
    const li = document.createElement("li"),
      b = document.createElement("button");
    b.type = "button";
    b.setAttribute("role", "menuitem");
    b.disabled = !!item.disabled;
    if (item.danger) b.className = "is-danger";
    b.append(icon(item.icon), document.createTextNode(item.label));
    b.onclick = async (e) => {
      e.stopPropagation();
      el.remove();
      try {
        await item.run();
      } catch (error) {
        window.dispatchEvent(
          new CustomEvent("gravewright:actor-error", { detail: error.message }),
        );
      }
    };
    li.append(b);
    el.append(li);
  }
  el.onkeydown = (e) => {
    const buttons = [...el.querySelectorAll("button:not(:disabled)")],
      i = buttons.indexOf(document.activeElement);
    if (e.key === "Escape") {
      el.remove();
      e.stopPropagation();
    }
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) {
      e.preventDefault();
      buttons[
        e.key === "Home"
          ? 0
          : e.key === "End"
            ? buttons.length - 1
            : (i + (e.key === "ArrowUp" ? -1 : 1) + buttons.length) %
              buttons.length
      ]?.focus();
    }
  };
  document.body.append(el);
  const r = el.getBoundingClientRect();
  el.style.left =
    Math.max(8, Math.min(event.clientX, innerWidth - r.width - 8)) + "px";
  el.style.top =
    Math.max(8, Math.min(event.clientY, innerHeight - r.height - 8)) + "px";
  return el;
}
window.addEventListener("click", () => menu?.remove());
const panel = document.getElementById("actors-panel"),
  workspace = document.getElementById("table-workspace"),
  campaign = workspace.dataset.tableId;
const labels = JSON.parse(
  document.getElementById("map-text")?.textContent || "{}",
);
const kallistisSkills = [
  ["atletismo", "Atletismo"], ["combate", "Combate"], ["pontaria", "Pontaria"],
  ["furtividade", "Furtividade"], ["percepcao", "Percepção"],
  ["sobrevivencia", "Sobrevivência"], ["investigacao", "Investigação"],
  ["conhecimento", "Conhecimento"], ["oficio", "Ofício"],
  ["influencia", "Influência"], ["empatia", "Empatia"], ["cuidado", "Cuidado"],
  ["magia", "Magia"], ["evocacao", "Evocação"], ["velarim", "Velarim"],
];
let state = {
    actors: [],
    actorTypes: [],
    folders: [],
    templates: [],
    players: [],
    is_gm: false,
  },
  sheet,
  dialog,
  runtimeDialog,
  deletedTemplate,
  popup,
  kallistisImportDialog,
  kallistisImportPayload;
const command = (action, data) =>
  window.gravewrightRealtime.resourceCommand("actors", action, data);
async function startKallistisImport(file) {
  const raw = await file.text();
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch {
    throw Error("O arquivo não contém JSON válido.");
  }
  const data = new FormData();
  data.set("campaign_id", campaign);
  data.set("file", file);
  const response = await fetch("/api/kallistis/import/preview", {
    method: "POST",
    body: data,
    headers: { "X-CSRF-Token": csrfToken() },
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok || !result.valid) throw Error(result.error || "Ficha KALLISTIS rejeitada.");
  const optionsResponse = await fetch("/api/kallistis/import/options", {
    credentials: "same-origin",
    cache: "no-store",
  });
  const options = await optionsResponse.json().catch(() => ({}));
  if (!optionsResponse.ok) throw Error(options.error || "Não foi possível listar campanhas.");
  openKallistisImport(result.preview, payload, options.campaigns || []);
}

function csrfToken() {
  return decodeURIComponent(
    document.cookie.match(/(?:^|; )gravewright-csrf=([^;]*)/)?.[1] || "",
  );
}

function openKallistisImport(previewData, payload, campaigns) {
  kallistisImportDialog?.remove();
  const el = clone("kallistis-import-dialog");
  kallistisImportDialog = el;
  kallistisImportPayload = payload;
  const set = (name, value) => {
    el.querySelector("[data-import-" + name + "]").textContent = value;
  };
  set("character", previewData.character_name);
  set("state", previewData.source_state);
  set("mode", previewData.export_mode);
  set("canonical", previewData.canonical ? "sim" : "não");
  set("mesa", previewData.mesa?.name || "Não atribuída");
  set("email", previewData.player.email_present ? "presente" : "ausente");
  set("id", previewData.kallistis_character_id);
  const groups = el.querySelector("[data-import-groups]");
  groups.replaceChildren();
  for (const [label, values] of [
    ["Importados", previewData.mapping.imported],
    ["Preservados como metadados de origem", previewData.mapping.preserved_as_source_metadata],
    ["Não representados", previewData.mapping.unsupported],
  ]) {
    const row = document.createElement("p");
    row.textContent = label + ": " + (values.length ? values.join(", ") : "nenhum");
    groups.append(row);
  }
  const campaignSelect = el.elements.campaign;
  const membershipSelect = el.elements.membership;
  for (const row of campaigns) campaignSelect.append(new Option(row.name, row.id));
  if (campaigns.some((row) => row.id === campaign)) campaignSelect.value = campaign;
  const renderMemberships = () => {
    const selected = campaigns.find((row) => row.id === campaignSelect.value);
    membershipSelect.replaceChildren();
    for (const member of selected?.memberships || [])
      membershipSelect.append(new Option(member.name, member.id));
    membershipSelect.disabled = !(selected?.memberships?.length);
    el.querySelector("[type=submit]").disabled = membershipSelect.disabled;
  };
  campaignSelect.onchange = renderMemberships;
  renderMemberships();
  el.querySelector("header button").onclick = () => {
    el.remove();
    kallistisImportDialog = undefined;
    kallistisImportPayload = undefined;
  };
  el.onsubmit = async (event) => {
    event.preventDefault();
    const submit = el.querySelector("[type=submit]");
    const status = el.querySelector("[data-import-status]");
    submit.disabled = true;
    status.hidden = true;
    try {
      const response = await fetch("/api/kallistis/import/confirm", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken(),
        },
        body: JSON.stringify({
          campaign_id: campaignSelect.value,
          membership_id: membershipSelect.value,
          payload: kallistisImportPayload,
        }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok || !result.valid) throw Error(result.error || "Importação rejeitada.");
      el.remove();
      kallistisImportDialog = undefined;
      kallistisImportPayload = undefined;
      window.gravewrightRealtime?.actorsSubscribe();
    } catch (cause) {
      status.textContent = cause.message;
      status.hidden = false;
      submit.disabled = false;
    }
  };
  const r = panel.getBoundingClientRect();
  el.style.left = Math.max(13, r.left - 258) + "px";
  el.style.top = Math.max(13, r.top + 51) + "px";
  document.body.append(el);
}
function error(message) {
  if (!panel) return;
  const el = panel.querySelector("[role=alert]");
  el.textContent = message;
  show(el, true);
}
function form(id, title, save) {
  dialog?.remove();
  const el = clone(id);
  dialog = el;
  el.setAttribute("aria-label", title);
  el.querySelector("header strong").textContent = title;
  const r = panel.getBoundingClientRect();
  el.style.left = Math.max(13, r.left - 258) + "px";
  el.style.top = Math.max(13, r.top + 51) + "px";
  el.querySelector("header button").onclick = () => el.remove();
  el.onsubmit = async (e) => {
    e.preventDefault();
    const button = el.querySelector("[type=submit]");
    button.disabled = true;
    try {
      await save(el);
      el.remove();
    } catch (cause) {
      const p = el.querySelector("[role=alert]");
      p.textContent = cause.message;
      show(p, true);
    } finally {
      button.disabled = false;
    }
  };
  document.body.append(el);
  el.querySelector("input")?.focus();
  return el;
}
function syncActorTypes() {
  const select = dialog?.querySelector('[name=actorType]');
  if (!select || select.disabled) return;
  const selected = select.value;
  select.replaceChildren(...state.actorTypes.map((type) => new Option(type.label, type.id)));
  if (state.actorTypes.some((type) => type.id === selected)) select.value = selected;
  dialog.querySelector('[type=submit]').disabled = !state.actorTypes.length;
}
function edit(actor, folderId) {
  const el = form(
    "actor-form",
    actor ? labels.editActor : labels.newActor,
    (el) =>
      command(actor ? "actor.update" : "actor.create", {
        id: actor?.id,
        version: actor?.version,
        name: el.elements.name.value,
        actorType: actor?.actorType || el.elements.actorType.value,
        folderId: folderId ?? actor?.folderId,
        data: { pdf: { asset: el.elements.template.value } },
      }),
  );
  el.elements.name.value = actor?.name || "";
  el.elements.actorType.disabled = !!actor;
  syncActorTypes();
  show(el.querySelector("[data-actor-type]"), !actor);
  show(
    el.querySelector("[data-actor-template]"),
    !actor && state.systemId === 'gravewright-pdf-system' && !!state.templates.length,
  );
  show(
    el.querySelector("[data-no-templates]"),
    !actor && state.systemId === 'gravewright-pdf-system' && !state.templates.length,
  );
  el.querySelector("[type=submit] span").textContent = actor
    ? "Save"
    : labels.createActor;
  for (const a of state.templates)
    el.elements.template.append(new Option(a.name, a.id));
}
function folder(existing, parentId) {
  const el = form(
    "map-folder-form",
    existing ? "Edit folder" : labels.createActorFolder,
    (el) =>
      command(existing ? "folder.update" : "folder.create", {
        id: existing?.id,
        parentId: parentId ?? existing?.parentId,
        name: el.elements.label.value,
        color: el.elements.color.value,
      }),
  );
  if (existing) {
    el.elements.label.value = existing.name;
    el.elements.color.value = existing.color;
    el.elements.picker.value = existing.color;
  }
  el.elements.picker.oninput = (e) =>
    (el.elements.color.value = e.target.value);
}
function permissions(actor) {
  const el = form("actor-permissions", "Permissions — " + actor.name, (el) =>
    command("actor.permissions", {
      id: actor.id,
      permissions: Object.fromEntries(
        state.players.map((p) => [
          p.id,
          el.querySelector(`input[name="p-${p.id}"]:checked`).value,
        ]),
      ),
    }),
  );
  for (const p of state.players) {
    const row = clone("actor-permission-row");
    row.querySelector("legend").textContent = p.name;
    for (const input of row.querySelectorAll("input")) {
      input.name = "p-" + p.id;
      input.checked = input.value === (actor.permissions?.[p.id] || "none");
    }
    el.querySelector("[data-permission-rows]").append(row);
  }
  if (!state.players.length) {
    el.querySelector("[data-permission-rows]").textContent =
      "No players in this table.";
    show(el.querySelector("[type=submit]"), false);
  }
}
function open(actor, token) {
  sheet?.close();
  sheet = openSheet(campaign, actor.id, token, state.is_gm, () => {
    sheet = undefined;
  });
}
function runtime(actor) {
  runtimeDialog?.remove();
  const el = clone("actor-runtime");
  runtimeDialog = el;
  el.dataset.runtimeActorId = actor.id;
  el.querySelector("header strong").textContent = "Runtime — " + actor.name;
  const r = panel.getBoundingClientRect();
  el.style.left = Math.max(13, r.left - 258) + "px";
  el.style.top = Math.max(13, r.top + 51) + "px";
  el.querySelector("header button").onclick = () => { el.remove(); runtimeDialog = undefined; };
  const editable = actor.canEdit;
  const showError = message => {
    const p = el.querySelector("[role=alert]");
    p.textContent = message;
    show(p, true);
  };
  const run = (action, data = {}) => command(action, { id: actor.id, ...data }).then(result => {
    if (result?.runtime) render({ runtime: result.runtime });
    return result;
  }).catch(cause => showError(cause.message));
  const render = current => {
    const state = current.runtime || {};
    const resources = state.resources || {};
    const labels = { vitality: "Vitality", lucidity: "Lucidity", flow: "Flow", breath: "Breath", determination: "Determination" };
    const box = el.querySelector("[data-runtime-resources]");
    box.replaceChildren();
    for (const name of Object.keys(labels)) {
      const value = resources[name] || { current: 0, max: 0 };
      const row = document.createElement("div");
      row.className = "actor-runtime-dialog__resource";
      const label = document.createElement("strong");
      label.textContent = `${labels[name]}: ${value.current}/${value.max}`;
      const spend = document.createElement("button");
      spend.type = "button"; spend.textContent = "−"; spend.disabled = !editable;
      spend.title = `Spend 1 ${labels[name]}`;
      spend.onclick = () => run("runtime.resource", { resource: name, operation: "spend", amount: 1 });
      const gain = document.createElement("button");
      gain.type = "button"; gain.textContent = "+"; gain.disabled = !editable;
      gain.title = `Recover 1 ${labels[name]}`;
      gain.onclick = () => run("runtime.resource", { resource: name, operation: "recover", amount: 1 });
      row.append(label, spend, gain); box.append(row);
    }
    const rulesBox = el.querySelector("[data-runtime-rules]");
    const canonical = state.rules || {};
    const economy = canonical.action_economy || {};
    const coro = canonical.coro || {};
    rulesBox.textContent = `Fulgor ${canonical.fulgor ?? 0}/5 · Sombra ${canonical.sombra ?? 0}/6 · Coro ${coro.pulses ?? 0}/${(coro.maximum_bars ?? 1) * 4} · Ação ${economy.action ?? 0} · Movimento ${economy.movement ?? 0} · Reação ${economy.reaction ?? 0}`;
    for (const input of el.querySelectorAll("fieldset input")) input.value = state.attributes?.[input.name] ?? 0;
    const skillsBox = el.querySelector("[data-runtime-skills]");
    skillsBox.replaceChildren();
    for (const [name, labelText] of kallistisSkills) {
      const label = document.createElement("label");
      label.textContent = labelText;
      const input = document.createElement("input");
      input.name = name; input.type = "number"; input.min = "0"; input.max = "5";
      input.dataset.runtimeSkill = name; input.value = state.skills?.[name] ?? 0;
      label.append(input); skillsBox.append(label);
    }
    for (const button of el.querySelectorAll("button[data-runtime-action]")) button.disabled = !editable;
    const conditions = el.querySelector("[data-runtime-conditions]");
    conditions.replaceChildren();
    for (const item of state.conditions || []) {
      const row = document.createElement("div");
      row.textContent = item.type;
      const remove = document.createElement("button");
      remove.type = "button"; remove.textContent = "Remove"; remove.disabled = !editable;
      remove.onclick = () => run("runtime.condition.remove", { conditionId: item.id });
      row.append(" ", remove); conditions.append(row);
    }
  };
  el.querySelector('[name="condition_type"]').replaceChildren(...["ABALADO", "EXPOSTO", "IMOBILIZADO", "LENTO", "SANGRANDO", "SILENCIADO", "DISSONANTE", "FRATURADO", "CORROMPIDO", "CAIDO"].map(type => new Option(type, type)));
  el.querySelector('[data-runtime-action="safe_pause"]').onclick = () => run("runtime.safe_pause");
  el.querySelector('[data-runtime-action="full_rest"]').onclick = () => run("runtime.full_rest");
  el.querySelectorAll('[data-runtime-rule]').forEach(button => {
    button.onclick = () => {
      const operation = button.dataset.runtimeRule;
      const data = operation === "fulgor" ? { amount: 1 } : operation === "coro.add" ? { eligible: true } : {};
      run("runtime.rules", { operation, ...data });
    };
  });
  el.querySelector('[data-runtime-action="condition.apply"]').onclick = () => run("runtime.condition.apply", { conditionType: el.elements.condition_type.value });
  el.querySelector('[data-runtime-action="initialize"]').onclick = () => run("runtime.initialize", {
    attributes: Object.fromEntries([...el.querySelectorAll("[data-runtime-attribute]"), el.elements.marco].map(input => [input.name, Number(input.value)])),
    skills: Object.fromEntries([...el.querySelectorAll("[data-runtime-skill]")].map(input => [input.dataset.runtimeSkill, Number(input.value)])),
  });
  el.querySelector("[type=submit]")?.removeAttribute("type");
  render(actor);
  el._runtimeRender = render;
  document.body.append(el);
}
function remove(actor) {
  const el = clone("journal-confirm");
  el.querySelector("p").textContent = "Remove " + actor.name + "?";
  const b = el.querySelectorAll("button");
  b[0].onclick = async () => {
    try {
      await command("actor.delete", { id: actor.id });
      el.remove();
    } catch (e) {
      error(e.message);
    }
  };
  b[1].onclick = () => el.remove();
  document.body.append(el);
}
function paint() {
  if (!panel) return;
  const search = panel.querySelector("[type=search]").value,
    view = directoryView(state.folders, state.actors, search),
    root = panel.querySelector("[data-actor-tree]");
  root.replaceChildren();
  const draw = (host, parent = null) => {
    host.dataset.actorFolder = parent || "";
    host.dataset.treeDrop = parent || "";
    host.dataset.treeKind = "actor";
    for (const f of state.folders.filter(
      (f) => (f.parentId || null) === parent && view.visibleFolders.has(f.id),
    )) {
      const el = clone("journal-folder");
      el.dataset.actorFolder = f.id;
      el.dataset.treeDrop = f.id;
      el.dataset.treeKind = "actor";
      el.style.setProperty("--folder-color", f.color);
      el.querySelector(".gw-folder__label").textContent = f.name;
      el.querySelector(".gw-folder__count").textContent = view.counts.get(f.id);
      const key = `gravewright.directory.${campaign}.actors.${f.id}`,
        toggle = el.querySelector(".gw-folder__toggle");
      let expanded = !!search;
      try {
        expanded ||= localStorage.getItem(key) === "true";
      } catch {}
      show(el.querySelector(".gw-folder__content"), expanded);
      el.classList.toggle("gw-folder--open", expanded);
      toggle.setAttribute("aria-expanded", String(expanded));
      toggle.onclick = () => {
        try {
          localStorage.setItem(key, String(!expanded));
        } catch {}
        paint();
      };
      toggle.draggable = false;
      toggle.onpointerdown = (e) => {
        if (state.is_gm)
          beginTreeDrag(
            e,
            {
              id: f.id,
              label: f.name,
              kind: "actor",
              folder: true,
              icon: "FolderPlus",
            },
            (target) => target !== f.id && target !== (f.parentId ?? null),
            (parentId) =>
              command("folder.update", {
                id: f.id,
                parentId: parentId ?? null,
              }).catch((e) => error(e.message)),
          );
      };
      toggle.ondragstart = (e) => {
        e.dataTransfer.setData(
          "application/x-gravewright-actor",
          JSON.stringify({ folderId: f.id }),
        );
        e.stopPropagation();
      };
      toggle.oncontextmenu = (e) =>
        context(e, [
          { icon: "PencilSimple", label: "Edit folder", run: () => folder(f) },
          {
            icon: "FolderPlus",
            label: "Create folder",
            run: () => folder(null, f.id),
          },
          {
            icon: "Trash",
            label: "Delete folder",
            run: () => command("folder.delete", { id: f.id, recursive: false }),
          },
        ]);
      const b = el.querySelectorAll(".gw-folder__actions button");
      b[0].onclick = () => edit(null, f.id);
      if (b[1]) b[1].onclick = (e) => toggle.oncontextmenu(e);
      if (!state.is_gm) {
        el.querySelector(".gw-folder__actions")?.remove();
        toggle.oncontextmenu = null;
      }
      draw(el.querySelector(".gw-folder__content"), f.id);
      host.append(el);
    }
    const list = document.createElement("div");
    list.className = "actor-directory__list";
    for (const a of state.actors.filter(
      (a) => (a.folderId || null) === parent && view.visibleEntries.has(a.id),
    )) {
      const el = clone("actor-entry");
      el.querySelector("strong").textContent = a.name;
      el.querySelector("small").textContent =
        state.actorTypes.find((type) => type.id === a.actorType)?.label || a.actorType;
      if (a.portraitUrl) {
        const image = document.createElement("img");
        image.src = a.portraitUrl;
        image.alt = "";
        el.querySelector("svg").replaceWith(image);
      }
      el.onclick = () => open(a);
      el.draggable = false;
      el.onpointerdown = (e) => {
        if (state.is_gm)
          beginTreeDrag(
            e,
            {
              id: a.id,
              label: a.name,
              kind: "actor",
              folder: false,
              icon: "User",
            },
            (target) => target !== (a.folderId ?? null),
            (folderId) =>
              command("actor.update", {
                id: a.id,
                version: a.version,
                folderId: folderId ?? null,
              }).catch((e) => error(e.message)),
          );
      };
      el.ondragstart = (e) => {
        e.dataTransfer.setData(
          "application/x-gravewright-actor",
          JSON.stringify({ actorId: a.id }),
        );
      };
      el.oncontextmenu = (e) => {
        context(e, [
            { icon: "Heart", label: "Runtime resources", run: () => runtime(a) },
            ...(state.is_gm ? [
            { icon: "NotePencil", label: "Open sheet", run: () => open(a) },
            {
              icon: "PencilSimple",
              label: labels.editActor,
              run: () => edit(a),
            },
            {
              icon: "UsersThree",
              label: "Permissions",
              run: () => permissions(a),
            },
            {
              icon: "Trash",
              label: labels.removeActor,
              danger: true,
              run: () => remove(a),
            },
            ] : []),
          ]);
      };
      list.append(el);
    }
    host.append(list);
  };
  draw(root);
  show(
    panel.querySelector(".actor-directory__empty"),
    !view.visibleEntries.size,
  );
  const templates = panel.querySelector("[data-templates]");
  templates.replaceChildren();
  const folder = clone("journal-folder");
  folder.querySelector(".gw-folder__label").textContent = "Templates";
  folder.querySelector(".gw-folder__count").textContent =
    state.templates.length;
  folder.querySelector(".gw-folder__actions")?.remove();
  const body = folder.querySelector(".gw-folder__content");
  let expanded = !!search;
  try {
    expanded ||=
      localStorage.getItem(
        `gravewright.directory.${campaign}.actors.__templates__`,
      ) === "true";
  } catch {}
  show(body, expanded);
  folder.classList.toggle("gw-folder--open", expanded);
  folder.querySelector(".gw-folder__toggle").onclick = () => {
    try {
      localStorage.setItem(
        `gravewright.directory.${campaign}.actors.__templates__`,
        String(!expanded),
      );
    } catch {}
    paint();
  };
  for (const a of state.templates.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase()),
  )) {
    const row = document.createElement("span");
    row.className = "game-directory__item actor-directory__template";
    const text = document.createElement("span"),
      strong = document.createElement("strong"),
      small = document.createElement("small");
    strong.textContent = a.name;
    small.textContent = "PDF";
    text.append(strong, small);
    row.append(icon("FilePdf"), text);
    if (state.is_gm) {
      const b = document.createElement("button");
      b.className = "actor-directory__template-remove";
      b.setAttribute(
        "aria-label",
        deletedTemplate === a.id
          ? "Confirm remove template"
          : "Remove template",
      );
      b.append(icon("Trash"));
      b.onclick = async () => {
        if (deletedTemplate !== a.id) {
          deletedTemplate = a.id;
          paint();
          return;
        }
        try {
          await command("asset.delete", { id: a.id });
          deletedTemplate = null;
        } catch (e) {
          error(e.message);
        }
      };
      row.append(b);
    }
    body.append(row);
  }
  templates.append(folder);
}
window.gravewrightActors = {
  toggle() {
    mergePatch({ _actorsOpen: !getPath("_actorsOpen") });
  },
  open: (actorId, token) => open({ id: actorId }, token),
};
if (panel) {
  panel.querySelector(".game-directory").dataset.treeScroll = "";
  panel.onclick = (e) => {
    const a = e.target.closest("[data-actor-panel]")?.dataset.actorPanel;
    if (a === "close") mergePatch({ _actorsOpen: false });
    if (a === "minimize") panel.classList.toggle("game-panel--minimized");
    if (a === "import-kallistis") {
      panel.querySelector("[data-kallistis-import]")?.click();
      return;
    }
    if (a === "detach") {
      if (popup && !popup.closed) {
        popup.focus();
        return;
      }
      popup = window.open("", "actors-directory", "popup,width=377,height=754");
      if (!popup) return;
      for (const css of document.querySelectorAll("link[rel=stylesheet]"))
        popup.document.head.append(css.cloneNode(true));
      const marker = document.createComment("actors-directory");
      panel.replaceWith(marker);
      popup.document.body.append(panel);
      panel.classList.add("game-panel--detached");
      popup.onpagehide = () => {
        marker.replaceWith(panel);
        panel.classList.remove("game-panel--detached");
      };
    }
    if (a === "create") edit();
    if (a === "folder") folder();
    if (a === "upload") panel.querySelector("[data-template-upload]").click();
  };
  panel.querySelector("[type=search]").oninput = paint;
  const input = panel.querySelector("[data-template-upload]");
  if (input)
    input.onchange = async () => {
      const file = input.files[0];
      input.value = "";
      if (!file) return;
      const data = new FormData();
      data.set("file", file);
      try {
        const r = await fetch(`/api/containers/${campaign}/actor-upload`, {
          method: "POST",
          body: data,
          headers: {
            "X-CSRF-Token": decodeURIComponent(
              document.cookie.match(/(?:^|; )gravewright-csrf=([^;]*)/)?.[1] ||
                "",
            ),
          },
        });
        if (!r.ok) throw Error((await r.json()).message);
      } catch (e) {
        error(e.message);
      }
    };
  const importInput = panel.querySelector("[data-kallistis-import]");
  if (importInput)
    importInput.onchange = async () => {
      const file = importInput.files[0];
      importInput.value = "";
      if (!file) return;
      try {
        await startKallistisImport(file);
      } catch (cause) {
        error(cause.message);
      }
    };
  panel.ondragover = (e) => {
    if (
      state.is_gm &&
      e.dataTransfer.types.includes("application/x-gravewright-actor")
    )
      e.preventDefault();
  };
  panel.ondrop = async (e) => {
    const value = e.dataTransfer.getData("application/x-gravewright-actor");
    if (!value) return;
    e.preventDefault();
    try {
      const data = JSON.parse(value),
        folderId =
          e.target.closest("[data-actor-folder]")?.dataset.actorFolder || null;
      if (data.actorId) {
        const actor = state.actors.find((a) => a.id === data.actorId);
        await command("actor.update", {
          id: actor.id,
          version: actor.version,
          folderId,
        });
      } else
        await command("folder.update", {
          id: data.folderId,
          parentId: folderId,
        });
    } catch (cause) {
      error(cause.message);
    }
  };
  window.addEventListener("gravewright:actors.state", (e) => {
    state = e.detail;
    syncActorTypes();
    paint();
    if (sheet && sheet.element.dataset.actorId) {
      const a = state.actors.find(
        (a) => a.id === sheet.element.dataset.actorId,
      );
      if (!a || (sheet.element.dataset.canEdit === "true" && !a.canEdit))
        sheet.close();
    }
    if (runtimeDialog) {
      const current = state.actors.find(a => a.id === runtimeDialog.dataset.runtimeActorId);
      if (current) runtimeDialog._runtimeRender?.(current);
    }
  });
  window.addEventListener("gravewright:actor-error", (e) => error(e.detail));
  window.addEventListener("gravewright:connected", () =>
    window.gravewrightRealtime.actorsSubscribe(),
  );
  window.addEventListener("gravewright:modules.updated", () =>
    window.gravewrightRealtime.actorsSubscribe(),
  );
  window.gravewrightRealtime?.actorsSubscribe();
  window.addEventListener("gravewright:access-revoked", () => {
    sheet?.close();
    dialog?.remove();
    runtimeDialog?.remove();
    menu?.remove();
    state = { ...state, actors: [], templates: [], folders: [] };
    paint();
  });
}

window.addEventListener("pagehide", () => {
  cancelTreeDrag("actor");
  popup?.close();
  sheet?.close();
  dialog?.remove();
  runtimeDialog?.remove();
  menu?.remove();
});

let dragChip;
window.addEventListener("gravewright:tree-drag", () => {
  queueMicrotask(() => {
    const subject = draggedItem.value;
    if (!subject) {
      dragChip?.remove();
      dragChip = undefined;
      return;
    }
    if (!dragChip) {
      dragChip = document.createElement("div");
      dragChip.className = "gw-tree-preview";
      dragChip.setAttribute("aria-hidden", "true");
      const strong = document.createElement("strong");
      strong.textContent = subject.label;
      const glyph = subject.folder ? "FolderPlus" : "User";
      dragChip.append(icon(glyph), strong);
      document.body.append(dragChip);
      registerTreePreview(dragChip);
    }
  });
});
