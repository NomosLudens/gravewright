extends Control
## Read Gravewright's authorized campaign snapshots and request movements.
## Never invent actors, persist state locally, or move a token before server confirmation.

const LEVEL_HEIGHT := 0.45
const TILE_THICKNESS := 0.14
const MAX_CELLS := 32

const GROUND := Color("#24232b")
const GROUND_ALT := Color("#2b2933")
const FRIENDLY := Color("#c8c5d0")
const HOSTILE := Color("#9b78bd")

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
var _socket_url := ""
var _reconnect_attempts := 0
var _reconnect_elapsed := 0.0
var _reconnect_in_progress := false
var _reconnect_failure_elapsed := 0.0
const MAX_RECONNECT_ATTEMPTS := 5
var _status := "Conectando ao Gravewright…"
var _hud_panel: PanelContainer
var _world_viewport: SubViewport
var _world_camera: Camera3D
var _world_root: Node3D
var _world_geometry: Node3D
var _terrain_toolbar_control: HFlowContainer
var _terrain_tools: Array[Button] = []
var _terrain_initialize_button: Button
var _mission_label: Label
var _selection_label: Label
var _resolution_label: Label
var _mission_admin_row: HFlowContainer
var _damage_button: Button
var _role_picker: OptionButton
var _attribute_picker: OptionButton
var _friendly_representative: OptionButton
var _hostile_representative: OptionButton
var _combat_admin_row: HFlowContainer
var _combat_admin_label: Label


func _ready() -> void:
    resized.connect(_resize_world)
    _build_world()
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
    _socket_url = protocol + str(origin.get("host", "")) + "/ws/tables/" + _campaign_id + "/"
    _connect_socket()
    queue_redraw()


func _build_world() -> void:
    var container := SubViewportContainer.new()
    container.name = "TacticalWorldView"
    container.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    container.mouse_filter = Control.MOUSE_FILTER_IGNORE
    container.stretch = true
    add_child(container)
    move_child(container, 0)

    var header_card := PanelContainer.new()
    header_card.name = "TacticsBrandHeader"
    header_card.position = Vector2(14.0, 10.0)
    var header_style := StyleBoxFlat.new()
    header_style.bg_color = Color("#17161de8")
    header_style.border_color = Color("#4a4057")
    header_style.set_border_width_all(1)
    header_style.set_corner_radius_all(7)
    header_style.content_margin_left = 8
    header_style.content_margin_right = 8
    header_style.content_margin_top = 5
    header_style.content_margin_bottom = 5
    header_card.add_theme_stylebox_override("panel", header_style)
    var header := VBoxContainer.new()
    header.name = "TacticsBrandHeader"
    header.add_theme_constant_override("separation", 1)
    header.mouse_filter = Control.MOUSE_FILTER_IGNORE
    var title := Label.new()
    title.text = "GRAVEWRIGHT  /  TACTICS"
    title.add_theme_font_size_override("font_size", 18)
    title.add_theme_color_override("font_color", Color("#a783d3"))
    header.add_child(title)
    var subtitle := Label.new()
    subtitle.text = "KALLISTIS  ·  CAMPO TÁTICO"
    subtitle.add_theme_font_size_override("font_size", 10)
    subtitle.add_theme_color_override("font_color", Color("#b9b5c0"))
    header.add_child(subtitle)
    header_card.add_child(header)
    add_child(header_card)

    _world_viewport = SubViewport.new()
    _world_viewport.size = Vector2i(maxi(1, int(size.x)), maxi(1, int(size.y)))
    _world_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    _world_viewport.transparent_bg = true
    container.add_child(_world_viewport)

    _world_root = Node3D.new()
    _world_viewport.add_child(_world_root)
    var environment := Environment.new()
    environment.background_mode = Environment.BG_COLOR
    environment.background_color = Color(0.0, 0.0, 0.0, 0.0)
    environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.ambient_light_color = Color("#9a8aa8")
    environment.ambient_light_energy = 0.55
    var world_environment := WorldEnvironment.new()
    world_environment.environment = environment
    _world_root.add_child(world_environment)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-52.0, -28.0, 0.0)
    sun.light_color = Color("#ddd8e6")
    sun.light_energy = 0.9
    sun.shadow_enabled = true
    _world_root.add_child(sun)

    _world_camera = Camera3D.new()
    _world_camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    _world_camera.current = true
    _world_root.add_child(_world_camera)
    _world_geometry = Node3D.new()
    _world_geometry.name = "ServerBackedMapGeometry"
    _world_root.add_child(_world_geometry)
    _resize_world()


