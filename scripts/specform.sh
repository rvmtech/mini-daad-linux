#!/bin/bash
#
# Copyright (C) 2026 Ricardo Villalba <rvm3000@gmail.com>
# License: GPL v2 or later
#

set -e

usage() {
    echo "Uso: $0 -a <direccion_carga> <entrada.bin> <salida.bin>"
    exit 1
}

# Validar argumentos
[ "$1" = "-a" ] || usage
LOADADDR="$2"
INFILE="$3"
OUTFILE="$4"

[ -f "$INFILE" ] || { echo "Error: no existe $INFILE"; exit 1; }

# Valores +3DOS
ISSUE=1
VERSION=0

# Tamaño del fichero original
ORIG_SIZE=$(stat -c %s "$INFILE")
# Tamaño total incluyendo cabecera
TOTAL_SIZE=$((ORIG_SIZE + 128))

TMP=$(mktemp)

# -------- Construir header 0..126 --------
{
    # 0–7: firma
    printf 'PLUS3DOS'

    # 8: soft EOF
    printf '\x1A'

    # 9–10: issue/version
    printf '\x01\x00'

    # 11–14: tamaño total del archivo con header (uint32 LE)
    for s in 0 8 16 24; do
        printf '%b' "$(printf '\\x%02X' $(( (TOTAL_SIZE >> s) & 0xFF )))"
    done

    # 15: tipo BASIC = CODE
    printf '\x03'

    # 16–17: longitud del bloque BASIC (uint16 LE)
    printf '%b' "$(printf '\\x%02X\\x%02X' $(( ORIG_SIZE & 0xFF )) $(( (ORIG_SIZE >> 8) & 0xFF )))"

    # 18–19: dirección de carga (uint16 LE)
    printf '%b' "$(printf '\\x%02X\\x%02X' $(( LOADADDR & 0xFF )) $(( (LOADADDR >> 8) & 0xFF )))"

    # 20–22: reservado
    printf '\x00\x00\x00'

    # 23–126: reservado (104 bytes = 0)
    printf '\x00%.0s' {1..104}

} > "$TMP"

# -------- Calcular checksum (0–126) --------
CHECKSUM=$(od -An -t u1 "$TMP" | awk '{for(i=1;i<=NF;i++) s+=$i} END{print s % 256}')
printf '%b' "$(printf '\\x%02X' "$CHECKSUM")" >> "$TMP"

# -------- Concatenar binario original --------
cat "$TMP" "$INFILE" > "$OUTFILE"
rm "$TMP"

echo "✔ +3DOS correcto creado: $OUTFILE"
echo "  - Dirección de carga: $LOADADDR"
echo "  - Tamaño bloque: $ORIG_SIZE bytes"
echo "  - Tamaño total con header: $TOTAL_SIZE bytes"
