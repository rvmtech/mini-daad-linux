#!/usr/bin/env bash
#
# Copyright (C) 2026 Ricardo Villalba <rvm3000@gmail.com>
# License: GPL v2 or later
#

# Exit immediately if a command fails
set -e

# ---- VARIABLES ----
. ./config.sh

if [ -f ./custom.sh ]; then
    . ./custom.sh
fi

. ./scripts/functions.sh

init

cecho 6 "Copying required files..."

set_interpreter "zx128k"

cecho 6 "Compiling game..."

./TOOLS/DRC/drf zx 128k "$GAME.dsf"
php ./TOOLS/DRC/drb.php zx 128k $GAMELANG "$GAME.json" "$GAME.DDB" -s

cecho 6 "Preparing images (if any)..."

prepare_images "spectrum"

cecho 6 "Preparing release files..."

php ./TOOLS/DRC/pager128k.php -s -i IMAGES

mkdir -p RELEASE/ZX128K
TAPFILE="RELEASE/ZX128K/$GAME.tap"

POSTER=""
[ -f "IMAGES/daad.scr" ] && POSTER="IMAGES/daad.scr"

./TOOLS/DRC/daadmaker $TAPFILE DS128K.BIN "$GAME.DDB" $POSTER \
                      "ASSETS/CHARSET/$FONT6" \
                      INDEX.BIN DAAD.SDG

clean

cecho 6 "Game created: $(pwd)/$TAPFILE"

if [ "$RUN_GAME" = true ] && [ -n "$SPECTRUM_EMULATOR" ]; then
    cecho e "Game is ready, press any key to test or Ctrl+C to cancel"
    CMD=()
    for arg in "${SPECTRUM_EMULATOR[@]}"; do
      CMD+=( "${arg//\{tapfile\}/$TAPFILE}" )
    done
    cecho 4 "The following command will be run:"
    cecho 5 "${CMD[*]}"
    read -r
    "${CMD[@]}"
fi