func _resize_world() -> void:
    if not is_instance_valid(_world_viewport):
        return
    _world_viewport.size = Vector2i(maxi(1, int(size.x)), maxi(1, int(size.y)))
    _position_world_camera()


func _position_world_camera() -> void:
    if not is_instance_valid(_world_camera):
        return
    var dims := _grid_dimensions()
    var max_elevation := 0.0
    for cell in _terrain().get("cells", []):
        if typeof(cell) == TYPE_DICTIONARY:
            max_elevation = maxf(max_elevation, absf(float(cell.get("elevation", 0))))
    var target := Vector3(0.0, max_elevation * LEVEL_HEIGHT * 0.5, 0.0)
    _world_camera.size = maxf(9.0, float(maxi(dims.x, dims.y)) * 1.12)
    _world_camera.position = target + Vector3(_world_camera.size * 0.85, _world_camera.size * 1.25, _world_camera.size * 0.85)
    _world_camera.look_at(target, Vector3.UP)


func _world_material(color: Color, roughness: float = 0.92) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = roughness
    return material


func _world_box(parent: Node3D, center: Vector3, dimensions: Vector3, color: Color, casts_shadow: bool = true) -> MeshInstance3D:
    var box := BoxMesh.new()
    box.size = dimensions
    var instance := MeshInstance3D.new()
    instance.mesh = box
    instance.material_override = _world_material(color)
    instance.position = center
    if not casts_shadow:
        instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    parent.add_child(instance)
    return instance


func _sync_world() -> void:
    if not is_instance_valid(_world_geometry):
        return
    for child in _world_geometry.get_children():
        child.queue_free()
    _position_world_camera()
    if _map.is_empty():
        return
    var dims := _grid_dimensions()
    _world_box(_world_geometry, Vector3(0, -1.2, 0), Vector3(dims.x + 4.0, 0.2, dims.y + 4.0), Color("#18161e"), false)
    var selected := _selected_token()
    var reach := _movement_reach()
    for y in range(dims.y):
        for x in range(dims.x):
            var cell := _terrain_cell(x, y)
            var elevation := int(cell.get("elevation", 0)) if not cell.is_empty() else 0
            var top := float(elevation) * LEVEL_HEIGHT
            var bottom := minf(-TILE_THICKNESS, top - TILE_THICKNESS)
            var height := top - bottom
            var ground := _terrain_color(str(cell.get("terrain_type", "")), (x + y) % 2 == 0) if not cell.is_empty() else GROUND if (x + y) % 2 == 0 else GROUND_ALT
            if not selected.is_empty() and int(selected.get("gridX", -999)) == x and int(selected.get("gridY", -999)) == y:
                ground = Color("#58416e")
            var center := Vector3(float(x) - float(dims.x) * 0.5 + 0.5, (top + bottom) * 0.5, float(y) - float(dims.y) * 0.5 + 0.5)
            _world_box(_world_geometry, center, Vector3(0.96, height, 0.96), ground)
            if reach > 0 and not selected.is_empty():
                var distance := absi(x - int(selected.get("gridX", -999))) + absi(y - int(selected.get("gridY", -999)))
                var preview_reachable := distance == 1
                if bool(_terrain().get("initialized", false)):
                    preview_reachable = distance == 1 and _preview_step_allowed(selected, cell, reach)
                if preview_reachable:
                    _world_box(_world_geometry, Vector3(center.x, top + 0.015, center.z), Vector3(0.76, 0.025, 0.76), Color("#7a4bc2aa"), false)
            if _terrain_selected == Vector2i(x, y):
                _world_box(_world_geometry, Vector3(center.x, top + 0.035, center.z), Vector3(0.84, 0.035, 0.84), Color("#b69ad8cc"), false)
    _sync_world_walls(dims)
    _sync_world_connections(dims)
    for token in _tokens:
        var x := int(token.get("gridX", -999))
        var y := int(token.get("gridY", -999))
        if x < 0 or y < 0 or x >= dims.x or y >= dims.y:
            continue
        var cell := _terrain_cell(x, y)
        var top := float(token.get("elevation", cell.get("elevation", 0))) * LEVEL_HEIGHT
        var center := Vector3(float(x) - float(dims.x) * 0.5 + 0.5, top + 0.38, float(y) - float(dims.y) * 0.5 + 0.5)
        var token_root := Node3D.new()
        token_root.position = center
        _world_geometry.add_child(token_root)
        var base := CylinderMesh.new()
        base.top_radius = 0.36
        base.bottom_radius = 0.4
        base.height = 0.08
        var base_instance := MeshInstance3D.new()
        base_instance.mesh = base
        base_instance.material_override = _world_material(Color("#7a4bc2") if str(token.get("id", "")) == _selected_id else Color("#716b7b"))
        token_root.add_child(base_instance)
        var body := CapsuleMesh.new()
        body.radius = 0.22
        body.height = 0.58
        var body_instance := MeshInstance3D.new()
        body_instance.mesh = body
        body_instance.position.y = 0.38
        var body_color := HOSTILE if token.get("disposition") == "hostile" else FRIENDLY
        body_instance.material_override = _world_material(body_color, 0.78)
        token_root.add_child(body_instance)
        var head := SphereMesh.new()
        head.radius = 0.17
        head.height = 0.34
        var head_instance := MeshInstance3D.new()
        head_instance.mesh = head
        head_instance.position.y = 0.78
        head_instance.material_override = _world_material(body_color.lightened(0.12), 0.72)
        token_root.add_child(head_instance)
        if str(token.get("id", "")) == _selected_id:
            var name := Label3D.new()
            name.text = str(token.get("name", ""))
            name.font_size = 18
            name.pixel_size = 0.006
            name.billboard = BaseMaterial3D.BILLBOARD_ENABLED
            name.modulate = Color("#f0edf4")
            name.outline_size = 5
            name.position.y = 1.05
            token_root.add_child(name)


