#!/usr/bin/env python3
"""Build the canonical in-repo game source and copy the release into Android."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "game_source"
subprocess.run([sys.executable, str(SOURCE / "build.py")], check=True)
release = SOURCE / "dist" / "game_hall_lan_v6_2.py"
target = ROOT / "app" / "src" / "main" / "python" / release.name
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(release, target)
print(f"Synced {release} -> {target}")
