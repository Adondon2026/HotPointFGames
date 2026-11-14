# ZMZ v0.19.1 拆家大战补丁说明

> 分支：`Zmz_dev` | 基于 `v0.19.0` 的修复补丁 | 不修改 `main`

## 修复一：从游戏厅进入拆家大战时卡在“正在进入对局”

**根因：** `v0.19.0` 把 `siege_audio.js` 拼接在 `siege.html` 内联脚本末尾，而游戏厅入口在脚本末尾、音频模块初始化前就会执行 `enter('state')`。该函数调用 `siegeAudio.unlock()`，触发 `ReferenceError: Cannot access 'siegeAudio' before initialization`，导致加载流程中断。与音乐文件大小无关。

**修复：** 在 `build.py` 组装独立拆家页面时，先在 `<script>` 开头放置音频模块，再初始化游戏逻辑；无用户点击的自动进入不再提前启动音频；同时为进入失败提供明确提示，不再无限显示加载文案。

## 修复二：设置弹窗仅看到增益，旧选项难以使用且手机无法滚动

**根因：** `v0.19.0` 直接把 16 个勾选项塞进原有设置表单网格，却只给独立拆家页加样式，没有给游戏厅设置页对应的样式。原有 `liteSettings()` 又遍历所有后代 `label`（含新增的复选框），布局和显示切换互相干扰。

**修复：** 保留原来全部设置字段的顺序与操作。新的增益选择放入**默认折叠**的独立区域，点击展开才显示 16 项；两列复选框紧凑排列且独占设置网格整行。设置面板恢复明确的 `overflow-y:auto`、移动端触摸滚动和每次打开时回到顶部。标签遍历只针对原始设置项。

## 构建隔离：尽量保持上游 Android 源码结构

- 不再把 `com.chuanmahjong.nearby.zmz` 写死在 `app/build.gradle`。正常构建使用上游原始 `applicationId` / `versionName` / `versionCode`。
- 仅在 CI 构建 `Zmz_dev` APK 时传入 `-PzmzBuild=true`，条件生成独立 `applicationId=com.chuanmahjong.nearby.zmz.debug` 和 `HotPointFGames-ZMZ-v0.19.1-debug.apk`，可以与主线 APP 共存。
- Android 清单使用兼容原源码的完整 Activity/Service 类名和条件化应用标签；恢复上游的 `MainActivity.kt`、`GameServerService.kt`、`strings.xml` 内容，便于后续合并。
- `GameUpdates.kt` 根据构建标记选择更新通道：**ZMZ APK** 只接收 `zmz-game-...`，原构建只接收 `game-...`。不再把开发通道硬编码为所有 APK 的默认设置。
- GitHub Actions 同时保持两套逻辑：主线正常构建；仅 `Zmz_dev` 构建专属安装包和 `zmz-game-v0.19.1-...` 游戏更新。
- `v0.19.0` 的更新文档保留作为历史记录；此文件是单独的 `v0.19.1` 修复记录。

## 验证

新增脚本 `game_source/tests/test_siege_ui_regression.js` 检查独立页面脚本语法、音频初始化顺序、自动进入对局以及设置窗口的旧设置保留、增益折叠和移动端滚动；在 GitHub Actions 中与现有 Python 游戏测试、Android APK 构建一同执行。

仍需在真实手机上人工验证：游戏厅进入拆家对局、手机纵向滑动/选项勾选、背景音乐与炮声切换、两款 APP 共存。

> 安装包与 GitHub Release 由 `Zmz_dev` 的 CI 构建与发布。仅改动本补丁涉及的文件，不合并到 `main`。