func _sync_world_walls(dims: Vector2i) -> void:
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
        var first := Vector3((float(wall.get("x1", 0)) - offset_x) / cell_size - float(dims.x) * 0.5, 0.4, (float(wall.get("y1", 0)) - offset_y) / cell_size - float(dims.y) * 0.5)
        var second := Vector3((float(wall.get("x2", 0)) - offset_x) / cell_size - float(dims.x) * 0.5, 0.4, (float(wall.get("y2", 0)) - offset_y) / cell_size - float(dims.y) * 0.5)
        var delta := second - first
        if delta.length() < 0.001:
            continue
        var wall_mesh := BoxMesh.new()
        wall_mesh.size = Vector3(0.12, 0.8, delta.length()) if absf(delta.x) > absf(delta.z) else Vector3(delta.length(), 0.8, 0.12)
        var wall_instance := MeshInstance3D.new()
        wall_instance.mesh = wall_mesh
        wall_instance.material_override = _world_material(Color("#77717f"))
        wall_instance.position = (first + second) * 0.5
        if absf(delta.x) > absf(delta.z):
            wall_instance.rotation.y = atan2(delta.x, delta.z)
        else:
            wall_instance.rotation.y = atan2(delta.x, delta.z)
        _world_geometry.add_child(wall_instance)


func _sync_world_connections(dims: Vector2i) -> void:
    for connection in _terrain().get("connections", []):
        if typeof(connection) != TYPE_DICTIONARY:
            continue
        var from: Variant = connection.get("from", [])
        var to: Variant = connection.get("to", [])
        if typeof(from) != TYPE_ARRAY or typeof(to) != TYPE_ARRAY or from.size() != 2 or to.size() != 2:
            continue
        var from_cell := Vector2i(int(from[0]), int(from[1]))
        var to_cell := Vector2i(int(to[0]), int(to[1]))
        if from_cell.x < 0 or from_cell.y < 0 or to_cell.x < 0 or to_cell.y < 0 or from_cell.x >= dims.x or to_cell.x >= dims.x or from_cell.y >= dims.y or to_cell.y >= dims.y:
            continue
        var from_data := _terrain_cell(from_cell.x, from_cell.y)
        var to_data := _terrain_cell(to_cell.x, to_cell.y)
        var start := Vector3(float(from_cell.x) - float(dims.x) * 0.5 + 0.5, float(from_data.get("elevation", 0)) * LEVEL_HEIGHT, float(from_cell.y) - float(dims.y) * 0.5 + 0.5)
        var finish := Vector3(float(to_cell.x) - float(dims.x) * 0.5 + 0.5, float(to_data.get("elevation", 0)) * LEVEL_HEIGHT, float(to_cell.y) - float(dims.y) * 0.5 + 0.5)
        var along_x := from_cell.x != to_cell.x
        for step in range(3):
            var point := start.lerp(finish, float(step + 1) / 4.0)
            point.y += 0.08
            var step_size := Vector3(0.30, 0.12, 0.70) if along_x else Vector3(0.70, 0.12, 0.30)
            _world_box(_world_geometry, point, step_size, Color("#82758f"))


func _connect_socket() -> void:
    _socket = WebSocketPeer.new()
    # The first authenticated sync batches terrain, actors, tokens and combat
    # snapshots. Godot's 64 KiB default can silently drop one of those frames.
    _socket.inbound_buffer_size = 1024 * 1024
    _socket.outbound_buffer_size = 256 * 1024
    var error := _socket.connect_to_url(_socket_url)
    if error != OK:
        _reconnect_in_progress = false
        _status = "Falha ao conectar ao Gravewright: " + str(error)
        return
    _reconnect_in_progress = true
    _reconnect_failure_elapsed = 0.0


