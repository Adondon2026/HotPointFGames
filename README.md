# 热点游戏厅 HotPointFGames

离线好友联机：房主开启手机热点，APP 启动本机 Python 服务，其他人通过浏览器扫码加入。无需互联网、云服务器或账号。

## 本地电脑预览（无需 Android SDK）

进入 `game_source/`，先执行 `python build.py`，然后双击 `START_GAME.bat` 或执行 `python run_preview.py`。浏览器自动打开本机游戏厅。手机连接同一 Wi-Fi，点击大厅「邀请朋友」扫码加入。账户和历史积分保存在该运行设备，具体规则见 [本地预览说明](game_source/README.md)。

## 单人 / 好友体验

一个人也可直接开局；五款游戏均支持本地机器人（你画我猜为机器人出题的简笔画练习）。大厅可手动添加或移除机器人，规则与设置按游戏独立披露。无需热点即可在本机浏览器或 Android APP 内单人玩。

## 最快的游戏开发方式

唯一开发源码位于 game_source/。五个游戏分别维护后端、动作和 Web UI。不要手改 app/src/main/python/game_hall_lan_v6_2.py，它是构建产物。

    python game_source/build.py
    python game_source/dist/game_hall_lan_v6_2.py

在电脑浏览器打开 http://127.0.0.1:8000/；也可以把生成的单文件放到 Termux 测试。修改规则、UI、词库、新游戏后，重新运行第一条命令即可。

## Android APP：安装一次，离线导入更新

1. 在 APP 首页停止游戏厅（主动停止会结束当前房间）。
2. 点击「导入新版游戏文件」，选择自己构建的 game_source/dist/game_hall_lan_v6_2.py 或 .txt。
3. 确认关闭 APP，再点击桌面图标重新打开、启动游戏厅。
4. 需要恢复时，停止游戏厅，点击「恢复内置游戏」。

导入文件保存在 APP 私有目录，最大 4 MB；导入前检查 Python 语法与基础运行接口，启动时加载失败则回退内置版。只导入自己构建的可信文件：Python 导入是执行代码，不是安全沙箱。恢复内置版不会主动删除游戏存档，但不同游戏版本的存档格式仍需兼容。

## 构建 Android APK

推荐 GitHub Actions：

- 游戏规则、UI 或词库更新：Actions → Game files，构建后在 Artifacts 下载可导入的 .py / .txt，无需编译 Android。
- Android 宿主更新：Actions → Android build → Run workflow，构建成功后在 Artifacts 下载 APK。宿主源码变更时也会自动触发。

两种构建均无需在本机安装 Android SDK。

本地可使用 JDK 17、Android SDK Platform 36.1、Python 3.13 和仓库自带 Gradle Wrapper：

    python tools/sync_game_source.py
    .\gradlew.bat assembleDebug

APK：app/build/outputs/apk/debug/app-debug.apk。Linux/macOS 使用 bash gradlew assembleDebug。

当前支持 Android 7+、ARM64。默认产物为调试 APK；不同电脑或 CI 的调试签名可能不同，不能覆盖安装签名不同的 APK。需要长期原位升级 APK 时，应使用同一私有签名密钥（不要提交密钥到仓库）。游戏文件导入无需重新签名或安装 APK。

## 测试

    python game_source/tests/smoke_test.py
    python tools/sync_game_source.py
    python tests/test_android_bridge.py

游戏核心和 Android 桥接测试不需要 Android SDK。原有 Playwright UI 测试仍可通过 npm 安装后运行。
