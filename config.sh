# --------------------------------------------------
# Mini DAAD Linux configuration file
#
# Lines starting with '#' are comments and are ignored.
# Some configuration options are provided but commented out.
# To enable one of those options, remove the '#' at the beginning
# of the line.
# --------------------------------------------------

# --------------------------------------------------
# Name of the game
# Must match the name of the .dsf source file (without the extension)
# --------------------------------------------------
GAME="TEST"

# --------------------------------------------------
# Split screen mode (Amstrad CPC and Commodore 64 only)
# splitModeOff : normal graphic mode
# splitModeOn  : enables split screen so the graphic area can use a mode
#                with more colours
# --------------------------------------------------
SPLITSCR="splitModeOff"

# --------------------------------------------------
# Height of the graphic area (in pixels)
# Defines how many lines of the image are shown on screen
# --------------------------------------------------
IMGLINES=96

# --------------------------------------------------
# Enable SVGA graphics for the MS-DOS version
# 0 = disabled (standard VGA)
# 1 = enabled (SVGA images will be used)
# --------------------------------------------------
SVGA=0

# --------------------------------------------------
# Automatically run the game after compilation
# true  = launch the configured emulator
# false = only build the release files
# --------------------------------------------------
RUN_GAME=true

# --------------------------------------------------
# Fonts used by the different targets
# --------------------------------------------------
FONT6="AD8x6.CHR"
FONT8="AD8x8.CHR"
FONTB="C64bold.CHR"
FONTPCDAAD="MSDOS.FNT"

# --------------------------------------------------
# A comma-separated list of images to preload into
# memory for faster display.
# Example: BUFFERED_IMAGES="008,014,012,020"
# --------------------------------------------------
BUFFERED_IMAGES=""

# --------------------------------------------------
# Emulators
#
# The emulator variables define the command used to run the game
# after compilation.
#
# The placeholder {tapfile} will be replaced by the generated
# game file (.tap, .dsk, .d64, etc).
#
# The placeholder {imgdir} will be replaced by the directory
# containing the images (used by the Spectrum Next build).
# --------------------------------------------------

# Path to the ZEsarUX executable (optional)
#ZESARUX_BIN=$HOME/ZEsarUX/zesarux

# Common ZEsarUX options used by several targets
ZESARUX_COMMON=(
    --noconfigfile
    --load-additional-config
    --quickexit
    --realvideo
    --nosplash
    --forcevisiblehotkeys
    --forceconfirmyes
    --nowelcomemessage
    --cpuspeed 100
)

# ZX Spectrum emulator command
# Default configuration uses Fuse
#SPECTRUM_EMULATOR=(fuse --machine plus2 --tape {tapfile})

# If ZEsarUX is available, it can also be used for several platforms
if [[ -n "${ZESARUX_BIN:-}" ]]; then
    if [[ -z "${SPECTRUM_EMULATOR:-}" ]]; then
        SPECTRUM_EMULATOR=(
            "$ZESARUX_BIN"
            "${ZESARUX_COMMON[@]}"
            --zoom 2
            --machine P2
            {tapfile}
        )
    fi

    # Amstrad CPC emulator command
    CPC_EMULATOR=(
        "$ZESARUX_BIN"
        "${ZESARUX_COMMON[@]}"
        --zoom 1
        --machine CPC6128
        {tapfile}
    )

    # ZX Spectrum Next emulator command
    # {imgdir} will be replaced with the directory containing the images
    NEXT_EMULATOR=(
        "$ZESARUX_BIN"
        "${ZESARUX_COMMON[@]}"
        --fastautoload
        --zoom 1
        --machine tbblue
        --tbblue-fast-boot-mode
        --enable-esxdos-handler
        --esxdos-root-dir {imgdir}
        {tapfile}
    )
fi

# Commodore 64 emulator command (VICE)
#C64_EMULATOR=(x64sc +drive8truedrive -virtualdev8 +confirmonexit -autostart {tapfile})

# MS-DOS emulator command (DOSBox)
#MSDOS_EMULATOR=dosbox

# --------------------------------------------------
# Language settings
# --------------------------------------------------
