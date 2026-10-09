// Copyright (c) 2026 Colin Creasman
//
// SPDX-License-Identifier: MIT
//
// Description:
//  Seeed Studio XIAO nRF52840 Plus, soldered flat and face down on the back of the PCB, the way
//  the Forager mounts its regular XIAO. The module's flat underside lies on the PCB's back copper;
//  its USB-C socket, reset button and LEDs face the case floor.
//
//  Pad positions come from Seeed's KiCad files for the Plus
//  (Seeed_Studio_XIAO_nRF52840_v1.1, Plus variant): 14 castellations at the regular XIAO positions
//  plus 9 extra castellations 1.27 mm between them. The PCB pads stick out 1.5 mm past the module
//  edge, so every castellation can be soldered from the edge with an iron.
//
//  D16 (P0.31) is wired to the module's battery-voltage divider, so it gets no pad.
//
//  The module's BAT+ pad sits on its underside. The footprint puts a plated hole under it, so it
//  is soldered from the front by feeding solder into the hole. Battery - does not need the module's
//  BAT- pad: it is the same net as the GND castellation.
//
//  Local frame (KiCad, y down, as seen from the front of the PCB): USB-C end at -x, antenna end
//  at +x, D0..D6 edge at -y, D7..VBUS edge at +y.
//
// Params:
//    rotate_mirrored: default true
//      adds 180 degrees on mirrored (right-half) points. The module is not mirrored, only turned,
//      so it stays face down and its USB-C end still points out of the board.
//    antenna_keepout: default true
//      no copper pour from the antenna end to 4.5 mm past it (as on the Forager), and no tracks or
//      vias right behind the module's antenna end.
//    via_keepout: default true
//      no vias under the module's bare underside pads (SWD/reset test pads, BAT+/BAT-). Other vias
//      under the module are tented, as on the Forager.
//    show_labels: default true
//      pin names on the back silkscreen, just inside the pad ends (0.8 mm, JLC minimum). The module
//      covers them once soldered; they are there to check orientation and pins before that.
//    D0..D15, D17..D19, V3V3, GND, VBUS, BAT_P: nets.

