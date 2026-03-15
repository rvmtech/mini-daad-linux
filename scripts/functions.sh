#
# Copyright (C) 2026 Ricardo Villalba <rvm3000@gmail.com>
# License: GPL v2 or later
#

shopt -s nullglob

APPVERSION=0.5.1

intro() {
    cecho 6 "==============================="
    cecho 6 "Mini Daad Linux v. $APPVERSION"
    cecho 6 "==============================="
}

init() {
    intro
    cecho 6 "Initializing..."

    if [ -z "${GAMELANG+x}" ]; then
        printf -- "--- Please select (E)nglish, (S)panish, (G)erman, (F)rench or (P)ortuguese: "
        read -r choice

        case "$(printf "%s" "$choice" | tr '[:lower:]' '[:upper:]')" in
            E)
                GAMELANG="EN"
                BASELANG="EN"
                ;;
            S)
                GAMELANG="ES"
                BASELANG="ES"
                ;;
            G)
                GAMELANG="DE"
                BASELANG="EN"
                ;;
            P)
                GAMELANG="PT"
                BASELANG="ES"
                ;;
            F)
                GAMELANG="FR"
                BASELANG="EN"
                ;;
            *)
                echo "Invalid selection. Defaulting to English."
                GAMELANG="EN"
                BASELANG="EN"
                ;;
        esac

        # Guardar configuración
        {
            echo "GAMELANG=\"$GAMELANG\""
            echo "BASELANG=\"$BASELANG\""
        } >> config.sh
    fi

    echo "Language: $GAMELANG $BASELANG"

    # Crear fichero DSF si no existe
    if [ ! -f "$GAME.dsf" ]; then
        cp "ASSETS/TEMPLATES/BLANK_${GAMELANG}.DSF" "$GAME.dsf"
    fi

    mkdir -p IMAGES/PC
    mkdir -p IMAGES/CPC
    mkdir -p IMAGES/HTML
    mkdir -p SOUNDS
}

cecho() {
    local code="$1"
    local message="$2"
    local colors=(30 34 31 35 32 36 93 37)
    local ansi="${colors[$code]:-37}"  # blanco por defecto
    printf "\033[%sm%s\033[0m\n" "$ansi" "$message"
}

clean() {
    rm -f *.json
    rm -f *.DDB
    rm -f *.ddb
    rm -f *.TMP
    rm -f *.tmp
    rm -f *.BIN
    rm -f *.SDG
    rm -f *.XMB
    rm -f *.PT
    rm -f DAAD.SCR
    rm -f sdi
    rm -f edi
    rm -f *.mdg
}

create_zx_sdg() {
    cp ASSETS/ZX/DAAD.SDG .
    dd if=DAAD.SDG of=SDG.HEAD bs=1 count=13 2>/dev/null
    dd if=DAAD.SDG of=SDG.TAIL bs=1 skip=2061 count=28 2>/dev/null
    cat SDG.HEAD "ASSETS/CHARSET/$FONT6" SDG.TAIL > DAAD.SDG
    rm SDG.HEAD SDG.TAIL
}

set_interpreter() {
    local mode="$1"

    if [ "$mode" = "zx128k" ]; then
        if [ "$BASELANG" == "ES" ]; then
            cp ASSETS/ZX/128K/DS128KS.BIN DS128K.BIN
        else
            cp ASSETS/ZX/128K/DS128KE.BIN DS128K.BIN
        fi
        create_zx_sdg
    fi

    if [ "$mode" = "zx48k" ]; then
        if [ "$BASELANG" == "ES" ]; then
            cp ASSETS/ZX/ZXSPECTRUM/DS48IS.BIN DS48K.BIN
        else
            cp ASSETS/ZX/ZXSPECTRUM/DS48IE.BIN DS48K.BIN
        fi
        create_zx_sdg
    fi

    if [ "$mode" = "plus3" ]; then
        if [ "$BASELANG" == "ES" ]; then
            cp ASSETS/ZX/PLUS3/DSP3S.BIN DSP3.BIN
        else
            cp ASSETS/ZX/PLUS3/DSP3E.BIN DSP3.BIN
        fi
        create_zx_sdg
    fi

    if [ "$mode" = "next" ]; then
        if [ "$BASELANG" == "ES" ]; then
            cp ASSETS/ZX/ZXNEXT/DSNEXTS.BIN DSNEXT.BIN
        else
            cp ASSETS/ZX/ZXNEXT/DSNEXTE.BIN DSNEXT.BIN
        fi
    fi

    if [ "$mode" = "cpc" ]; then
        if [ "$BASELANG" == "ES" ]; then
            cp ASSETS/CPC/DCPCISF.BIN DCPC.BIN
        else
            cp ASSETS/CPC/DCPCIEF.BIN DCPC.BIN
        fi
    fi

    if [ "$mode" = "msx1" ]; then
        if [ "$BASELANG" == "ES" ]; then
            cp ASSETS/MSX/MSX1/DMSXISF.BIN DAAD.Z80
        else
            cp ASSETS/MSX/MSX1/DMSXIEF.BIN DAAD.Z80
        fi
    fi

    if [ "$mode" = "msx2" ]; then
        cp ASSETS/MSX/MSX2/msx2daad_1.5.1_${BASELANG}_SC8.com msx2daad.com
    fi
}

