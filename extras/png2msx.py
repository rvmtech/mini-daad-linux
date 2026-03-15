#!/usr/bin/env python3
"""
png2msx.py - Convertidor de imágenes PNG/JPG al formato SC2 de MSX1 (SCREEN 2)

Especificaciones del TMS9918A en modo Graphic II (SCREEN 2):
  - Resolución: 256x192 píxeles
  - Organización: 32x24 tiles de 8x8 píxeles
  - SCREEN 2 divide la pantalla en 3 tercios de 8 filas de tiles (64 líneas) cada uno
  - Cada tercio tiene su propio juego de 256 patrones únicos (un patrón por tile)
  - Restricción de color: CADA FILA DE 8x1 PÍXELES tiene exactamente 2 colores
    (foreground = bit=1, background = bit=0), elegibles libremente de los 16 colores

Algoritmos de dithering disponibles:
  none     : Sin dithering    — cuantización directa, sin difusión de error (defecto)
  floyd    : Floyd-Steinberg  — suave, propaga error a 4 vecinos. El más habitual.
  atkinson : Atkinson         — difunde solo 3/4 del error, genera imagen más nítida
                                con zonas de negro/blanco más limpias. Estilo Mac clásico.
  bayer    : Ordered/Bayer    — matriz de umbral 8x8, sin propagación. Produce un patrón
                                de puntos regular, aspecto más "retro/gráfico".

Intensidad (--strength 0.0-1.0):
  Escala el error que se propaga. 0.0 = sin dither, 1.0 = dither completo.
  Solo afecta a floyd y atkinson. Bayer usa su propia escala implícita.

Preprocesado (aplicado tras escalar, antes de convertir):
  --saturation : factor de saturación. 1.0=sin cambio, >1 más vívido, <1 más gris.
  --contrast   : factor de contraste.  1.0=sin cambio, >1 más contraste, <1 más plano.
  --brightness : factor de brillo.     1.0=sin cambio, >1 más claro, <1 más oscuro.

Estructura del archivo .SC2 (14343 bytes):
  - Bytes   0-6       : Cabecera BIOS MSX (0xFE + 3 words little-endian)
  - Bytes   7-0x1806  : Pattern Generator Table (6144 bytes, VRAM 0x0000-0x17FF)
  - Bytes 0x1807-0x1AFF: Pattern Name Table (768 bytes, VRAM 0x1800-0x1AFF)
  - Bytes 0x1B00-0x2006: Relleno / Sprite tables (zeros)
  - Bytes 0x2007-0x37FF: Color Table (6144 bytes, VRAM 0x2000-0x37FF)

Estructura del archivo .SC8:
  - Bytes 0-6    : Cabecera BIOS MSX (0xFE + 3 words little-endian)
  - Bytes 7-...  : Bitmap 256x212, un byte por píxel (GGGRRR BB)
"""

import sys
import struct
import argparse
from pathlib import Path
from collections import Counter

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("Dependencias necesarias: pip install Pillow numpy")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
#  Matriz de Bayer 8x8 (valores 0-63, normalizada a [-0.5, 0.5])
# ─────────────────────────────────────────────────────────────────────────────
BAYER_8x8 = np.array([
    [ 0, 32,  8, 40,  2, 34, 10, 42],
    [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44,  4, 36, 14, 46,  6, 38],
    [60, 28, 52, 20, 62, 30, 54, 22],
    [ 3, 35, 11, 43,  1, 33,  9, 41],
    [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47,  7, 39, 13, 45,  5, 37],
    [63, 31, 55, 23, 61, 29, 53, 21],
], dtype=np.float32) / 63.0 - 0.5   # rango [-0.5, 0.5]


# ─────────────────────────────────────────────────────────────────────────────
#  Paleta TMS9918A — 16 colores fijos (SC2)
# ─────────────────────────────────────────────────────────────────────────────
TMS_PALETTE = [
    (  0,   0,   0),   #  0 Transparent / Black
    (  0,   0,   0),   #  1 Black
    ( 33, 200,  66),   #  2 Medium Green
    ( 94, 220, 120),   #  3 Light Green
    ( 84,  85, 237),   #  4 Dark Blue
    (125, 118, 252),   #  5 Light Blue
    (212,  82,  77),   #  6 Dark Red
    ( 66, 235, 245),   #  7 Cyan
    (252,  85,  84),   #  8 Medium Red
    (255, 121, 120),   #  9 Light Red
    (212, 193,  84),   # 10 Dark Yellow
    (230, 206, 128),   # 11 Light Yellow
    ( 33, 176,  59),   # 12 Dark Green
    (201,  91, 186),   # 13 Magenta
    (204, 204, 204),   # 14 Gray
    (255, 255, 255),   # 15 White
]

