"""
Applet: Night Clock
Summary: Very dim clock for night mode
Description: A minimal clock whose colour is configurable all the way down to
  near-black. On Tidbyt/Tronbyt hardware the panel's own brightness control
  bottoms out well above "nightlight" level, so the only way to go dimmer is to
  darken the pixels themselves. That is what this app is for.
Author: febrile42
"""

load("render.star", "render")
load("schema.star", "schema")
load("time.star", "time")

DEFAULT_COLOR = "#180800"
DEFAULT_FONT = "6x13"
DEFAULT_TZ = "America/New_York"

HEX_DIGITS = "0123456789abcdef"

# Hex colours may be #RGB, #RGBA, #RRGGBB or #RRGGBBAA.
HEX_LENGTHS = [3, 4, 6, 8]

TRUE_VALUES = ["true", "1", "yes", "on"]
FALSE_VALUES = ["false", "0", "no", "off"]

# The 10x20 face is wide enough that a 12-hour time with a meridiem will not fit
# across 64 pixels, and a second line in the same face will not fit beneath it.
WIDE_FONT = "10x20"
WIDE_FONT_SECONDARY = "5x8"

def is_hex_color(value):
    """Whether this is something render.Text will accept as a colour.

    render.Text fails the whole render on a malformed colour, and treats an
    empty string as white, so the value has to be checked before it gets there.
    """
    if not value.startswith("#"):
        return False

    digits = value[1:].lower()
    if len(digits) not in HEX_LENGTHS:
        return False

    for digit in digits.elems():
        if digit not in HEX_DIGITS:
            return False
    return True

def cfg_color(config, key, fallback):
    """Read a colour, falling back on anything render.Text would choke on.

    A config value can be present but empty, from a cleared field or from the
    settings page's config import, and config.str only supplies its default when
    the key is absent entirely. An empty string then reaches render.Text, which
    renders it white. On an app whose entire purpose is being dim, that is a
    full-brightness screen in the middle of the night.
    """
    value = config.str(key, "")
    if value == None:
        return fallback

    value = value.strip()
    if not is_hex_color(value):
        return fallback
    return value

def cfg_bool(config, key, fallback):
    """Read a toggle without letting an empty value abort the render.

    config.bool raises on a value that is present but empty, failing the whole
    app rather than the one setting.
    """
    value = config.str(key, "")
    if value == None:
        return fallback

    value = value.strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    return fallback

def cfg_font(config, key, fallback):
    """Read a font name, rejecting anything render.Text does not know."""
    value = config.str(key, "")
    if value == None:
        return fallback

    value = value.strip()
    if value not in render.fonts:
        return fallback
    return value

def main(config):
    # An empty timezone would fail in_location. A non-empty but unknown one
    # still would, and Starlark has no way to catch that, but $tz is supplied by
    # the server from the device's own location rather than typed by hand.
    timezone = config.get("$tz", "")
    if not timezone:
        timezone = DEFAULT_TZ
    now = time.now().in_location(timezone)

    color = cfg_color(config, "color", DEFAULT_COLOR)
    font = cfg_font(config, "font", DEFAULT_FONT)
    show_date = cfg_bool(config, "show_date", False)

    # At 10x20 a 12-hour time with a meridiem overflows the panel, so that face
    # is 24-hour only. Matches how the Custom Clock app handles the same font.
    twelve_hour = cfg_bool(config, "twelve_hour", True) and font != WIDE_FONT
    time_format = "3:04 PM" if twelve_hour else "15:04"

    children = [
        render.Text(
            content = now.format(time_format),
            font = font,
            color = color,
        ),
    ]

    if show_date:
        date_font = WIDE_FONT_SECONDARY if font == WIDE_FONT else font
        children.append(render.Text(
            content = now.format("Mon Jan 2"),
            font = date_font,
            color = color,
        ))

    return render.Root(
        delay = 1000,
        child = render.Box(
            child = render.Column(
                expanded = True,
                main_align = "center",
                cross_align = "center",
                children = children,
            ),
        ),
    )

def get_schema():
    fonts = []
    for key, value in render.fonts.items():
        if key == WIDE_FONT:
            display = "%s (24 hour only, date shrinks to %s)" % (key, WIDE_FONT_SECONDARY)
        else:
            display = key
        fonts.append(schema.Option(display = display, value = value))

    return schema.Schema(
        version = "1",
        fields = [
            schema.Color(
                id = "color",
                name = "Colour",
                desc = "Darker = dimmer. This is the real night-mode lever; the panel cannot dim below its hardware floor.",
                icon = "palette",
                default = DEFAULT_COLOR,
                palette = [
                    "#0c0400",
                    "#180800",
                    "#301000",
                    "#0a0a0a",
                    "#181818",
                    "#300000",
                    "#001800",
                ],
            ),
            schema.Dropdown(
                id = "font",
                name = "Font",
                desc = "Change the font of the time.",
                icon = "font",
                default = DEFAULT_FONT,
                options = fonts,
            ),
            schema.Toggle(
                id = "twelve_hour",
                name = "12-hour clock",
                desc = "Show 12-hour time instead of 24-hour.",
                icon = "clock",
                default = True,
            ),
            schema.Toggle(
                id = "show_date",
                name = "Show date",
                desc = "Show the date beneath the time.",
                icon = "calendar",
                default = False,
            ),
        ],
    )
