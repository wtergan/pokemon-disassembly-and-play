# mGBA Socket Concurrency Encounter

## Encounter

The first browser screenshot of the basic deck showed intermittent `Internal Server Error` even though individual API smoke checks passed.

## Symptoms

- Concurrent browser refreshes called `/health`, `/snapshot`, `/telemetry`, and `/traces`.
- mGBA socket responses became corrupted, with partial fields from different responses appearing in one error.
- Snapshot sometimes reported a missing screenshot file after protocol corruption.

## Root Cause

`MgbaSocketBridge` uses one line-oriented socket. FastAPI serves endpoint handlers in worker threads, so multiple requests wrote and read the same socket concurrently.

## Fix

Serialize every bridge protocol request with a `threading.Lock` around the write/read pair. Add a contention test that fails if multiple requests can overlap the line-protocol critical section.

## Prevention

- Treat each emulator bridge socket as single-reader/single-writer unless the protocol explicitly supports request IDs.
- Browser/API smoke should include concurrent endpoint calls, not only sequential curl checks.