# Pesos perceptuales para distancia de color
_W = np.array([0.299, 0.587, 0.114], dtype=np.float32)
PALETTE_NP = np.array(TMS_PALETTE, dtype=np.float32)   # shape (16, 3)


def nearest_palette_index(pixel: np.ndarray) -> int:
    """Índice del color más cercano en la paleta TMS9918A."""
    diff = (PALETTE_NP - pixel) * _W
    return int(np.argmin(np.sum(diff * diff, axis=1)))


def best_two_colors(pixels_8x1: np.ndarray) -> tuple:
    """
    Elige los 2 colores de la paleta que minimizan el error cuadrático total
    para una fila de 8 píxeles (restricción 8×1 del TMS9918A).
    Devuelve (fg_index, bg_index) donde fg = color del bit=1.
    """
    indices = [nearest_palette_index(pixels_8x1[i]) for i in range(8)]
    counts = Counter(indices)

    if len(counts) == 1:
        idx = list(counts.keys())[0]
        complement = 1 if idx != 1 else 15
        return idx, complement

    if len(counts) == 2:
        top = [c for c, _ in counts.most_common(2)]
        return top[0], top[1]

    # Más de 2 candidatos: buscar la mejor pareja por fuerza bruta (top N)
    candidates = [c for c, _ in counts.most_common(min(8, len(counts)))]
    best_error = float('inf')
    best_pair = (candidates[0], candidates[1])

    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            ci, cj = candidates[i], candidates[j]
            rgb_i = PALETTE_NP[ci]
            rgb_j = PALETTE_NP[cj]
            error = 0.0
            for px in pixels_8x1:
                di = float(np.sum(((px - rgb_i) * _W) ** 2))
                dj = float(np.sum(((px - rgb_j) * _W) ** 2))
                error += min(di, dj)
            if error < best_error:
                best_error = error
                best_pair = (ci, cj)

    return best_pair


def preprocess(img_f: np.ndarray,
               saturation: float = 1.0,
               contrast: float = 1.0,
               brightness: float = 1.0) -> np.ndarray:
    """
    Aplica ajustes a una imagen float32 (H, W, 3) en rango [0, 255].
    Orden: brillo → contraste → saturación.

    brightness : multiplica todos los canales. >1 aclara, <1 oscurece.
    contrast   : escala alrededor de 128. >1 más contraste, <1 más plano.
    saturation : mezcla con escala de grises. >1 más vívido, <1 más gris.
    """
    if brightness == 1.0 and contrast == 1.0 and saturation == 1.0:
        return img_f

    out = img_f.copy()

    if brightness != 1.0:
        out = out * brightness

    if contrast != 1.0:
        out = (out - 128.0) * contrast + 128.0

    if saturation != 1.0:
        lum = (out * _W).sum(axis=2, keepdims=True)  # luminancia perceptual (H,W,1)
        out = lum + (out - lum) * saturation

    return np.clip(out, 0.0, 255.0)


