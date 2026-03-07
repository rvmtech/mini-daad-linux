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

set_interpreter "zx48k"

cecho 6 "Compiling game..."

./TOOLS/DRC/drf zx 48k "$GAME.dsf" -force-normal-messages tape48
php ./TOOLS/DRC/drb.php zx 48k $GAMELANG "$GAME.json" "$GAME.DDB" -s

cecho 6 "Preparing release files..."

mkdir -p RELEASE/ZX48K
TAPFILE="RELEASE/ZX48K/$GAME.tap"

POSTER=""
[ -f "IMAGES/daad.scr" ] && POSTER="IMAGES/daad.scr"

./TOOLS/DRC/daadmaker $TAPFILE DS48K.BIN "$GAME.DDB" $POSTER "ASSETS/CHARSET/$FONT6"

clean

cecho 6 "Game created: $(pwd)/$TAPFILE"

if [ "$RUN_GAME" = true ] && [ -n "$SPECTRUM_EMULATOR" ]; then
    cecho 6 "Game is ready, press any key to test or Ctrl+C to cancel"
    CMD=()
    for arg in "${SPECTRUM_EMULATOR[@]}"; do
      CMD+=( "${arg//\{tapfile\}/$TAPFILE}" )
    done
    cecho 4 "The following command will be run:"
    cecho 5 "${CMD[*]}"
    read -r
    "${CMD[@]}"
fi
