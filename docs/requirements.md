# Fortemis: goals and requirements

Fortemis is a low-profile, wireless, split keyboard designed from scratch. It combines three boards
the owner already uses:

| Source board | What Fortemis takes from it |
|---|---|
| **Ferris Sweep** (Bling LP build by keebmaker) | Column layout: a tiny footprint and the steep column stagger, especially on the pinky |
| **TOTEM** by GEIST (and **Totemist**, ErgoMech's closed-source 36-key derivative) | Column splay angles only |
| **Forager** by carrefinho (sold by PandaKB) | Thumb-cluster placement and **everything else**: enclosed case, how the controller and battery are fitted, reset access, size, sturdiness, weight |

The name combines **For**ager, **Tem** (TOTEM/Totemist) and Ferr**is**.

This file records what the owner asked for. How each requirement is being met, and the decisions
behind that, are in [design-log.md](design-log.md).

## 1. Background

- The Ferris Sweep is the owner's favorite keyboard, because of its tiny footprint and the steep
  stagger on the pinky column.
- The owner's hands sweat a lot (hyperhidrosis). On the plateless Sweep, moisture has caused dead
  keys and switches keep falling out. The Forager's fully enclosed two-piece case has had neither
  problem: the top plate holds every switch in place, and the board is sealed in.
- The owner can easily press the Forager's reset button through a small print-in-place tab in the
  bottom case, and likes its size, sturdiness and light weight.
- The owner does not like the controller and battery arrangement on the Sweep or the TOTEM, or the
  loose wires visible on their current Sweep.
- The owner already has a few Seeed XIAO nRF52840 boards, the controller used in the Forager and
  TOTEM.
- All three of the owner's boards run ZMK with nearly the same keymap: QWERTY with home-row mods,
  and thumb keys Enter | Shift-Tab | NUM-Space | Backspace.

## 2. Tooling and deliverables

| ID | Requirement | Priority |
|---|---|---|
| T1 | Design the board with the free, open-source, beginner-friendly keyboard PCB tool from Ben Vallack's video. That tool is **Ergogen** ([video](https://www.youtube.com/watch?v=M_VuXVErD6E)). | MUST |
| T2 | Produce PCB design files (KiCad), case **STL** files, and everything else needed to build the board from scratch: fabrication outputs, parts list, firmware and build instructions. | MUST |
| T3 | Keep everything in this repository. | MUST |
| T4 | Write down the goals and requirements (this file), and keep a running record of the design process as work goes on ([design-log.md](design-log.md)). | MUST |

## 3. Layout

| ID | Requirement | Priority |
|---|---|---|
| L1 | **Column stagger** is the same as the Ferris Sweep's. | MUST |
| L1b | Make the stagger of the **4th and 5th columns** 10–20 % steeper, without straying far from the Sweep. | BONUS |
| L2 | **Column splay** uses the TOTEM's horizontal splay angles for each column, and nothing else. The stagger still follows L1. Owner's description: "barely perceptible between the first/second/third columns, getting wider toward the pinky column". | MUST |
| L3 | **Thumb cluster** has the same position (distance and angle) relative to the rest of the keyboard as the Forager's. | MUST |
| L4 | 34 keys: 3×5 plus 2 thumbs per half. Adding a 3rd thumb key per half (36 keys) is a bonus, but only if it doesn't enlarge the footprint or add PCB requirements. "Don't sweat it." | MUST (34) / BONUS (36) |
| L5 | Keys are as close together as **Choc keycaps** allow (Choc spacing). Fitting MX keycaps is not a goal. | MUST |

## 4. Electronics

| ID | Requirement | Priority |
|---|---|---|
| E1 | The controller is a **Seeed XIAO nRF52840**, like the Forager and TOTEM. It may be soldered straight to the PCB; no socket is needed. | SHOULD (preference) |
| E2 | **Wireless**, with a battery in each half. Copy how the Forager fits its XIAO and battery. | MUST |
| E3 | **Hot-swap sockets** for Kailh **Choc v1** switches. | MUST |
| E3b | Also accept **Choc v2** switches, as the Toucan2 does. | BONUS (big) |
| E4 | **Diodeless** like the Sweep is strongly wanted. If only a nice!nano can do diodeless, and only at 34 keys, use the nice!nano with 2 thumb keys per half. The exception is if that would break the Forager case's physical dimensions, which take priority. | SHOULD (strong) |
| E5 | A **power switch** and a **reset switch** on **each half**. The power switch must not be tiny like the Sweep's. TOTEM-sized switches are acceptable. | MUST |

## 5. Case and looks

| ID | Requirement | Priority |
|---|---|---|
| C1 | The case and everything else follow the **Forager**: a fully enclosed two-piece case, a top plate that holds the switches, reset access through a tab in the bottom case, the same size class, sturdy and light. | MUST (top priority) |
| C2 | No loose wires visible from outside. Everything sits inside the case, as on the Forager. | MUST |
| C3 | If the PCB makes any Forager feature impossible, **stop and tell the owner** so they can decide. | MUST (process) |

## 6. How ambiguous points were read

These readings were made without asking the owner. Each one is a single setting in the design, so
it is easy to change.

1. **"4th and 5th column" means the ring and pinky columns.** The owner numbered the TOTEM's columns
   from the inner side ("first/second/third … toward the pinky"). Counting that way also matches
   finger numbering (ring = 4, pinky = 5) and the owner's liking for a steep pinky stagger.
2. **Totemist splay means TOTEM splay.** Totemist has no public hardware files, and the owner said
   to use TOTEM. TOTEM's PCB has the inner, index and middle columns exactly parallel (0°), the
   ring column at 4° and the pinky column at 10°. The "barely perceptible" angle the owner sees is
   the ring column's 4°.
3. **Forager power switch.** The Forager has no power switch. It relies on ZMK's sleep mode, and its
   reset is the XIAO's own button pressed through the case lever. E5 is met by adding a power
   switch that is large enough to use with a finger, and by keeping the Forager's reset lever.
4. **Thumb position relative to the keyboard** is measured from the bottom key of the inner index
   column, the nearest key. That keeps the same gap and angle between the thumbs and the main keys
   as on the Forager.

## 7. Acceptance criteria

- The Ergogen config in `ergogen/` regenerates the layout, outlines and PCB.
- Layout: stagger matches the Sweep, with L1b applied to ring and pinky. Column angles are
  0/0/0/4/10° from the inner column outward. Thumbs sit relative to the inner column exactly as on
  the Forager. No Choc keycaps (17.5 × 16.5 mm) overlap.
- PCB: routed, passes KiCad DRC with no errors, and has Gerber, drill, BOM and placement outputs
  ready for ordering. Choc v1 hot-swap is required and v2 is supported if possible. Diodeless if
  possible. Power switch on each half. Reset reachable as on the Forager.
- Case: two-piece enclosed STL per half (top plate and base), built to the Forager's dimensions
  (8.4 mm stack, 2.2 mm top plate, 6.2 mm base). It includes the USB-C opening, reset lever, LED
  light pipe, power-switch opening and screw bosses, with no wires showing.
- Docs: parts list with links, build guide, and firmware (ZMK shield) for the chosen controller.