def convert_image_to_sc2(
    input_path: str,
    output_path: str,
    lines: int = 192,
    dither: str = 'none',
    strength: float = 1.0,
    saturation: float = 1.0,
    contrast: float = 1.0,
    brightness: float = 1.0,
    preview_path: str = None,
) -> None:
    if lines % 8 != 0 or not (8 <= lines <= 192):
        raise ValueError(f"'lines' debe ser múltiplo de 8 y entre 8 y 192 (recibido: {lines})")
    if dither not in ('floyd', 'atkinson', 'bayer', 'none'):
        raise ValueError(f"'dither' debe ser floyd, atkinson, bayer o none (recibido: {dither})")
    strength = max(0.0, min(1.0, strength))

    # ── 1. Cargar y escalar imagen ────────────────────────────────────────────
    print(f"Cargando: {input_path}")
    img = Image.open(input_path).convert('RGB')
    original_size = img.size
    img = img.resize((256, 192), Image.LANCZOS)
    if original_size != (256, 192):
        print(f"  Redimensionada de {original_size[0]}x{original_size[1]} a 256x192")

    img_f = np.array(img, dtype=np.float32)            # (192, 256, 3)
    img_f = preprocess(img_f, saturation, contrast, brightness)
    err   = np.zeros((192, 256, 3), dtype=np.float32)

    if dither == 'bayer':
        bayer_field = np.zeros((192, 256), dtype=np.float32)
        for y in range(192):
            for x in range(256):
                bayer_field[y, x] = BAYER_8x8[y % 8, x % 8]
        bayer_field *= 64.0 * strength
        bayer_volume = np.stack([bayer_field] * 3, axis=-1)  # (192,256,3)

    # ── 2. Tablas VRAM ────────────────────────────────────────────────────────
    pattern_table = bytearray(6144)
    color_table   = bytearray(6144)

    name_table = bytearray(768)
    for tr in range(24):
        for tc in range(32):
            name_table[tr * 32 + tc] = (tr % 8) * 32 + tc

    # ── 3. Bucle de conversión ────────────────────────────────────────────────
    algo_name = {'floyd': 'Floyd-Steinberg', 'atkinson': 'Atkinson',
                 'bayer': 'Ordered/Bayer', 'none': 'Sin dithering'}[dither]
    strength_str = f"  strength={strength:.2f}" if dither in ('floyd', 'atkinson') else ""
    print(f"Convirtiendo {lines} lineas  |  algoritmo: {algo_name}{strength_str}")

    for y in range(lines):
        tr           = y // 8
        row_in_tile  = y % 8
        third        = tr // 8
        row_in_third = tr % 8

        if y % 32 == 0:
            print(f"  {y/lines*100:5.1f}%  (linea {y}/{lines})")

        for tc in range(32):
            x = tc * 8

            if dither == 'bayer':
                raw = np.clip(img_f[y, x:x+8] + bayer_volume[y, x:x+8], 0.0, 255.0)
            else:
                raw = np.clip(img_f[y, x:x+8] + err[y, x:x+8], 0.0, 255.0)

            fg_idx, bg_idx = best_two_colors(raw)
            fg_rgb = PALETTE_NP[fg_idx]
            bg_rgb = PALETTE_NP[bg_idx]

            pattern_byte = 0
            for bit in range(8):
                px = raw[bit]
                d_fg = float(np.sum(((px - fg_rgb) * _W) ** 2))
                d_bg = float(np.sum(((px - bg_rgb) * _W) ** 2))

                if d_fg <= d_bg:
                    chosen = fg_rgb
                    pattern_byte |= (1 << (7 - bit))
                else:
                    chosen = bg_rgb

                if dither in ('floyd', 'atkinson'):
                    qe = (px - chosen) * strength
                    xp = x + bit

                    if dither == 'floyd':
                        if xp + 1 < 256:
                            err[y, xp+1]       += qe * (7.0/16.0)
                        if y + 1 < 192:
                            if xp - 1 >= 0:
                                err[y+1, xp-1] += qe * (3.0/16.0)
                            err[y+1, xp]       += qe * (5.0/16.0)
                            if xp + 1 < 256:
                                err[y+1, xp+1] += qe * (1.0/16.0)
                    else:  # atkinson
                        frac = qe * (1.0/8.0)
                        if xp + 1 < 256:
                            err[y, xp+1]       += frac
                        if xp + 2 < 256:
                            err[y, xp+2]       += frac
                        if y + 1 < 192:
                            if xp - 1 >= 0:
                                err[y+1, xp-1] += frac
                            err[y+1, xp]       += frac
                            if xp + 1 < 256:
                                err[y+1, xp+1] += frac
                        if y + 2 < 192:
                            err[y+2, xp]       += frac

            patron_en_tercio = row_in_third * 32 + tc
            offset = third * 256 * 8 + patron_en_tercio * 8 + row_in_tile
            pattern_table[offset] = pattern_byte
            color_table[offset]   = ((fg_idx & 0x0F) << 4) | (bg_idx & 0x0F)

    print(f"  100.0%  (linea {lines}/{lines}) OK")

    # ── 4. Construir bloque VRAM y archivo ───────────────────────────────────
    vram = bytearray(0x3800)
    vram[0x0000:0x1800] = pattern_table
    vram[0x1800:0x1B00] = name_table + bytearray(0x1B00 - 0x1800 - len(name_table))
    vram[0x2000:0x3800] = color_table

    header = struct.pack('<BHHH', 0xFE, 0x0000, 0x37FF, 0x0000)
    output_data = header + bytes(vram)
    assert len(output_data) == 14343

    Path(output_path).write_bytes(output_data)
    print(f"\nArchivo SC2 guardado: {output_path}  ({len(output_data)} bytes)")
    print('  Carga en MSX con:  BLOAD"fichero.SC2",S')

    if preview_path:
        _save_preview_sc2(bytes(vram), preview_path, lines)


