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

if [ "$GAMELANG" == "ES" ]; then
    INTERPRETER=sdi
    cp ASSETS/C64/dc64isf.prg $INTERPRETER
else
    INTERPRETER=edi
    cp ASSETS/C64/dc64ief.prg $INTERPRETER
fi

mkdir -p RELEASE/C64
DSKFILE="RELEASE/C64/$GAME.d64"
cp "ASSETS/C64/C64_$BASELANG.D64" "$DSKFILE"

cecho 6 "Compiling game..."

./TOOLS/DRC/drf c64 "$GAME.dsf" "$SPLITSCR"
php ./TOOLS/DRC/drb.php c64 $GAMELANG "$GAME.json" daad.ddb -ch -s

cecho 6 "Preparing images (if any)..."

prepare_images "c64"

cecho 6 "Preparing release files..."

# ---- PREPARE THE FONT -----
cp ASSETS/C64/apart1.prg .
dd if=apart1.prg of=apart1.head bs=1 count=16 status=none
dd if=apart1.prg of=apart1.tail bs=1 skip=2064 count=36 status=none
cat apart1.head ASSETS/CHARSET/"$FONTB" apart1.tail > apart1.tmp
rm apart1.head apart1.tail apart1.prg

c1541 -attach "$DSKFILE" -write apart1.tmp apart1
c1541 -attach "$DSKFILE" -write daad.ddb bpart1
c1541 -attach "$DSKFILE" -write $INTERPRETER

for f in *.XMB; do
    name="${f%.XMB}"
    c1541 -attach "$DSKFILE" -write "$f" "$name"
done

for f in IMAGES/*64; do
    c1541 -attach "$DSKFILE" -write "$f"
done

clean

cecho 6 "Game created: $(pwd)/$DSKFILE"

if [ "$RUN_GAME" = true ] && [ -n "$C64_EMULATOR" ]; then
    cecho 6 "Game is ready, press any key to test or Ctrl+C to cancel"
    CMD=()
    for arg in "${C64_EMULATOR[@]}"; do
        CMD+=( "${arg//\{tapfile\}/$DSKFILE}" )
    done
    cecho 4 "The following command will be run:"
    cecho 5 "${CMD[*]}"
    read -r
    "${CMD[@]}"
fi
