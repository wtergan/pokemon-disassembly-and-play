"""Programmable runtime package for Pokemon FireRed/LeafGreen automation.

The runtime owns HTTP control surfaces, emulator bridge contracts, trace
recording, and game-specific telemetry adapters. It intentionally keeps emulator
primitives separate from Pokemon state decoding so mGBA, BizHawk, FireRed, and
LeafGreen support can evolve independently.
"""

