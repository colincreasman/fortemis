// Copyright (c) 2026 Colin Creasman
//
// SPDX-License-Identifier: MIT
//
// Description:
//  M2 surface-mount nut (Würth/PEM style SMTSO2020MTJ, 2.0 mm long), soldered on the back of the
//  PCB. The case screws into it from the top plate and from the base, like on the Forager.
//  Same land as the Forager's Nuts_SMD:SMTSO2020MTJ_M2: plated 3.8 mm hole, 6.2 mm pad.

module.exports = {
  params: {
    designator: 'NUT',
    pad: 6.2,
    drill: 3.8,
  },
  body: p => `
  (footprint "fortemis:nut_smd_m2"
    (layer "B.Cu")
    ${p.at}
    (property "Reference" "${p.ref}" (at 0 ${p.pad / 2 + 1} ${p.r}) (layer "B.SilkS") ${p.ref_hide}
      (effects (font (size 1 1) (thickness 0.15)) (justify mirror)))
    (property "Value" "SMTSO2020MTJ" (at 0 0 ${p.r}) (layer "B.Fab")
      (effects (font (size 0.6 0.6) (thickness 0.1)) (justify mirror)))
    (attr smd)
    (fp_circle (center 0 0) (end ${p.pad / 2 + 0.25} 0) (stroke (width 0.05) (type solid)) (fill none) (layer "B.CrtYd"))
    (fp_circle (center 0 0) (end ${p.pad / 2 + 0.25} 0) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
    (fp_circle (center 0 0) (end ${p.pad / 2} 0) (stroke (width 0.1) (type solid)) (fill none) (layer "B.Fab"))
    (pad "" thru_hole circle (at 0 0 ${p.r}) (size ${p.pad} ${p.pad}) (drill ${p.drill}) (layers "*.Cu" "*.Mask"))
  )
  `
}
