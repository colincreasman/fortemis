# ZMK Cheat Sheet
## Key Codes
### [All Codes](https://zmk.dev/docs/codes)
Each key's codes are above page.

### [Modifiers Functions](https://zmk.dev/docs/codes/modifiers)

`xx(code)` adds modifier key to the `code`.
They can be comined. `&kp LC(RA(B))` = <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>b</kbd>.

Modifier functions

- `LS(code)` : Left Shift
- `RS(code)` : Right Shift
- `LC(code)` : Left Control
- `RC(code)` : Right Control
- `LA(code)` : Left Alt
- `RA(code)` : Right Alt
- `LG(code)` : Left GUI (Windows / Command / Meta)
- `RG(code)` : Right GUI (Windows / Command / Meta)

## Behaviors

### [Key Press Behaviors](https://zmk.dev/docs/behaviors/key-press)
```c
&kp key
```
press the `key`.

### [Momentary layer](https://zmk.dev/docs/behaviors/layers#momentary-layer)
```c
&mo layer
```
momentary activate specified `layer`.

### [To Layer](https://zmk.dev/docs/behaviors/layers#to-layer)
```c
&to layer
```
Enable the `layer` and the default layer, and disable all other layers. (maybe it for &trans behavior).

### [Toggle Layer](https://zmk.dev/docs/behaviors/layers#toggle-layer)
```c
&tog layer
```
Enable the `layer` until the `layer` is disabled.

### [Key Toggle Behavior](https://zmk.dev/docs/behaviors/key-toggle)
```c
&kt key
```
toggle the `key` hold or released.

### [Sticky Key Behavior](https://zmk.dev/docs/behaviors/sticky-key)
```c
&sk key
```
Stick the `key` till next key pressed.

### [Sticky Layer Behavior](https://zmk.dev/docs/behaviors/sticky-layer)
```c
&sl layer
```
Stick the `layer` till next key pressed.

