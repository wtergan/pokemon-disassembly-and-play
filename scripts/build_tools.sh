#!/bin/sh

# Run repository-relative tools from the project root, even from another cwd.
POKEMON_SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$POKEMON_SCRIPT_DIR/.." || exit 1
make -C tools/aif2pcm CXX=${1:-g++}
make -C tools/bin2c CXX=${1:-g++}
make -C tools/gbafix CXX=${1:-g++}
make -C tools/gbagfx CXX=${1:-g++}
make -C tools/preproc CXX=${1:-g++}
make -C tools/ramscrgen CXX=${1:-g++}
make -C tools/rsfont CXX=${1:-g++}
make -C tools/scaninc CXX=${1:-g++}
make -C tools/mapjson CXX=${1:-g++}
make -C tools/jsonproc CXX=${1:-g++}
