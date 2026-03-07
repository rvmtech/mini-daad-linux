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

set_interpreter "cpc"

cecho 6 "Compiling game..."

DAADBIN="${GAME%%-*}"
DAADBIN="${DAADBIN:0:8}.BIN"

./TOOLS/DRC/drf cpc "$GAME.dsf" "$SPLITSCR"
php ./TOOLS/DRC/drb.php cpc $GAMELANG "$GAME.json" DAAD.DDB -s
./TOOLS/DRC/mcrf $DAADBIN DCPC.BIN DAAD.DDB ASSETS/CPC/BLANK.GRA "ASSETS/CHARSET/$FONT8"

cecho 6 "Preparing images (if any)..."

prepare_images "cpc"

cecho 6 "Preparing release files..."

mkdir -p RELEASE/CPC
DSKFILE="RELEASE/CPC/$GAME.dsk"
#cp ASSETS/CPC/BLANK.DSK $DSKFILE
./TOOLS/cpcxfs/cpcxfs -f -nData "$DSKFILE"

./TOOLS/cpcxfs/cpcxfs "$DSKFILE" -f -p $DAADBIN

for f in IMAGES/CPC/*.cpc; do
    ./TOOLS/cpcxfs/cpcxfs "$DSKFILE" -p "$f"
done

for f in *.XMB; do
    ./TOOLS/cpcxfs/cpcxfs "$DSKFILE" -p "$f"
done

clean

cecho 6 "Game created: $(pwd)/$DSKFILE"

if [ "$RUN_GAME" = true ] && [ -n "$CPC_EMULATOR" ]; then
    cecho 6 "Game is ready, press any key to test or Ctrl+C to cancel"
    cecho 6 "Type RUN \"${DAADBIN%.BIN}\" in the emulator to run the game"
    CMD=()
    for arg in "${CPC_EMULATOR[@]}"; do
      CMD+=( "${arg//\{tapfile\}/$DSKFILE}" )
    done
    cecho 4 "The following command will be run:"
    cecho 5 "${CMD[*]}"
    read -r
    "${CMD[@]}"
fi
