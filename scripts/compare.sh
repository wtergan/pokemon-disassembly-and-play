#!/bin/bash

# Run repository-relative tools from the project root, even from another cwd.
POKEMON_SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$POKEMON_SCRIPT_DIR/.." || exit 1
# Compares baserom.gba and pokefirered.gba

# create baserom_compare.dump if necessary
if [ ! -f baserom_compare.dump ]; then
	hexdump -C baserom.gba > baserom_compare.dump # can create an empty baserom_compare.dump if no baserom.gba
fi

hexdump -C pokefirered.gba > pokefirered_compare.dump

diff -u baserom_compare.dump pokefirered_compare.dump | less
