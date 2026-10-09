// Copyright (c) 2026 Colin Creasman
//
// SPDX-License-Identifier: MIT
//
// Description:
//  Solder pads for a small LiPo pouch cell (301230: 30 x 12 x 3 mm) that lies on the case floor
//  under the PCB, as on the Forager: the back silkscreen shows where the cell goes, and its two
//  wires are trimmed to reach two pads next to it.
//
//  The area the cell may take (length x width, the cell plus its size tolerance) is drawn on the
//  back silkscreen and the nominal cell on B.Fab. The pads go wherever there is room, given in the
//  footprint's local frame (KiCad, y down, cell centre at the origin, length along x).
//  On mirrored (right-half) points every x is flipped, so the right half is the left's mirror image.
//
// Params:
//    length, width: area for the cell (mm)
//    cell_length, cell_width, cell_thickness: nominal cell (mm), drawn on B.Fab and in the label
//    pos_x, pos_y, neg_x, neg_y: pad centres (mm, local frame of the left half)
//    pad_size: pad size (mm). + is square and marked on the silkscreen, - is round.
//    pos, neg: nets

module.exports = {
  params: {
    designator: 'BT',
    length: 31,
    width: 12.5,
    cell_length: 30,
    cell_width: 12,
    cell_thickness: 3,
    pos_x: -17.5,
    pos_y: -2,
    neg_x: -17.5,
    neg_y: 2,
    pad_size: 2,
    pos: { type: 'net', value: 'BAT_RAW' },
    neg: { type: 'net', value: 'GND' },
  },
  body: p => {
    const s = p.point.meta.mirrored ? -1 : 1
    const rect = (l, w, layer, width) => `
    (fp_rect (start ${-l / 2} ${-w / 2}) (end ${l / 2} ${w / 2}) (stroke (width ${width}) (type solid)) (fill none) (layer "${layer}"))`
    const pad = (name, x, y, shape, net) => `
    (pad "${name}" smd ${shape} (at ${s * x} ${y} ${p.r}) (size ${p.pad_size} ${p.pad_size}) (layers "B.Cu" "B.Mask") ${net})`
    // "+" beside the + pad, on its side away from the cell (as on the Forager, only + is marked)
    const label = (text, x, y) => `
    (fp_text user "${text}" (at ${s * (x + Math.sign(x) * (p.pad_size / 2 + 0.9))} ${y} ${p.r}) (layer "B.SilkS")
      (effects (font (size 1 1) (thickness 0.15)) (justify mirror)))`
    return `
  (footprint "fortemis:battery_lipo_pads"
    (layer "B.Cu")
    ${p.at}
    (property "Reference" "${p.ref}" (at 0 ${p.width / 2 - 1.5} ${p.r}) (layer "B.SilkS") ${p.ref_hide}
      (effects (font (size 1 1) (thickness 0.15)) (justify mirror)))
    (property "Value" "LiPo ${p.cell_thickness}0${p.cell_width}${p.cell_length}" (at 0 1.5 ${p.r}) (layer "B.Fab")
      (effects (font (size 1 1) (thickness 0.15)) (justify mirror)))
    (fp_text user "LiPo ${p.cell_length}x${p.cell_width}x${p.cell_thickness}" (at 0 0 ${p.r}) (layer "B.SilkS")
      (effects (font (size 1 1) (thickness 0.15)) (justify mirror)))
    (attr smd)
    ${rect(p.length, p.width, 'B.SilkS', 0.12)}
    ${rect(p.cell_length, p.cell_width, 'B.Fab', 0.1)}
    ${pad('1', p.pos_x, p.pos_y, 'rect', p.pos.str)}
    ${pad('2', p.neg_x, p.neg_y, 'circle', p.neg.str)}
    ${label('+', p.pos_x, p.pos_y)}
  )
  `
  }
}
