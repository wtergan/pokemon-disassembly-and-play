# Owned ROM, inputs, and save containment

**Implementation:** available through the real-runtime verifier CLI.
**Verification:** passed on 2026-08-16 for the owned FireRed Rev 1 and
LeafGreen Rev 1 targets, each with matching ROM identity and dedicated
runtime state.

The retained FireRed report records `ok: true`, matching ROM identity, all
10 GBA key-bit checks, a successful checkpoint save/reload, snapshot frame
120, and `normal_saves_unchanged: true`. The LeafGreen report records the
same checks, snapshot frame 81, and unchanged normal saves. The parent-run
cleanup check found no owned Windows mGBA process after stop. This verifies
the input and persistence boundary; it does not prove game progression.

Current evidence is local and ignored by Git:
[FireRed report](../../../../../.runtime-logs/verification/report.json) ·
[LeafGreen report](../../../../../.runtime-logs/recovery-2026-08-16/leafgreen/report.json).
The files are not available from a clean clone. Use the
[recipe](../../SKILL.md) with a fresh ignored output folder to repeat the
checks.

Story progress, battles, and LeafGreen semantic gameplay remain unverified.
