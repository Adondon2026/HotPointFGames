# 游戏核心 v6.2（唯一开发源码）

五个游戏按规则、动作和网页分文件维护；构建后仍是零依赖 Python 单文件。此目录从用户提供的 v6.2 模块化源码同步，生成内容与原 APK 内置游戏一致。

- parts/games/：各游戏后端和动作
- web/games/：各游戏 HTML / JS
- parts/01_draw_constants.pyfrag：981 条中文词库（运行时唯一来源）
- web/00_common.js、web/90_common.js：房间与通信、公共 UI

运行 python build.py，生成 dist/game_hall_lan_v6_2.py 和 .txt。不要手改 APK 内的生成文件。