image_output() {
    local base="$1"
    local ext="$2"
    local output="${base}${ext}"
    IFS=',' read -r -a BUFFERED_ARRAY <<< "$BUFFERED_IMAGES"
    for b in "${BUFFERED_ARRAY[@]}"; do
        [[ "$b" == "$base" ]] && echo "L:${output}" && return
    done
    echo "$output"
}

prepare_images() {
    local mode="$1"
    mkdir -p IMAGES
    rm -f IMAGES/SCRMAKER.LOG

    if [ "$mode" = "spectrum" ]; then
    (
        cd IMAGES
        for i in *.scr; do
            if [[ "$i" != "daad.scr" ]]; then
                base=$(basename "$i" .scr)
                output=$(image_output "$base" ".128")
                if [ ! -f "$base.zx0" ]; then
                    ../TOOLS/DRC/scrcrop "$base.scr" "$base.sct" "256" "$IMGLINES"
                    ../TOOLS/ZX0/zx0 -f "$base.sct" "$base.zx0"
                    rm "$base.sct"
                fi
                ../TOOLS/SCRMAKER/scrmaker spectrum128 "$base.zx0" "$output" "256" "$IMGLINES" "0,0"
            fi
        done
    )
    fi

    if [ "$mode" = "next" ]; then
        for i in IMAGES/*.pcx; do
            base=$(basename "$i" .pcx)
            ./TOOLS/SCRMAKER/scrmaker specnext "$i" "RELEASE/ZXNEXT/$base.ly2" 256 "$IMGLINES" "0,0" /s
        done
    fi

    if [ "$mode" = "cpc" ]; then
    (
        cd IMAGES/CPC
        for i in *.scr; do
            base=$(basename "$i" .scr)
            ../../TOOLS/MALUVA/sc2daad cpc "$i" "$base.cpc" "$IMGLINES"
        done
    )
    fi

    if [ "$mode" = "msx1" ]; then
    (
        cd IMAGES
        for i in *.sc2; do
            base=$(basename "$i" .sc2)
            ../TOOLS/MALUVA/sc2daad msx "$i" "$base.ms2" "$IMGLINES"
        done
    )
    fi

    if [ "$mode" = "msx2" ]; then
    (
        cd IMAGES
        for i in *.sc8; do
            if [ "$i" = "daad.sc8" ]; then
                ../scripts/imgwizard.py c "$i" 212 RLE
                mv daad.im8 loading.im8
            else
                base=$(basename "$i" .sc8)
                ../scripts/imgwizard.py c "$i" "$IMGLINES" RLE
            fi
        done
    )
    fi

    if [ "$mode" = "c64" ]; then
    (
        cd IMAGES/
        if [[ "$SPLITSCR" == "splitModeOff" ]]; then
            echo "Processing ART files"
            for i in *.art; do
                base=$(basename "$i" .art)
                ../TOOLS/MALUVA/sc2daad c64 "$i" "${base}64" "$IMGLINES"
            done
        else
            echo "Processing KOA files"
            for i in *.koa; do
                base=$(basename "$i" .koa)
                ../TOOLS/MALUVA/sc2daad c64 "$i" "${base}64" "$IMGLINES"
            done
            for i in *.kla; do
                base=$(basename "$i" .kla)
                ../TOOLS/MALUVA/sc2daad c64 "$i" "${base}64" "$IMGLINES"
            done
        fi
    )
    fi
}
