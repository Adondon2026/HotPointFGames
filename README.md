# 热点游戏厅 Android 外壳

这是“局域网游戏厅 v6.2”的最小 Android 封装：房主手动开启热点，APK 内置并启动 Python HTTP 服务，朋友连接热点后扫码进入。

## 同步游戏源码

```powershell
python tools/sync_game_source.py
```

该命令会构建同级目录中的 `game_hall_modular_v6_2_source`，并把单文件发布版复制到 APK 的 Python 源码目录。

## 构建

使用 Android Studio 打开本目录，或运行：

```powershell
.\gradlew.bat assembleDebug
```

当前仅打包 `arm64-v8a`，最低支持 Android 7。
