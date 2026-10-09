# Fortemis build guide

How to build a Fortemis from the files in this repository: parts, ordering the PCBs, soldering,
firmware and the case. Fortemis is built the same way as the Forager, so this guide follows the
Forager's [build guide](https://github.com/carrefinho/forager/blob/main/docs/build-guide.md). The
reasons behind each part are in [design-log.md](design-log.md).

> **Not built yet.** No Fortemis has been built, so nothing here has been tried on real hardware.

## Parts

Counts are for the whole keyboard (both halves).

### Electronics

| Part | Count | Where to buy | Notes |
|---|---|---|---|
| Fortemis PCB, left and right | 1 of each | Any PCB maker, such as JLCPCB ([below](#ordering-the-pcbs)) | `pcb/fab/fortemis_left.zip` and `pcb/fab/fortemis_right.zip` |
| Seeed Studio XIAO nRF52840 **Plus** | 2 | [Seeed Studio](https://www.seeedstudio.com/Seeed-Studio-XIAO-nRF52840-Plus-p-6359.html) | Must be the **Plus**. The regular XIAO nRF52840 and its Sense version, which the Forager uses, have too few pads to wire 18 keys without diodes. The XIAO nRF52840 Sense Plus has the same pads but is untested. |
| Kailh Choc hot-swap socket (CPG135001S30) | 36 | [LCSC C5333465](https://www.lcsc.com/product-detail/C5333465.html), [Typeractive](https://typeractive.xyz/products/hotswap-sockets) (Choc, packs of 10), [lowprokb.ca](https://lowprokb.ca/products/kalih-choc-hot-swap-sockets) | 18 per half |
| M2 SMD nut, 2 mm long (SMTSO2020MTJ) | 10 | [LCSC C2916384](https://www.lcsc.com/product-detail/C2916384.html) | 5 per half. The case screws into them. |
| SPDT slide switch (MSK12C02) | 2 | [LCSC C431540](https://www.lcsc.com/product-detail/C431540.html) | The power switches. The Ferris Sweep's K3-1296S-E1 and the C&K PCM12SMTR fit too. |
| LiPo battery, 301230 (30 × 12 × 3 mm, about 110 mAh), without a connector | 2 | [Typeractive](https://typeractive.xyz/products/lithium-battery-110mah) ("No Connector") | **No thicker than 3 mm**: the 401230 that the Forager also takes doesn't fit. The wires are soldered to the PCB. |

### Switches and keycaps

| Part | Count | Where to buy | Notes |
|---|---|---|---|
| Kailh Choc v1 switches | 36 | [Typeractive](https://typeractive.xyz/products/choc-switches), [lowprokb.ca](https://lowprokb.ca/products/kailh-choc-low-profile-switches) | Any type. Choc v2 switches fit the PCB, but how they fit the top plate is untested. |
| Choc keycaps, 1u | 36 | [MBK at Typeractive](https://typeractive.xyz/products/mbk-keycaps), [DDC at lowprokb.ca](https://lowprokb.ca/products/ddc-choc-pbt-blank-keycaps) | Choc-spaced keycaps (17.5 × 16.5 mm). Keycaps made for MX spacing are too big. All 36 are 1u, thumbs included: there's no room for 1.5u. |

### Case

| Part | Count | Where to buy | Notes |
|---|---|---|---|
| 3D-printed case parts | 4 | `case/` | A top plate and a base for each half ([printing](#printing-the-case)) |
| M2 countersunk (flat head) screws, **4 mm** long | 18 | [McMaster-Carr 91294A002](https://www.mcmaster.com/91294A002/) | 9 per half. Not 5 mm: a screw from the top and one from the bottom meet in each nut. |
| Rubber bumpers | 8 or more | [McMaster-Carr 95495K18](https://www.mcmaster.com/95495K18/) | Anything that isn't too thick |
| Clear 1.75 mm 3D-printer filament | 2 pieces, 6 mm long | | Light pipes for the XIAO's LED |

### Optional

| Part | Count | Where to buy | Notes |
|---|---|---|---|
| PandaKB ZMK dongle | 1 | [PandaKB](https://pandakb.com/shop/keyboard-kit/pandakb-zmk-split-keyboard-dongle/) | For [dongle mode](../README.md#dongle-mode-pandakb-usb-dongle) |

The Forager's magnetic tenting legs are left out of this case.

### Tools

A soldering iron with a fine tip, thin solder, flux, tweezers, a multimeter, flush cutters, an FDM
3D printer, and a hex key or screwdriver that fits the screws.

## Ordering the PCBs

The halves are separate boards, so order each zip as its own design. At JLCPCB, upload the zip and
set:

| Setting | Value |
|---|---|
| Layers | 2 |
| PCB thickness | 1.6 mm. The case is built around it. |
| Size | Read from the zip: 145.5 × 119.7 mm |
| Colour, surface finish | Any |
| Quantity | The minimum (5 at JLCPCB). One of each half is needed. |

After changing the PCBs, rebuild the files with `python3 ergogen/tools/pcb.py fab`.

### Optional: PCB assembly

`pcb.py fab` also writes JLCPCB's assembly files for each half: `pcb/fab/fortemis_<half>_bom.csv`
lists the parts with their LCSC numbers, and `pcb/fab/fortemis_<half>_cpl.csv` says where each one
goes. They cover the sockets, nuts and power switch. You solder the XIAO and the battery yourself.

- Every part is on the back of the board, so choose assembly on the **bottom side**.
- Check every part in JLCPCB's placement preview, especially the sockets and the power switch. The
  files use KiCad's positions and angles, and JLCPCB's part models don't always share KiCad's zero
  angle. Rotate any part that sits wrong.
- LCSC had no Choc sockets (C5333465) in stock on 2026-10-08. If JLCPCB has none either, leave them
  out and solder them by hand: they're the easiest parts.

## Soldering

Every part goes on the back of the PCB, the side with the XIAO's pin names. The front only has
two labels, BAT+ and PWR. Build both halves the same way. This guide assumes a soldering iron; a
hot plate or hot air with solder paste works too.

### 1. XIAO nRF52840 Plus

The XIAO is soldered straight to the PCB, without pin headers or a socket. It lies flat on the back
of the PCB, its own flat underside against the board, with its components facing you and its USB-C
port at the board edge. On the right half it is turned around, not flipped: the pin names on the
PCB show where each pad goes.

1. Check the XIAO against the pin names on the PCB before soldering anything. Once soldered, it
   covers them.
2. Hold it flat and lined up with the pads, and solder two pads at opposite corners. Check that it
   is still flat and lined up, then solder the rest. Keep it pressed flat: the case leaves little
   room around it.
3. The Plus's extra pads are only 1.27 mm apart. Use flux, and check each pad against its
   neighbours for solder bridges, with a magnifier or a multimeter.
4. Turn the board over. The plated hole marked BAT+ sits under the XIAO's BAT+ pad. Feed solder into
   the hole until it bonds to the pad; holding the iron's tip in the hole helps. Keep the joint flat:
   the top plate has only a 0.6 mm pocket above it.

### 2. Power switch

The MSK12C02 goes on the back of the tab on the outer edge, its lever pointing out past the edge
and its two plastic pegs in the two small holes. Solder the two large side pads first, then the
three pins. One of the four small pads stays empty.

The middle pin has a pad at both of its possible positions, so the switch works either way round.
That only changes which way is ON: you'll find out when the battery is connected (step 5).

### 3. Hot-swap sockets

Place each socket so its two round cups sit over the switch's two pin holes; it only lines up one
way. Tin one pad, slide the socket into place while reheating it, then solder the other pad.

### 4. Nuts

Push the five nuts into their holes from the back. They must be fully seated, sticking out on the
back like everything else. Solder around each one's edge (use flux: they take a lot of heat), then
peel off the protective tape.

### 5. Firmware, test and battery

Flash and test each half over USB before soldering the battery and closing the case. The README's
[Firmware](../README.md#firmware) section explains where the `.uf2` files come from and which one
goes where.

1. Plug a half into a computer and double-press the reset button on the XIAO. It shows up as a USB
   drive, usually named `XIAO-SENSE`. If the XIAO has run ZMK before, copy the settings reset onto
   it first and repeat this step.
2. Copy the half's firmware onto the drive. On its first start, the half restarts once by itself to
   free its NFC pins for keys.
3. Test every key. Plug the left half into the computer, and power the right half from any USB
   charger: it connects to the left half by Bluetooth. Touch each socket's two metal tabs together
   with tweezers, and check that the key types in a key tester. The keymap is in
   `boards/shields/fortemis/fortemis.keymap`.
4. Unplug the half. Trim the battery's wires so that they reach the two pads next to the battery's
   outline (`LiPo 30x12x3`) with the cell inside it. Cut and solder one wire at a time, so the bare
   ends never touch: red to the square pad marked +, black to the other.
5. Slide the power switch both ways. The XIAO's LED shows the battery level when the half turns on,
   which tells you which way is ON.

The power switch sits between the battery and the XIAO, so the battery only charges over USB while
the switch is ON. The firmware doesn't deep-sleep: turn a half off with the switch when not in use.

## Printing the case

Print the four STL files in `case/` with an FDM printer, the way they're oriented: the base floor
down and the top plate's top face up. No supports are needed: apart from the lowest 0.6 mm of the
base's rounded bottom edge, nothing overhangs by more than 45° except a few short bridges.

The reset lever in each base's floor is printed in place. As the Forager's guide warns, too much
first-layer squish can fuse it to the floor; adjust the z-offset if it is stuck.

## Fitting the case

1. Cut two 6 mm pieces of clear 1.75 mm filament. From inside each base, push one into the hole at
   the USB-C end until it is flush with the outside. A small tool such as a hex key helps.
2. Put the top plate on the front of the PCB. Press a few switches through the plate into the
   sockets near the corners to line it up, then fit the four top screws. There is no top screw at
   the thumb nut.
3. Turn the half over and lay the battery on its outline.
4. Fit the base, USB-C end first so that the port slides into its slot. The power switch's lever
   comes out through the notch in the wall. Hold the plate and base together along the edges so
   they line up, and fit the five bottom screws.
5. Press in the rest of the switches, fit the keycaps, and stick the bumpers on the bottom.

To reach the bootloader once the case is closed, double-press the lever in the floor next to the
USB-C port.

## Licenses

The switch footprint, `ergogen/footprints/ceoloide/switch_choc_v1_v2.js` from
[ceoloide/ergogen-footprints](https://github.com/ceoloide/ergogen-footprints), is licensed
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), which forbids commercial use.
Both PCBs include it, so build them for yourself but don't sell them. The Fortemis footprints in
`ergogen/footprints/fortemis/` are MIT.
