#!/bin/bash

# Run repository-relative tools from the project root, even from another cwd.
POKEMON_SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$POKEMON_SCRIPT_DIR/.." || exit 1
# $1: phrase to find
# $2: phrase to replace $1
if [ "$1" = "" -o "$2" = "" ]; then
	echo "Usage: $0 [PHRASE TO FIND] [PHRASE TO REPLACE PHRASE TO FIND]"
	exit 0
fi

sed -i 's/\<'"$1"'\>/'"$2"'/' $(grep -lwr --include="*.s" --include="*.h" --include="*.c" --include="*.inc" --include="*.json" --include="*.txt" --exclude-dir="tools" --exclude-dir=".git" --exclude-dir="build" --exclude-dir="berry_fix/build" --exclude-dir="berry_fix/payload/build" --exclude-dir=".travis" "$1")
