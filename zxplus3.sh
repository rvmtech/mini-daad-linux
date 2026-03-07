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

set_interpreter "plus3"

cecho 6 "Compiling game..."

./TOOLS/DRC/drf zx plus3 "$GAME.dsf"
php ./TOOLS/DRC/drb.php zx plus3 $GAMELANG "$GAME.json" DAAD.DDB -3h -s

cecho 6 "Preparing images (if any)..."

prepare_images "spectrum"
if [ -f "IMAGES/SCRMAKER.LOG" ]; then
(
    cd IMAGES
    php ../TOOLS/plus3cache/plus3cache.php SCRMAKER.LOG
)
fi

cecho 6 "Preparing release files..."

mkdir -p RELEASE/ZXPLUS3
DSKFILE="RELEASE/ZXPLUS3/$GAME.dsk"
cp ASSETS/ZX/PLUS3/PLUS3.DSK $DSKFILE

mv DSP3.BIN DSP3.TMP
mv DAAD.SDG DAAD.TMP
./scripts/specform.sh -a 63447 DAAD.TMP DAAD.SDG
./scripts/specform.sh -a 24576 DSP3.TMP DSP3.BIN

./TOOLS/cpcxfs/cpcxfs "$DSKFILE" -f -p DAAD.SDG
./TOOLS/cpcxfs/cpcxfs "$DSKFILE" -p DSP3.BIN
./TOOLS/cpcxfs/cpcxfs "$DSKFILE" -p DAAD.DDB

for f in IMAGES/*.128; do
    ./TOOLS/cpcxfs/cpcxfs "$DSKFILE" -p "$f"
done

for f in *.XMB; do
    ./TOOLS/cpcxfs/cpcxfs "$DSKFILE" -p "$f"
done

if [ -f IMAGES/DAAD.GRA ]; then
    ./TOOLS/cpcxfs/cpcxfs "$DSKFILE" -p IMAGES/DAAD.GRA
fi

POSTER="IMAGES/daad.scr"
if [ -f "$POSTER" ]; then
    ./scripts/specform.sh -a 16384 $POSTER DAAD.SCR
    ./TOOLS/cpcxfs/cpcxfs "$DSKFILE" -f -p DAAD.SCR
fi

clean

cecho 6 "Game created: $(pwd)/$DSKFILE"

if [ "$RUN_GAME" = true ] && [ -n "$SPECTRUM_EMULATOR" ]; then
    cecho 6 "Game is ready, press any key to test or Ctrl+C to cancel"
    CMD=()
    for arg in "${SPECTRUM_EMULATOR[@]}"; do
      CMD+=( "${arg//\{tapfile\}/$DSKFILE}" )
    done
    cecho 4 "The following command will be run:"
    cecho 5 "${CMD[*]}"
    read -r
    "${CMD[@]}"
fi