module.exports = {
  params: {
    designator: 'MCU',
    rotate_mirrored: true,
    antenna_keepout: true,
    via_keepout: true,
    show_labels: true,
    D0: { type: 'net', value: 'D0' },
    D1: { type: 'net', value: 'D1' },
    D2: { type: 'net', value: 'D2' },
    D3: { type: 'net', value: 'D3' },
    D4: { type: 'net', value: 'D4' },
    D5: { type: 'net', value: 'D5' },
    D6: { type: 'net', value: 'D6' },
    D7: { type: 'net', value: 'D7' },
    D8: { type: 'net', value: 'D8' },
    D9: { type: 'net', value: 'D9' },
    D10: { type: 'net', value: 'D10' },
    D11: { type: 'net', value: 'D11' },
    D12: { type: 'net', value: 'D12' },
    D13: { type: 'net', value: 'D13' },
    D14: { type: 'net', value: 'D14' },
    D15: { type: 'net', value: 'D15' },
    D17: { type: 'net', value: 'D17' },
    D18: { type: 'net', value: 'D18' },
    D19: { type: 'net', value: 'D19' },
    V3V3: { type: 'net', value: '3V3' },
    GND: { type: 'net', value: 'GND' },
    VBUS: { type: 'net', value: 'VBUS' },
    BAT_P: { type: 'net', value: 'BAT_P' },
  },
  body: p => {
    const rot = p.r + (p.rotate_mirrored && p.point.meta.mirrored ? 180 : 0)
    const rad = rot * Math.PI / 180
    const r4 = v => Math.round(v * 10000) / 10000
    // local footprint coordinates -> absolute board coordinates (for zones)
    const abs = (x, y) => `(xy ${r4(p.x + x * Math.cos(rad) + y * Math.sin(rad))} ${r4(p.y - x * Math.sin(rad) + y * Math.cos(rad))})`

    const HALF_L = 10.48   // module is 20.96 long (USB to antenna)
    const EDGE = 8.89      // and 17.78 wide (castellated edges)
    const OUT = 1.5        // pad reach past the module edge
    const PAD_W = 0.85
    const MAIN_IN = 1.016  // Seeed land pattern: regular pads reach 1.016 under the module
    const EXTRA_IN = 0.216 // and the extra (Plus) pads 0.216

    // [pad name, net param, local x, edge (-1 = D0..D6 edge, +1 = D7..VBUS edge), extra pad?]
    const pins = [
      ['D0', 'D0', -7.62, -1, false],
      ['D11', 'D11', -6.35, -1, true],
      ['D1', 'D1', -5.08, -1, false],
      ['D12', 'D12', -3.81, -1, true],
      ['D2', 'D2', -2.54, -1, false],
      ['D13', 'D13', -1.27, -1, true],
      ['D3', 'D3', 0, -1, false],
      ['D14', 'D14', 1.27, -1, true],
      ['D4', 'D4', 2.54, -1, false],
      ['D15', 'D15', 3.81, -1, true],
      ['D5', 'D5', 5.08, -1, false],
      ['D6', 'D6', 7.62, -1, false],
      ['5V', 'VBUS', -7.62, 1, false],
      ['GND', 'GND', -5.08, 1, false],
      ['3V3', 'V3V3', -2.54, 1, false],
      ['D10', 'D10', 0, 1, false],
      ['D19', 'D19', 1.27, 1, true],
      ['D9', 'D9', 2.54, 1, false],
      ['D18', 'D18', 3.81, 1, true],
      ['D8', 'D8', 5.08, 1, false],
      ['D17', 'D17', 6.35, 1, true],
      ['D7', 'D7', 7.62, 1, false],
    ]

    let pads = ''
    let labels = ''
    for (const [name, net, x, side, extra] of pins) {
      const inner = extra ? EXTRA_IN : MAIN_IN
      const len = inner + OUT
      const y = side * (EDGE - inner + len / 2)
      pads += `
    (pad "${name}" smd roundrect (at ${x} ${r4(y)} ${rot}) (size ${PAD_W} ${r4(len)}) (layers "B.Cu" "B.Paste" "B.Mask") (roundrect_rratio 0.25) ${p[net].str})`
      if (p.show_labels) {
        // inside the module outline, running inward from just past the pad ends: there is no room
        // outside the pads at the board edge
        const ly = side * (EDGE - MAIN_IN - 0.3)
        labels += `
    (fp_text user "${name}" (at ${x} ${r4(ly)} ${rot + 90}) (layer "B.SilkS")
      (effects (font (size 0.8 0.8) (thickness 0.15)) (justify ${side < 0 ? 'right' : 'left'} mirror)))`
      }
    }

    // BAT+ is on the module's underside: plated hole under it, soldered from the front
    pads += `
    (pad "BAT+" thru_hole circle (at 5.035 -0.992 ${rot}) (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask") ${p.BAT_P.str})`

    const outline = (layer, w) => `
    (fp_rect (start ${-HALF_L} ${-EDGE}) (end ${HALF_L} ${EDGE}) (stroke (width ${w}) (type solid)) (fill none) (layer "${layer}"))`

    const zone = (name, layers, rules, pts) => `
  (zone (net 0) (net_name "") (layers "${layers}") (name "${name}") (hatch edge 0.5)
    (connect_pads (clearance 0)) (min_thickness 0.25) (filled_areas_thickness no)
    (keepout ${rules})
    (fill (thermal_gap 0.5) (thermal_bridge_width 0.5))
    (polygon (pts ${pts.map(([x, y]) => abs(x, y)).join(' ')})))`

    const rect = (x0, y0, x1, y1) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

    let zones = ''
    if (p.antenna_keepout) {
      // no copper at all right behind the antenna; around it only no pour, as on the Forager
      zones += zone(`${p.ref} behind antenna`, 'F&B.Cu',
        '(tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed)',
        rect(8.3, -8.4, HALF_L + 0.5, 8.4))
      zones += zone(`${p.ref} around antenna`, 'F&B.Cu',
        '(tracks allowed) (vias allowed) (pads allowed) (copperpour not_allowed) (footprints allowed)',
        rect(8.3, -10.5, 15, 10.5))
    }
    if (p.via_keepout) {
      // tented vias under the module are fine (Forager does it), but not under its bare pads
      const no_vias = '(tracks allowed) (vias not_allowed) (pads allowed) (copperpour allowed) (footprints allowed)'
      zones += zone(`${p.ref} no vias at test pads`, 'F&B.Cu', no_vias, rect(-9.45, -2.15, -5.15, 2.15))
      zones += zone(`${p.ref} no vias at battery pads`, 'F&B.Cu', no_vias, rect(3.7, -1.8, 6.35, 1.8))
    }

    return `
  (footprint "fortemis:mcu_xiao_nrf52840_plus"
    (layer "B.Cu")
    (at ${p.x} ${p.y} ${rot})
    (property "Reference" "${p.ref}" (at 0 0 ${rot}) (layer "B.SilkS") ${p.ref_hide}
      (effects (font (size 1 1) (thickness 0.15)) (justify mirror)))
    (property "Value" "XIAO nRF52840 Plus" (at 0 2 ${rot}) (layer "B.Fab")
      (effects (font (size 1 1) (thickness 0.15)) (justify mirror)))
    (attr smd)
    ${outline('B.Fab', 0.1)}
    ${outline('F.Fab', 0.1)}
    (fp_rect (start ${-HALF_L - 0.25} ${-EDGE - OUT - 0.25}) (end ${HALF_L + 0.25} ${EDGE + OUT + 0.25})
      (stroke (width 0.05) (type solid)) (fill none) (layer "B.CrtYd"))
    (fp_line (start ${HALF_L + 0.25} -7.6) (end ${HALF_L + 0.25} 7.6) (stroke (width 0.15) (type solid)) (layer "B.SilkS"))
    (fp_text user "USB" (at ${-HALF_L + 1.6} 0 ${rot + 90}) (layer "B.Fab")
      (effects (font (size 1 1) (thickness 0.15)) (justify mirror)))
    (fp_text user "XIAO Plus, face down on back" (at 0 0 ${rot}) (layer "F.Fab")
      (effects (font (size 1 1) (thickness 0.15))))
    (fp_text user "BAT+" (at 5.035 -2.6 ${rot}) (layer "F.SilkS")
      (effects (font (size 0.8 0.8) (thickness 0.12))))
    ${labels}
    ${pads}
  )
  ${zones}
    `
  }
}
