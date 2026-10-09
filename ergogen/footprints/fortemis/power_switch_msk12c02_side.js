// Copyright (c) 2026 Colin Creasman
//
// SPDX-License-Identifier: MIT
//
// Description:
//  Side-actuated SPDT slide switch (Shou Han MSK12C02, the TOTEM's power switch) soldered under
//  the PCB at a board edge, lever pointing out of the board. Also fits the Korean Hroparts
//  K3-1296S-E1 (Ferris Sweep) and C&K PCM12SMTR, which share the same 3-pin pattern.
//
//  Those parts have asymmetric pins (3.0 mm then 1.5 mm apart), and a part soldered on the back is
//  seen mirrored from the front. To make the footprint impossible to get wrong, the common (middle)
//  pin has a pad at both possible positions. Either way round, the common pin lands on a `from` pad
//  and one outer pin lands on the `to` pad; only the ON direction of the lever changes.
//
//  Local frame (KiCad, y down): the switch's front face (lever side) is at y = 0 and the lever
//  points toward -y, which is the point's "up" direction in Ergogen. The board edge must be at
//  y = -edge_gap, so the shell pads keep 0.3 mm from it (PCB maker's minimum).
//
// Params:
//    from: net of the common pin (battery +)
//    to: net of the switched pin (to the controller's BAT+)

module.exports = {
  params: {
    designator: 'PWR',
    edge_gap: 0.35,
    from: { type: 'net', value: 'BAT_RAW' },
    to: { type: 'net', value: 'BAT_P' },
  },
  body: p => {
    const r = p.r
    const pad = (name, x, y, w, h, net) =>
      `(pad "${name}" smd roundrect (at ${x} ${y} ${r}) (size ${w} ${h}) (layers "B.Cu" "B.Paste" "B.Mask") (roundrect_rratio 0.15) ${net})`
    const line = (x0, y0, x1, y1, layer, w = 0.12) =>
      `(fp_line (start ${x0} ${y0}) (end ${x1} ${y1}) (stroke (width ${w}) (type solid)) (layer "${layer}"))`

    // pins: 0.8 wide, from 2.28 to 4.05 behind the front face (covers MSK12C02 and PCM12SMTR)
    const PIN_Y = 3.165
    const PIN_H = 1.77
    return `
  (footprint "fortemis:power_switch_msk12c02_side"
    (layer "B.Cu")
    ${p.at}
    (property "Reference" "${p.ref}" (at 0 5.4 ${r}) (layer "B.SilkS") ${p.ref_hide}
      (effects (font (size 1 1) (thickness 0.15)) (justify mirror)))
    (property "Value" "MSK12C02" (at 0 5.4 ${r}) (layer "B.Fab")
      (effects (font (size 1 1) (thickness 0.15)) (justify mirror)))
    (attr smd)
    ${pad('1', -2.25, PIN_Y, 0.8, PIN_H, p.to.str)}
    ${pad('2', -0.75, PIN_Y, 0.8, PIN_H, p.from.str)}
    ${pad('2', 0.75, PIN_Y, 0.8, PIN_H, p.from.str)}
    ${pad('3', 2.25, PIN_Y, 0.8, PIN_H, '')}
    ${pad('', -3.85, 1.45, 1.5, 3.0, '')}
    ${pad('', 3.85, 1.45, 1.5, 3.0, '')}
    (pad "" np_thru_hole circle (at -1.5 1.42 ${r}) (size 1.1 1.1) (drill 1.1) (layers "*.Cu" "*.Mask"))
    (pad "" np_thru_hole circle (at 1.5 1.42 ${r}) (size 1.1 1.1) (drill 1.1) (layers "*.Cu" "*.Mask"))
    (fp_rect (start -3.35 0) (end 3.35 2.8) (stroke (width 0.1) (type solid)) (fill none) (layer "B.Fab"))
    (fp_rect (start -0.75 -1.45) (end 0.75 0) (stroke (width 0.1) (type solid)) (fill none) (layer "B.Fab"))
    ${line(-4.8, -p.edge_gap, 4.8, -p.edge_gap, 'B.Fab', 0.05)}
    ${line(-2.9, 2.9, -2.75, 2.9, 'B.SilkS')}
    ${line(2.75, 2.9, 2.9, 2.9, 'B.SilkS')}
    (fp_text user "PWR" (at 0 -1.2 ${r}) (layer "F.SilkS")
      (effects (font (size 0.8 0.8) (thickness 0.12))))
    (fp_rect (start -4.85 ${-p.edge_gap}) (end 4.85 4.3) (stroke (width 0.05) (type solid)) (fill none) (layer "B.CrtYd"))
  )
    `
  }
}