func _process(_delta: float) -> void:
    _update_hud()
    _socket.poll()
    var state := _socket.get_ready_state()
    if state == WebSocketPeer.STATE_OPEN:
        if not _connected:
            _connected = true
            _reconnect_in_progress = false
            _reconnect_attempts = 0
            _reconnect_elapsed = 0.0
            _status = "Conectado. Consultando mapas autorizados…"
            _send("maps.sync", {})
        while _socket.get_available_packet_count() > 0:
            _receive(_socket.get_packet().get_string_from_utf8())
    elif state == WebSocketPeer.STATE_CLOSED:
        if _connected:
            _connected = false
            _reconnect_in_progress = false
            _reconnect_elapsed = 0.0
            _reconnect_failure_elapsed = 0.0
            # A command may have reached the server before its acknowledgement
            # was lost. Drop local pending IDs; never replay mutable commands.
            _pending_request = ""
            _pending_resource_request = ""
            _pending_terrain_request = ""
            _status = "Conexão caiu. Tentando retomar sem repetir comandos…"
        if _reconnect_in_progress:
            _reconnect_failure_elapsed += _delta
            if _reconnect_failure_elapsed >= 2.0:
                _reconnect_in_progress = false
                _reconnect_elapsed = 0.0
        if not _reconnect_in_progress:
            if _reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
                _status = "Reconexão interrompida após %s tentativas. Recarregue para iniciar uma nova sessão." % MAX_RECONNECT_ATTEMPTS
                set_process(false)
            else:
                _reconnect_elapsed += _delta
                var wait_seconds := minf(0.5 * pow(2.0, float(_reconnect_attempts)), 8.0)
                if _reconnect_elapsed >= wait_seconds:
                    _reconnect_attempts += 1
                    _reconnect_elapsed = 0.0
                    _status = "Reconectando (%s/%s)…" % [_reconnect_attempts, MAX_RECONNECT_ATTEMPTS]
                    _connect_socket()
    queue_redraw()


func _input(event: InputEvent) -> void:
    if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_H:
        if is_instance_valid(_hud_panel):
            _hud_panel.visible = not _hud_panel.visible
        get_viewport().set_input_as_handled()


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
                _sync_world()
                queue_redraw()
        "resources.state":
            if payload.get("module") == "combat" and payload.get("sceneId") == _scene_id:
                var combat_state: Variant = payload.get("state", {})
                if typeof(combat_state) == TYPE_DICTIONARY:
                    _combat = combat_state
                    _sync_world()
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
            _sync_world()
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
    _terrain_by_cell.clear()
    for entry in data.get("maps", []):
        if typeof(entry) == TYPE_DICTIONARY and entry.get("id") == _scene_id:
            _map = entry
            break
    if _scene_id.is_empty() or _map.is_empty():
        _status = "Nenhum mapa ativo está disponível para esta sessão."
        _sync_world()
        return
    _status = "Mapa: " + str(_map.get("name", "sem nome")) + ". Lendo unidades…"
    _sync_world()
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
    var mission: Variant = _combat.get("mission")
    if typeof(mission) == TYPE_DICTIONARY and mission.get("state") == "ACTIVE":
        return false
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


func _point_to_cell(point: Vector2) -> Vector2i:
    if not is_instance_valid(_world_camera):
        return Vector2i(-1, -1)
    var ray_origin := _world_camera.project_ray_origin(point)
    var ray_direction := _world_camera.project_ray_normal(point)
    if absf(ray_direction.y) < 0.0001:
        return Vector2i(-1, -1)
    var dims := _grid_dimensions()
    var selected := Vector2i(-1, -1)
    var nearest := INF
    for y in range(dims.y):
        for x in range(dims.x):
            var elevation := float(_terrain_cell(x, y).get("elevation", 0))
            var plane_y := elevation * LEVEL_HEIGHT
            var distance := (plane_y - ray_origin.y) / ray_direction.y
            if distance < 0.0 or distance >= nearest:
                continue
            var hit := ray_origin + ray_direction * distance
            var local_x := hit.x + float(dims.x) * 0.5
            var local_z := hit.z + float(dims.y) * 0.5
            if local_x >= float(x) and local_x <= float(x + 1) and local_z >= float(y) and local_z <= float(y + 1):
                selected = Vector2i(x, y)
                nearest = distance
    return selected