def _save_preview_sc2(vram: bytes, preview_path: str, lines: int) -> None:
    """Decodifica la VRAM SC2 y guarda un PNG de preview."""
    pgt = vram[0x0000:0x1800]
    ct  = vram[0x2000:0x3800]
    img = Image.new('RGB', (256, lines))
    px  = img.load()
    for y in range(lines):
        tr = y // 8; row_in_tile = y % 8
        third = tr // 8; row_in_third = tr % 8
        for tc in range(32):
            x = tc * 8
            off = third * 256 * 8 + (row_in_third * 32 + tc) * 8 + row_in_tile
            pb = pgt[off]; cb = ct[off]
            fg = (cb >> 4) & 0xF; bg = cb & 0xF
            fg_rgb = tuple(int(v) for v in PALETTE_NP[fg])
            bg_rgb = tuple(int(v) for v in PALETTE_NP[bg])
            for b in range(8):
                px[x + b, y] = fg_rgb if pb & (1 << (7 - b)) else bg_rgb
    img.save(preview_path)
    print(f"  Preview guardado: {preview_path}")


# ─────────────────────────────────────────────────────────────────────────────
#  Conversión SC8 (MSX2, SCREEN 8, Graphic 7)
#  Formato píxel: GGGRRR BB — 256 colores, 256x212, sin restricciones de color
# ─────────────────────────────────────────────────────────────────────────────
_SC8_BLUE_DAC = [0, 73, 146, 255]
_SC8_RGB_DAC  = [0, 36, 73, 109, 146, 182, 219, 255]

SC8_PALETTE = np.zeros((256, 3), dtype=np.float32)
for code in range(256):
    g3 = (code >> 5) & 0x07
    r3 = (code >> 2) & 0x07
    b2 = (code     ) & 0x03
    SC8_PALETTE[code] = [_SC8_RGB_DAC[r3], _SC8_RGB_DAC[g3], _SC8_BLUE_DAC[b2]]


def rgb_to_sc8_byte(r: int, g: int, b: int) -> int:
    """Convierte un color RGB (0-255) al byte SC8 más cercano."""
    r3 = round(r * 7 / 255)
    g3 = round(g * 7 / 255)
    b_dists = [abs(b - bv) for bv in _SC8_BLUE_DAC]
    b2 = b_dists.index(min(b_dists))
    return ((g3 & 0x07) << 5) | ((r3 & 0x07) << 2) | (b2 & 0x03)


