# Mini DAAD Linux

🇪🇸 [Lee este documento en español](LEEME.md)

This is a collection of scripts and tools that allow you to build
text adventures natively for retro computers such as the ZX Spectrum,
Amstrad CPC, Commodore 64, and several others, using the DAAD interpreters.

It is based on [DAAD Ready](https://www.ngpaws.com/daadready/index.html).

The rest of this document assumes that you are already familiar with
creating adventures using this system. If not, we recommend reading the
**DAAD Ready** documentation before continuing.

## License

The **scripts developed specifically for Mini DAAD Linux**
are distributed under the license:

> **GNU General Public License v2 or later (GPL v2+)**

However, this project makes use of tools, utilities, and
components developed by third parties.

Each of these elements may be subject to **its own license**. Users
should check the licensing conditions on each tool's official website.

Some external tools used:

 * [DRC](https://github.com/Utodev/DRC)
 * [PCDAAD](https://github.com/Utodev/PCDAAD)
 * [MALUVA](https://github.com/Utodev/MALUVA)
 * [ZX0](https://github.com/einar-saukas/ZX0)
 * [CPCXfs](https://www.octoate.de/download/cpcxfs/)
 * [DSKTOOL](https://github.com/lvitals/dsktool)

## Dependencies

* In order to run the scripts, **PHP** must be installed.
  To generate HTML games, the **php-gd** extension is also required.

* If you want to create a game for Commodore 64, you must install
  the **VICE** emulator, since the scripts use one of its utilities
  to create the game disk.

* For MSX2, **Python 3** with the **NumPy** library is also required.

You will also need several emulators if you want to test your game.
The emulators to be used can be configured in the `config.sh` file.

### Recommended emulators

Some emulators are usually included in Linux distributions,
so they are easy to install (although you may need to locate
and install the ROMs for the machines).

- [Fuse](https://fuse-emulator.sourceforge.net), an emulator for ZX Spectrum machines.
- [Vice](https://vice-emu.sourceforge.io), an emulator for Commodore machines.
- [Dosbox](https://www.dosbox.com), an MS-DOS emulator.
- [OpenMSX](https://openmsx.org), an emulator for MSX1 and MSX2.
  It requires the ROMs `nms8250_basic-bios2.rom`, `nms8250_disk.rom`, and `nms8250_msx2sub.rom`.
- [ZEsarUX](https://github.com/chernandezba/zesarux), emulates several machines,
  including traditional ZX Spectrum models, the newer ZX Spectrum Next,
  and others such as the Amstrad CPC 6128.

## Supported platforms

Currently, Mini DAAD Linux can compile games for the following platforms:

- ZX Spectrum 48K (no graphics)
- ZX Spectrum 128K
- ZX Spectrum +3
- ZX Spectrum Next
- Amstrad CPC 6128
- Commodore 64
- MSX 1
- MSX 2
- MS-DOS
- HTML (playable in web browsers)

## How to use

The procedure to compile a game for a specific machine is as follows:

1) Place the `.dsf` file containing the game source code in the same
   directory as the scripts.  
   If you do not have a `.dsf` file, running one of the scripts will
   create a sample file.

2) Edit the `config.sh` file and set **GAME** to the name of the game
   (it must match the name of the `.dsf` file without the `.dsf` extension).

3) Place the images in the `IMAGES` folder as explained in the [Multimedia](#multimedia) section.

4) Run one of the following scripts, which will compile the game:

    | Script             | Platform            |
    |--------------------|--------------------|
    | `zx48k.sh`         | ZX Spectrum 48K    |
    | `zx128k.sh`        | ZX Spectrum 128K   |
    | `zxplus3.sh`       | ZX Spectrum +3     |
    | `zxnext.sh`        | ZX Spectrum Next   |
    | `c64.sh`           | Commodore 64       |
    | `cpc6128.sh`       | Amstrad CPC 6128   |
    | `msx1.sh`          | MSX 1             |
    | `msx2.sh`          | MSX 2             |
    | `msdos.sh`         | MS-DOS             |
    | `html.sh`          | HTML               |

If compilation succeeds and the corresponding emulator is installed, the
game will launch automatically.

The generated files can be found inside the `RELEASE` directory.

## Multimedia

Images for each platform must be placed in the following directories:

| Platform                  | Format        | Resolution | Folder            |
|---------------------------|--------------|------------|-------------------|
| ZX Spectrum               | `.scr`       | 256x192    | `IMAGES`          |
| Amstrad CPC (mode 0)      | `.scr`/`.pal`| 160x200    | `IMAGES/CPC`      |
| Amstrad CPC (mode 1)      | `.scr`/`.pal`| 320x200    | `IMAGES/CPC`      |
| ZX Spectrum Next          | `.pcx`       | 256x192    | `IMAGES`          |
| Commodore 64 (HiRes)      | `.art`       | 320x200    | `IMAGES`          |
| Commodore 64 (Multicolor) | `.koa`       | 160x200    | `IMAGES`          |
| MSX 1                     | `.sc2`       | 256x192    | `IMAGES`          |
| MSX 2                     | `.sc8`       | 256x212    | `IMAGES`          |
| MS-DOS (VGA)              | `.pcx`       | 320x200    | `IMAGES/PC`       |
| MS-DOS (SVGA)             | `.pcx`       | 640x400    | `IMAGES/PC/SVGA`  |
| HTML                      | `.png`       | 320x200    | `IMAGES/HTML`     |

Videos must be placed in:

| Platform       | Format | Resolution | Folder            |
|----------------|--------|------------|-------------------|
| MS-DOS (VGA)   | `.fli` | 320x200    | `IMAGES/PC`       |
| MS-DOS (SVGA)  | `.fli` | 320x200    | `IMAGES/PC/SVGA`  |
| HTML           | `.mp4` | 320x200    | `IMAGES/HTML`     |

Sounds:

| Platform | Format | Folder   |
|----------|--------|----------|
| MS-DOS   | `.wav` | `SOUNDS` |
| HTML     | `.mp3` | `SOUNDS` |

## The `config.sh` configuration file

The `config.sh` file allows you to define compilation options
for the game, as well as configure the emulators to run it.

### Game options

* `GAME`  
  Name of the game. It must match the name of the `.dsf` file without the extension.

* `SPLITSCR` (`splitModeOff` / `splitModeOn`)  
  Option used in Amstrad CPC and Commodore 64.  
  If set to `splitModeOn`, the graphic area will use a display mode
  with more colours but lower resolution.

* `IMGLINES`  
  Number of image lines that will be displayed on screen.

* `BUFFERED_IMAGES` (ZX Spectrum +3 only)  
  A comma-separated list of images to preload into memory for faster display.
  Example: `BUFFERED_IMAGES="008,014,012,020"`

* `SVGA` (`0` / `1`)  
  If set to `1`, SVGA images will be used in the MS-DOS version.

* `RUN_GAME` (`true` / `false`)  
  If set to `true`, the corresponding emulator will be executed
  automatically after compiling the game.

### Emulator configuration

* `ZESARUX_BIN`  
  Path to the ZEsarUX emulator executable.

* `SPECTRUM_EMULATOR`  
  Command to run the ZX Spectrum emulator.

* `CPC_EMULATOR`  
  Command to run the Amstrad CPC emulator.

* `NEXT_EMULATOR`  
  Command to run the ZX Spectrum Next emulator.

* `C64_EMULATOR`  
  Command to run the Commodore 64 emulator.  

* `MSDOS_EMULATOR`  
  Command to run the MS-DOS emulator.

* `MSX_EMULATOR`..
  Command to run the MSX 1 and MSX 2 emulator.
