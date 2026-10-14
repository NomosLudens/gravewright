extends Control
## Read Gravewright's authorized campaign snapshots and request movements.
## Never invent actors, persist state locally, or move a token before server confirmation.

const HALF_WIDTH := 24.0
const HALF_HEIGHT := 12.0
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
var _tokens: Array[Dictionary] = []
var _selected_id := ""
var _pending_request := ""
var _connected := false
var _status := "Conectando ao Gravewright…"


func _ready() -> void:
    resized.connect(queue_redraw)
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
    _scene_id = next_scene
    _map.clear()
    for entry in data.get("maps", []):
        if typeof(entry) == TYPE_DICTIONARY and entry.get("id") == _scene_id:
            _map = entry
            break
    if _scene_id.is_empty() or _map.is_empty():
        _status = "Nenhum mapa ativo está disponível para esta sessão."
        return
    _status = "Mapa: " + str(_map.get("name", "sem nome")) + ". Lendo unidades…"
    _send("tokens.sync", {"mapId": _scene_id})


func _grid_dimensions() -> Vector2i:
    var cell_size := maxf(1.0, float(_map.get("gridSize", 70)) * float(_map.get("imageScale", 1)))
    return Vector2i(
        clampi(int(ceil(float(_map.get("width", 0)) / cell_size)), 1, MAX_CELLS),
        clampi(int(ceil(float(_map.get("height", 0)) / cell_size)), 1, MAX_CELLS)
    )


func _origin() -> Vector2:
    return Vector2(size.x * 0.5, 86.0)


func _project(cell: Vector2) -> Vector2:
    return _origin() + Vector2(
        (cell.x - cell.y) * HALF_WIDTH,
        (cell.x + cell.y) * HALF_HEIGHT
    )


func _point_to_cell(point: Vector2) -> Vector2i:
    var p := point - _origin()
    var u := p.x / HALF_WIDTH
    var v := p.y / HALF_HEIGHT
    return Vector2i(floori((u + v) / 2.0), floori((v - u) / 2.0))


func _token_on_cell(cell: Vector2i) -> Dictionary:
    for entry in _tokens:
        if floori(float(entry.get("gridX", -999))) == cell.x and floori(float(entry.get("gridY", -999))) == cell.y:
            return entry
    return {}


func _selected_token() -> Dictionary:
    for entry in _tokens:
        if entry.get("id") == _selected_id:
            return entry
    return {}


func _gui_input(event: InputEvent) -> void:
    if not event is InputEventMouseButton or not event.pressed:
        return
    if event.button_index == MOUSE_BUTTON_RIGHT:
        _selected_id = ""
        queue_redraw()
        return
    if event.button_index != MOUSE_BUTTON_LEFT or _map.is_empty() or not _pending_request.is_empty():
        return
    var target := _point_to_cell(event.position)
    var dims := _grid_dimensions()
    if target.x < 0 or target.y < 0 or target.x >= dims.x or target.y >= dims.y:
        return
    var hit := _token_on_cell(target)
    if not hit.is_empty():
        if bool(hit.get("canControl", false)):
            _selected_id = str(hit.get("id", ""))
            _status = "Unidade selecionada: " + str(hit.get("name", ""))
        else:
            _selected_id = ""
            _status = "Você não controla essa unidade."
        queue_redraw()
        return
    var selected := _selected_token()
    if selected.is_empty() or not bool(selected.get("canControl", false)):
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


func _draw() -> void:
    draw_rect(Rect2(Vector2.ZERO, size), Color("#14161c"))
    var font: Font = ThemeDB.fallback_font
    draw_string(font, Vector2(20, 30), "GRAVEWRIGHT  /  TACTICS", HORIZONTAL_ALIGNMENT_LEFT, -1, 22, EMBER)
    draw_string(font, Vector2(20, 55), "VTT tático • movimento validado pelo servidor", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color.WHITE)
    if _map.is_empty():
        draw_string(font, Vector2(20, 130), _status, HORIZONTAL_ALIGNMENT_LEFT, size.x - 40, 17, Color.WHITE)
        return
    var dims := _grid_dimensions()
    for y in range(dims.y):
        for x in range(dims.x):
            var a := _project(Vector2(x, y))
            var b := _project(Vector2(x + 1, y))
            var c := _project(Vector2(x + 1, y + 1))
            var d := _project(Vector2(x, y + 1))
            var ground := GROUND if (x + y) % 2 == 0 else GROUND_ALT
            if _selected_id != "":
                var sel := _selected_token()
                if not sel.is_empty() and int(sel.get("gridX", -999)) == x and int(sel.get("gridY", -999)) == y:
                    ground = Color("#81512f")
            draw_colored_polygon(PackedVector2Array([a, b, c, d]), ground)
            for edge in [[a, b], [b, c], [c, d], [d, a]]:
                draw_line(edge[0], edge[1], BORDER, 1.0)
    for token in _tokens:
        var x := float(token.get("gridX", -999))
        var y := float(token.get("gridY", -999))
        if x < 0 or y < 0 or x >= dims.x or y >= dims.y:
            continue
        var center := _project(Vector2(x + 0.5, y + 0.5))
        var tint := HOSTILE if token.get("disposition") == "hostile" else FRIENDLY
        var outline := EMBER if str(token.get("id", "")) == _selected_id else Color("#17181c")
        draw_rect(Rect2(center + Vector2(-9, -20), Vector2(18, 19)), outline)
        draw_rect(Rect2(center + Vector2(-7, -18), Vector2(14, 15)), tint)
        var name := str(token.get("name", ""))
        if name.is_empty():
            name = "?"
        draw_string(font, center + Vector2(-18, -27), name, HORIZONTAL_ALIGNMENT_CENTER, 90, 12, Color.WHITE)
    draw_rect(Rect2(0, size.y - 55, size.x, 55), Color("#0b0d12"))
    draw_string(font, Vector2(15, size.y - 31), _status, HORIZONTAL_ALIGNMENT_LEFT, size.x - 30, 15, Color.WHITE)
    draw_string(font, Vector2(15, size.y - 10), "Clique numa unidade autorizada; clique numa célula adjacente para enviar o movimento.", HORIZONTAL_ALIGNMENT_LEFT, size.x - 30, 12, Color("#acacba"))
