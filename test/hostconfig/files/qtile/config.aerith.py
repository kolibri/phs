import socket

from libqtile import bar, extension, layout, qtile, widget
from libqtile.config import Click, Drag, Group, Key, Match, Screen
from libqtile.lazy import lazy
from libqtile.utils import guess_terminal
from libqtile.backend.wayland import InputConfig

mod = "mod4"
terminal = "qterminal"  # guess_terminal()

keys = [
    Key([mod], "h", lazy.layout.left(), desc="Move focus to left"),
    Key([mod], "l", lazy.layout.right(), desc="Move focus to right"),
    Key([mod], "j", lazy.layout.down(), desc="Move focus down"),
    Key([mod], "k", lazy.layout.up(), desc="Move focus up"),
    Key(
        [mod, "shift"], "h", lazy.layout.shuffle_left(), desc="Move window to the left"
    ),
    Key(
        [mod, "shift"],
        "l",
        lazy.layout.shuffle_right(),
        desc="Move window to the right",
    ),
    Key([mod, "shift"], "j", lazy.layout.shuffle_down(), desc="Move window down"),
    Key([mod, "shift"], "k", lazy.layout.shuffle_up(), desc="Move window up"),
    Key([mod, "control"], "h", lazy.layout.grow_left(), desc="Grow window to the left"),
    Key(
        [mod, "control"], "l", lazy.layout.grow_right(), desc="Grow window to the right"
    ),
    Key([mod, "control"], "j", lazy.layout.grow_down(), desc="Grow window down"),
    Key([mod, "control"], "k", lazy.layout.grow_up(), desc="Grow window up"),
    Key([mod], "n", lazy.layout.normalize(), desc="Reset all window sizes"),
    Key([mod], "Return", lazy.spawn(terminal), desc="Launch terminal"),
    Key([mod], "Space", lazy.next_layout(), desc="Toggle between layouts"),
    Key([mod], "w", lazy.window.kill(), desc="Kill focused window"),
    Key([mod, "control"], "r", lazy.reload_config(), desc="Reload the config"),
    Key([mod, "control"], "q", lazy.shutdown(), desc="Shutdown Qtile"),
    Key([mod], "r", lazy.spawncmd(), desc="Spawn a command using a prompt widget"),
    Key(
        [],
        "XF86AudioLowerVolume",
        # lazy.spawn("amixer -q sset Master 1%-"),
        lazy.spawn("wpctl set-volume @DEFAULT_AUDIO_SINK@ 1%-"),
        desc="Volume Down",
    ),
    Key(
        [],
        "XF86AudioRaiseVolume",
        # lazy.spawn("amixer -q sset Master 1%+"),
        lazy.spawn("wpctl set-volume @DEFAULT_AUDIO_SINK@ 1%+"),
        desc="Volume Up",
    ),
    # Key([], "Print", lazy.spawn('sh -c "maim ~/screenshots/$(date +%Y%m%d-%H%M%S).png"')),
]

groups = [Group(i) for i in "1234567"]

for i in groups:
    keys.extend(
        [
            Key(
                [mod],
                i.name,
                lazy.group[i.name].toscreen(),
                desc="Switch to group {}".format(i.name),
            ),
            Key(
                [mod, "shift"],
                i.name,
                lazy.window.togroup(i.name),
                desc="move focused window to group {}".format(i.name),
            ),
        ]
    )

layouts = [
    layout.Spiral(margin=10, ratio=0.55, main_pane_ratio=0.45),
    layout.RatioTile(margin=5),
    layout.Tile(margin=5),
    layout.MonadThreeCol(margin=10),
    # layout.MonadThreeCol(margin=10, main_centered=False),
    # layout.MonadWide(margin=10, ratio=0.65),
    layout.Max(margin=10),
]

widget_defaults = dict(
    font="mono",
    fontsize=14,
    padding=3,
    border_width=1,
    border_focus="#dddddd",
    margin=5,
)
extension_defaults = widget_defaults.copy()

