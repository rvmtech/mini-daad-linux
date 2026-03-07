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

mkdir -p RELEASE/HTML
cp ASSETS/HTML/* RELEASE/HTML

cecho 6 "Compiling game..."

./TOOLS/DRC/drf html "$GAME.dsf"
php ./TOOLS/DRC/drb.php html $GAMELANG "$GAME.json" game.ddb -s
mv game.jddb RELEASE/HTML/daad.jddb
php ./TOOLS/jDAADFontMaker/jDAADFontMaker.php ASSETS/CHARSET/$FONT6 RELEASE/HTML/font.js

cecho 6 "Preparing images and sounds (if any)..."

for f in SOUNDS/*.mp3; do
    cp "$f" RELEASE/HTML/
done

for f in IMAGES/HTML/*.mp4; do
    cp "$f" RELEASE/HTML/
done

IMGWIDTH=320
for f in IMAGES/HTML/*.png; do
    php ./TOOLS/jDAADImager/jDAADImager.php "$f" RELEASE/HTML/images.js "$IMGWIDTH" "$IMGLINES" 0,0
done

php ./TOOLS/jDAADImager/jDAADMultimedia.php RELEASE/HTML/  0,0

cecho 6 "Preparing release files..."

if compgen -G "*.XMB"; then
    mv *.XMB RELEASE/HTML/
fi

clean

cecho 6 "Game created: $(pwd)/RELEASE/HTML/index.html"

if [ "$RUN_GAME" = true ]; then
    cecho 6 "Game is ready, press any key to test or Ctrl+C to cancel"
    read -r
    xdg-open RELEASE/HTML/index.html
fi
