# SNES for Analogue Pocket

This is my fork of [drizzt’s SNES Experimental core](https://github.com/drizzt/openfpga-snes), based on [agg23’s Analogue Pocket port](https://github.com/agg23/openFPGA-SNES) of the original core by [srg320](https://github.com/srg320) ([Patreon](https://www.patreon.com/srg320)). The fork starts at upstream commit [`397f759`](https://github.com/drizzt/openfpga-snes/commit/397f759356ec680dd516a05a89b3734ea5716d71).

This fork adds the Composite Blend options described below. Please report issues with my additions to this repository. I cannot help with issues in the original core or its ports, as I am not their author; please report those to the relevant upstream repository.

> [!NOTE]
>
> Save states, Memories, and Sleep are supported for regular carts and the DSP, Super FX (GSU), SA-1, and CX4 chips. S-DD1, SPC7110, and BSX games are not supported. See [Savestates/Memories/Sleep](#savestatesmemoriessleep) below.

## Composite Blend

Choose **Composite Blend** in Core Settings. **Off** is the default.

| Setting | Effect |
| --- | --- |
| Off | Passes the core’s RGB pixels through the filter pipeline without filtering. |
| Kitrinx Style | Averages neighboring RGB pixels, based on Kitrinx’s `cofi.sv` blend. |
| NTSC Light / Medium / Strong | Applies progressively stronger horizontal filters to luma and chroma. |
| PAL Light / Medium / Strong | Uses the corresponding luma response and mixes 75% of current-line chroma with 25% from the previous line. |
| PAL Strong+ | Uses the PAL Strong horizontal response and mixes current- and previous-line chroma evenly. |

The NTSC and PAL modes derive digital components from the core’s RGB pixels: `Y = (R + 2G + B) >> 2`, `Cr = R − Y`, and `Cb = B − Y`. They filter luma and chroma separately across neighboring pixels, then convert the result back to RGB. PAL modes average chroma between adjacent lines; they do not average luma vertically. Signed arithmetic and output clipping prevent chroma reconstruction from wrapping at RGB limits.

This is a digital luma/chroma bandwidth approximation. It does not encode or decode a composite waveform, model a color subcarrier, or reproduce effects such as dot crawl. The filtered RGB feeds both the Pocket display path and the Analogizer video input; the Analogizer interface is by [RndMnkIII](https://github.com/RndMnkIII). Composite Blend is separate from **Pseudo Transparency**.

The RGB blend style is adapted from [Kitrinx’s `cofi.sv`](https://github.com/opengateware/openFPGA-Genesis/blob/0032b2c6904131f11496396763a3d8b1a4a19445/src/fpga/core/rtl/cofi.sv), as used in [ericlewis’s Genesis Pocket core](https://github.com/ericlewis/openfpga-genesis). The current filter implementation passes its simulation and all seven core variants pass the reported build and constrained timing checks. Pocket hardware testing is pending.

## Installation

### Manual mode
Back up `Cores/agg23.SNES_experimental` first; installing this core replaces that folder. Preserve custom palettes and your preferred `video.json`.  
You can download the latest build from releases as a zip. Just copy its `Assets`, `Cores`, and `Platforms` folders into the root of your SD card, merging the folders. 
Finder on macOS replaces folders instead of merging them, so hold the alt-key while dragging-dropping them onto the sd-card and click "merge". 
Restore your backup to revert.

The core metadata requires Analogue OS 1.1 or later. Updaters may overwrite a manually installed core.

## Usage

Place ROMs in `/Assets/snes/common`. Both headered and unheadered ROMs are supported.

## Features

### Dock Support

The core supports four players/controllers through the Analogue Dock. Enable **Use Multitap** for four-player mode.

**Swap P1 & P2** exchanges the controllers driving the first and second SNES ports. It resets to off when the core is reloaded.

### Expansion Chips

The core supports the MiSTer expansion chips listed below:

* SA-1 (Super Mario RPG)
* Super FX/GSU-1/2 (Star Fox)
* DSP (Super Mario Kart)
* CX4 (Mega Man X 2)
* S-DD1 (Star Ocean)
* SPC7110 (Far East of Eden)
* ST1010 (F1 Roc 2)
* BSX (Satellaview)

Super Game Boy, ST011 (Hayazashi Nidan Morita Shougi), and ST018 (Hayazashi Nidan Morita Shougi 2) are not supported by the MiSTer core and therefore are not supported here. The MSU-1 homebrew expansion is also unsupported.

#### BSX

BSX ROMs must be patched to run without a BIOS. The BSX BIOS is not supported.

### Savestates/Memories/Sleep

Save states, Memories, and Sleep support regular carts and the DSP, Super FX/GSU, SA-1, and CX4 chips. They are not supported for S-DD1, SPC7110, or BSX games.

Sleep requires working save states. Pressing the Pocket power button while playing an unsupported cart can turn off the Pocket and lose the current game state.

### Video

* **Square Pixels** switches from the SNES’s 8:7 pixel aspect ratio to 1:1 for games designed around square pixels.
* **Pseudo Transparency** blends adjacent pixels to simulate transparency in some games.

### Turbo

* **CPU Turbo** increases the main SNES CPU speed and can affect compatibility. See the [MiSTer list of games](https://github.com/MiSTer-devel/SNES_MiSTer/blob/master/SNES_Turbo.md) for known behavior.
* **SuperFX Turbo** increases the GSU speed. It can be combined with CPU Turbo in games such as Star Fox.

### Controller Options

Choose Gamepad, Super Scope, Justifier, or Mouse under **Controller Options**.

### Lightguns

Most lightgun games use the Super Scope; Lethal Enforcers uses the Justifier. Move the crosshair with the D-pad or left stick. Press A to fire and B to reload. Adjust D-pad aim speed with **D-Pad Aim Speed**.

Stick aiming may only work when a controller is paired over Bluetooth rather than connected directly to the Analogue Dock by USB.

### SNES Mouse

Move the mouse with the D-pad or left stick. Press A and B for left and right clicks. Adjust D-pad movement speed with **D-Pad Aim Speed**. The Dock firmware does not currently support a USB mouse.

## License and packaging credits

The original [GPLv3 license](LICENSE) and upstream notices are retained. Packaging uses [agg23/pocketpublish](https://github.com/agg23/pocketpublish), with its OpenGateware contributors’ MIT notice preserved.
