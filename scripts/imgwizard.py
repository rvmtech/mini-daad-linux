#!/usr/bin/env python3
"""
imgwizard.py - Python reimplementation of imgwizard.php
Copyright (C) 2026 Ricardo Villalba <rvm3000@gmail.com>
License: GPL v2 or later

A tool to create and manage MSX image files in several screen modes
to be used by MSX2DAAD engine.

Output file format:
    Offset Size  Description
    0x0000  3    Image magic string: "IMG"
    0x0003  1    Source screen type ('5','6','7','8','A','C')
    0x0004 ...   Chunks

Chunk types:
     0  Redirect
     1  Palette (32 bytes, 12-bit RGB333 in 2-byte format)
     2  RAW data
     3  RLE data
     4  PLETTER data
    16  Reset VRAM pointer
    17  ClearWindow (CLS)
    18  SkipBytes
    19  Pause
"""

import sys
import os
import struct
import subprocess
import tempfile

# ── Constants ────────────────────────────────────────────────────────────────
MAGIC        = b"IMG"
CHUNK_HEAD   = 5
CHUNK_SIZE   = 2043

CHUNK_REDIRECT = 0
CHUNK_PALETTE  = 1
CHUNK_RAW      = 2
CHUNK_RLE      = 3
CHUNK_PLETTER  = 4
CHUNK_RESET    = 16
CHUNK_CLS      = 17
CHUNK_SKIP     = 18
CHUNK_PAUSE    = 19

# Bytes per line for each screen mode (keyed by screen char '5'..'8','A','C')
BYTES_PER_LINE = {'5': 128, '6': 128, '7': 256, '8': 256, 'A': 256, 'C': 256}

# Pixels per byte for each screen mode
PIXELS_PER_BYTE = {'5': 2, '6': 4, '7': 2, '8': 1, 'A': 1, 'C': 1}

# ── Helpers ───────────────────────────────────────────────────────────────────

def strpad(text, length, char=' '):
    return str(text).rjust(length, char)


def pack_chunk_header(chunk_type, size_out, size_in):
    """Pack a 5-byte chunk header: uint8 type, uint16le size_out, uint16le size_in"""
    return struct.pack('<BHH', chunk_type, size_out, size_in)


def check_screen_mode(filename):
    scr = os.path.basename(filename)[-1].upper()
    if scr not in ('5', '6', '7', '8', 'A', 'C'):
        sys.exit(f"\nERROR: bad screen mode ['{scr}']...\n")
    return scr


def get_transparent_color_byte(transparent, scr):
    if transparent < 0:
        return transparent
    if scr in ('5', '7'):
        transparent = (transparent & 0x0F) | ((transparent & 0x0F) << 4)
    elif scr == '6':
        transparent = transparent & 0x03
        transparent = transparent | (transparent << 2) | (transparent << 4) | (transparent << 6)
    elif scr == 'C':
        sys.exit("SCREEN 12 images can't support transparency at this time...\n")
    return transparent & 0xFF


def convert_palette_89(pal: bytes) -> bytes:
    """Convert a 89-byte palette (RGB triplets at offset 0x29) to 32-byte MSX format."""
    out = bytearray()
    for i in range(16):
        r = pal[0x29 + i * 3]
        g = pal[0x29 + i * 3 + 1]
        b = pal[0x29 + i * 3 + 2]
        out.append(((r & 0x0F) << 4) | (b & 0x0F))
        out.append(g & 0x0F)
    return bytes(out)


def check_paletted_colors(data: bytes, scr: str):
    """Warn about PAPER/INK color usage. Returns (data, paper, ink)."""
    bpp = 4
    if scr == '6':
        bpp = 2
    elif scr == '8':
        bpp = 8
    ppb  = 8 // bpp
    mask = (1 << bpp) - 1

    colors = [0] * (mask + 1)
    for byte in data:
        b = byte
        for _ in range(ppb):
            colors[b & mask] += 1
            b >>= bpp

    paper = ink = None
    if scr != '8':
        if colors[0] > 0:
            print("WARNING: PAPER Color (index 0) is used in the image!")
        if colors[mask] > 0:
            print(f"WARNING: INK Color (index {mask}) is used in the image!")
    return data, paper, ink


