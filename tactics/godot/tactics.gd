extends Control
## Read Gravewright's authorized campaign snapshots and request movements.
## Never invent actors, persist state locally, or move a token before server confirmation.

const HALF_WIDTH := 24.0
const HALF_HEIGHT := 12.0
const ELEVATION_PIXELS := 8.0
const MAX_CELLS := 32

const GROUND := Color("#25252c")
const GROUND_ALT := Color("#2b2c34")
const BORDER := Color("#53515a")
const EMBER := Color("#ff893e")
const FRIENDLY := Color("#7ed7d0")
const HOSTILE := Color("#e77b79")

var _socket := WebSocketPeer.new()
var _campaign_id := ""
var _scene_id := ""
var _map: Dictionary = {}
var _combat: Dictionary = {}
var _tokens: Array[Dictionary] = []
var _selected_id := ""
var _mode := "move"
var _attack_attribute := "corpo"
var _mission_role := "ALLY"
var _terrain_selected := Vector2i(-1, -1)
var _terrain_by_cell: Dictionary = {}
var _terrain_type := "NORMAL"
var _terrain_height := 0
var _terrain_connect_mode := false
var _pending_request := ""
var _pending_resource_request := ""
var _pending_terrain_request := ""
var _connected := false
var _status := "Conectando ao Gravewright…"
var _mission_label: Label
var _selection_label: Label
var _resolution_label: Label
var _damage_amount: SpinBox
var _role_picker: OptionButton
var _attribute_picker: OptionButton


