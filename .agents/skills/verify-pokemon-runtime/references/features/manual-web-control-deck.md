# Manual web control deck

**Implementation:** available at `/` on the local runtime server.
**Verification:** selected live checks passed on 2026-08-16. The semantic Run-button path also passed; the full deck and accessibility have not been audited.

The browser check covered the live deck at a 390-pixel viewport. Its game
image loaded at 240 pixels wide. Pressing and releasing **Hold A** left no
input held, and the UI state-slot **Save** then **Load** round trip reported
the same slot. A fresh browser Run displayed `semantic: success: 1 step`, field/high and held:none; see the local ignored [browser proof](../../../../../.runtime-logs/recovery-2026-08-16/browser-run-proof.txt).

The local ignored [live deck mobile capture](../../../../../.runtime-logs/recovery-2026-08-16/deck-mobile.png)
shows layout and loaded content. The input trace and slot round-trip were
observed during the parent-run browser check. The capture is not committed
and is unavailable from a clean clone.

Open `http://127.0.0.1:8795/` after launching the server. The
[verification recipe](../../SKILL.md) gives the isolated launch and cleanup
steps. The 2026-06-04 fake-runtime browser pass remains historical background,
not evidence for the current live runtime.

Source anchors: `tools/runtime/static/` and `tools/runtime/runtime_app.py`.
