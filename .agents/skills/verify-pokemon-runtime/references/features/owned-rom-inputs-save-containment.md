# Owned ROM, inputs, and save containment

**Implementation:** available through the real-runtime verifier CLI.
**Verification:** passed for the owned FireRed Rev 1 and
LeafGreen Rev 1 targets, each with matching ROM identity and dedicated
runtime state.

The retained FireRed report records `ok: true`, matching ROM identity, all
10 GBA key-bit checks, a successful checkpoint save/reload, snapshot frame
120, and `normal_saves_unchanged: true`. The LeafGreen report records the
same checks, snapshot frame 81, and unchanged normal saves. The parent-run
cleanup check found no owned Windows mGBA process after stop. This verifies
the input and persistence boundary; it does not prove game progression.

The FireRed and LeafGreen reports remain local and ignored by Git. They
are not available from a clean clone. Use the
[recipe](../../SKILL.md) with a fresh ignored output folder to repeat the
checks.

Story progress, battles, and LeafGreen semantic gameplay remain unverified.