def add_palette(file: str, file_data: bytes, scr: str, pal: bytes = None,
                paper=None, ink=None) -> bytes:
    """Build a CHUNK_PALETTE chunk, loading palette from .PLx/.PAL file or embedded."""
    palette_file = ""
    if pal is None:
        base = file[:-3] if len(file) > 3 else file
        for candidate in (base + "PL" + scr, base + "PAL"):
            if os.path.exists(candidate):
                palette_file = candidate
                break
        if not palette_file:
            # Try embedded palette at fixed offsets
            if scr in ('5', '6'):
                offset = 0x7680
            else:
                offset = 0xFA80
            if len(file_data) >= offset + 32:
                palette_file = file
                pal = file_data[offset:offset + 32]

    if pal is not None or palette_file:
        print(f"### Adding image palette from file '{palette_file}'")
        print(f"    #CHUNK  1 RGB333 Palette 32 bytes")
        if pal is None:
            with open(palette_file, 'rb') as f:
                pal = f.read()
        if len(pal) == 89:
            pal = convert_palette_89(pal)
        elif len(pal) != 32:
            sys.exit("\nERROR: Unknown Palette format!\n")

        pal = bytearray(pal)
        if paper is not None:
            pal[0], pal[paper * 2]     = pal[paper * 2],     pal[0]
            pal[1], pal[paper * 2 + 1] = pal[paper * 2 + 1], pal[1]
        if ink is not None:
            pal[30], pal[ink * 2]     = pal[ink * 2],     pal[30]
            pal[31], pal[ink * 2 + 1] = pal[ink * 2 + 1], pal[31]

        return pack_chunk_header(CHUNK_PALETTE, 32, 32) + bytes(pal)
    else:
        print("### Palette not found")
        return b""


# ── RLE encoder ───────────────────────────────────────────────────────────────
# Uses numpy to vectorise run detection for a significant speedup over
# pure Python. Falls back to pure Python if numpy is not available.

try:
    import numpy as np
    _HAVE_NUMPY = True
except ImportError:
    _HAVE_NUMPY = False


def _rle_core(data: bytes, mark: int, transparent: int) -> bytes:
    """Encode data, prepending the mark byte and appending the EOF marker."""
    if _HAVE_NUMPY and len(data) > 0:
        arr = np.frombuffer(data, dtype=np.uint8)
        n   = len(arr)

        # Locate run boundaries: position 0 is always a boundary
        boundaries        = np.empty(n, dtype=bool)
        boundaries[0]     = True
        boundaries[1:]    = arr[1:] != arr[:-1]
        run_starts        = np.where(boundaries)[0]
        run_values        = arr[run_starts].tolist()
        run_ends          = np.empty(len(run_starts), dtype=np.intp)
        run_ends[:-1]     = run_starts[1:]
        run_ends[-1]      = n
        run_lengths       = (run_ends - run_starts).tolist()

        out = bytearray([mark])
        for val, length in zip(run_values, run_lengths):
            is_mark        = (val == mark)
            is_transparent = (transparent >= 0) and (val == transparent)
            if length > 3 or is_mark or is_transparent:
                # Emit in chunks of max 255
                rem = length
                while rem > 0:
                    chunk = min(rem, 255)
                    if is_transparent:
                        out += bytes([mark, 1, chunk])
                    else:
                        out += bytes([mark, chunk, val])
                    rem -= chunk
            else:
                out += bytes([val] * length)
        out += bytes([mark, 0])
        return bytes(out)

    # Pure Python fallback
    out = bytearray([mark])
    i   = 0
    n   = len(data)
    while i < n:
        v = data[i]
        j = 0
        while i + j < n and data[i + j] == v:
            j += 1
        is_mark        = (v == mark)
        is_transparent = (transparent >= 0) and (v == transparent)
        if j > 3 or is_mark or is_transparent:
            rem = j
            while rem > 0:
                chunk = min(rem, 255)
                if is_transparent:
                    out += bytes([mark, 1, chunk])
                else:
                    out += bytes([mark, chunk, v])
                rem -= chunk
            i += j
        else:
            out += bytes([v] * j)
            i   += j
    out += bytes([mark, 0])
    return bytes(out)


