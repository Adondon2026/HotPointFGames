"""The upstream APK stays unchanged unless a ZMZ build is explicitly requested."""
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
notes=read('docs/ZMZ_v0.19.1_补丁说明.md')
assert 'namespace "com.chuanmahjong.nearby"' in gradle
assert 'applicationId "com.chuanmahjong.nearby"' in gradle
assert 'gradleProperty("zmzBuild")' in gradle
assert 'applicationIdSuffix(zmzBuild ? ".zmz.debug" : ".debug")' in gradle
assert 'versionCode(zmzBuild ? 7 : 4)' in gradle
assert '0.19.1-ZMZ' in gradle
assert 'HotPointFGames-ZMZ-v0.19.1-' in gradle
assert 'android:label="${gameHallLabel}"' in manifest
assert 'com.chuanmahjong.nearby.MainActivity' in manifest
assert '热点游戏厅' in strings and 'ZMZ' not in strings
assert 'BuildConfig.ZMZ_BUILD' in updates
assert 'else Regex("game-' in updates
assert 'Regex("zmz-game-v[0-9]+' in updates
assert 'zmz-game-v0.19.1-' in workflow
assert '--latest=false' in workflow
assert 'bash gradlew assembleDebug -PzmzBuild=true --no-daemon' in android
assert 'app/build/outputs/apk/debug/*.apk' in android
assert 'HotPointFGames-ZMZ-v0.19.1-Android' in android
assert 'ZMZ v0.19.1' in notes and '正在进入对局' in notes
pattern=re.compile(r'zmz-game-v\d+\.\d+\.\d+-\d+-\d+-[a-f0-9]{7,40}')
assert pattern.fullmatch('zmz-game-v0.19.1-123-1-51ee19de42bc')
assert not pattern.fullmatch('game-123-1-51ee19de42bc')
print('ZMZ v0.19.1 build isolation and release channel verified')
