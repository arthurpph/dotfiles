local function exec(keys, command, options)
    hl.bind(keys, hl.dsp.exec_cmd(command), options)
end

exec("SUPER + Return", fileManager)
exec("SUPER + T", terminal)
exec("SUPER + D", "pgrep -x rofi >/dev/null && pkill -x rofi || " .. menu)
hl.bind("SUPER + SHIFT + Q", hl.dsp.window.close())
exec("SUPER + SHIFT + C", "hyprctl reload")
exec("SUPER + SHIFT + E",
    [[swaynag -t warning -m 'End the Hyprland session?' -B 'Yes, log out' "hyprctl dispatch 'hl.dsp.exit()'"]])

for _, pair in ipairs({ { "H", "Left", "l" }, { "J", "Down", "d" }, { "K", "Up", "u" }, { "L", "Right", "r" } }) do
    for i = 1, 2 do
        hl.bind("SUPER + " .. pair[i], hl.dsp.focus({ direction = pair[3] }))
        hl.bind("SUPER + SHIFT + " .. pair[i], hl.dsp.window.move({ direction = pair[3] }))
    end
end
for i = 1, 10 do
    local key = i % 10
    hl.bind("SUPER + " .. key, hl.dsp.focus({ workspace = i }))
    hl.bind("SUPER + SHIFT + " .. key, hl.dsp.window.move({ workspace = i, follow = false }))
end

hl.bind("SUPER + B", hl.dsp.layout("preselect r"))
hl.bind("SUPER + V", hl.dsp.layout("preselect d"))
exec("SUPER + S", "python3 ~/.config/hypr/scripts/sway-layout.py stacked")
exec("SUPER + W", "python3 ~/.config/hypr/scripts/sway-layout.py tabbed")
exec("SUPER + E", "python3 ~/.config/hypr/scripts/sway-layout.py split")
hl.bind("SUPER + F", hl.dsp.window.fullscreen({ mode = "fullscreen" }))
hl.bind("SUPER + SHIFT + Space", hl.dsp.window.float({ action = "toggle" }))
hl.bind("SUPER + Space", function()
    local window = hl.get_active_window()
    if window then
        hl.dispatch(hl.dsp.focus({ window = window.floating and "tiled" or "floating" }))
    end
end)
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true })
hl.bind("SUPER + M", function()
    local monitor = hl.get_active_monitor()
    if monitor then
        local target = monitor.name == "DP-1" and "HDMI-A-1" or "DP-1"
        hl.dispatch(hl.dsp.workspace.move({ monitor = target }))
    end
end)

-- Named special workspace: Hyprland's scratchpad equivalent.
hl.bind("SUPER + SHIFT + minus", hl.dsp.window.move({ workspace = "special:scratchpad", follow = false }))
hl.bind("SUPER + minus", hl.dsp.workspace.toggle_special("scratchpad"))
hl.bind("SUPER + R", hl.dsp.submap("resize"))
hl.define_submap("resize", function()
    for _, entry in ipairs({ { "H", -10, 0 }, { "Left", -10, 0 }, { "J", 0, 10 }, { "Down", 0, 10 },
        { "K", 0,   -10 }, { "Up", 0, -10 }, { "L", 10, 0 }, { "Right", 10, 0 } }) do
        hl.bind(entry[1], hl.dsp.window.resize({ x = entry[2], y = entry[3], relative = true }), { repeating = true })
    end
    hl.bind("Return", hl.dsp.submap("reset"))
    hl.bind("Escape", hl.dsp.submap("reset"))
end)

exec("XF86AudioMute", "pactl set-sink-mute @DEFAULT_SINK@ toggle", { locked = true })
exec("XF86AudioLowerVolume", "pactl set-sink-volume @DEFAULT_SINK@ -5%", { locked = true, repeating = true })
exec("XF86AudioRaiseVolume", "pactl set-sink-volume @DEFAULT_SINK@ +5%", { locked = true, repeating = true })
exec("XF86AudioMicMute", "pactl set-source-mute @DEFAULT_SOURCE@ toggle", { locked = true })
exec("XF86MonBrightnessDown", "brightnessctl set 5%-", { locked = true, repeating = true })
exec("XF86MonBrightnessUp", "brightnessctl set 5%+", { locked = true, repeating = true })
exec("XF86AudioPlay", "playerctl --player=spotify,firefox play-pause", { locked = true })
exec("XF86AudioNext", "playerctl next", { locked = true })
exec("XF86AudioPrev", "playerctl previous", { locked = true })
exec("Print", "bash ~/.config/hypr/scripts/screenshot.sh region")
exec("SHIFT + Print", "bash ~/.config/hypr/scripts/screenshot.sh full")
exec("SUPER + G", "hyprlock")
exec("SUPER + Tab", "hyprlock")
exec("SUPER + C", "pkill -SIGUSR1 -f '^gpu-screen-recorder( |$)'")

-- Desktop controls relocated away from the Sway shortcuts.
exec("SUPER + ALT + S", "qs ipc call wheel toggle")
exec("SUPER + ALT + E", fileManager)
exec("SUPER + ALT + B", browser)
exec("SUPER + ALT + W", "qs -n -p ~/.config/quickshell/hyprquickpaper")
exec("SUPER + ALT + V", "cliphist list | rofi -dmenu -p '' | cliphist decode | wl-copy")
exec("SUPER + ALT + C", "qs ipc call todo toggle")
exec("SUPER + ALT + L", "python3 ~/.config/43pr/bin/theme.py toggle")
exec("SUPER + I", "qs ipc call settings toggle")
exec("SUPER + N", "qs ipc call notifications toggle")
exec("SUPER + GRAVE", "qs ipc call powermenu toggle")
exec("SUPER + O", "bash ~/.config/hypr/scripts/opacity.sh")
exec("SUPER + SHIFT + W", "qs ipc call bar toggle")
exec("SUPER + X", "hyprctl switchxkblayout current next")

-- Zoom
local function zoomfunction(value)
    local zoomvalue = hl.get_config("cursor:zoom_factor")
    if (zoomvalue + value) > 1.5 then
        hl.config({ cursor = { zoom_factor = 1.5 } })
    elseif (zoomvalue + value) < 1.0 then
        hl.config({ cursor = { zoom_factor = 1.0 } })
    else
        hl.config({ cursor = { zoom_factor = zoomvalue + value } })
    end
end
hl.bind(mainMod .. " + mouse_down", function() zoomfunction(-0.5) end, { repeating = true })
hl.bind(mainMod .. " + mouse_up", function() zoomfunction(0.5) end, { repeating = true })

--# Zoom with keypad
hl.bind(mainMod .. " + code:82", function() zoomfunction(-0.3) end, { repeating = true })
hl.bind(mainMod .. " + code:86", function() zoomfunction(0.3) end, { repeating = true })