def rle_encode(data: bytes, add_size=True, mark: int = None,
               eof=True, transparent=-1) -> bytes:
    out = bytearray()
    if add_size:
        out += struct.pack('<H', len(data))

    if mark is None:
        if _HAVE_NUMPY and len(data) > 0:
            freq = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
            mark = int(np.argmin(freq))
        else:
            freq = [0] * 256
            for b in data:
                freq[b] += 1
            mark = freq.index(min(freq))
        out.append(mark)

    # _rle_core always prepends mark byte and appends EOF (mark, 0)
    encoded = _rle_core(data, mark, transparent)
    # encoded[0]  = mark byte  (already in `out` when mark was auto-detected,
    #               or known to caller when passed in — either way, skip it)
    # encoded[-2:] = EOF (mark, 0)
    if not eof:
        out += encoded[1:-2]   # strip leading mark AND trailing EOF
    else:
        out += encoded[1:]     # strip only leading mark, keep EOF

    return bytes(out)


def rle_encode_selection(data: bytes, x: int, y: int, w: int, h: int,
                         transparent: int, pixels_per_byte: int,
                         bytes_per_line: int) -> bytes:
    if _HAVE_NUMPY and len(data) > 0:
        freq = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
        mark = int(np.argmin(freq))
    else:
        freq = [0] * 256
        for b in data:
            freq[b] += 1
        mark = freq.index(min(freq))

    out = bytearray([mark])
    xb  = x // pixels_per_byte
    wb  = round(w / pixels_per_byte)
    skip = bytes_per_line - wb

    for i in range(h):
        row_start = xb + (y + i) * bytes_per_line
        row_data  = data[row_start: row_start + wb]
        out += rle_encode(row_data, add_size=False, mark=mark,
                          eof=False, transparent=transparent)
        if skip and i < h - 1:
            tmp = skip
            while tmp:
                chunk = min(tmp, 255)
                out += bytes([mark, 1, chunk])
                tmp -= chunk

    out += bytes([mark, 0])
    return bytes(out)


# ── Compression dispatcher ────────────────────────────────────────────────────

