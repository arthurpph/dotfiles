#!/usr/bin/env python3
"""Map Sway layout shortcuts to Hyprland groups and dwindle splits."""
import json
import subprocess
import sys

def call(*args):
    return subprocess.check_output(['hyprctl', *args], text=True)

window = json.loads(call('-j', 'activewindow'))
if not window:
    sys.exit(0)
grouped = bool(window.get('grouped'))
mode = sys.argv[1]
if mode == 'split':
    if grouped:
        call('dispatch', 'hl.dsp.group.toggle()')
    else:
        call('dispatch', 'hl.dsp.layout("togglesplit")')
else:
    stacked = 'true' if mode == 'stacked' else 'false'
    call('eval', f'hl.config({{group = {{groupbar = {{stacked = {stacked}}}}}}})')
    if not grouped:
        call('dispatch', 'hl.dsp.group.toggle()')