func _token_at_point(point: Vector2) -> Dictionary:
    var cell := _point_to_cell(point)
    if cell.x < 0 or cell.y < 0:
        return {}
    for index in range(_tokens.size() - 1, -1, -1):
        var token := _tokens[index]
        if int(token.get("gridX", -999)) == cell.x and int(token.get("gridY", -999)) == cell.y:
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
        _sync_world()
        queue_redraw()
        return
    if event.button_index != MOUSE_BUTTON_LEFT or _map.is_empty() or not _pending_request.is_empty():
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
            _sync_world()
            return
        if bool(token_hit.get("canControl", false)):
            _selected_id = str(token_hit.get("id", ""))
            _status = "Unidade selecionada: " + str(token_hit.get("name", ""))
        else:
            _selected_id = ""
            _status = "Você não controla essa unidade."
        queue_redraw()
        _sync_world()
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
                _sync_world()
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
        _sync_world()
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
    _terrain_toolbar_control = HFlowContainer.new()
    _terrain_toolbar_control.name = "TerrainTools"
    _terrain_toolbar_control.position = Vector2(20.0, 66.0)
    _terrain_toolbar_control.add_theme_constant_override("h_separation", 4)
    _terrain_toolbar_control.add_theme_constant_override("v_separation", 3)
    add_child(_terrain_toolbar_control)
    _terrain_initialize_button = _hud_button("Preparar terreno", 132)
    _terrain_initialize_button.pressed.connect(func(): _send_terrain("initialize", {"width": 16, "height": 16}))
    _terrain_toolbar_control.add_child(_terrain_initialize_button)
    var terrain_labels := ["Normal", "Difícil", "Severo", "Bloqueio"]
    var terrain_types := ["NORMAL", "DIFICIL", "SEVERO", "INTRANSPONIVEL"]
    for index in range(terrain_labels.size()):
        var terrain_type: String = terrain_types[index]
        var terrain_button := _hud_button(terrain_labels[index], 72)
        terrain_button.pressed.connect(func(): _terrain_type = terrain_type)
        _terrain_tools.append(terrain_button)
        _terrain_toolbar_control.add_child(terrain_button)
    var lower_button := _hud_button("Altura −", 72)
    lower_button.pressed.connect(func(): _terrain_height = maxi(-20, _terrain_height - 1))
    _terrain_tools.append(lower_button)
    _terrain_toolbar_control.add_child(lower_button)
    var higher_button := _hud_button("Altura +", 72)
    higher_button.pressed.connect(func(): _terrain_height = mini(20, _terrain_height + 1))
    _terrain_tools.append(higher_button)
    _terrain_toolbar_control.add_child(higher_button)
    var stairs_button := _hud_button("Escada", 66)
    stairs_button.pressed.connect(func():
        _terrain_connect_mode = not _terrain_connect_mode
        _terrain_selected = Vector2i(-1, -1)
    )
    _terrain_tools.append(stairs_button)
    _terrain_toolbar_control.add_child(stairs_button)

    var panel := PanelContainer.new()
    panel.name = "TacticsHud"
    panel.tooltip_text = "Controles táticos. Pressione H para recolher o painel."
    panel.anchor_left = 0.0
    panel.anchor_right = 1.0
    panel.anchor_top = 1.0
    panel.anchor_bottom = 1.0
    panel.offset_left = 14.0
    panel.offset_right = -14.0
    panel.offset_top = -156.0
    panel.offset_bottom = -10.0
    panel.mouse_filter = Control.MOUSE_FILTER_PASS
    var panel_style := StyleBoxFlat.new()
    panel_style.bg_color = Color("#17161dee")
    panel_style.border_color = Color("#544b61")
    panel_style.set_border_width_all(1)
    panel_style.set_corner_radius_all(9)
    panel_style.content_margin_left = 9
    panel_style.content_margin_right = 9
    panel_style.content_margin_top = 7
    panel_style.content_margin_bottom = 7
    panel.add_theme_stylebox_override("panel", panel_style)
    _hud_panel = panel
    add_child(panel)
    var column := VBoxContainer.new()
    column.add_theme_constant_override("separation", 3)
    panel.add_child(column)

    _mission_label = Label.new()
    _mission_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    _mission_label.clip_text = true
    _mission_label.add_theme_font_size_override("font_size", 13)
    _mission_label.add_theme_color_override("font_color", Color("#d5c5ea"))
    _mission_label.text = "Missão ainda não criada"
    column.add_child(_mission_label)

    var first := HFlowContainer.new()
    first.add_theme_constant_override("h_separation", 4)
    first.add_theme_constant_override("v_separation", 3)
    column.add_child(first)
    var move_button := _hud_button("Mover", 62)
    move_button.pressed.connect(func(): _set_mode("move"))
    first.add_child(move_button)
    var attack_button := _hud_button("Atacar", 62)
    attack_button.pressed.connect(func(): _set_mode("attack"))
    first.add_child(attack_button)
    var ambush_button := _hud_button("Emboscada", 82)
    ambush_button.pressed.connect(func(): _set_mode("ambush"))
    first.add_child(ambush_button)
    _attribute_picker = OptionButton.new()
    _attribute_picker.add_item("Corpo + Combate")
    _attribute_picker.add_item("Agilidade + Combate")
    _attribute_picker.custom_minimum_size = Vector2(132, 27)
    _style_hud_control(_attribute_picker)
    _attribute_picker.item_selected.connect(func(index: int): _attack_attribute = "corpo" if index == 0 else "agilidade")
    first.add_child(_attribute_picker)
    var next_button := _hud_button("Próxima ativação", 112)
    next_button.pressed.connect(_next_activation)
    first.add_child(next_button)

    _mission_admin_row = HFlowContainer.new()
    _mission_admin_row.add_theme_constant_override("h_separation", 4)
    _mission_admin_row.add_theme_constant_override("v_separation", 3)
    column.add_child(_mission_admin_row)
    var create_button := _hud_button("Criar missão", 86)
    create_button.pressed.connect(func(): _mission_command("mission.create", {"definition": "knossos-evacuation"}))
    _mission_admin_row.add_child(create_button)
    _role_picker = OptionButton.new()
    _role_picker.add_item("Aliado")
    _role_picker.set_item_metadata(0, "ALLY")
    _role_picker.add_item("Silmari")
    _role_picker.set_item_metadata(1, "HOSTILE")
    _role_picker.add_item("Nomos evacuar")
    _role_picker.set_item_metadata(2, "EVACUEE")
    _role_picker.custom_minimum_size = Vector2(126, 27)
    _style_hud_control(_role_picker)
    _role_picker.item_selected.connect(func(index: int): _mission_role = str(_role_picker.get_item_metadata(index)))
    _mission_admin_row.add_child(_role_picker)
    var register_button := _hud_button("Registrar token", 98)
    register_button.pressed.connect(_register_selected)
    _mission_admin_row.add_child(register_button)
    var ready_button := _hud_button("Pronto", 58)
    ready_button.pressed.connect(func(): _mission_command("mission.ready", {}))
    _mission_admin_row.add_child(ready_button)
    var start_button := _hud_button("Iniciar missão", 92)
    start_button.pressed.connect(func(): _mission_command("mission.start", {}))
    _mission_admin_row.add_child(start_button)
    var abort_button := _hud_button("Encerrar", 66)
    abort_button.pressed.connect(func(): _mission_command("mission.abort", {"reason": "gm_abort"}))
    _mission_admin_row.add_child(abort_button)

    _combat_admin_row = HFlowContainer.new()
    _combat_admin_row.add_theme_constant_override("h_separation", 4)
    _combat_admin_row.add_theme_constant_override("v_separation", 3)
    column.add_child(_combat_admin_row)
    _friendly_representative = OptionButton.new()
    _friendly_representative.custom_minimum_size = Vector2(132, 27)
    _friendly_representative.tooltip_text = "Representante aliado para a iniciativa por lados."
    _style_hud_control(_friendly_representative)
    _combat_admin_row.add_child(_friendly_representative)
    _hostile_representative = OptionButton.new()
    _hostile_representative.custom_minimum_size = Vector2(132, 27)
    _hostile_representative.tooltip_text = "Representante Silmari para a iniciativa por lados."
    _style_hud_control(_hostile_representative)
    _combat_admin_row.add_child(_hostile_representative)
    var roll_sides := _hud_button("Rolar iniciativa", 104)
    roll_sides.pressed.connect(_roll_side_initiative)
    _combat_admin_row.add_child(roll_sides)
    var friendly_first := _hud_button("Aliados primeiro", 104)
    friendly_first.pressed.connect(func(): _combat_command("choose-first-side", {"side": "friendly"}))
    _combat_admin_row.add_child(friendly_first)
    var hostile_first := _hud_button("Silmari primeiro", 104)
    hostile_first.pressed.connect(func(): _combat_command("choose-first-side", {"side": "hostile"}))
    _combat_admin_row.add_child(hostile_first)
    var start_combat := _hud_button("Iniciar combate", 100)
    start_combat.pressed.connect(func(): _combat_command("start"))
    _combat_admin_row.add_child(start_combat)
    _combat_admin_label = Label.new()
    _combat_admin_label.clip_text = true
    _combat_admin_label.custom_minimum_size.x = 110
    _combat_admin_label.add_theme_font_size_override("font_size", 11)
    _combat_admin_label.add_theme_color_override("font_color", Color("#bca4d8"))
    _combat_admin_row.add_child(_combat_admin_label)

    var third := HBoxContainer.new()
    third.add_theme_constant_override("separation", 8)
    column.add_child(third)
    _damage_button = _hud_button("Aplicar dano", 102)
    _damage_button.pressed.connect(_apply_damage)
    third.add_child(_damage_button)
    _selection_label = Label.new()
    _selection_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    _selection_label.clip_text = true
    _selection_label.add_theme_font_size_override("font_size", 11)
    _selection_label.add_theme_color_override("font_color", Color("#c6c2cf"))
    _selection_label.size_flags_stretch_ratio = 2.0
    third.add_child(_selection_label)
    _resolution_label = Label.new()
    _resolution_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    _resolution_label.size_flags_stretch_ratio = 1.0
    _resolution_label.custom_minimum_size.x = 110
    _resolution_label.clip_text = true
    _resolution_label.add_theme_font_size_override("font_size", 11)
    _resolution_label.add_theme_color_override("font_color", Color("#c7a9e9"))
    third.add_child(_resolution_label)