screens = [
    Screen(
        wallpaper="/home/ko/.ko/wallpaper/wallpaper_kookaboora.jpg",
        wallpaper_mode="stretch",
        top=bar.Bar(
            [
                widget.TextBox(text="[" + socket.gethostname() + "]"),
                widget.CurrentLayout(icon_first=True),
                widget.GroupBox(
                    disable_drag=True,
                    highlight_method="block",
                    this_current_screen_border="#2a2a2a",
                ),
                widget.Sep(),
                widget.Prompt(),
                widget.TaskList(
                    highlight_method="block",
                    border="#2a2a2a",
                    max_title_width=200,
                    txt_minimized="*",
                ),
                widget.Spacer(background="#eeeeee", length=1),
                widget.LaunchBar(
                    progs=[
                        ("firefox", "firefox", "firefox"),
                        ("files", "pcmanfm", "file manager"),
                        ("term", "qterminal", "terminal"),
                        ("zed", "zeditor", "zeditor"),
                        # ('pycharm', 'pycharm', 'pycharm'),
                        ("steam", "steam", "Steam"),
                        ("obsidian", "obsidian", "Obsidian"),
                        # ('scad', 'openscad', 'openscad'),
                        # ('freecad', 'freecad', 'freecad'),
                        # ('kicad', 'kicad', 'kicad'),
                        # ('flatcam', 'flatcam-qt6', 'flatcam'),
                        # ('bCNC', 'bCNC', 'bCNC'),
                        # ('slice', 'prusa-slicer', 'prusa-sclicer'),
                        ("vlc", "vlc", "VLC"),
                        # ('office', 'libreoffice', 'office'),
                        ("scribus", "scribus", "scribus"),
                        ("lutris", "lutris", "lutris"),
                        ("discord", "discord", "discord"),
                    ],
                    text_only=True,
                    background="#1a1a1a",
                ),
                widget.CheckUpdates(distro="Arch"),
                widget.DF(visible_on_warn=False),
                widget.CPUGraph(type="box", graph_color="#2a2a2a"),
                widget.NetGraph(type="line", graph_color="#2a2a2a"),
                widget.Sep(),
                widget.ThermalSensor(),
                widget.Sep(),
                widget.CapsNumLockIndicator(),
                widget.Sep(),
                #widget.Systray(),
                widget.StatusNotifier(),
                widget.CheckUpdates(distro="Arch", no_update_string="No updates"),
                widget.Clock(format="%Y-%m-%d %H:%M:%S ", background="#1a1a1a"),
                widget.Sep(),
                widget.PulseVolume(),
            ],
            24,
            border_width=[1, 1, 1, 1],
            margin=[5, 5, 0, 5],
        ),
    ),
]

# Drag floating layouts.
mouse = [
    Drag(
        [mod], "Button1", lazy.window.set_position(), start=lazy.window.get_position()
    ),
    Drag(
        [mod], "Button3", lazy.window.set_size_floating(), start=lazy.window.get_size()
    ),
    Click([mod], "Button2", lazy.window.bring_to_front()),
]

dgroups_key_binder = None
dgroups_app_rules = []  # type: list
follow_mouse_focus = True
bring_front_click = False
cursor_warp = False
floating_layout = layout.Floating(
    float_rules=[
        # Run the utility of `xprop` to see the wm class and name of an X client.
        # *layout.Floating.default_float_rules,
        Match(wm_class="confirmreset"),  # gitk
        Match(wm_class="makebranch"),  # gitk
        Match(wm_class="maketag"),  # gitk
        Match(wm_class="ssh-askpass"),  # ssh-askpass
        Match(title="branchdialog"),  # gitk
        Match(title="pinentry"),  # GPG key password entry
    ]
)
auto_fullscreen = True
focus_on_window_activation = "smart"
reconfigure_screens = True

auto_minimize = True
wl_input_rules = {
    "type:keyboard": InputConfig(
        kb_layout="de",
        kb_variant="deadgraveacute",
    ),
}
wmname = "LG3D"
