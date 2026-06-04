# mGBA WSL Bridge Encounter

## Encounter

The first mGBA bridge smoke failed even after the dev build accepted `--script`.

## Symptoms

- Stable Windows mGBA `0.10.5` rejected `--script`.
- Dev mGBA loaded the Lua bridge only after staging it to a Windows-local `C:\...` path.
- Custom `POKEMON_RUNTIME_*` environment variables did not reach Windows processes until exported through `WSLENV`.
- mGBA could listen on Windows, and Windows could connect to it, but WSL could not connect to the Windows listener.
- `emu:runFrame()` from the live GUI socket callback caused the bridge request to time out.

## Root Cause

The WSL/Windows interop boundary affects process environment, current working directory, path shape, and socket reachability. mGBA's live GUI scripting callback is not a safe place to synchronously drive frames.

## Prevention

- Prefer Lua-client reverse sockets for Windows mGBA launched from WSL.
- Pass all runtime env vars through `WSLENV`.
- Stage scripts and screenshots onto Windows-local paths.
- Use real-time waits for frame progression in visible mGBA.
- Keep command-level socket timeouts and Lua `pcall` error handling enabled.