func _style_hud_control(control: Control) -> void:
    control.add_theme_font_size_override("font_size", 12)
    control.add_theme_color_override("font_color", Color("#e5e2eb"))


func _hud_button(label: String, width: float) -> Button:
    var button := Button.new()
    button.text = label
    button.custom_minimum_size = Vector2(width, 27)
    button.focus_mode = Control.FOCUS_NONE
    button.add_theme_font_size_override("font_size", 12)
    button.add_theme_color_override("font_color", Color("#e5e2eb"))
    button.add_theme_color_override("font_hover_color", Color("#ffffff"))
    button.add_theme_color_override("font_pressed_color", Color("#d8c2f4"))
    var normal := StyleBoxFlat.new()
    normal.bg_color = Color("#26242d")
    normal.border_color = Color("#514b5a")
    normal.set_border_width_all(1)
    normal.set_corner_radius_all(5)
    normal.content_margin_left = 6
    normal.content_margin_right = 6
    var hover := normal.duplicate() as StyleBoxFlat
    hover.bg_color = Color("#38313f")
    hover.border_color = Color("#8e69bd")
    var pressed := normal.duplicate() as StyleBoxFlat
    pressed.bg_color = Color("#463455")
    button.add_theme_stylebox_override("normal", normal)
    button.add_theme_stylebox_override("hover", hover)
    button.add_theme_stylebox_override("pressed", pressed)
    _style_hud_control(button)
    return button