def convert_image_to_sc8(
    input_path: str,
    output_path: str,
    dither: str = 'none',
    strength: float = 1.0,
    saturation: float = 1.0,
    contrast: float = 1.0,
    brightness: float = 1.0,
    preview_path: str = None,
) -> None:
    HEIGHT = 212
    if dither not in ('floyd', 'atkinson', 'bayer', 'none'):
        raise ValueError(f"'dither' inválido: {dither}")
    strength = max(0.0, min(1.0, strength))

    # ── 1. Cargar y escalar ───────────────────────────────────────────────────
    print(f"Cargando: {input_path}")
    img = Image.open(input_path).convert('RGB')
    original_size = img.size
    img = img.resize((256, HEIGHT), Image.LANCZOS)
    if original_size != (256, HEIGHT):
        print(f"  Redimensionada de {original_size[0]}x{original_size[1]} a 256x{HEIGHT}")

    img_f = np.array(img, dtype=np.float32)
    img_f = preprocess(img_f, saturation, contrast, brightness)
    err   = np.zeros((HEIGHT, 256, 3), dtype=np.float32)

    if dither == 'bayer':
        bayer_field = np.zeros((HEIGHT, 256), dtype=np.float32)
        for y in range(HEIGHT):
            for x in range(256):
                bayer_field[y, x] = BAYER_8x8[y % 8, x % 8]
        bayer_volume = np.stack([bayer_field * 64.0 * strength] * 3, axis=-1)

    # ── 2. Dithering y cuantización ───────────────────────────────────────────
    algo_name = {'floyd': 'Floyd-Steinberg', 'atkinson': 'Atkinson',
                 'bayer': 'Ordered/Bayer', 'none': 'Sin dithering'}[dither]
    strength_str = f"  strength={strength:.2f}" if dither in ('floyd', 'atkinson') else ""
    print(f"Convirtiendo 256x{HEIGHT}  |  algoritmo: {algo_name}{strength_str}")

    # LUT para cuantización SC8 vectorizada: (r3, g3, b2) -> byte
    _sc8_lut = np.zeros((8, 8, 4), dtype=np.uint8)
    for _r3 in range(8):
        for _g3 in range(8):
            for _b2 in range(4):
                _sc8_lut[_r3, _g3, _b2] = ((_g3 & 7) << 5) | ((_r3 & 7) << 2) | (_b2 & 3)
    _b_dac_np = np.array(_SC8_BLUE_DAC, dtype=np.float32)  # (4,)

    def quantize_pixel_sc8(px: np.ndarray) -> tuple:
        """Cuantiza un pixel (3,) a (sc8_byte, chosen_rgb). Numpy inline, sin Python puro."""
        r3 = int(min(7, round(float(px[0]) * 7.0 / 255.0)))
        g3 = int(min(7, round(float(px[1]) * 7.0 / 255.0)))
        b2 = int(np.argmin(np.abs(px[2] - _b_dac_np)))
        code = int(_sc8_lut[r3, g3, b2])
        return code, SC8_PALETTE[code]

    bitmap = bytearray(256 * HEIGHT)

    for y in range(HEIGHT):
        if y % 32 == 0:
            print(f"  {y/HEIGHT*100:5.1f}%  (linea {y}/{HEIGHT})")

        if dither in ('none', 'bayer'):
            # Sin dependencia horizontal: vectorizar toda la fila de golpe
            if dither == 'bayer':
                row = np.clip(img_f[y] + bayer_volume[y], 0.0, 255.0)  # (256, 3)
            else:
                row = np.clip(img_f[y], 0.0, 255.0)

            r3 = np.clip(np.round(row[:, 0] * (7.0/255.0)), 0, 7).astype(np.int32)
            g3 = np.clip(np.round(row[:, 1] * (7.0/255.0)), 0, 7).astype(np.int32)
            b2 = np.argmin(np.abs(row[:, 2:3] - _b_dac_np), axis=1).astype(np.int32)
            codes = _sc8_lut[r3, g3, b2]
            bitmap[y*256:(y+1)*256] = codes.tobytes()

        else:
            # Floyd / Atkinson: dependencia horizontal secuencial → bucle en x
            # pero cuantización y difusión vertical vectorizadas
            row_codes = np.zeros(256, dtype=np.uint8)
            row_qe    = np.zeros((256, 3), dtype=np.float32)

            for x in range(256):
                px = np.clip(img_f[y, x] + err[y, x], 0.0, 255.0)
                code, chosen = quantize_pixel_sc8(px)
                row_codes[x] = code
                row_qe[x]    = (px - chosen) * strength

                # Difusión horizontal (secuencial, no se puede vectorizar)
                if dither == 'floyd':
                    if x + 1 < 256:
                        err[y, x+1] += row_qe[x] * (7.0/16.0)
                else:  # atkinson
                    if x + 1 < 256: err[y, x+1] += row_qe[x] * (1.0/8.0)
                    if x + 2 < 256: err[y, x+2] += row_qe[x] * (1.0/8.0)

            bitmap[y*256:(y+1)*256] = row_codes.tobytes()

            # Difusión vertical: toda la fila de golpe (siempre vectorizable)
            if dither == 'floyd' and y + 1 < HEIGHT:
                err[y+1, :-1] += row_qe[1:]  * (3.0/16.0)   # ↙
                err[y+1]      += row_qe       * (5.0/16.0)   # ↓
                err[y+1, 1:]  += row_qe[:-1]  * (1.0/16.0)  # ↘
            elif dither == 'atkinson':
                f = row_qe * (1.0/8.0)
                if y + 1 < HEIGHT:
                    err[y+1, :-1] += f[1:]    # ↙
                    err[y+1]      += f         # ↓
                    err[y+1, 1:]  += f[:-1]   # ↘
                if y + 2 < HEIGHT:
                    err[y+2]      += f         # ↓↓

    print(f"  100.0%  (linea {HEIGHT}/{HEIGHT}) OK")

    # ── 3. Construir archivo SC8 ──────────────────────────────────────────────
    end_addr = len(bitmap) - 1
    header   = struct.pack('<BHHH', 0xFE, 0x0000, end_addr, 0x0000)
    output_data = header + bytes(bitmap)

    Path(output_path).write_bytes(output_data)
    print(f"\nArchivo SC8 guardado: {output_path}  ({len(output_data)} bytes)")
    print('  Carga en MSX con:  SCREEN 8 : BLOAD"fichero.SC8",S')

    if preview_path:
        _save_preview_sc8(bytes(bitmap), preview_path)


