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

mkdir -p RELEASE/MSX1
DSKFILE="RELEASE/MSX1/$GAME.dsk"
cp ASSETS/MSX/MSX1/MSX1.DSK "$DSKFILE"

set_interpreter "msx1"

cecho 6 "Compiling game..."

./TOOLS/DRC/drf msx "$GAME.dsf"
php ./TOOLS/DRC/drb.php msx $GAMELANG "$GAME.json" daad.ddb -s

cecho 6 "Preparing images (if any)..."

prepare_images "msx1"

cecho 6 "Preparing release files..."

# ---- PREPARE THE FONT -----
cp ASSETS/MSX/MSX1/DAAD.MDG daad.mdg
dd count=218 bs=1 if=daad.mdg of=mdg.head
dd skip=2266 count=34 bs=1 if=daad.mdg of=mdg.tail
cat mdg.head "ASSETS/CHARSET/$FONT6" mdg.tail > daad.tmp
rm mdg.head mdg.tail daad.mdg
mv daad.tmp daad.mdg

./TOOLS/dsktool/dsktool a "$DSKFILE" daad.ddb
./TOOLS/dsktool/dsktool a "$DSKFILE" daad.mdg
./TOOLS/dsktool/dsktool a "$DSKFILE" DAAD.Z80
./TOOLS/dsktool/dsktool a "$DSKFILE" ASSETS/MSX/MSX1/msxdaad.com
rm DAAD.Z80

for f in *.XMB; do
    name="${f%.XMB}"
    ./TOOLS/dsktool/dsktool a "$DSKFILE" "$f"
done

for f in IMAGES/*.ms2; do
    ./TOOLS/dsktool/dsktool a "$DSKFILE" "$f"
done

clean

cecho 6 "Game created: $(pwd)/$DSKFILE"

if [ "$RUN_GAME" = true ] && [ -n "$MSX_EMULATOR" ]; then
    cecho 6 "Game is ready, press any key to test or Ctrl+C to cancel"
    CMD=()
    for arg in "${MSX_EMULATOR[@]}"; do
        CMD+=( "${arg//\{tapfile\}/$DSKFILE}" )
    done
    cecho 4 "The following command will be run:"
    cecho 5 "${CMD[*]}"
    read -r
    "${CMD[@]}"
fi
