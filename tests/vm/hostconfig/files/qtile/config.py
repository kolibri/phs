from libqtile import bar, layout, widget
from libqtile.config import Group, Screen

keys = []
groups = [Group("1")]
layouts = [layout.Max()]

widget_defaults = {
    "font": "sans",
    "fontsize": 14,
    "padding": 4,
}
extension_defaults = widget_defaults.copy()

screens = [
    Screen(
        top=bar.Bar(
            [
                widget.TextBox("PHS VM test"),
                widget.Spacer(),
                widget.Clock(format="%Y-%m-%d %H:%M:%S"),
            ],
            28,
        ),
    ),
]

mouse = []
dgroups_key_binder = None
dgroups_app_rules = []
follow_mouse_focus = True
bring_front_click = False
cursor_warp = False
floating_layout = layout.Floating()
auto_fullscreen = True
focus_on_window_activation = "smart"
reconfigure_screens = True
auto_minimize = True
wmname = "LG3D"
