"""ZMZ channel isolation after syncing main v0.24."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
def read(p):return (root/p).read_text(encoding='utf-8')
gradle=read('app/build.gradle')
manifest=read('app/src/main/AndroidManifest.xml')
updates=read('app/src/main/java/com/chuanmahjong/nearby/GameUpdates.kt')
build=read('game_source/build.py')
game=read('.github/workflows/game.yml')
android=read('.github/workflows/android.yml')
siege=read('game_source/parts/98_siege.pyfrag')
assert 'versionCode(zmzBuild ? 14 : 5)' in gradle
assert '0.24.2-ZMZ' in gradle and '1.4' in gradle
assert 'applicationIdSuffix(zmzBuild ? ".zmz.debug" : ".debug")' in gradle
assert 'HotPointFGames-ZMZ-v0.24.2-' in gradle
assert 'android:label="${gameHallLabel}"' in manifest
assert 'BuildConfig.ZMZ_BUILD' in updates
assert 'Regex("zmz-game-v[0-9]+' in updates
assert 'else Regex("game-' in updates
assert 'LATEST_MANIFEST' in updates and 'resolveLatest' in updates
assert 'GAME_DISPLAY_VERSION = "ZMZ v0.24.2"' in build
assert 'web/games/siege_catalog.js' in build
assert 'zmz-game-v0.24.2-' in game and '--latest=false' in game
assert "'Zmz_dev'" in android and 'PzmzBuild=true' in android
assert 'testDebugUnitTest' in android
assert '_siege_v24' in siege and 'def _siege_v20_push' in siege and 'def _siege_gun_gravity' in siege
assert all((root/'game_source/web/games/siege_catalog.js').read_text(encoding='utf-8').find(k)>=0 for k in ('spiral','clone','repeat','push'))
pattern=re.compile(r'zmz-game-v\d+\.\d+\.\d+-\d+-\d+-[a-f0-9]{7,40}')
assert pattern.fullmatch('zmz-game-v0.24.2-123-1-51ee19de42bc')
print('ZMZ v0.24.2: independent Android ID, v24 upstream, full channel split PASS')