func _ready() -> void:
    resized.connect(queue_redraw)
    _build_hud()
    if not OS.has_feature("web"):
        _status = "Este cliente requer exportação web na origem do Gravewright."
        set_process(false)
        queue_redraw()
        return

    # Browser origin is read-only; session cookies stay owned by the browser.
    var raw_origin: Variant = JavaScriptBridge.eval(
        "JSON.stringify({protocol:location.protocol,host:location.host,campaign:new URLSearchParams(location.search).get('campaign')})"
    )
    if typeof(raw_origin) != TYPE_STRING:
        _status = "Não foi possível identificar a origem do navegador."
        set_process(false)
        return

    var origin: Variant = JSON.parse_string(raw_origin)
    if typeof(origin) != TYPE_DICTIONARY:
        _status = "Origem do navegador inválida."
        set_process(false)
        return

    _campaign_id = str(origin.get("campaign", ""))
    var pattern := RegEx.new()
    pattern.compile("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
    if pattern.search(_campaign_id) == null:
        _status = "Informe ?campaign=<UUID> de uma campanha autorizada."
        set_process(false)
        return

    var protocol := "wss://" if origin.get("protocol") == "https:" else "ws://"
    var url: String = protocol + str(origin.get("host", "")) + "/ws/tables/" + _campaign_id + "/"
    var error := _socket.connect_to_url(url)
    if error != OK:
        _status = "Falha ao iniciar WebSocket: " + str(error)
        set_process(false)
    queue_redraw()


func _process(_delta: float) -> void:
    _update_hud()
    _socket.poll()
    var state := _socket.get_ready_state()
    if state == WebSocketPeer.STATE_OPEN:
        if not _connected:
            _connected = true
            _status = "Conectado. Consultando mapas autorizados…"
            _send("maps.sync", {})
        while _socket.get_available_packet_count() > 0:
            _receive(_socket.get_packet().get_string_from_utf8())
    elif state == WebSocketPeer.STATE_CLOSED:
        _status = "Conexão encerrada (" + str(_socket.get_close_code()) + "). Reabra após confirmar a sessão."
        _selected_id = ""
        _pending_request = ""
        _tokens.clear()
        set_process(false)
    queue_redraw()


func _send(kind: String, payload: Dictionary) -> bool:
    if _socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
        return false
    return _socket.send_text(JSON.stringify({"type": kind, "payload": payload})) == OK


func _receive(raw: String) -> void:
    var parsed: Variant = JSON.parse_string(raw)
    if typeof(parsed) != TYPE_DICTIONARY:
        return
    var kind := str(parsed.get("type", ""))
    var payload: Variant = parsed.get("payload", {})
    if typeof(payload) != TYPE_DICTIONARY:
        return
    match kind:
        "session.ping":
            _send("session.pong", {})
        "maps.state":
            _load_map(payload)
        "maps.layers":
            if payload.get("sceneId") == _scene_id:
                _map["layers"] = payload
                _terrain_by_cell.clear()
                var grid: Variant = payload.get("tacticalTerrain", {})
                if typeof(grid) == TYPE_DICTIONARY:
                    for cell in grid.get("cells", []):
                        if typeof(cell) == TYPE_DICTIONARY:
                            _terrain_by_cell[Vector2i(int(cell.get("x", -1)), int(cell.get("y", -1)))] = cell
                queue_redraw()
        "resources.state":
            if payload.get("module") == "combat" and payload.get("sceneId") == _scene_id:
                var combat_state: Variant = payload.get("state", {})
                if typeof(combat_state) == TYPE_DICTIONARY:
                    _combat = combat_state
        "resources.ack":
            if payload.get("requestId") == _pending_resource_request:
                _pending_resource_request = ""
                _status = "Ação validada pelo Gravewright. Estado sincronizando…"
                _send("resources.sync", {"module": "combat", "sceneId": _scene_id})
        "resources.error":
            if payload.get("requestId") == _pending_resource_request:
                _pending_resource_request = ""
                _status = "Ação recusada: " + str(payload.get("message", "erro do servidor"))
                _send("resources.sync", {"module": "combat", "sceneId": _scene_id})
        "tokens.state":
            if payload.get("mapId") != _scene_id:
                return
            _tokens.clear()
            for entry in payload.get("tokens", []):
                if typeof(entry) == TYPE_DICTIONARY:
                    _tokens.append(entry)
            if _pending_request.is_empty():
                _status = "Estado real sincronizado. Unidades visíveis: " + str(_tokens.size())
        "tokens.ack":
            if payload.get("requestId") == _pending_request:
                _pending_request = ""
                _status = "Comando confirmado pelo Gravewright. Atualizando…"
                _send("tokens.sync", {"mapId": _scene_id})
        "maps.ack":
            if payload.get("requestId") == _pending_terrain_request:
                _pending_terrain_request = ""
                _status = "Terreno validado e salvo pelo servidor."
                _send("maps.layers", {"mapId": _scene_id})
        "maps.error":
            if payload.get("requestId") == _pending_terrain_request:
                _pending_terrain_request = ""
                _status = "Edição de terreno recusada: " + str(payload.get("message", "erro do servidor"))
                _send("maps.layers", {"mapId": _scene_id})
        "tokens.error":
            if payload.get("requestId") == _pending_request:
                _pending_request = ""
                _status = "Movimento recusado: " + str(payload.get("message", "erro do servidor"))
                _send("tokens.sync", {"mapId": _scene_id})
        "error":
            _status = "Servidor: " + str(payload.get("message", payload.get("code", "erro")))
        "table.joined":
            _status = "Sessão autorizada. Carregando campanha…"


func _load_map(data: Dictionary) -> void:
    var active: Variant = data.get("activeMapId", "")
    var next_scene: String = active if typeof(active) == TYPE_STRING else ""
    if next_scene != _scene_id:
        _tokens.clear()
        _selected_id = ""
        _pending_request = ""
        _pending_resource_request = ""
    _scene_id = next_scene
    _map.clear()
    _combat.clear()
    for entry in data.get("maps", []):
        if typeof(entry) == TYPE_DICTIONARY and entry.get("id") == _scene_id:
            _map = entry
            break
    if _scene_id.is_empty() or _map.is_empty():
        _status = "Nenhum mapa ativo está disponível para esta sessão."
        return
    _status = "Mapa: " + str(_map.get("name", "sem nome")) + ". Lendo unidades…"
    _send("tokens.sync", {"mapId": _scene_id})
    _send("maps.layers", {"mapId": _scene_id})
    _send("resources.sync", {"module": "combat", "sceneId": _scene_id})


func _grid_dimensions() -> Vector2i:
    var tactical := _terrain()
    if bool(tactical.get("initialized", false)):
        return Vector2i(int(tactical.get("width", 1)), int(tactical.get("height", 1)))
    var cell_size := maxf(1.0, float(_map.get("gridSize", 70)) * float(_map.get("imageScale", 1)))
    return Vector2i(
        clampi(int(ceil(float(_map.get("width", 0)) / cell_size)), 1, MAX_CELLS),
        clampi(int(ceil(float(_map.get("height", 0)) / cell_size)), 1, MAX_CELLS)
    )


func _terrain() -> Dictionary:
    var layers: Variant = _map.get("layers", {})
    if typeof(layers) != TYPE_DICTIONARY:
        return {}
    var terrain: Variant = layers.get("tacticalTerrain", {})
    return terrain if typeof(terrain) == TYPE_DICTIONARY else {}


func _terrain_cell(x: int, y: int) -> Dictionary:
    var cell: Variant = _terrain_by_cell.get(Vector2i(x, y), {})
    return cell if typeof(cell) == TYPE_DICTIONARY else {}


func _terrain_editable() -> bool:
    return bool(_terrain().get("canEdit", false))


func _send_terrain(action: String, data: Dictionary) -> void:
    if not _pending_terrain_request.is_empty():
        return
    var request_id := _uuid_v4()
    var payload := {
        "requestId": request_id,
        "action": "objects",
        "data": {"mapId": _scene_id, "area": "terrain", "action": action, "data": data}
    }
    if _send("maps.command", payload):
        _pending_terrain_request = request_id
        _status = "Salvando terreno com revisão " + str(_terrain().get("version", 0)) + "…"
    else:
        _status = "Não foi possível enviar a edição de terreno."


func _origin() -> Vector2:
    return Vector2(size.x * 0.5, 86.0)


func _project(cell: Vector2) -> Vector2:
    return _origin() + Vector2(
        (cell.x - cell.y) * HALF_WIDTH,
        (cell.x + cell.y) * HALF_HEIGHT
    )


func _point_to_cell(point: Vector2) -> Vector2i:
    if bool(_terrain().get("initialized", false)):
        var dims := _grid_dimensions()
        var selected := Vector2i(-1, -1)
        # Match the same painter order used by _draw(): later polygons are
        # visually on top and must win where elevated floors overlap.
        for y in range(dims.y):
            for x in range(dims.x):
                var cell := _terrain_cell(x, y)
                var lift := Vector2(0, int(cell.get("elevation", 0)) * ELEVATION_PIXELS)
                var polygon := PackedVector2Array([
                    _project(Vector2(x, y)) - lift,
                    _project(Vector2(x + 1, y)) - lift,
                    _project(Vector2(x + 1, y + 1)) - lift,
                    _project(Vector2(x, y + 1)) - lift,
                ])
                if Geometry2D.is_point_in_polygon(point, polygon):
                    selected = Vector2i(x, y)
        return selected
    var p := point - _origin()
    var u := p.x / HALF_WIDTH
    var v := p.y / HALF_HEIGHT
    return Vector2i(floori((u + v) / 2.0), floori((v - u) / 2.0))


func _token_at_point(point: Vector2) -> Dictionary:
    # Tokens are drawn after the terrain, so test them first in reverse draw order.
    for index in range(_tokens.size() - 1, -1, -1):
        var token := _tokens[index]
        var x := float(token.get("gridX", -999))
        var y := float(token.get("gridY", -999))
        var center := _project(Vector2(x + 0.5, y + 0.5))
        center.y -= float(token.get("elevation", 0)) * ELEVATION_PIXELS
        if Rect2(center + Vector2(-9, -20), Vector2(18, 19)).has_point(point):
            return token
    return {}


func _selected_token() -> Dictionary:
    for entry in _tokens:
        if entry.get("id") == _selected_id:
            return entry
    return {}


func _movement_reach() -> int:
    var selected := _selected_token()
    if selected.is_empty() or not bool(selected.get("canControl", false)):
        return 0
    for combatant in _combat.get("combatants", []):
        if typeof(combatant) != TYPE_DICTIONARY or combatant.get("token_id") != selected.get("id"):
            continue
        var movement: Variant = combatant.get("movement")
        if typeof(movement) != TYPE_DICTIONARY or not bool(combatant.get("is_current", false)):
            return 0
        if movement.get("mode") != "GRID":
            return 0
        return maxi(0, int(movement.get("pointsPerMove", 0)) - int(movement.get("used", 0)))
    return 0


func _gui_input(event: InputEvent) -> void:
    if not event is InputEventMouseButton or not event.pressed:
        return
    if event.button_index == MOUSE_BUTTON_RIGHT:
        _selected_id = ""
        queue_redraw()
        return
    if event.button_index != MOUSE_BUTTON_LEFT or _map.is_empty() or not _pending_request.is_empty():
        return
    if _terrain_editable() and event.position.y < 90.0:
        if not bool(_terrain().get("initialized", false)):
            _send_terrain("initialize", {"width": 16, "height": 16})
        elif event.position.x < 102.0:
            _terrain_type = "NORMAL"
        elif event.position.x < 184.0:
            _terrain_type = "DIFICIL"
        elif event.position.x < 266.0:
            _terrain_type = "SEVERO"
        elif event.position.x < 348.0:
            _terrain_type = "INTRANSPONIVEL"
        elif event.position.x < 402.0:
            _terrain_height -= 1
        elif event.position.x < 456.0:
            _terrain_height += 1
        else:
            _terrain_connect_mode = not _terrain_connect_mode
            _terrain_selected = Vector2i(-1, -1)
        queue_redraw()
        return
    var token_hit := _token_at_point(event.position)
    if not token_hit.is_empty():
        if _mode in ["attack", "ambush"]:
            if _selected_id.is_empty():
                if bool(token_hit.get("canControl", false)):
                    _selected_id = str(token_hit.get("id", ""))
                    _status = "Atacante selecionado: " + str(token_hit.get("name", ""))
                else:
                    _status = "Selecione primeiro uma unidade que você controla."
            elif str(token_hit.get("id", "")) == _selected_id:
                _status = "Selecione um alvo adjacente e visível."
            else:
                _send_attack(token_hit, _mode == "ambush")
            queue_redraw()
            return
        if bool(token_hit.get("canControl", false)):
            _selected_id = str(token_hit.get("id", ""))
            _status = "Unidade selecionada: " + str(token_hit.get("name", ""))
        else:
            _selected_id = ""
            _status = "Você não controla essa unidade."
        queue_redraw()
        return
    var target := _point_to_cell(event.position)
    var dims := _grid_dimensions()
    if target.x < 0 or target.y < 0 or target.x >= dims.x or target.y >= dims.y:
        return
    if _terrain_editable() and bool(_terrain().get("initialized", false)):
        if _terrain_connect_mode:
            if _terrain_selected.x < 0:
                _terrain_selected = target
                _status = "Selecione a célula ortogonal de destino da escadaria."
            else:
                var from_cell := _terrain_cell(_terrain_selected.x, _terrain_selected.y)
                var to_cell := _terrain_cell(target.x, target.y)
                if not from_cell.is_empty() and not to_cell.is_empty():
                    _send_terrain("connect", {
                        "expectedVersion": int(_terrain().get("version", 0)),
                        "x": _terrain_selected.x, "y": _terrain_selected.y,
                        "toX": target.x, "toY": target.y, "kind": "STAIR"
                    })
                _terrain_selected = Vector2i(-1, -1)
            queue_redraw()
            return
        var cell := _terrain_cell(target.x, target.y)
        if cell.is_empty():
            return
        _terrain_selected = target
        var next_elevation := clampi(int(cell.get("elevation", 0)) + _terrain_height, -20, 20)
        _send_terrain("cell", {
            "expectedVersion": int(_terrain().get("version", 0)),
            "x": target.x, "y": target.y,
            "terrainType": _terrain_type,
            "elevation": next_elevation
        })
        _terrain_height = 0
        queue_redraw()
        return
    var selected := _selected_token()
    if selected.is_empty() or not bool(selected.get("canControl", false)):
        return
    if _mode != "move":
        _status = "A ação selecionada exige escolher um token-alvo."
        return
    var start := Vector2i(int(selected.get("gridX", -999)), int(selected.get("gridY", -999)))
    # A deliberately conservative first command: one orthogonal cell.
    if abs(target.x - start.x) + abs(target.y - start.y) != 1:
        _status = "Neste incremento, mova apenas uma célula ortogonal."
        return
    var request_id := _uuid_v4()
    var command := {
        "requestId": request_id,
        "action": "move",
        "data": {
            "mapId": _scene_id,
            "id": selected["id"],
            "gridX": target.x,
            "gridY": target.y,
            "expectedVersion": int(selected.get("version", 0)),
            "path": []
        }
    }
    if _send("tokens.command", command):
        _pending_request = request_id
        _status = "Movimento enviado; aguardando confirmação do servidor…"
    else:
        _status = "Falha ao enviar movimento. Nenhuma posição alterada."


func _uuid_v4() -> String:
    var bytes := Crypto.new().generate_random_bytes(16)
    bytes[6] = (bytes[6] & 0x0f) | 0x40
    bytes[8] = (bytes[8] & 0x3f) | 0x80
    var hex := ""
    for b in bytes:
        hex += "%02x" % b
    return "%s-%s-%s-%s-%s" % [
        hex.substr(0, 8), hex.substr(8, 4), hex.substr(12, 4),
        hex.substr(16, 4), hex.substr(20, 12)
    ]


func _build_hud() -> void:
    var panel := PanelContainer.new()
    panel.name = "TacticsHud"
    panel.anchor_left = 0.0
    panel.anchor_right = 1.0
    panel.anchor_top = 1.0
    panel.anchor_bottom = 1.0
    panel.offset_left = 8.0
    panel.offset_right = -8.0
    panel.offset_top = -132.0
    panel.offset_bottom = -4.0
    panel.mouse_filter = Control.MOUSE_FILTER_STOP
    add_child(panel)
    var column := VBoxContainer.new()
    column.add_theme_constant_override("separation", 2)
    panel.add_child(column)

    var first := HBoxContainer.new()
    first.add_theme_constant_override("separation", 4)
    column.add_child(first)
    var move_button := _hud_button("Mover", 72)
    move_button.pressed.connect(func(): _set_mode("move"))
    first.add_child(move_button)
    var attack_button := _hud_button("Atacar", 72)
    attack_button.pressed.connect(func(): _set_mode("attack"))
    first.add_child(attack_button)
    var ambush_button := _hud_button("Emboscada", 94)
    ambush_button.pressed.connect(func(): _set_mode("ambush"))
    first.add_child(ambush_button)
    _attribute_picker = OptionButton.new()
    _attribute_picker.add_item("Corpo + Combate")
    _attribute_picker.add_item("Agilidade + Combate")
    _attribute_picker.custom_minimum_size.x = 150
    _attribute_picker.item_selected.connect(func(index: int): _attack_attribute = "corpo" if index == 0 else "agilidade")
    first.add_child(_attribute_picker)
    var next_button := _hud_button("Próxima ativação", 132)
    next_button.pressed.connect(_next_activation)
    first.add_child(next_button)
    _mission_label = Label.new()
    _mission_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    _mission_label.text = "Missão ainda não criada"
    first.add_child(_mission_label)

    var second := HBoxContainer.new()
    second.add_theme_constant_override("separation", 4)
    column.add_child(second)
    var create_button := _hud_button("Criar missão", 94)
    create_button.pressed.connect(func(): _mission_command("mission.create", {"definition": "knossos-evacuation"}))
    second.add_child(create_button)
    _role_picker = OptionButton.new()
    _role_picker.add_item("Aliado")
    _role_picker.set_item_metadata(0, "ALLY")
    _role_picker.add_item("Silmari")
    _role_picker.set_item_metadata(1, "HOSTILE")
    _role_picker.add_item("Nomos evacuar")
    _role_picker.set_item_metadata(2, "EVACUEE")
    _role_picker.custom_minimum_size.x = 136
    _role_picker.item_selected.connect(func(index: int): _mission_role = str(_role_picker.get_item_metadata(index)))
    second.add_child(_role_picker)
    var register_button := _hud_button("Registrar token", 106)
    register_button.pressed.connect(_register_selected)
    second.add_child(register_button)
    var ready_button := _hud_button("Pronto", 66)
    ready_button.pressed.connect(func(): _mission_command("mission.ready", {}))
    second.add_child(ready_button)
    var start_button := _hud_button("Iniciar missão", 100)
    start_button.pressed.connect(func(): _mission_command("mission.start", {}))
    second.add_child(start_button)
    var abort_button := _hud_button("Encerrar", 76)
    abort_button.pressed.connect(func(): _mission_command("mission.abort", {"reason": "gm_abort"}))
    second.add_child(abort_button)
    _selection_label = Label.new()
    _selection_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    second.add_child(_selection_label)

    var third := HBoxContainer.new()
    third.add_theme_constant_override("separation", 4)
    column.add_child(third)
    _damage_amount = SpinBox.new()
    _damage_amount.min_value = 0
    _damage_amount.max_value = 100
    _damage_amount.value = 1
    _damage_amount.custom_minimum_size.x = 78
    third.add_child(_damage_amount)
    var damage_button := _hud_button("Aplicar dano ao selecionado", 190)
    damage_button.pressed.connect(_apply_damage)
    third.add_child(damage_button)
    _resolution_label = Label.new()
    _resolution_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    third.add_child(_resolution_label)


func _hud_button(label: String, width: float) -> Button:
    var button := Button.new()
    button.text = label
    button.custom_minimum_size = Vector2(width, 34)
    button.focus_mode = Control.FOCUS_NONE
    return button


func _set_mode(mode: String) -> void:
    _mode = mode
    _status = "Modo: " + ("ataque corpo a corpo" if mode == "attack" else "Emboscada (Nível I)" if mode == "ambush" else "movimento") + ". Selecione unidade e alvo."
    if mode == "move":
        _selected_id = ""
    queue_redraw()


func _send_resource_command(action: String, data: Dictionary) -> void:
    if not _pending_resource_request.is_empty():
        return
    var request_id := _uuid_v4()
    var payload := {"module": "combat", "requestId": request_id, "action": action, "data": data}
    if _send("resources.command", payload):
        _pending_resource_request = request_id
        _status = "Enviando " + action + " ao Gravewright…"
    else:
        _status = "Não foi possível enviar a ação de combate."


func _combat_command(action: String, data: Dictionary = {}) -> void:
    var payload := {"sceneId": _scene_id, "version": int(_combat.get("version", 0))}
    payload.merge(data, true)
    _send_resource_command(action, payload)


func _mission_command(action: String, data: Dictionary) -> void:
    var payload := {"sceneId": _scene_id}
    if action != "mission.create":
        var mission: Variant = _combat.get("mission")
        if typeof(mission) != TYPE_DICTIONARY:
            _status = "Crie uma missão antes de mudar seu estado."
            return
        payload["version"] = int(mission.get("version", 0))
        payload["combatVersion"] = int(_combat.get("version", 0))
    payload.merge(data, true)
    _send_resource_command(action, payload)


func _register_selected() -> void:
    var token := _selected_token()
    if token.is_empty():
        _status = "Selecione um token persistido antes de registrá-lo na missão."
        return
    _mission_command("mission.participant.add", {
        "actorId": str(token.get("actorId", "")),
        "tokenId": str(token.get("id", "")),
        "role": _mission_role,
    })


func _next_activation() -> void:
    _combat_command("next")


func _apply_damage() -> void:
    var target := _selected_token()
    if target.is_empty():
        _status = "Selecione o token que receberá dano."
        return
    _combat_command("damage", {
        "targetId": str(target.get("id", "")),
        "rawDamage": int(_damage_amount.value),
        "damageEventId": _uuid_v4(),
    })


func _send_attack(target: Dictionary, use_ambush: bool) -> void:
    var attacker := _selected_token()
    if attacker.is_empty():
        _status = "Selecione o atacante antes do alvo."
        return
    var data := {
        "sceneId": _scene_id,
        "version": int(_combat.get("version", 0)),
        "actorId": str(attacker.get("actorId", "")),
        "targetId": str(target.get("id", "")),
        "targetDefense": "GUARDA",
        "action": {
            "action_label": "Emboscada" if use_ambush else "Ataque corpo a corpo",
            "attribute": {"name": "Corpo" if _attack_attribute == "corpo" else "Agilidade"},
            "skill": {"name": "Combate"},
        },
    }
    if use_ambush:
        data["technique"] = "Emboscada"
    _combat_command("attack", data)
    _selected_id = ""
    _mode = "move"


func _update_hud() -> void:
    if not is_instance_valid(_mission_label) or not is_instance_valid(_selection_label):
        return
    var mission: Variant = _combat.get("mission")
    if typeof(mission) == TYPE_DICTIONARY:
        var current := str(_combat.get("current_name", "sem ativação"))
        _mission_label.text = "%s · %s · Rodada %s · %s" % [str(mission.get("definition", {}).get("title", "Missão")), str(mission.get("state", "")), str(_combat.get("round", 0)), current]
    else:
        _mission_label.text = "Missão ainda não criada · Rodada %s · %s" % [str(_combat.get("round", 0)), str(_combat.get("current_name", "sem ativação"))]
    var selected := _selected_token()
    _selection_label.text = "Seleção: " + str(selected.get("name", "nenhuma")) + " · " + _status
    var resolutions: Variant = _combat.get("config", {}).get("resolutions", [])
    if typeof(resolutions) == TYPE_ARRAY and not resolutions.is_empty():
        var latest: Variant = resolutions.back()
        if typeof(latest) == TYPE_DICTIONARY:
            if latest.get("kind") == "damage":
                _resolution_label.text = "Dano: %s · proteção %s · Vitalidade %s → %s" % [str(latest.get("post_protection_damage", 0)), str(latest.get("protection_value", 0)), str(latest.get("vitality_before", "?")), str(latest.get("vitality_after", "?"))]
            else:
                var status := "sucesso" if bool(latest.get("success", false)) else "falha"
                var technique: Variant = latest.get("technique", {})
                var suffix := " · " + str(technique.get("name", "")) if typeof(technique) == TYPE_DICTIONARY and not technique.is_empty() else ""
                _resolution_label.text = "Ataque %s: total %s vs %s%s" % [status, str(latest.get("total", "?")), str(latest.get("target_defense_value", "?")), suffix]
    else:
        _resolution_label.text = "Aguardando resolução de combate do servidor."


func _draw() -> void:
    draw_rect(Rect2(Vector2.ZERO, size), Color("#14161c"))
    var font: Font = ThemeDB.fallback_font
    draw_string(font, Vector2(20, 30), "GRAVEWRIGHT  /  TACTICS", HORIZONTAL_ALIGNMENT_LEFT, -1, 22, EMBER)
    draw_string(font, Vector2(20, 55), "VTT tático • movimento validado pelo servidor", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color.WHITE)
    if _map.is_empty():
        draw_string(font, Vector2(20, 130), _status, HORIZONTAL_ALIGNMENT_LEFT, size.x - 40, 17, Color.WHITE)
        return
    if _terrain_editable():
        var grid := _terrain()
        if not bool(grid.get("initialized", false)):
            draw_rect(Rect2(20, 64, 250, 25), Color("#34323c"))
            draw_string(font, Vector2(26, 82), "Criar terreno tático 16 × 16", HORIZONTAL_ALIGNMENT_LEFT, 240, 13, Color("#f5d18c"))
        else:
            _draw_terrain_toolbar(font)
    var dims := _grid_dimensions()
    var reach := _movement_reach()
    for y in range(dims.y):
        for x in range(dims.x):
            var cell := _terrain_cell(x, y)
            var elevation := int(cell.get("elevation", 0)) if not cell.is_empty() else 0
            var lift := Vector2(0, elevation * ELEVATION_PIXELS)
            var floor_a := _project(Vector2(x, y))
            var floor_b := _project(Vector2(x + 1, y))
            var floor_c := _project(Vector2(x + 1, y + 1))
            var floor_d := _project(Vector2(x, y + 1))
            var a := floor_a - lift
            var b := floor_b - lift
            var c := floor_c - lift
            var d := floor_d - lift
            var ground := _terrain_color(str(cell.get("terrain_type", "")), (x + y) % 2 == 0)
            if cell.is_empty():
                ground = GROUND if (x + y) % 2 == 0 else GROUND_ALT
            var token := _selected_token()
            if not token.is_empty() and int(token.get("gridX", -999)) == x and int(token.get("gridY", -999)) == y:
                ground = Color("#81512f")
            if elevation > 0:
                draw_colored_polygon(PackedVector2Array([floor_a, floor_b, b, a]), Color("#4b4541"))
                draw_colored_polygon(PackedVector2Array([floor_d, floor_c, c, d]), Color("#36343a"))
            draw_colored_polygon(PackedVector2Array([a, b, c, d]), ground)
            var selected := _selected_token()
            if reach > 0 and not selected.is_empty():
                var distance := absi(x - int(selected.get("gridX", -999))) + absi(y - int(selected.get("gridY", -999)))
                var preview_reachable := distance > 0 and distance <= reach
                if bool(_terrain().get("initialized", false)):
                    preview_reachable = distance == 1 and _preview_step_allowed(selected, cell, reach)
                if preview_reachable:
                    draw_colored_polygon(PackedVector2Array([a, b, c, d]), Color("#7774d844"))
            if str(cell.get("terrain_type", "")) == "INTRANSPONIVEL":
                draw_colored_polygon(PackedVector2Array([a + Vector2(0, -3), b + Vector2(0, -3), c + Vector2(0, -3), d + Vector2(0, -3)]), Color("#4d4950"))
                draw_line(a + Vector2(0, -3), c + Vector2(0, -3), Color("#bd776e"), 3.0)
                draw_line(b + Vector2(0, -3), d + Vector2(0, -3), Color("#bd776e"), 3.0)
            if _terrain_selected == Vector2i(x, y):
                for edge in [[a, b], [b, c], [c, d], [d, a]]:
                    draw_line(edge[0], edge[1], EMBER, 3.0)
            for edge in [[a, b], [b, c], [c, d], [d, a]]:
                draw_line(edge[0], edge[1], BORDER, 1.0)
    _draw_terrain_walls()
    _draw_terrain_connections()
    for token in _tokens:
        var x := float(token.get("gridX", -999))
        var y := float(token.get("gridY", -999))
        if x < 0 or y < 0 or x >= dims.x or y >= dims.y:
            continue
        var ground_center := _project(Vector2(x + 0.5, y + 0.5))
        var elevation := float(token.get("elevation", 0))
        var center := ground_center - Vector2(0, elevation * ELEVATION_PIXELS)
        var tint := HOSTILE if token.get("disposition") == "hostile" else FRIENDLY
        var outline := EMBER if str(token.get("id", "")) == _selected_id else Color("#17181c")
        if elevation != 0:
            draw_line(ground_center, center, Color("#d1c7a6"), 2.0)
            draw_circle(ground_center, 5.0, Color("#10111688"))
        draw_rect(Rect2(center + Vector2(-9, -20), Vector2(18, 19)), outline)
        draw_rect(Rect2(center + Vector2(-7, -18), Vector2(14, 15)), tint)
        var name := str(token.get("name", ""))
        if name.is_empty():
            name = "?"
        draw_string(font, center + Vector2(-18, -27), name, HORIZONTAL_ALIGNMENT_CENTER, 90, 12, Color.WHITE)
    var selected := _selected_token()
    var runtime: Variant = selected.get("runtime", {})
    if typeof(runtime) == TYPE_DICTIONARY:
        var vitality: Variant = runtime.get("resources", {}).get("vitality", {})
        var conditions: Array = runtime.get("conditions", [])
        draw_string(font, Vector2(20, 80), "%s · Vitalidade %s/%s · Condições %s" % [str(selected.get("name", "")), str(vitality.get("current", "–")), str(vitality.get("max", "–")), str(conditions.size())], HORIZONTAL_ALIGNMENT_LEFT, size.x - 40, 13, Color("#e7d3a1"))
    var mission: Variant = _combat.get("mission")
    if typeof(mission) == TYPE_DICTIONARY:
        draw_string(font, Vector2(20, 103), "Objetivo: evacuar Nomos até a zona · Estado %s" % str(mission.get("state", "")), HORIZONTAL_ALIGNMENT_LEFT, size.x - 40, 13, Color("#f0d19b"))


func _terrain_color(terrain_type: String, alternate: bool) -> Color:
    match terrain_type:
        "NORMAL": return Color("#716852") if alternate else Color("#665e4c")
        "DIFICIL": return Color("#93704c") if alternate else Color("#846445")
        "SEVERO": return Color("#72534d") if alternate else Color("#674a47")
        "INTRANSPONIVEL": return Color("#42424a") if alternate else Color("#393940")
        _: return GROUND if alternate else GROUND_ALT


func _draw_terrain_toolbar(font: Font) -> void:
    var labels := ["N Normal", "2 Difícil", "3 Severo", "4 Bloqueio", "H−", "H+", "Escada"]
    var colors := [Color("#766b59"), Color("#9b7248"), Color("#74534e"), Color("#44434b"), Color("#383c48"), Color("#383c48"), Color("#414b48")]
    var x := 20.0
    for i in range(labels.size()):
        var width := 82.0 if i < 4 else 54.0
        draw_rect(Rect2(x, 64, width - 3, 22), colors[i])
        draw_string(font, Vector2(x + 4, 80), labels[i], HORIZONTAL_ALIGNMENT_LEFT, width - 6, 11, Color.WHITE)
        x += width
    draw_string(font, Vector2(x + 4, 80), "Conexão: " + ("STAIR" if not _terrain_connect_mode else "clique 2 células"), HORIZONTAL_ALIGNMENT_LEFT, 180, 11, Color("#f4d18a"))


func _draw_terrain_walls() -> void:
    var layers: Variant = _map.get("layers", {})
    if typeof(layers) != TYPE_DICTIONARY:
        return
    var cell_size := maxf(1.0, float(_map.get("gridSize", 70)) * float(_map.get("imageScale", 1)))
    var offset_x := float(_map.get("gridOffsetX", 0)) * float(_map.get("imageScale", 1))
    var offset_y := float(_map.get("gridOffsetY", 0)) * float(_map.get("imageScale", 1))
    for wall in layers.get("walls", []):
        if typeof(wall) != TYPE_DICTIONARY or wall.get("movement_behavior", "block") == "pass":
            continue
        if wall.get("kind") == "door" and wall.get("door_state") == "open":
            continue
        var a := _project(Vector2((float(wall.get("x1", 0)) - offset_x) / cell_size, (float(wall.get("y1", 0)) - offset_y) / cell_size))
        var b := _project(Vector2((float(wall.get("x2", 0)) - offset_x) / cell_size, (float(wall.get("y2", 0)) - offset_y) / cell_size))
        draw_line(a, b, Color("#d29a66"), 3.0)


func _preview_step_allowed(token: Dictionary, target: Dictionary, remaining: int) -> bool:
    if target.is_empty() or not bool(target.get("traversable", false)):
        return false
    var x := int(token.get("gridX", -1))
    var y := int(token.get("gridY", -1))
    var from_cell := _terrain_cell(x, y)
    if from_cell.is_empty():
        return false
    if int(target.get("movement_cost", 0)) > remaining:
        return false
    if int(from_cell.get("elevation", 0)) != int(target.get("elevation", 0)):
        var found := false
        for connection in _terrain().get("connections", []):
            if typeof(connection) != TYPE_DICTIONARY:
                continue
            var from: Variant = connection.get("from", [])
            var to: Variant = connection.get("to", [])
            if typeof(from) != TYPE_ARRAY or typeof(to) != TYPE_ARRAY or from.size() != 2 or to.size() != 2:
                continue
            var forward := int(from[0]) == x and int(from[1]) == y and int(to[0]) == int(target.get("x", -2)) and int(to[1]) == int(target.get("y", -2))
            var reverse := int(to[0]) == x and int(to[1]) == y and int(from[0]) == int(target.get("x", -2)) and int(from[1]) == int(target.get("y", -2))
            if forward or reverse:
                found = true
                break
        if not found:
            return false
    return true


func _draw_terrain_connections() -> void:
    var center := Vector2.ZERO
    for connection in _terrain().get("connections", []):
        if typeof(connection) != TYPE_DICTIONARY:
            continue
        var from: Variant = connection.get("from", [])
        var to: Variant = connection.get("to", [])
        if typeof(from) != TYPE_ARRAY or typeof(to) != TYPE_ARRAY or from.size() != 2 or to.size() != 2:
            continue
        var first := Vector2(int(from[0]), int(from[1]))
        var second := Vector2(int(to[0]), int(to[1]))
        var first_cell := _terrain_cell(int(first.x), int(first.y))
        var second_cell := _terrain_cell(int(second.x), int(second.y))
        var first_lift := Vector2(0, int(first_cell.get("elevation", 0)) * ELEVATION_PIXELS)
        var second_lift := Vector2(0, int(second_cell.get("elevation", 0)) * ELEVATION_PIXELS)
        center = ((_project(first + Vector2(0.5, 0.5)) - first_lift) + (_project(second + Vector2(0.5, 0.5)) - second_lift)) * 0.5
        for step in range(3):
            var offset := Vector2(-5.0 + step * 5.0, float(step * 2))
            draw_line(center + offset + Vector2(-5, 2), center + offset + Vector2(5, -2), Color("#f2d18e"), 2.0)