func _set_mode(mode: String) -> void:
    _mode = mode
    _status = "Modo: " + ("ataque corpo a corpo" if mode == "attack" else "Emboscada (Nível I)" if mode == "ambush" else "movimento") + ". Selecione unidade e alvo."
    if mode == "move":
        _selected_id = ""
    _sync_world()
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


func _roll_side_initiative() -> void:
    var friendly_id := _selected_representative_id(_friendly_representative)
    var hostile_id := _selected_representative_id(_hostile_representative)
    if friendly_id.is_empty() or hostile_id.is_empty():
        _status = "Escolha um representante vivo de cada lado."
        return
    _combat_command("roll-initiative", {
        "friendlyRepresentative": friendly_id,
        "hostileRepresentative": hostile_id,
    })


func _selected_representative_id(picker: OptionButton) -> String:
    if picker == null or picker.item_count == 0 or picker.selected < 0:
        return ""
    return str(picker.get_item_metadata(picker.selected))


func _refresh_representative_picker(picker: OptionButton, side: String) -> void:
    var representatives: Array[Dictionary] = []
    for row in _combat.get("combatants", []):
        if typeof(row) == TYPE_DICTIONARY and row.get("side") == side and not bool(row.get("defeated", false)):
            representatives.append(row)
    var signature_parts: Array[String] = []
    for row in representatives:
        signature_parts.append(str(row.get("id", "")) + ":" + str(row.get("name", "")))
    var signature := "|".join(signature_parts)
    var key := side + ":" + signature
    if picker == null:
        return
    var previous := str(picker.get_meta("signature", ""))
    if previous == key:
        return
    picker.clear()
    for row in representatives:
        var index := picker.item_count
        picker.add_item(str(row.get("name", "Representante")))
        picker.set_item_metadata(index, str(row.get("id", "")))
    picker.set_meta("signature", key)


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
    var actor_id := str(target.get("actorId", ""))
    var attack: Dictionary = {}
    var resolutions: Variant = _combat.get("config", {}).get("resolutions", [])
    if typeof(resolutions) == TYPE_ARRAY:
        for index in range(resolutions.size() - 1, -1, -1):
            var item: Variant = resolutions[index]
            if typeof(item) == TYPE_DICTIONARY and item.get("kind") == "action" and item.get("targetId") == actor_id and bool(item.get("success", false)) and typeof(item.get("damageProfile")) == TYPE_DICTIONARY and not item.has("damageEventId"):
                attack = item
                break
    if attack.is_empty():
        _status = "Nenhum ataque bem-sucedido e sem dano registrado contra este alvo."
        return
    _combat_command("damage", {
        "targetId": str(target.get("id", "")),
        "attackResolutionId": str(attack.get("id", "")),
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
    var gm_role := bool(_terrain().get("canEdit", false))
    var combat_active := bool(_combat.get("active", false))
    var gm_controls := gm_role and not combat_active
    if is_instance_valid(_terrain_toolbar_control):
        _terrain_toolbar_control.visible = _terrain_editable()
    if is_instance_valid(_terrain_initialize_button):
        _terrain_initialize_button.visible = not bool(_terrain().get("initialized", false))
    for terrain_button in _terrain_tools:
        terrain_button.visible = bool(_terrain().get("initialized", false))
    if is_instance_valid(_mission_admin_row):
        _mission_admin_row.visible = gm_role
    if is_instance_valid(_combat_admin_row):
        _combat_admin_row.visible = gm_controls
    if is_instance_valid(_damage_button):
        _damage_button.visible = gm_role and combat_active
    if is_instance_valid(_hud_panel):
        _hud_panel.offset_top = -156.0 if gm_controls else -116.0 if gm_role else -88.0
    _refresh_representative_picker(_friendly_representative, "friendly")
    _refresh_representative_picker(_hostile_representative, "hostile")
    var initiative: Variant = _combat.get("config", {}).get("side_initiative", {})
    var has_roll: bool = typeof(initiative) == TYPE_DICTIONARY and initiative.has("winner")
    var chosen_side := str(_combat.get("config", {}).get("first_side", ""))
    if is_instance_valid(_combat_admin_label):
        _combat_admin_label.text = "Iniciativa %s · primeiro lado: %s" % [str(initiative.get("winner", "pendente")), chosen_side if not chosen_side.is_empty() else "pendente"]
    if is_instance_valid(_combat_admin_row):
        for child in _combat_admin_row.get_children():
            if child is Button:
                match child.text:
                    "Rolar iniciativa": child.disabled = bool(_combat.get("active", false)) or _friendly_representative.item_count == 0 or _hostile_representative.item_count == 0
                    "Aliados primeiro", "Silmari primeiro": child.disabled = bool(_combat.get("active", false)) or not has_roll
                    "Iniciar combate": child.disabled = bool(_combat.get("active", false)) or chosen_side not in ["friendly", "hostile"]
    if typeof(mission) == TYPE_DICTIONARY:
        var current := str(_combat.get("current_name", "sem ativação"))
        _mission_label.text = "%s · %s · Rodada %s · %s" % [str(mission.get("definition", {}).get("title", "Missão")), str(mission.get("state", "")), str(_combat.get("round", 0)), current]
    else:
        _mission_label.text = "Missão ainda não criada · Rodada %s · %s" % [str(_combat.get("round", 0)), str(_combat.get("current_name", "sem ativação"))]
    var selected := _selected_token()
    _selection_label.text = "Seleção: " + str(selected.get("name", "nenhuma")) + " · " + _status
    _selection_label.tooltip_text = _selection_label.text
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
        _resolution_label.text = "Sem resultado recente"
    _resolution_label.tooltip_text = _resolution_label.text


func _draw() -> void:
    draw_rect(Rect2(Vector2.ZERO, size), Color("#111015"))
    if _map.is_empty():
        var font: Font = ThemeDB.fallback_font
        draw_string(font, Vector2(20, 112), _status, HORIZONTAL_ALIGNMENT_LEFT, size.x - 40, 15, Color("#d2ced8"))


func _terrain_color(terrain_type: String, alternate: bool) -> Color:
    match terrain_type:
        "NORMAL": return Color("#4b4853") if alternate else Color("#403e49")
        "DIFICIL": return Color("#62546f") if alternate else Color("#564861")
        "SEVERO": return Color("#4d3c57") if alternate else Color("#403247")
        "INTRANSPONIVEL": return Color("#34323b") if alternate else Color("#2c2a32")
        _: return GROUND if alternate else GROUND_ALT


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
