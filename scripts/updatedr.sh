#!/bin/bash
#
# Copyright (C) 2026 Ricardo Villalba <rvm3000@gmail.com>
# License: GPL v2 or later
#

if [ ! -d "ASSETS" ]; then
    exit 1
fi

if [ ! -f /tmp/daadready.zip ]; then
    wget https://github.com/Utodev/DAAD-Ready/archive/refs/heads/master.zip -O /tmp/daadready.zip
fi

bsdtar --strip-components=1 -xvf /tmp/daadready.zip --no-same-permissions \
    "DAAD-Ready-master/ASSETS/C64/*" \
    "DAAD-Ready-master/ASSETS/CHARSET/*" \
    "DAAD-Ready-master/ASSETS/CPC/*" \
    "DAAD-Ready-master/ASSETS/HTML/*" \
    "DAAD-Ready-master/ASSETS/MSDOS/*" \
    "DAAD-Ready-master/ASSETS/TEMPLATES/*" \
    "DAAD-Ready-master/ASSETS/ZX/*" \
    "DAAD-Ready-master/TOOLS/DRC/*.php" \
    "DAAD-Ready-master/TOOLS/jDAADFontMaker/*.php" \
    "DAAD-Ready-master/TOOLS/jDAADImager/*.php" \
    "DAAD-Ready-master/TOOLS/plus3cache/plus3cache.php"

find ASSETS -type f -exec chmod 644 {} \;
find TOOLS -type f -name "*.php" -exec chmod 644 {} \;
