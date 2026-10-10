#!/usr/bin/env python3
import json
import os
import shutil
import tempfile
from pathlib import Path


def merge_policy(existing):
    policy = json.loads(json.dumps(existing))
    extensions = policy.setdefault('policies', {}).setdefault('ExtensionSettings', {})
    extensions['pywalfox@frewacom.org'] = {
        'installation_mode': 'normal_installed',
        'install_url': 'https://addons.mozilla.org/firefox/downloads/latest/pywalfox/latest.xpi',
    }
    return policy


def install_policy(path):
    original = json.loads(path.read_text()) if path.exists() else {}
    policy = merge_policy(original)
    if policy == original:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = Path(tempfile.mkdtemp(prefix='hyprland-policy-backup-', dir=path.parent))
        shutil.copy2(path, backup / path.name)
    fd, name = tempfile.mkstemp(prefix='.hyprland-policy-', dir=path.parent)
    with os.fdopen(fd, 'w') as output:
        json.dump(policy, output, indent=2)
        output.write('\n')
    os.chmod(name, 0o644)
    os.replace(name, path)


if __name__ == '__main__':
    install_policy(Path('/usr/lib/firefox/distribution/policies.json'))
    print('Firefox: automatic Pywalfox extension installation configured.')