def _save_preview_sc8(bitmap: bytes, preview_path: str) -> None:
    """Decodifica el bitmap SC8 y guarda un PNG de preview."""
    HEIGHT = len(bitmap) // 256
    rgb = SC8_PALETTE[np.frombuffer(bitmap, dtype=np.uint8)].reshape(HEIGHT, 256, 3)
    img = Image.fromarray(rgb.astype(np.uint8), 'RGB')
    img.save(preview_path)
    print(f"  Preview guardado: {preview_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Convierte imagenes PNG/JPG a SC2 (MSX1, 256x192) o SC8 (MSX2, 256x212)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python png2msx.py imagen.png salida.SC2                    # SC2, sin dither
  python png2msx.py imagen.png salida.SC8 --format sc8      # SC8, sin dither
  python png2msx.py imagen.png salida.SC2 --dither floyd
  python png2msx.py imagen.png salida.SC2 --dither atkinson
  python png2msx.py imagen.png salida.SC2 --dither bayer
  python png2msx.py imagen.png salida.SC2 --dither floyd --strength 0.5
  python png2msx.py imagen.png salida.SC2 --lines 96
  python png2msx.py imagen.png salida.SC2 --preview salida.png
  python png2msx.py imagen.png salida.SC2 --saturation 1.5 --contrast 1.2
  python png2msx.py imagen.png salida.SC2 --saturation 1.4 --contrast 1.3 --brightness 0.9 --dither atkinson --strength 0.5

Algoritmos de dithering:
  none     : Sin dithering — cuantizacion directa (defecto)
  floyd    : Floyd-Steinberg — suave, propaga error a 4 vecinos
  atkinson : Atkinson — 3/4 del error, zonas solidas mas limpias
  bayer    : Ordered/Bayer 8x8 — patron de puntos regular, aspecto retro

Formatos:
  sc2  : MSX1 SCREEN 2, 256x192, 16 colores TMS9918A, 2 colores por fila 8x1
  sc8  : MSX2 SCREEN 8, 256x212, 256 colores GGGRRR BB, sin restricciones
        """
    )
    parser.add_argument('input',  help='Imagen de entrada (PNG, JPG, BMP...)')
    parser.add_argument('output', help='Archivo de salida .SC2 o .SC8')
    parser.add_argument(
        '--format', choices=['sc2', 'sc8'], default='sc2',
        help='Formato de salida: sc2 (MSX1, 256x192, defecto) o sc8 (MSX2, 256x212)'
    )
    parser.add_argument(
        '--lines', type=int, default=192,
        help='[SC2] Lineas a convertir (multiplo de 8, max 192). Por defecto: 192'
    )
    parser.add_argument(
        '--dither', choices=['floyd', 'atkinson', 'bayer', 'none'], default='none',
        help='Algoritmo de dithering (defecto: none)'
    )
    parser.add_argument(
        '--strength', type=float, default=1.0,
        help='Intensidad del dithering 0.0-1.0 (defecto: 1.0). Solo floyd y atkinson.'
    )
    parser.add_argument(
        '--saturation', type=float, default=1.0,
        help='Factor de saturacion (defecto: 1.0). >1 mas vivido, <1 mas gris.'
    )
    parser.add_argument(
        '--contrast', type=float, default=1.0,
        help='Factor de contraste (defecto: 1.0). >1 mas contraste, <1 mas plano.'
    )
    parser.add_argument(
        '--brightness', type=float, default=1.0,
        help='Factor de brillo (defecto: 1.0). >1 mas claro, <1 mas oscuro.'
    )
    parser.add_argument(
        '--preview', type=str, default=None, metavar='FICHERO.PNG',
        help='Guardar un PNG con la imagen resultante tras la conversion.'
    )
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: no se encuentra '{args.input}'")
        sys.exit(1)

    if args.format == 'sc2':
        convert_image_to_sc2(args.input, args.output, args.lines, args.dither, args.strength,
                              args.saturation, args.contrast, args.brightness, args.preview)
    else:
        convert_image_to_sc8(args.input, args.output, args.dither, args.strength,
                              args.saturation, args.contrast, args.brightness, args.preview)


if __name__ == '__main__':
    main()
