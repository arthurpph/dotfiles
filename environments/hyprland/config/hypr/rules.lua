-- Docs: https://wiki.hypr.land/Configuring/Basics/Window-Rules/
-- To check class name, open the app and run:
-- hyprctl clients

hl.layer_rule({
    match = { namespace = "rofi" },
    blur = true,
    ignore_alpha = 0.15,
})

-- Opacity rules for all windows except fullscreen
hl.window_rule({
    match = { class = ".*" },
    opacity = "1.0 override",
})
hl.window_rule({
    match = { class = ".*", fullscreen = true },
    opacity = "1.0 override",
})

--hl.window_rule({
--    name = "brave-opaque",
--    match = { class = "^brave-browser$" },
--    opacity = "1.0 override",
--})

hl.window_rule({
    match = { class = "kitty" },
    suppress_event = "maximize",
})

hl.window_rule({
    name = "float-pavucontrol",
    match = { class = "^(pavucontrol)$" },
    float = true,
    size = { "monitor_w*0.6", "monitor_h*0.7" },
    center = true,
})

hl.window_rule({
    name = "float-thunar",
    match = { class = "^(thunar|Thunar)$" },
    opaque = true,
    force_rgbx = true,
    float = true,
    size = { "monitor_w*0.6", "monitor_h*0.7" },
    center = true,
})

-- Assign new windows to the same workspaces as sway/config.
for _, entry in ipairs({
    { "^(Alacritty|alacritty)$", "1" },
    { "^(discord|Discord)$", "2" },
    { "^(brave-browser|Brave-browser|firefox|org.qutebrowser.qutebrowser)$", "3" },
    { "^(Spotify|spotify)$", "4" },
    { "^(steam|Steam)$", "5" },
}) do
    hl.window_rule({ match = { class = entry[1] }, workspace = entry[2] .. " silent" })
end
hl.window_rule({ match = { class = "^(io.github.celluloid_player.Celluloid|Celluloid)$" }, fullscreen = true })
hl.window_rule({ match = { workspace = "8" }, float = true })

hl.window_rule({
    name = "float-nm-connection-editor",
    match = { class = "^(nm-connection-editor)$" },
    float = true,
})

hl.window_rule({
    name = "float-blueman-manager",
    match = { class = "^(blueman-manager)$" },
    float = true,
})

hl.window_rule({
    name = "float-open-file",
    match = { title = "^(Open File)$" },
    float = true,
})

hl.window_rule({
    name = "float-save-file",
    match = { title = "^(Save File)$" },
    float = true,
})

-- Wine can restore Radmin VPN beyond the monitor bounds.
hl.window_rule({
    name = "float-radmin-vpn",
    match = { class = "^(rvrvpngui\\.exe|RvRvpnGui\\.exe)$", title = "^Radmin VPN$" },
    float = true,
    center = true,
})

hl.window_rule({
    name = "float-loupe",
    match = { class = "^(org\\.gnome\\.Loupe|loupe)$" },
    float = true,
    size = { "monitor_w*0.75", "monitor_h*0.8" },
    center = true,
})

-- GTK portal file chooser used by browsers and other applications.
hl.window_rule({
    name = "opaque-gtk-file-chooser",
    match = { class = "^(xdg-desktop-portal-gtk)$" },
    opaque = true,
    force_rgbx = true,
    float = true,
})
