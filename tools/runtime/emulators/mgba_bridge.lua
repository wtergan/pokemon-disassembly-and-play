-- mGBA Lua socket bridge for the local Pokemon runtime.
--
-- The Python runtime sends one tab-separated command per line. This script keeps
-- parsing intentionally small so it does not depend on a JSON library inside
-- mGBA.

local function getenv(name, fallback)
	if os and os.getenv then
		return os.getenv(name) or fallback
	end
	return fallback
end

local connect_host = getenv("POKEMON_RUNTIME_HOST", "127.0.0.1")
local bind_host = getenv("POKEMON_RUNTIME_BIND_HOST", connect_host)
if bind_host == "" or bind_host == "0.0.0.0" then
	bind_host = nil
end
local port = tonumber(getenv("POKEMON_RUNTIME_PORT", "8766"))
local connection_mode = getenv("POKEMON_RUNTIME_CONNECTION_MODE", "server")
local log_file = getenv("POKEMON_RUNTIME_LOG_FILE", nil)
local server = nil
local clients = {}
local next_client_id = 1
local client_connected = false
local client_connect_attempts = 0
local next_client_connect_frame = 0

-- Windows-to-WSL loopback forwarding can become available a few frames after
-- mGBA starts. Keep retries finite and frame-spaced so a missing runtime does
-- not continuously block the emulator's Lua callback.
local MAX_CLIENT_CONNECT_ATTEMPTS = 20
local CLIENT_CONNECT_RETRY_FRAMES = 30

local KEYS = {
	-- addKey/clearKey accept bit indices, unlike addKeys/clearKeys.
	a = 0,
	b = 1,
	select = 2,
	start = 3,
	right = 4,
	left = 5,
	up = 6,
	down = 7,
	r = 8,
	l = 9,
}

