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

local KEYS = {
	a = 1,
	b = 2,
	select = 4,
	start = 8,
	left = 16,
	right = 32,
	up = 64,
	down = 128,
	r = 256,
	l = 512,
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
	local sock = socket.tcp()
	local id = next_client_id
	next_client_id = id + 1
	clients[id] = sock
	sock:add("received", function() client_received(id) end)
	sock:add("error", function() stop_client(id) end)
	if sock:connect(connect_host, port) then
		runtime_log("connected to " .. tostring(connect_host) .. ":" .. tostring(port))
	else
		runtime_log("failed to connect to " .. tostring(connect_host) .. ":" .. tostring(port), true)
		stop_client(id)
	end
end

if connection_mode == "client" then
	start_client()
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
