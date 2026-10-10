-- MONITORS.LUA
-- https://wiki.hypr.land/Configuring/Monitors/
-- Find your monitor names with:
--   hyprctl monitors

-- 1. First monitor
-- hl.monitor({ output = "eDP-1", mode = "preferred", position = "auto", scale = 1 })
-- hl.monitor({ output = "HDMI-A-1", disabled = true })

-- 2. Second monitor
-- hl.monitor({ output = "eDP-1", disabled = true })
-- hl.monitor({ output = "HDMI-A-1", mode = "preferred", position = "auto", scale = 1 })

-- 3. Extend / Auto
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 }) 
-- Physical arrangement: HDMI on the left, DisplayPort on the right.
hl.monitor({ output = "HDMI-A-1", mode = "preferred", position = "0x0", scale = 1 })
hl.monitor({ output = "DP-1", mode = "preferred", position = "1920x0", scale = 1 })

-- 4. Duplicate
-- hl.monitor({ output = "eDP-1", mode = "preferred", position = "0x0", scale = 1 })
-- hl.monitor({ output = "HDMI-A-1", mode = "preferred", position = "0x0", scale = 1 })

-- 5. Second vertical monitor
-- hl.monitor({ output = "HDMI-A-1", mode = "preferred", position = "0x0", scale = 1 })
-- hl.monitor({ output = "eDP-1", mode = "preferred", position = "1920x0", scale = 1, transform = 1 })

pcall(function()
    local path = os.getenv("HOME") .. "/.config/quickshell/state/display.lua"
    local f = io.open(path, "r")
    if f then
        f:close()
        dofile(path)
    end
end)

-- WORKSPACE RULES
-- https://wiki.hypr.land/Configuring/Workspace-Rules/

-- hl.workspace_rule({ workspace = "name:gaming", monitor = PRIMARY_MONITOR, default = true })


-- hl.workspace_rule({ workspace = "5", monitor = MONITOR2, default = true, persistent = true })
-- hl.workspace_rule({ workspace = "6", monitor = MONITOR2, default = true, persistent = true })

