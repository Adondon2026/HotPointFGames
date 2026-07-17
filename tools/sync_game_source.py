#!/usr/bin/env python3
"""Build the modular source and copy its single-file release into the APK."""

from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT.parent / "game_hall_modular_v6_2_source"
SOURCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SOURCE

subprocess.run([sys.executable, str(SOURCE / "build.py")], check=True)
release = SOURCE / "dist" / "game_hall_lan_v6_2.py"
target = ROOT / "app" / "src" / "main" / "python" / release.name
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(release, target)
print(f"Synced {release} -> {target}")
