"""Checks the ZMZ v1.4.0 APK identity and game-update channel separation."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
def read(path):return (ROOT/path).read_text(encoding='utf-8')
gradle=read('app/build.gradle')
manifest=read('app/src/main/AndroidManifest.xml')
strings=read('app/src/main/res/values/strings.xml')
updates=read('app/src/main/java/com/chuanmahjong/nearby/GameUpdates.kt')
workflow=read('.github/workflows/game.yml')
android=read('.github/workflows/android.yml')
notes=read('docs/ZMZ_v1.4.0_更新说明.md')
assert 'namespace "com.chuanmahjong.nearby"' in gradle
assert 'applicationId "com.chuanmahjong.nearby.zmz"' in gradle
assert 'applicationIdSuffix ".debug"' in gradle
assert 'versionCode 5' in gradle and 'versionName "1.4.0-ZMZ"' in gradle
assert 'HotPointFGames-ZMZ-v1.4.0-' in gradle
assert 'android:label="@string/app_name"' in manifest
assert 'com.chuanmahjong.nearby.MainActivity' in manifest
assert '热点游戏厅 ZMZ' in strings
assert 'HOST_VERSION = 5' in updates
assert 'zmz-game-v[0-9]+' in updates
assert 'split(\'-\')[3].toLong()' in updates
assert 'split(\'-\')[4].toLong()' in updates
assert 'zmz-game-v1.4.0-' in workflow
assert 'github.ref == \'refs/heads/Zmz_dev\'' in workflow
assert '--latest=false' in workflow
assert 'HotPointFGames-ZMZ-v1.4.0-debug.apk' in android
assert 'HotPointFGames-ZMZ-v1.4.0-Android' in android
assert all(s in notes for s in ('ZMZ v1.4.0','增益','海浪琶音','轻快像素','独立更新','com.chuanmahjong.nearby.zmz.debug'))
pattern=re.compile(r'zmz-game-v\d+\.\d+\.\d+-\d+-\d+-[a-f0-9]{7,40}')
assert pattern.fullmatch('zmz-game-v1.4.0-123-1-ca42fee34997')
assert not pattern.fullmatch('game-123-1-ca42fee34997')
assert not pattern.fullmatch('zmz-game-v1.4.0-main')
print('ZMZ v1.4.0 channel and identity verified')
