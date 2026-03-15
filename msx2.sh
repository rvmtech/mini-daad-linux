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

mkdir -p RELEASE/MSX2
DSKFILE="RELEASE/MSX2/$GAME.dsk"
cp ASSETS/MSX/MSX2/MSX2.DSK "$DSKFILE"

set_interpreter "msx2"

cecho 6 "Compiling game..."

./TOOLS/DRC/drf msx2 8_6 "$GAME.dsf"
php ./TOOLS/DRC/drb.php msx2 8_6  $GAMELANG "$GAME.json" daad.ddb -s

cecho 6 "Preparing images (if any)..."

prepare_images "msx2"

cecho 6 "Preparing release files..."

# ---- PREPARE THE FONT -----

# Generate PNGs
php ./TOOLS/imgwizard/chr2png.php "ASSETS/CHARSET/$FONT6"

# convert to sc8
./extras/png2msx.py --format sc8 font0.png font0.sc8
./extras/png2msx.py --format sc8 font1.png font1.sc8

# convert to im8
./scripts/imgwizard.py c font0.sc8 32 RLE
./scripts/imgwizard.py d font0.im8 1
./scripts/imgwizard.py c font1.sc8 40 RLE
./scripts/imgwizard.py d font1.im8 1
./scripts/imgwizard.py j font.im8 font0.im8 ASSETS/MSX/MSX2/GLUE.IM8 font1.im8

# Clean
rm font*.png
rm font*.sc8
rm font*.im8

./TOOLS/dsktool/dsktool a "$DSKFILE" daad.ddb
./TOOLS/dsktool/dsktool a "$DSKFILE" msx2daad.com
./TOOLS/dsktool/dsktool a "$DSKFILE" FONT.IM8

if [ -f "0.XMB" ]; then
    mv "0.XMB" "TEXTS.XDB"
    ./TOOLS/dsktool/dsktool a "$DSKFILE" "TEXTS.XDB"
    rm "TEXTS.XDB"
fi

for f in IMAGES/*.im8; do
    ./TOOLS/dsktool/dsktool a "$DSKFILE" "$f"
done

clean
rm msx2daad.com

cecho 6 "Game created: $(pwd)/$DSKFILE"
cecho 2 "IMPORTANT: The MSX2 interpreter is tied to license obligations if you sell the game,"
cecho 2 "check them at: https://github.com/nataliapc/msx2daad/blob/master/LICENSE"

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
