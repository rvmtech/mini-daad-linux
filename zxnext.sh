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
mkdir -p RELEASE/ZXNEXT

set_interpreter "next"

cecho 6 "Compiling game..."

./TOOLS/DRC/drf zx next "$GAME.dsf"
php ./TOOLS/DRC/drb.php zx next $GAMELANG "$GAME.json" "$GAME.DDB" -s

cecho 6 "Preparing images (if any)..."

prepare_images "next"

cecho 6 "Preparing release files..."

TAPFILE="RELEASE/ZXNEXT/$GAME.tap"

./TOOLS/DRC/daadmaker $TAPFILE DSNEXT.BIN "$GAME.DDB" "ASSETS/CHARSET/$FONT6"

if compgen -G "*.XMB"; then
    mv *.XMB RELEASE/ZXNEXT/
fi

clean

cecho 6 "Game created: $(pwd)/$TAPFILE"

if [ "$RUN_GAME" = true ] && [ -n "$NEXT_EMULATOR" ]; then
    cecho 6 "Game is ready, press any key to test or Ctrl+C to cancel"
    CMD=()
    for arg in "${NEXT_EMULATOR[@]}"; do
        arg="${arg//\{tapfile\}/$TAPFILE}"
        arg="${arg//\{imgdir\}/RELEASE/ZXNEXT}"
        CMD+=("$arg")
    done
    cecho 4 "The following command will be run:"
    cecho 5 "${CMD[*]}"
    read -r
    "${CMD[@]}"
fi
