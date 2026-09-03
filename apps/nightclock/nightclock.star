"""
Applet: Night Clock
Summary: Very dim clock for night mode
Description: A minimal clock whose colour is configurable all the way down to
  near-black. On Tidbyt/Tronbyt hardware the panel's own brightness control
  bottoms out well above "nightlight" level, so the only way to go dimmer is to
  darken the pixels themselves. That is what this app is for.
Author: ha-homelab
"""

load("render.star", "render")
load("schema.star", "schema")
load("time.star", "time")

DEFAULT_COLOR = "#180800"
DEFAULT_TZ = "America/New_York"

def main(config):
    timezone = config.get("$tz", DEFAULT_TZ)
    now = time.now().in_location(timezone)

    color = config.str("color", DEFAULT_COLOR)
    time_format = "3:04" if config.bool("twelve_hour", True) else "15:04"

    children = [
        render.Text(
            content = now.format(time_format),
            font = "10x20",
            color = color,
        ),
    ]

    if config.bool("show_date", False):
        children.append(render.Text(
            content = now.format("Mon Jan 2"),
            font = "tom-thumb",
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
