# 热点游戏厅 HotPointFGames

离线好友联机：房主开启手机热点，APP 启动本机 Python 服务，其他人通过浏览器扫码加入。无需互联网、云服务器或账号。

## 本地电脑预览（无需 Android SDK）

进入 `game_source/`，先执行 `python build.py`，然后双击 `START_GAME.bat` 或执行 `python run_preview.py`。浏览器自动打开本机游戏厅。手机连接同一 Wi-Fi，点击大厅「邀请朋友」扫码加入。账户和历史积分保存在该运行设备，具体规则见 [本地预览说明](game_source/README.md)。

## ZMZ v0.19.2 开发版（独立安装／独立更新）

**最新补丁 v0.19.2**：设置中勾选增益时「已选 X / 16」实时变化；重进战场自动恢复上次选择的海浪／像素背景乐，Android WebView 允许随战场自动启动音乐。详情见 [v0.19.2 补丁说明](docs/ZMZ_v0.19.2_补丁说明.md)。

`Zmz_dev` 分支的 Android 调试版使用独立应用包名 `com.chuanmahjong.nearby.zmz.debug`，桌面名称为「热点游戏厅 ZMZ」，可以与师兄的主线 APK 共存，不覆盖原 APP 的账号与存档。输出文件为 `HotPointFGames-ZMZ-v0.19.2-debug.apk`，Actions 产物名为 `HotPointFGames-ZMZ-v0.19.2-Android`。

ZMZ 版在线游戏更新仅接受 `zmz-game-v0.19.2-<run>-<attempt>-<sha>` 发布包，由 `Zmz_dev` 的 **Game files** 工作流构建并发布；主线仍使用 `game-...`，更新通道互相隔离。此次 **v0.19.0** 同时包含拆家大战的增益种类勾选、两首原创合成背景音乐切换与炮击音效，以及 Android 应用独立安装、独立更新机制。完整说明见 [ZMZ v0.19.0 版本更新说明](docs/ZMZ_v0.19.0_更新说明.md)。

## v0.10 多房间与拆家大战

公共大厅统一账户与二维码；创建或加入好友房间后，房主选择游戏、设置并直接开局。七款游戏均可多房间并行。拆家大战支持动态战场、三种堡垒、风力、无限或有限炮弹、六种可组合道具、炮弹跟随镜头和基础弹/强化弹平衡。旧单房间进行中对局不会迁移；账号和积分数据库保留。

## 单人 / 好友体验

一个人也可直接开局；七款游戏均支持本地机器人（你画我猜为机器人出题的简笔画练习）。大厅可手动添加或移除机器人，规则与设置按游戏独立披露。无需热点即可在本机浏览器或 Android APP 内单人玩。

## 斗地主牌桌体验

斗地主采用竖屏与横屏专属布局、底牌折叠、按序行动呈现及可回看记录。纯真人好友局胜利 +3、失败 0；含机器人仅统计练习战绩，历史积分保留，游戏原始分与账户积分独立。详见 [本地预览说明](game_source/README.md)。

## 军棋

双人暗棋军棋，基于 ArmyChessPython v0.6.1 与 v1.1 冻结规则。支持单人机器人与好友联机、布阵、山界、两种军旗胜利模式、求和悔棋及结束后复盘。手机横竖屏采用不同棋盘方向。

## 最快的游戏开发方式

唯一开发源码位于 game_source/。七个游戏分别维护后端、动作和 Web UI。不要手改 app/src/main/python/game_hall_lan_v6_2.py，它是构建产物。

    python game_source/build.py
    python game_source/dist/game_hall_lan_v6_2.py

在电脑浏览器打开 http://127.0.0.1:8000/；也可以把生成的单文件放到 Termux 测试。修改规则、UI、词库、新游戏后，重新运行第一条命令即可。

## Android APP 1.3：在线一键更新

首次安装 Android build 生成的新版 APK。APP 首页自动检查公开 GitHub Releases；发现新版后点击「下载并更新」。若服务器正在运行，请等朋友结束游戏后手动停止，再确认更新。应用仅从本仓库的 HTTPS 发布地址下载，限制文件大小、校验 SHA-256 和 Python 接口，并原子替换游戏文件。加载失败时尝试恢复上一个导入版本，否则回退内置版。账户和积分文件不参与替换。更新需联网，游戏仍可离线。游戏源码提交 main 后，Game files 测试通过才发布独立游戏 Release；不需要安装新 APK。宿主变更仍需安装 APK；调试签名可能不同，卸载会丢失本地数据。

## Android APP：安装一次，离线导入更新

1. 在 APP 首页停止游戏厅（主动停止会结束当前房间）。
2. 点击「导入新版游戏文件」，选择自己构建的 game_source/dist/game_hall_lan_v6_2.py 或 .txt。
3. 确认关闭 APP，再点击桌面图标重新打开、启动游戏厅。
4. 需要恢复时，停止游戏厅，点击「恢复内置游戏」。

导入文件保存在 APP 私有目录，最大 4 MB；导入前检查 Python 语法与基础运行接口，启动时加载失败则回退内置版。只导入自己构建的可信文件：Python 导入是执行代码，不是安全沙箱。恢复内置版不会主动删除游戏存档，但不同游戏版本的存档格式仍需兼容。

## 构建 Android APK

推荐 GitHub Actions：

- 游戏规则、UI 或词库更新：Actions → Game files，构建后在 Artifacts 下载可导入的 .py / .txt，无需编译 Android。
- 首次安装或 Android 宿主更新：Actions → Android build，构建成功后在 Artifacts 下载 HotPointFGames-Android，解压后安装 app-debug.apk。游戏源码及宿主变更均会自动触发。

两种构建均无需在本机安装 Android SDK。

本地可使用 JDK 17、Android SDK Platform 36.1、Python 3.13 和仓库自带 Gradle Wrapper：

    python tools/sync_game_source.py
    .\gradlew.bat assembleDebug

APK：app/build/outputs/apk/debug/app-debug.apk。Linux/macOS 使用 bash gradlew assembleDebug。

当前支持 Android 7+、ARM64。APP 内若已经导入旧版游戏，安装新版 APK 后旧导入文件仍优先加载；请停止游戏厅并恢复内置游戏，或导入同次构建的新版游戏文件，再重新打开 APP。手机热点房主应保持服务运行，好友连接同一热点后扫码进入公共大厅；iPhone 好友使用浏览器即可。默认产物为调试 APK；不同电脑或 CI 的调试签名可能不同，不能覆盖安装签名不同的 APK。需要长期原位升级 APK 时，应使用同一私有签名密钥（不要提交密钥到仓库）。游戏文件导入无需重新签名或安装 APK。

## 测试

    python game_source/tests/smoke_test.py
    python tools/sync_game_source.py
    python tests/test_android_bridge.py

游戏核心和 Android 桥接测试不需要 Android SDK。原有 Playwright UI 测试仍可通过 npm 安装后运行。