The devicetree document is [here](https://zmk.dev/docs/config/behaviors#sticky-key).

### [Transparent](https://zmk.dev/docs/behaviors/misc#transparent)
```c
&trans
```
Pass down to the next active layer in the stack.

### [None](https://zmk.dev/docs/behaviors/misc#none)
```c
&none
```
No behavior.

### [Caps Word Behavior](https://zmk.dev/docs/behaviors/caps-word)
```c
&caps_word
```
Capitalize till stop key pressed. stop key is not alphabet and `continue-list`.

The devicetree document is [here](https://zmk.dev/docs/config/behaviors#caps-word).

### [Key Repeat Behavior](https://zmk.dev/docs/behaviors/key-repeat)
```c
&key_repeat
```
Repeats the last key.

The devicetree document is [here](https://zmk.dev/docs/config/behaviors#key-repeat).

## [Conditional Layers](https://zmk.dev/docs/features/conditional-layers)
```c
    conditional_layers {
        compatible = "zmk,conditional-layers";
        tri_layer {
            if-layers = <1 2>;
            then-layer = <3>;
        };
    };
```
If some multiple layers are enabled (in above example, `1` and `2`), the then-layer (`3`) will be enabled.

## Hold-Tap related

### [Hold-Tap Behavior](https://zmk.dev/docs/behaviors/hold-tap)
Advanced Mod-Tap and Layer-Tap.

![](https://zmk.dev/assets/images/case1_2-0c88b39aeb0de9b5f5651c8274fa83f3.svg)

released within `tapping-term-ms`, sends tap key. hold after the time, sends (holds) the hold key.
```c
    behaviors {
        key: name {
            compatible = "zmk,behavior-hold-tap";
            label = "LABEL";
            #binding-cells = <2>;
            tapping-term-ms = <200>;
            quick-tap-ms = <0>;
            flavor = "flavor";
            bindings = <hold>, <tap>;
        };
    };
```
`flavor` in (`hold-preferred`, `balanced`, `tap-preferred`, `tap-unless-interrupted`)
`<hold>`, `<tap>` is behavior like `<&kp>`, `<&mo>`.
![](https://zmk.dev/assets/images/comparison-90bcec61f679e88a74490eb261d92940.svg)

The devicetree document is [here](https://zmk.dev/docs/config/behaviors#hold-tap).

### [Mod-Tap Behavior](https://zmk.dev/docs/behaviors/mod-tap)
```c
&mt modkey tapkey
```
hold to send `modkey`, tap to send `tapkey`.

This behavior equals the Hold-tap "hold-preferred" with (`hold` = key press(`&kp`), `tap` = key press(`&kp`)).
```c
    behaviors {
        mt_impl: mod-tap-by-hold-tap {
            compatible = "zmk,behavior-hold-tap";
            label = "MOD_TAP_BY_HOLD_TAP";
            #binding-cells = <2>;
            tapping-term-ms = <200>;
            quick-tap-ms = <0>;
            flavor = "hold-preferred";
            bindings = <&kp>, <&kp>;
        };
    };

    // &mt modkey tapkey = &mt_impl modkey tapkey
```

### [Layer-tap](https://zmk.dev/docs/behaviors/layers#layer-tap)
```c
&lt layer key
```
tap sends the `key`, holds activate the `layer`.

This behavior equals the Hold-tap "tap-preferred" with (`hold` = momentary layer(`&mo`), `tap` = key press(`&kp`)).
```c
    behaviors {
        lt_impl: layer-tap-by-hold-tap {
            compatible = "zmk,behavior-hold-tap";
            label = "LAYER_TAP_BY_HOLD_TAP";
            #binding-cells = <2>;
            tapping-term-ms = <200>;
            quick-tap-ms = <0>;
            flavor = "tap-preferred";
            bindings = <&mo>, <&kp>;
        };
    };

    // &lt layer key = &lt_impl layer key
```

## Other definitions

### [Mod-Morph Behavior](https://zmk.dev/docs/behaviors/mod-morph)
```c
    behaviors {
        key: name {
            compatible = "zmk,behavior-mod-morph";
            label = "LABEL";
            #binding-cells = <0>;
            bindings = <without mod behavior>, <with mod behavior>;
            mods = <(MOD_LGUI|MOD_LSFT|MOD_RGUI|MOD_RSFT)>;
            keep-mods = <(MOD_LSFT)>;
        };
    };
```
with MOD_* sends `with mod behavior`, without MOD_* sends the `without mod behavior`.

Available mods: `MOD_LSFT`, `MOD_RSFT`, `MOD_LCTL`, `MOD_RCTL`, `MOD_LALT`, `MOD_RALT`, `MOD_LGUI`, `MOD_RGUI`.

keep-mods' `MOD_*` will be keep holding with behavior.

The devicetree document is [here](https://zmk.dev/docs/config/behaviors#mod-morph).

### [Tap-Dance Behavior](https://zmk.dev/docs/behaviors/tap-dance)
```c
    behaviors {
        td0: tap_dance_0 {
            compatible = "zmk,behavior-tap-dance";
            label = "TAP_DANCE_0";
            #binding-cells = <0>;
            tapping-term-ms = <200>;
            bindings = <&kp N1>, <&kp N2>, <&kp N3>;
        };
    };
```
Change behavior by the count of tap.

The devicetree document is [here](https://zmk.dev/docs/config/behaviors#tap-dance).

## [Macro Behavior](https://zmk.dev/docs/behaviors/macros)
```c
    macros {
        zed_em_kay: zed_em_kay {
            label = "ZM_zed_em_kay";
            compatible = "zmk,behavior-macro";
            #binding-cells = <0>;
            bindings
                = <&macro_press &kp LSHFT>
                , <&macro_tap &kp Z &kp M &kp K>
                , <&macro_release &kp LSHFT>
                ;
        };
    };
```
WIP.

The devicetree document is [here](https://zmk.dev/docs/config/behaviors#macro).

## Hardware or firmware related

### [Reset Behaviors](https://zmk.dev/docs/behaviors/reset)
```c
&reset
```
Reset with current flashed firmware. (like restart)

### [Bootloader Reset](https://zmk.dev/docs/behaviors/reset#bootloader-reset)
```c
&bootloader
```
Reset to flash new firmware.

### [Bluetooth Behavior](https://zmk.dev/docs/behaviors/bluetooth)
```c
&bt BT_*
```
- BT_CLR : clear current connection info
- BT_NXT : switch to the next profile
- BT_PRV : switch to the previous profile
- BT_SEL number : switch to the 0-index number profile

### [Output Selection Behavior](https://zmk.dev/docs/behaviors/outputs)
```c
&out OUT_*
```
- OUT_USB : prefer use usb
- OUT_BLE : prefer use bluetooth low energy
- OUT_TOG : toggle above

### [RGB Underglow Behavior](https://zmk.dev/docs/behaviors/underglow)
```c
&rgb_ug RGB_*
```
WIP

### [Backlight Behavior](https://zmk.dev/docs/behaviors/backlight)
```c
&bl BL_*
```
WIP

### [Power Management Behaviors](https://zmk.dev/docs/behaviors/power)
```c
&ext_power EP_*
```
WIP

{% include_relative footer.html %}
