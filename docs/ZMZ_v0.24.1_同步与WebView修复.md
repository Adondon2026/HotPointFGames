# ZMZ v0.24.1｜同步学长主线与 Android WebView 滚动修复

## 基线与隔离
- 学长 `main` 基线：`6aa32a7c914b0761588ca88e22608a94d6100723`（2026-11-17）。
- ZMZ 基线：`51382cf3a24769a4c35b74e3c63cfe91b0e00c5c`。
- 整合使用一个双父 merge commit，优先采用 main 最新游戏规则、Android 更新器及配套完整测试，不对 main 提交任何修改。
- 仅专门 `-PzmzBuild=true` 的 APK 使用 `com.chuanmahjong.nearby.zmz.debug`，版本 `0.24.1-ZMZ`，与原始 APP 并存；普通 main 构建仍采用 `1.4` / versionCode 5。
- 独立在线更新频道是 `zmz-game-v0.24.1-*`，不会污染主线 Release latest；游戏网页显示使用 `build.py` 的 `GAME_DISPLAY_VERSION`，随在线升级变化。

## 完整同步的上游改动
- 保留学长新的拆家大战 v0.24 规则、组合编辑器、弹种触发控制、弹药数量与层数限制、移动炮台/物块物理和特殊地图。
- 完整同步新增的僵尸协作玩法、炮台朝向调整、窄屏侧栏、库存操作、道具选项与回归测试。
- 保留 v0.20.2 的负面弹发射偏角、重弹重力、推进恒速 2 秒/层、连续/分裂弹继承效果和建筑支撑坠落能力。这些相关实现已存在于学长最新 main 并由其新增回归测试覆盖。
- 更新 Android 宿主上游 `GameUpdates.kt` 的 HTTPS / 重定向 / 文件校验机制，同时将 ZMZ 频道检查限定为版本匹配的 ZMZ 发布。

## 第二阶段：内嵌 WebView 嵌套滚动修复（代码已实现）
- 同步之后，把 `siegeBuffChoices`（内层增益）改为独立限高滚动（45dvh、最高 420px），外层 `settingsModal .sheet` 保持可独立滚动。设置头部保持可见。
- Android `GameActivity` 在 `onPageFinished` 给页面注入 `zmz-webview` 标记。只有该标记存在，增益清单才改为 `touch-action:none` 并由 `zmz_scroll.js` 非 passive 的 `touchmove` 手动控制 `scrollTop`、阻止默认滚动及事件向外传播；到达内层滚动顶部和底部仍不会滑动外层。普通浏览器继续使用原生滚动，不受影响。
- 增益清单底部新增「收起增益设置 · 返回其他选项」按钮；关闭按钮置顶。Android APP 主界面新增「在浏览器打开游戏（兼容模式）」入口，连接**同一个 APP 托管的 `127.0.0.1` HTTP 服务**，不修改服务器、二维码、局域网/离线联机方式。
- 游戏规则和在线更新可通过已有 APK 在线安装；原生 WebView 识别、手势修复及浏览器入口必须安装本次 v0.24.1 APK。

## 验证
- 完整 GitHub 游戏 CI、上游 Playwright 浏览器回归以及 Android Gradle 构建和单元测试。
- 新增内外层滚动隔离的触摸手势测试与 Android WebView 宿主标记检查，重点验证展开、滑动、全选、收起、关闭设置。

### 诊断与选择

当前 APP 打开的是内置 Android System WebView，普通手机浏览器也是 Chromium 家族但版本、触摸默认行为及页面滚动链可能不同。两种客户端的增益设置不一致不能单凭现象断定是硬件缺陷；新版 UI 原本就存在两个可能抢手势的滚动容器。本补丁同时修 CSS 和 WebView 手势归属。

**默认保留内置 WebView**：可直接从房主 APP 进入游戏，服务端不受手机前后台切换影响。若特定手机系统仍有问题，可点击新增的「在浏览器打开游戏（兼容模式）」，使用外部 Chrome/系统浏览器打开 localhost，同样参与房主游戏。旧 APK 在线更新游戏文件只能得到 CSS/JS 修改；要有 WebView 标记及新增兼容入口，需安装 **ZMZ v0.24.1 APK**。
