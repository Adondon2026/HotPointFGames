# HotPointFGames · ZMZ v0.19.0 更新说明

> 发布分支：`Zmz_dev`  
> 统一版本号：**ZMZ v0.19.0**（Android `versionName = 0.19.0-ZMZ`、`versionCode = 6`）  
> 更新类型：拆家大战声音与可选增益 + ZMZ 专用 Android 安装包 + 独立游戏在线更新通道  
> 源码仓库：`Adondon2026/HotPointFGames`

本次把此前完成的**音乐、炮声和增益筛选**与本次的**Android 独立安装及独立更新**合并为一次 **ZMZ v0.19.0** 交付，不拆分发布为多个新版本。历史版本（如拆家 v0.18.2）仍作为上游开发记录保留。

## 一、拆家大战：开局增益筛选

- 在房主的「拆家大战 → 设置」内，提供全部 **16 种增益**的独立复选框。
- 可以**全选 / 全不选 / 任意组合**。取消全部勾选意味着当局不产生任何增益道具。
- 增益筛选由**服务器**执行，初始生成、不同地图、道具拾取后的再次刷新都只能生成已选种类。单人和双人对战均适用。
- 房主设置对整间房双方生效，下一局继续沿用房主的增益配置；未设置的旧房间默认全部启用。
- 原有「自动增益」与「战术储备」两种消耗方式保持不变。

## 二、拆家大战：音效及音乐

- 战场内有 **「海浪琶音 → 轻快像素 → 关闭」**三态背景音乐切换按钮，随时切换。
- 「海浪琶音」采用 maj7 / m7 交替及渐进琶音，海浪底噪显著降低。
- 「轻快像素」是原创的活泼复古平台游戏风格音乐，不使用现成游戏配乐旋律。
- 保留可爱基础开炮声；巨型弹、强力弹、分裂弹、冲击波、弹跳弹、穿透弹、黑洞、瞬移、建造等增益按类型叠加不同音调效果。
- **炮声单独开关**，不受背景音乐开关影响；开关选择保存在当前设备浏览器本地。
- 游戏实际集成采用内置 **Web Audio 原创合成**，无须额外 MP3 下载，和独立试听文件的合成音色可能存在细微差异；部分手机要求玩家先触碰战场才能允许播放。

## 三、Android ZMZ APK：与主线并存

| 项目 | 师兄主线 | ZMZ v0.19.0 开发版 |
| --- | --- | --- |
| GitHub 分支 | `main` | `Zmz_dev` |
| 调试版应用包名 | `com.chuanmahjong.nearby.debug` | **`com.chuanmahjong.nearby.zmz.debug`** |
| 安装后应用名称 | 热点游戏厅 | **热点游戏厅 ZMZ** |
| Android 版本 | 主线独立维护 | **0.19.0-ZMZ（versionCode 6）** |
| 构建输出文件 | `app-debug.apk` | **`HotPointFGames-ZMZ-v0.19.0-debug.apk`** |
| Actions 下载条目 | `HotPointFGames-Android` | **`HotPointFGames-ZMZ-v0.19.0-Android`** |
| 游戏在线更新发布标签 | `game-...` | **`zmz-game-v0.19.0-...`** |

**注意：只重命名 APK 文件不能并存安装。** 本次同时更换了 Android `applicationId`，因此 Android 系统会把 ZMZ 版识别为**不同应用**。两版可以分别安装，互不覆盖；各自的应用私有账户、积分和服务器存档也不会自动互通。Android 源码 `namespace` 保持原值，以保持 Kotlin、R 和 Chaquopy 代码兼容。

## 四、在线更新通道隔离

**ZMZ 版**在 APP 启动或手动点击「检查更新」时，访问同一个仓库的 GitHub Releases，但只接受符合 `zmz-game-vX.Y.Z-<run>-<attempt>-<sha>` 格式的发布标签。本版本生成的是 `zmz-game-v0.19.0-...`。

**发布流程：** `Zmz_dev` 提交游戏代码 → `Game files` 自动测试与单文件构建 → 生成 SHA-256 更新清单 → 发布该分支专用 `zmz-game-v0.19.0-...` Release → ZMZ APK 检查并提供下载；不会接受师兄主线的 `game-...` Release。反过来，师兄的原 APK 只接受原先的 `game-...` 标签，不识别 `zmz-game-v0.19.0-...`。

ZMZ 专用 Release 不会抢占 GitHub 仓库的全局「Latest」主线发布标记。更新下载采用 HTTPS、文件大小限制、SHA-256 校验和安全的原子替换／回退机制。

**在线更新的是游戏 Python 单文件，不是 Android APK 安装包。** 更新需要互联网；有更新时还需先停止游戏厅并确认下载，安装完成后重启 APP。修改 Android 原生宿主代码（例如未来再修改更新源或权限）时，仍需重新构建安装新版 APK。

## 五、取得本次 APK

1. 打开 GitHub 仓库的 **Actions → Android build**，选择来自 `Zmz_dev` 的**成功**运行记录。
2. 页面底部 **Artifacts** 下载 **`HotPointFGames-ZMZ-v0.19.0-Android`**。
3. 解压得到 **`HotPointFGames-ZMZ-v0.19.0-debug.apk`**，安装到 Android 手机即可。
4. 桌面上可同时保留师兄的「热点游戏厅」和新的「热点游戏厅 ZMZ」。
5. 此后仅改游戏规则或音乐时，可通过 ZMZ 游戏在线更新通道接收新游戏单文件，不必每次重新装 APK。

若需手动构建：Actions → Android build → **Run workflow** → 分支选择 **`Zmz_dev`**。电脑本地构建需满足原项目构建环境，执行 `python tools/sync_game_source.py` 后 `gradlew assembleDebug`，输出在 `app/build/outputs/apk/debug/`。

## 六、版本验证与注意事项

- 检查应用包名、APK 文件名、版本号与 Release 标签匹配；确认 ZMZ 应用只识别 ZMZ Release。
- 执行原有拆家测试、增益筛选回归测试和 Android 编译工作流。
- 实机重点检查：两 APP 并存、两边账号与积分互不影响、双背景乐切换、炮声独立开关和动态刷新道具筛选。
- Debug APK 是测试签名版本；后续如需长期通过安装新版 APK 原位升级 ZMZ 版，仍需保持签名一致。安装包可以并存不等于它们能够共用同一份本地存档。
- 本次全部修改仅提交 `Zmz_dev`，**不修改 `main`**。
