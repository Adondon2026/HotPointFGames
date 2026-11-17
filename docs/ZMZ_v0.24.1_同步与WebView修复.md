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

## 待完成：内嵌 WebView 嵌套滚动修复
- 同步之后，对 `settingsModal`（外层设置）及 `siegeBuffChoices`（内层增益）明确区分滚动，阻止滑动内层时手势传到外层。
- 在 Android WebView 环境做保底的非 passive touchmove 处理。普通浏览器保持浏览器原生惯性滚动，不进入保底路径。
- 保留顶部关闭/返回及增益折叠操作；再提供可选的外部浏览器打开本机服务器入口，供个别系统 WebView 出现兼容问题时使用。
- 游戏规则和在线更新可通过已有 APK 在线安装；原生 WebView 识别、手势修复及浏览器入口必须安装本次 v0.24.1 APK。

## 验证
- 完整 GitHub 游戏 CI、上游 Playwright 浏览器回归以及 Android Gradle 构建和单元测试。
- 新增内外层滚动隔离的触摸手势测试与 Android WebView 宿主标记检查，重点验证展开、滑动、全选、收起、关闭设置。