def compress_block(data: bytes, method: str, transparent=-1,
                   pletter_exe='pletter') -> bytes:
    """Compress a block of data. Returns compressed bytes."""
    if method == 'RAW':
        return data
    elif method == 'RLE':
        return rle_encode(data, add_size=False, eof=True, transparent=transparent)
    elif method == 'PLETTER':
        with tempfile.NamedTemporaryFile(delete=False, suffix='') as tmp:
            tmp_path = tmp.name
        try:
            with open(tmp_path, 'wb') as f:
                f.write(data)
            out_path = tmp_path + '.plet5'
            subprocess.run([pletter_exe, tmp_path], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with open(out_path, 'rb') as f:
                return f.read()
        finally:
            for p in (tmp_path, tmp_path + '.plet5'):
                try:
                    os.unlink(p)
                except FileNotFoundError:
                    pass
    else:
        sys.exit(f"Unknown compression method: {method}")


CHUNK_ID = {'RAW': CHUNK_RAW, 'RLE': CHUNK_RLE, 'PLETTER': CHUNK_PLETTER}


# ── Command: C — compress full-width image ────────────────────────────────────

def cmd_compress(file_in: str, lines: int, method: str,
                 transparent=-1, last_palette=False,
                 pletter_exe='pletter'):
    print(f"### Loading {file_in}")
    scr = check_screen_mode(file_in)
    print(f"### Mode SCREEN {int(scr, 16) if scr.isdigit() else scr}")
    print(f"### Lines {lines}")

    if transparent >= 0:
        method = 'RLE'
    print(f"### Compressor: {method}" + (" (forced)" if transparent >= 0 else ""))

    transparent = get_transparent_color_byte(transparent, scr)

    with open(file_in, 'rb') as f:
        raw = f.read()
    data = raw[7:]  # skip 7-byte MSX BSAVE header

    bpl = BYTES_PER_LINE[scr]
    rest = data[bpl * lines:]
    data = data[:bpl * lines]

    out = bytearray(MAGIC + scr.encode())
    chunk_id = 1

    # Palette for paletted screen modes (SC5/SC6/SC7), before image data
    if scr in ('5', '6', '7') and not last_palette:
        data, paper, ink = check_paletted_colors(data, scr)
        pal_chunk = add_palette(file_in, data + rest, scr)
        if pal_chunk:
            chunk_id += 1
            out += pal_chunk

    # CLS chunk if not transparent
    if transparent < 0:
        out += pack_chunk_header(CHUNK_CLS, 0, 0)
        print(f"    #CHUNK {strpad(chunk_id, 2)} CMD CLS (clear window)")
        chunk_id += 1

    # Compress image data into chunks.
    # The compressed output must fit in CHUNK_SIZE (2043) bytes.
    # Input size is unlimited -- binary search finds the largest input block
    # whose compressed output fits. This matches the original PHP behaviour
    # where size_in can be much larger than CHUNK_SIZE.
    full_size = len(data)
    pos = 0
    while pos < full_size:
        # Try compressing everything remaining first
        block      = data[pos:]
        compressed = compress_block(block, method, transparent, pletter_exe)
        size_out   = len(compressed)

        if size_out < CHUNK_SIZE:
            # Everything remaining fits in one chunk
            size_in = len(block)
        else:
            # Binary search: find largest input that compresses to <= CHUNK_SIZE
            lo, hi  = 1, full_size - pos
            size_in = 1
            compressed = compress_block(data[pos:pos + 1], method, transparent, pletter_exe)
            while lo <= hi:
                mid = (lo + hi) // 2
                c   = compress_block(data[pos:pos + mid], method, transparent, pletter_exe)
                if len(c) <= CHUNK_SIZE:
                    size_in    = mid
                    compressed = c
                    lo         = mid + 1
                else:
                    hi = mid - 1
            size_out = len(compressed)

        print(f"    #CHUNK {strpad(chunk_id, 2)} ({strpad(pos, 5)}): "
              f"sizeIn: {size_in} bytes (out: {size_out} bytes)")
        out += pack_chunk_header(CHUNK_ID[method], size_out, size_in) + compressed
        chunk_id += 1
        pos += size_in

    # Palette at last chunk (CL mode)
    if scr in ('5', '6', '7') and last_palette:
        data, paper, ink = check_paletted_colors(data, scr)
        pal_chunk = add_palette(file_in, data + rest, scr)
        if pal_chunk:
            chunk_id += 1
            out += pal_chunk

    ratio = f"{len(out) / full_size * 100:.1f}" if full_size > 0 else "0.0"
    print(f"    In: {full_size} bytes\n    Out: {len(out) + 7} bytes [{ratio}%]")

    base     = os.path.basename(file_in).lower()
    file_out = base[:-3] + "im" + scr.lower()
    print(f"### Writing {file_out}")
    with open(file_out, 'wb') as f:
        f.write(out)
    print("### Done\n")


# ── Command: S — compress rectangle ──────────────────────────────────────────

def cmd_compress_rect(file_in: str, x: int, y: int, w: int, h: int,
                      transparent=-1):
    print(f"### Loading {file_in}")
    scr = check_screen_mode(file_in)
    print(f"### Mode SCREEN {int(scr, 16) if scr.isdigit() else scr}")

    if int(scr, 16) >= 10 and (x % 4 != 0 or w % 4 != 0):
        sys.exit("\nERROR: SCREEN 10/12 needs 'x' and 'w' input to be multiple of 4...\n")

    print(f"### Rectangle Start:({x}, {y}) Width:({w}, {h})")
    print("### Compressor: RLE (forced)")

    transparent = get_transparent_color_byte(transparent, scr)

    with open(file_in, 'rb') as f:
        data = f.read()[7:]

    out = bytearray(MAGIC + scr.encode())
    chunk_id = 1

    ppb = PIXELS_PER_BYTE[scr]
    bpl = BYTES_PER_LINE[scr]

    if scr in ('5', '6', '7'):
        data, paper, ink = check_paletted_colors(data, scr)
        pal_chunk = add_palette(file_in, data, scr)
        if pal_chunk:
            chunk_id += 1
            out += pal_chunk

    if transparent < 0:
        out += pack_chunk_header(CHUNK_CLS, 0, 0)
        print(f"    #CHUNK {strpad(chunk_id, 2)} CMD CLS (clear window)")
        chunk_id += 1

    wb        = round(w / ppb)
    full_size = h * wb
    i         = 0

    while i < h:
        j = h - i
        while True:
            comp_out = rle_encode_selection(data, x, y + i, w, j,
                                            transparent, ppb, bpl)
            if len(comp_out) <= CHUNK_SIZE:
                break
            j -= 1

        size_in  = j * bpl
        size_out = len(comp_out)
        print(f"    #CHUNK {strpad(chunk_id, 2)} sizeIn: {j * wb} bytes (out: {size_out} bytes)")
        out += pack_chunk_header(CHUNK_RLE, size_out, size_in) + comp_out
        i        += j
        chunk_id += 1

    ratio    = f"{len(out) / full_size * 100:.1f}" if full_size > 0 else "0.0"
    print(f"    In: {full_size} bytes\n    Out: {len(out) + 7} bytes [{ratio}%]")

    base     = os.path.basename(file_in).lower()
    file_out = base[:-3] + "im" + scr.lower()
    print(f"### Writing {file_out}")
    with open(file_out, 'wb') as f:
        f.write(out)
    print("### Done\n")


# ── Command: L — list image content ──────────────────────────────────────────

def cmd_list(file_in: str, remove_id=None):
    print(f"### Reading file {file_in}")
    with open(file_in, 'rb') as f:
        data = f.read()

    if data[:3] != MAGIC:
        sys.exit("ERROR: bad file type...\n")

    scr = chr(data[3])
    if scr not in ('5', '6', '7', '8', 'A', 'C'):
        sys.exit(f"ERROR: bad screen mode ['{scr}']...\n")

    print(f"### Mode SCREEN {int(scr, 16) if scr.isdigit() else scr}")

    out       = bytearray(data[:4])
    pos       = 4
    total_raw = 0
    total_cmp = 0
    chunk_id  = 1
    last_type = 0

    while pos < len(data):
        chunk_type, size_out, size_in = struct.unpack_from('<BHH', data, pos)
        last_type = chunk_type
        size      = 5

        if chunk_type == CHUNK_REDIRECT:
            print(f"    CHUNK {chunk_id}: Redirect -> {strpad(size_out, 3, '0')}.IM{scr}")
        elif chunk_type == CHUNK_PALETTE:
            print(f"    CHUNK {chunk_id}: RGB333 Palette {size_in} bytes")
            size += size_out
        elif chunk_type == CHUNK_RAW:
            print(f"    CHUNK {chunk_id}: RAW Data: {size_in} bytes")
            size += size_out
        elif chunk_type == CHUNK_RLE:
            ratio = f"{size_out / size_in * 100:.1f}" if size_in else "0.0"
            print(f"    CHUNK {chunk_id}: RLE Data: {size_in} bytes "
                  f"({size_out} bytes compressed) [{ratio}%]")
            size += size_out
        elif chunk_type == CHUNK_PLETTER:
            ratio = f"{size_out / size_in * 100:.1f}" if size_in else "0.0"
            print(f"    CHUNK {chunk_id}: PLETTER Data: {size_in} bytes "
                  f"({size_out} bytes compressed) [{ratio}%]")
            size += size_out
        elif chunk_type == CHUNK_RESET:
            print(f"    CHUNK {chunk_id}: CMD:ResetPointer")
            size += size_out
        elif chunk_type == CHUNK_CLS:
            print(f"    CHUNK {chunk_id}: CMD:ClearWindow")
            size += size_out
        elif chunk_type == CHUNK_SKIP:
            print(f"    CHUNK {chunk_id}: CMD:SkipVRAMBytes ({size_out} bytes)")
            size += size_out
        elif chunk_type == CHUNK_PAUSE:
            print(f"    CHUNK {chunk_id}: CMD:Pause ({size_out}/50 seconds)")
            size += size_out
        else:
            sys.exit(f"    CHUNK {chunk_id}: UNKNOWN CHUNK TYPE!!!! [**Aborted**]\n")

        if chunk_type != CHUNK_REDIRECT:
            total_raw += size_in   # uncompressed
            total_cmp += size_out  # compressed

        if chunk_id == remove_id:
            print(f"--REMOVED CHUNK {chunk_id}--")
        else:
            out += data[pos: pos + size]

        pos      += size
        chunk_id += 1

    if remove_id is not None and remove_id >= chunk_id:
        print(f"!!!WARNING: CHUNK {remove_id} NOT FOUND!!!")

    if last_type != CHUNK_REDIRECT and remove_id is None:
        ratio = f"{total_cmp / total_raw * 100:.1f}" if total_raw else "0.0"
        print(f"### Original size:   {total_raw} bytes")
        print(f"### Compressed size: {total_cmp} bytes [{ratio}%]")

    print("### End of file")
    return bytes(out)


# ── Command: D — delete a chunk ───────────────────────────────────────────────

def cmd_delete(file_in: str, chunk_id: int):
    out = cmd_list(file_in, remove_id=chunk_id)
    print("### Saving file\n")
    with open(file_in, 'wb') as f:
        f.write(out)


# ── Command: J — join IMx files ───────────────────────────────────────────────

def cmd_join(file_out: str, files_in: list):
    print("### Joining images")
    out    = bytearray()
    magic4 = None

    for i, path in enumerate(files_in):
        print(f"    Copying image {path}")
        with open(path, 'rb') as f:
            data = f.read()
        if data[:3] != MAGIC:
            sys.exit("ERROR: All files must be images and with same screen mode!\n")
        if i == 0:
            magic4 = data[:4]
            out   += data
        else:
            if data[:3] != magic4[:3]:
                sys.exit("ERROR: All files must be images and with same screen mode!\n")
            out += data[4:]

    print(f"### Saving file {file_out}\n")
    with open(file_out, 'wb') as f:
        f.write(out)


# ── Command: R — create redirect file ────────────────────────────────────────

def cmd_redirect(file_out: str, new_loc: int):
    print("### Creating redirection file")
    scr = os.path.basename(file_out)[-1].upper()
    print(f"    Adding redirect location to {new_loc}")
    out = MAGIC + scr.encode() + struct.pack('<BHH', CHUNK_REDIRECT, new_loc, 0xFFFF)
    with open(file_out, 'wb') as f:
        f.write(out)
    print(f"### Writing {file_out}")
    print("### Done.\n")


# ── Command: 5A — SC5 → SCA ──────────────────────────────────────────────────

def cmd_sc5_to_sca(file_in: str, file_out: str, lines: int):
    print(f"### Loading {file_in}")
    with open(file_in, 'rb') as f:
        data = f.read()
    out = bytearray(b'\xfe\x00\x00\x00\xd4\x00\x00')
    print("### Converting SC5 to SCA...")
    pos  = 7
    size = 128 * lines
    while size > 0 and pos < len(data):
        orig = data[pos]
        out.append((orig & 0xF0) | 0x08)
        out.append(((orig << 4) & 0xFF) | 0x08)
        pos  += 1
        size -= 1
    print(f"### Saving file {file_out}\n")
    with open(file_out, 'wb') as f:
        f.write(out)


# ── Command: CA — SCC → SCA ───────────────────────────────────────────────────

def cmd_scc_to_sca(file_in: str, file_out: str, lines: int):
    print(f"### Loading {file_in}")
    with open(file_in, 'rb') as f:
        data = f.read()
    out = bytearray(b'\xfe\x00\x00\x00\xd4\x00\x00')
    print("### Converting SCC to SCA...")
    pos  = 7
    size = 256 * lines
    while size > 0 and pos < len(data):
        out.append(data[pos] & 0b11110111)
        pos  += 1
        size -= 1
    print(f"### Saving file {file_out}\n")
    with open(file_out, 'wb') as f:
        f.write(out)


# ── Syntax help ───────────────────────────────────────────────────────────────

def show_syntax():
    name = os.path.basename(sys.argv[0])
    print(f"""
IMGWIZARD v1.3.01 for MSX2DAAD  (Python port)
===================================================================
A tool to create and manage MSX image files in several screen modes
to be used by MSX2DAAD engine.

L) List image chunks:
    {name} l <fileIn.IM?>

C) Create an image IMx (CL - Create the palette at last chunk):
    {name} c[l] <fileIn.SC?> <lines> [compressor | transparent_color]

S) Create an image from a rectangle:
    {name} s <fileIn.SC?> <x> <y> <w> <h> [transparent_color]

R) Create a location redirection:
    {name} r <fileOut.IM?> <target_loc>

D) Remove a CHUNK from an image:
    {name} d <fileIn.IM?> <chunk_id>

J) Join several IMx files in just one:
    {name} j <fileOut.IM?> <fileIn1.IM?> [fileIn2.IM?] ...

5A) Transform a SC5 image to a RGB SC10(SCA) one:
    {name} 5a <fileIn.SC5> <fileOut.SCA> <lines>

CA) Transform a SC12(SCC) image to a YJK SC10(SCA) one:
    {name} ca <fileIn.SCC> <fileOut.SCA> <lines>

 <fileIn>      Input file in format SCx (SC5/SC6/SC7/SC8/SCA/SCC)
               Palette can be inside SCx file or PL5 PL6 PL7 files.
 <lines>       Image lines to get from input file.
 [compressor]  Compression type: RAW, RLE or PLETTER.
                 RAW: no compression but fastest load.
                 RLE: light compression but fast load (default).
                 PLETTER: high compression but slow.
 [transparent] Optional: the color index that will become transparent (decimal).
               Compression is forced to RLE.
 <target_loc>  Target location number to redirect to.
                 ex: r 12 redirects to image 012.IMx

Example: {name} c image.sc8 96 RLE
""")
    sys.exit(1)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        show_syntax()

    cmd = args[0].lower()

    # L — list
    if cmd == 'l' and len(args) == 2:
        cmd_list(args[1])
        print()
        return

    # R — redirect
    if cmd == 'r' and len(args) == 3:
        if not args[2].isdigit():
            sys.exit("ERROR: Redirect location is not an integer [0-255]...\n")
        cmd_redirect(args[1], int(args[2]))
        return

    # S — rectangle
    if cmd == 's' and len(args) >= 6:
        try:
            x, y, w, h = int(args[2]), int(args[3]), int(args[4]), int(args[5])
        except ValueError:
            sys.exit("ERROR: x, y, w, and h must be numeric and greater than zero...\n")
        transparent = -1
        if len(args) >= 7:
            if not args[6].lstrip('-').isdigit():
                sys.exit("ERROR: Not decimal number for transparent index color...\n")
            transparent = int(args[6])
            print(f"### Transparent color: {transparent}")
        cmd_compress_rect(args[1], x, y, w, h, transparent)
        return

    # CL — compress with palette at last chunk
    last_palette = False
    if cmd == 'cl':
        last_palette = True
        cmd = 'c'

    # C — compress full image
    if cmd == 'c' and len(args) >= 3:
        file_in = args[1]
        try:
            lines = int(args[2])
        except ValueError:
            sys.exit("ERROR: lines must be numeric and greater than zero [0-212]...\n")
        if not (1 <= lines <= 212):
            sys.exit("ERROR: lines must be numeric and greater than zero [0-212]...\n")

        method      = ''
        transparent = -1
        if len(args) >= 4:
            if args[3].lstrip('-').isdigit():
                transparent = int(args[3])
            else:
                method = args[3].upper()

        if method not in ('RAW', 'RLE', 'PLETTER') and transparent < 0:
            sys.exit("ERROR: Unknown compression method or not decimal number "
                     "for transparent index color...\n")

        if transparent >= 0:
            print(f"### Transparent color: {transparent}")
            method = 'RLE'

        cmd_compress(file_in, lines, method, transparent, last_palette)
        return

    # D — delete chunk
    if cmd == 'd' and len(args) == 3:
        if not args[2].isdigit():
            sys.exit("ERROR: ChunkID must be numeric and greater than zero...\n")
        cmd_delete(args[1], int(args[2]))
        return

    # J — join
    if cmd == 'j' and len(args) >= 4:
        cmd_join(args[1], args[2:])
        return

    # 5A — SC5 to SCA
    if cmd == '5a' and len(args) == 4:
        cmd_sc5_to_sca(args[1], args[2], int(args[3]))
        return

    # CA — SCC to SCA
    if cmd == 'ca' and len(args) == 4:
        cmd_scc_to_sca(args[1], args[2], int(args[3]))
        return

    show_syntax()


if __name__ == '__main__':
    main()
