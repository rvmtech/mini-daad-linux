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

if [[ "$SVGA" == "0" ]]; then
    IMGPATH="IMAGES/PC"
    IMGPATHBACK="../.."
    IMGWIDTH=320
    IMGHEIGHT=96
    INTROSIZE="320 200"
    echo "Creating VGA GAME"
else
    IMGPATH="IMAGES/PC/SVGA"
    IMGPATHBACK="../../.."
    IMGWIDTH=640
    IMGHEIGHT=192
    PARAMETER="-s"
    INTROSIZE="640 400"
    echo "Creating SVGA GAME"
fi

mkdir -p RELEASE/MSDOS/GAME

rm -f RELEASE/MSDOS/GAME/*.msd
rm -f RELEASE/MSDOS/GAME/*.fli
rm -f RELEASE/MSDOS/GAME/*.XMB
rm -f RELEASE/MSDOS/GAME/*.DDB
rm -f RELEASE/MSDOS/*.sh

cp -r ASSETS/MSDOS/* RELEASE/MSDOS/

if [ -f "ASSETS/CHARSET/$FONTPCDAAD" ]; then
    cp -f "ASSETS/CHARSET/$FONTPCDAAD" "RELEASE/MSDOS/GAME/DAAD.FNT"
else
    cp -f "ASSETS/CHARSET/$FONT6" "RELEASE/MSDOS/GAME/DAAD.CHR"
fi

cat >> "RELEASE/MSDOS/dosbox.conf" <<EOF
PCDAAD $PARAMETER
exit
EOF

echo "@PCDAAD $PARAMETER" > RELEASE/MSDOS/GAME/$GAME.BAT

cat >> "RELEASE/MSDOS/${GAME}_linux.sh" <<EOF
#!/usr/bin/env bash
$MSDOS_EMULATOR -noconsole
EOF

chmod +x "RELEASE/MSDOS/${GAME}_linux.sh"

echo "@dosbox.exe -noconsole" > "RELEASE/MSDOS/${GAME}_windows.bat"

cecho 6 "Compiling game..."

./TOOLS/DRC/drf pc vga256 "$GAME.dsf"
php ./TOOLS/DRC/drb.php pc vga256 $GAMELANG "$GAME.json" DAAD.DDB -s
mv DAAD.DDB RELEASE/MSDOS/GAME/DAAD.DDB

cecho 6 "Preparing images, videos and sounds (if any)..."

for f in $IMGPATH/*.pcx; do
    out="${f##*/}"
    out="RELEASE/MSDOS/GAME/${out%.pcx}.msd"
    if [[ "$(basename "$f")" == "daad.pcx" ]]; then
        ./TOOLS/SCRMAKER/scrmaker msdos "$f" "$out" $INTROSIZE 0,0 0-255
    else
        ./TOOLS/SCRMAKER/scrmaker msdos "$f" "$out" $IMGWIDTH $IMGHEIGHT 0,0 0-255 /s
    fi
done

for f in $IMGPATH/*.fli; do
    cp "$f" RELEASE/MSDOS/GAME/
done

for f in SOUNDS/*.wav; do
    out="${f##*/}"
    out="RELEASE/MSDOS/GAME/${out%.wav}.sfx"
    ./TOOLS/WAV2SFX/wav2sfx "$f" "$out"
done

cecho 6 "Preparing release files..."

if compgen -G "*.XMB"; then
    mv *.XMB RELEASE/MSDOS/GAME/
fi

clean

cecho 6 "Game created: $(pwd)/RELEASE/MSDOS/GAME/"

if [ "$RUN_GAME" = true ] && [ -n "$MSDOS_EMULATOR" ]; then
    cecho 6 "Game is ready, press any key to test or Ctrl+C to cancel"
    cecho 4 "The following emulator will be run:"
    cecho 5 "$MSDOS_EMULATOR"
    read -r
    (
    cd RELEASE/MSDOS/
    ./${GAME}_linux.sh
    )
fi