local function trim(value)
	return (value:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function split_tabs(value)
	local result = {}
	for part in value:gmatch("([^\t]+)") do
		table.insert(result, part)
	end
	return result
end

local function reply(sock, fields)
	sock:send(table.concat(fields, "\t") .. "\n")
end

local function runtime_log(message, is_error)
	local formatted = "Pokemon runtime bridge: " .. tostring(message)
	if is_error then
		console:error(formatted)
	else
		console:log(formatted)
	end
	if log_file and io and io.open then
		local file = io.open(log_file, "a")
		if file then
			file:write(formatted .. "\n")
			file:close()
		end
	end
end

local function ok(sock, fields)
	local parts = { "ok" }
	for _, field in ipairs(fields or {}) do
		table.insert(parts, field)
	end
	reply(sock, parts)
end

local function err(sock, message)
	reply(sock, { "err", "error=" .. tostring(message) })
end

local function frame_field()
	return "frame=" .. tostring(emu:currentFrame())
end

local function handle(sock, line)
	local parts = split_tabs(trim(line))
	local command = parts[1]

	if command == "ping" then
		ok(sock, { "bridge=mgba", frame_field() })
	elseif command == "frame" then
		ok(sock, { frame_field() })
	elseif command == "run" then
		local frames = tonumber(parts[2] or "1") or 1
		for _ = 1, frames do
			emu:runFrame()
		end
		ok(sock, { frame_field() })
	elseif command == "press" then
		local key = KEYS[parts[2] or ""]
		if not key then
			err(sock, "unknown key")
			return
		end
		emu:addKey(key)
		ok(sock, { frame_field() })
	elseif command == "release" then
		local key = KEYS[parts[2] or ""]
		if not key then
			err(sock, "unknown key")
			return
		end
		emu:clearKey(key)
		ok(sock, { frame_field() })
	elseif command == "read8" then
		ok(sock, { "value=" .. tostring(emu:read8(tonumber(parts[2]))), frame_field() })
	elseif command == "read16" then
		ok(sock, { "value=" .. tostring(emu:read16(tonumber(parts[2]))), frame_field() })
	elseif command == "read32" then
		ok(sock, { "value=" .. tostring(emu:read32(tonumber(parts[2]))), frame_field() })
	elseif command == "read_range" then
		local address = tonumber(parts[2])
		local length = tonumber(parts[3])
		if not address or not length or length < 1 or length > 4096 then
			err(sock, "read_range length must be between 1 and 4096")
			return
		end
		local bytes = emu:readRange(address, length)
		local hex = bytes:gsub(".", function(c) return string.format("%02x", string.byte(c)) end)
		ok(sock, { "data=" .. hex, frame_field() })
	elseif command == "screenshot" then
		local path = parts[2]
		if not path then
			err(sock, "missing screenshot path")
			return
		end
		emu:screenshot(path)
		ok(sock, { frame_field() })
	elseif command == "save_state" then
		local path = parts[2]
		if not path then
			err(sock, "missing save state path")
			return
		end
		ok(sock, { "saved=" .. tostring(emu:saveStateFile(path)), frame_field() })
	elseif command == "load_state" then
		local path = parts[2]
		if not path then
			err(sock, "missing load state path")
			return
		end
		ok(sock, { "loaded=" .. tostring(emu:loadStateFile(path)), frame_field() })
	else
		err(sock, "unknown command")
	end
end

local function stop_client(id)
	local sock = clients[id]
	clients[id] = nil
	if sock then
		sock:close()
	end
end

local function client_received(id)
	local sock = clients[id]
	if not sock then
		return
	end
	while true do
		local line, receive_err = sock:receive(1024)
		if line then
			local ok_handle, handle_err = pcall(handle, sock, line)
			if not ok_handle then
				runtime_log("command error: " .. tostring(handle_err), true)
				err(sock, handle_err)
			end
		else
			if receive_err ~= socket.ERRORS.AGAIN then
				stop_client(id)
			end
			return
		end
	end
end

local function accept_client()
	local sock, accept_err = server:accept()
	if accept_err then
		console:error("Pokemon runtime accept error: " .. tostring(accept_err))
		return
	end
	local id = next_client_id
	next_client_id = id + 1
	clients[id] = sock
	sock:add("received", function() client_received(id) end)
	sock:add("error", function() stop_client(id) end)
	runtime_log("client connected")
end

local function start_client()
	if client_connected or client_connect_attempts >= MAX_CLIENT_CONNECT_ATTEMPTS then
		return false
	end
	client_connect_attempts = client_connect_attempts + 1
	local sock, connect_err = socket.connect(connect_host, port)
	if not sock then
		next_client_connect_frame = emu:currentFrame() + CLIENT_CONNECT_RETRY_FRAMES
		runtime_log(
			"connect attempt "
				.. tostring(client_connect_attempts)
				.. "/"
				.. tostring(MAX_CLIENT_CONNECT_ATTEMPTS)
				.. " failed to "
				.. tostring(connect_host)
				.. ":"
				.. tostring(port)
				.. ": "
				.. tostring(connect_err),
			true
		)
		return false
	end
	local id = next_client_id
	next_client_id = id + 1
	clients[id] = sock
	sock:add("received", function() client_received(id) end)
	sock:add("error", function() stop_client(id) end)
	client_connected = true
	runtime_log("connected to " .. tostring(connect_host) .. ":" .. tostring(port))
	return true
end

local function retry_client_connection()
	if client_connected or emu:currentFrame() < next_client_connect_frame then
		return
	end
	start_client()
end

if connection_mode == "client" then
	start_client()
	callbacks:add("frame", retry_client_connection)
else
	server = socket.bind(bind_host, port)
	if not server then
		runtime_log("failed to bind " .. tostring(bind_host or "0.0.0.0") .. ":" .. tostring(port), true)
	else
		local ok_listen, listen_err = server:listen()
		if not ok_listen then
			runtime_log("listen error: " .. tostring(listen_err), true)
		else
			server:add("received", accept_client)
			runtime_log(
				"listening on "
					.. tostring(bind_host or "0.0.0.0")
					.. ":"
					.. tostring(port)
					.. " for "
					.. tostring(connect_host)
			)
		end
	end
end
