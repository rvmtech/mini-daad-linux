# Mini DAAD Linux

🇬🇧 [Read this document in English](README.md)

Lo siguiente es una colección de scripts y herramientas
que permiten construir nativamente aventuras conversacionales
para ordenadores retro, como el ZX Spectrum, Amstrad CPC,
Commodore 64 y varios más, usando los intérpretes del Daad.

Está basado en el [DAAD Ready](https://www.ngpaws.com/daadready/es.html).

En el resto del documento se asume que ya estás familiarizado con la
creación de aventuras con dicho sistema. Si no es así te recomiendo que
leas la documentación del **DAAD Ready** antes de continuar.

## Licencia

Los **scripts desarrollados específicamente para Mini DAAD Linux**
están distribuidos bajo licencia:

> **GNU General Public License v2 o superior (GPL v2+)**

Sin embargo, este proyecto hace uso de herramientas, utilidades y
componentes desarrollados por terceros.

Cada uno de esos elementos puede estar sujeto a **su propia licencia**.
Es responsabilidad del usuario consultar las condiciones específicas en
los sitios web oficiales de sus respectivos autores.

Algunas herramientas externas utilizadas:

 * [DRC](https://github.com/Utodev/DRC)
 * [PCDAAD](https://github.com/Utodev/PCDAAD)
 * [MALUVA](https://github.com/Utodev/MALUVA)
 * [ZX0](https://github.com/einar-saukas/ZX0)
 * [CPCXfs](https://www.octoate.de/download/cpcxfs/)

## Dependencias

Para poder ejecutar los scripts es necesario tener instalado PHP.
Para generar juegos en HTML, también se requiere la extensión `php-gd`.

Si quieres crear un juego para Commodore 64 necesitas instalar el
emulador Vice, ya que los scripts usan una utilidad suya para
crear el disco del juego.

Además harán falta varios emuladores si quieres probar tu juego.

En el fichero `config.sh` puedes configurar los emuladores a usar.

### Emuladores recomendados

Algunos emuladores suelen estar incluidos en las distribuciones
de Linux, por lo que son fáciles de instalar (aunque es posible que
tengas que buscar e instalar las ROMs de las máquinas).

  - [Fuse](https://fuse-emulator.sourceforge.net), es un emulador de máquinas ZX Spectrum.
  - [Vice](https://vice-emu.sourceforge.io), emulador de máquinas Commodore.
  - [Dosbox](https://www.dosbox.com), emulador de MS-DOS.
  - [ZEsarUX](https://github.com/chernandezba/zesarux), emula
    varias máquinas, incluyendo los ZX Spectrum tradicionales y el
    nuevo ZX Spectrum Next, y otros como Amstrad CPC 6128.

## Plataformas soportadas

Actualmente, Mini DAAD Linux permite compilar juegos para las siguientes
plataformas:

  - ZX Spectrum 48K (sin gráficos)
  - ZX Spectrum 128K
  - ZX Spectrum +3
  - ZX Spectrum Next
  - Amstrad CPC 6128
  - Commodore 64
  - MS-DOS
  - HTML (se puede jugar en navegadores web)

## Cómo se usa

El procedimiento para compilar un juego para una máquina determinada es el
siguiente:

1) Pon el fichero dsf, con el fuente del juego, en la misma carpeta de los scripts.
   Si no tienes ningún dsf, al ejecutar uno de los scripts se creará uno de ejemplo.

2) Edita el fichero `config.sh` y pon en **GAME** el nombre del juego (debe tener
   el mismo nombre del fichero dsf pero sin la extensión .dsf).

3) Pon las imágenes en la carpeta `IMAGES` según se explica en [Multimedia](#multimedia).

4) Ejecuta uno de estos scripts, que compilará el juego:

    | Script             | Plataforma         |
    |--------------------|--------------------|
    | `zx48k.sh`         | ZX Spectrum 48K   |
    | `zx128k.sh`        | ZX Spectrum 128K  |
    | `zxplus3.sh`       | ZX Spectrum +3    |
    | `zxnext.sh`        | ZX Spectrum Next  |
    | `c64.sh`           | Commodore 64      |
    | `cpc6128.sh`       | Amstrad CPC 6128  |
    | `msdos.sh`         | MS-DOS            |
    | `html.sh`          | HTML              |

Si la compilación acaba sin errores y has instalado el emulador correspondiente
podrás ejecutar el juego en el emulador.

Los ficheros generados los puedes encontrar dentro de la carpeta `RELEASE`.

## Multimedia

Las imágenes para cada plataforma deben estar en las siguientes carpetas:

| Plataforma                | Formato       | Resolución     | Carpeta          |
|---------------------------|---------------|----------------|----------------- |
| ZX Spectrum               | `.scr`        |   256x192      | `IMAGES`         |
| Amstrad CPC (modo 0)      | `.scr`/`.pal` |   160x200      | `IMAGES/CPC`     |
| Amstrad CPC (modo 1)      | `.scr`/`.pal` |   320x200      | `IMAGES/CPC`     |
| ZX Spectrum Next          | `.pcx`        |   256x192      | `IMAGES`         |
| Commodore 64 (HiRes)      | `.art`        |   320x200      | `IMAGES`         |
| Commodore 64 (Multicolor) |  `.koa`       |   160x200      | `IMAGES`         |
| MS-DOS (VGA)              | `.pcx`        |   320x200      | `IMAGES/PC`      |
| MS-DOS (SVGA)             | `.pcx`        |   640x400      | `IMAGES/PC/SVGA` |
| HTML                      | `.png`        |   320x200      | `IMAGES/HTML`    |

Los vídeos deben colocarse en:

| Plataforma                | Formato       | Resolución     | Carpeta          |
|---------------------------|---------------|----------------|----------------- |
| MS-DOS (VGA)              | `.fli`        |   320x200      | `IMAGES/PC`      |
| MS-DOS (SVGA)             | `.fli`        |   320x200      | `IMAGES/PC/SVGA` |
| HTML                      | `.mp4`        |   320x200      | `IMAGES/HTML`    |

Los sonidos:

| Plataforma                | Formato       | Carpeta       |
|---------------------------|---------------|-------------- |
| MS-DOS                    | `.wav`        | `SOUNDS`      |
| HTML                      | `.mp3`        | `SOUNDS`      |

## El archivo de configuración `config.sh`

El archivo `config.sh` permite definir opciones de compilación para el juego,
así como configurar los emuladores que se utilizarán para ejecutarlo.

### Opciones del juego

* `GAME`  
  Nombre del juego. Debe coincidir con el nombre del archivo `.dsf` sin la extensión.

* `SPLITSCR` (`splitModeOff` / `splitModeOn`)  
  Opción utilizada en Amstrad CPC y Commodore 64.
  Si se establece en `splitModeOn`, la zona gráfica utilizará
  el modo con mayor número de colores pero de menor resolución.

* `IMGLINES`  
  Número de líneas de imagen que se mostrarán en pantalla.

* `BUFFERED_IMAGES`  (solo para ZX Spectrum +3)  
   Una lista separada por comas de imágenes que se guardarán en memoria
   para que puedan mostrarse más rápidamente.
   Ejemplo: `BUFFERED_IMAGES="008,014,012,020"`

* `SVGA` (`0` / `1`)  
  Si se establece en `1`, se utilizarán imágenes SVGA en la versión para MS-DOS.

* `RUN_GAME` (`true` / `false`)  
  Si se establece en `true`, el emulador correspondiente se ejecutará automáticamente
  después de compilar el juego.

### Configuración de emuladores

* `ZESARUX_BIN`  
  Ruta al ejecutable del emulador ZEsarUX.

* `SPECTRUM_EMULATOR`  
  Comando utilizado para ejecutar el emulador de ZX Spectrum.
  El marcador `{tapfile}` será reemplazado por la ruta al archivo `.tap` o `.dsk`.

* `CPC_EMULATOR`  
  Comando utilizado para ejecutar el emulador de Amstrad CPC.
  `{tapfile}` se reemplaza por la ruta al archivo `.dsk`.

* `NEXT_EMULATOR`  
  Comando utilizado para ejecutar el emulador de ZX Spectrum Next.
  `{tapfile}` se reemplaza por la ruta al archivo `.tap` y `{imgdir}` por el directorio que contiene las imágenes.

* `C64_EMULATOR`  
  Comando utilizado para ejecutar el emulador de Commodore 64.
  `{tapfile}` se reemplaza por la ruta al archivo `.d64`.

* `MSDOS_EMULATOR`  
  Comando utilizado para ejecutar el emulador de MS-DOS.
