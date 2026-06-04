# Dedicated Runtime Emulator Instance

Date: 2026-06-03

## Status

Accepted.

## Decision

The FireRed/LeafGreen programmable runtime will use a separate dedicated emulator instance for automation, telemetry, web UI control, and Codex agent loops.

It will not attach to or drive the user's existing Mesen2 play sessions for the first implementation.

## Rationale

- Protects the user's real saves and active play sessions.
- Gives the runtime deterministic save states, trace logs, and reproducible test setup.
- Allows runtime-specific emulator configuration without changing the user's normal emulator profile.
- Keeps Codex/manual web UI input isolated from casual gameplay.
- Makes the first implementation easier to validate because every run starts from a known runtime-owned process and state path.

## Consequences

- The first feature plan should include a runtime-owned save-state and trace directory.
- ROMs remain outside git and are referenced by local path or local ignored config.
- The emulator bridge can be selected for automation quality instead of compatibility with the user's current Mesen2 session.
- Attaching to Mesen2 can remain a later optional integration after the dedicated runtime is stable.

