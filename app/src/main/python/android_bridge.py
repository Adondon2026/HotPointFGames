"""Stable Android runtime for trusted, locally imported single-file game builds."""
import ast
import importlib
import json
import os
import shutil
from pathlib import Path
import sys
import threading
import types

_lock = threading.RLock()
_server = None
_thread = None
_port = None
_last_error = ""
_warning = ""
_source = "builtin"
_restart_required = False
game = None

BUILTIN = "game_hall_lan_v6_2"
ACTIVE = "gamehall_import.py"
PENDING = "gamehall_import.pending"
FAILED = "gamehall_import.failed.py"
BACKUP = "gamehall_import.previous.py"
MAX_BYTES = 4 * 1024 * 1024
_REQUIRED_CLASSES = {"Handler", "ReliableThreadingHTTPServer"}
_REQUIRED_FUNCTIONS = {"fresh_state", "flush_state"}
_REQUIRED_VALUES = {"HOST", "STATE", "LOCK", "TOKENS", "ACTION_CACHE", "SAVE_EVENT"}


def _snapshot():
    alive = bool(_thread and _thread.is_alive() and _server)
    return json.dumps({"running": alive, "port": _port if alive else None,
                       "error": _last_error, "warning": _warning,
                       "source": _source, "restartRequired": _restart_required}, ensure_ascii=False)


def status():
    with _lock:
        return _snapshot()


def _check_file(path):
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("游戏文件不能超过 4 MB")
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(path))
    classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
    functions = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    if not _REQUIRED_CLASSES <= classes or not _REQUIRED_FUNCTIONS <= functions:
        raise ValueError("不是兼容的游戏厅单文件，请从项目 build.py 构建")
    return compile(tree, str(path), "exec")


def _stopped():
    return _server is None and not (_thread and _thread.is_alive())


def install_game(directory):
    """Validate without executing and atomically promote a private staged file."""
    global _restart_required
    with _lock:
        pending = Path(directory) / PENDING
        try:
            if not _stopped():
                raise RuntimeError("请先停止游戏厅")
            _check_file(pending)
            active = Path(directory) / ACTIVE
            backup = Path(directory) / BACKUP
            if active.is_file():
                staging = backup.with_suffix(".tmp")
                try:
                    shutil.copyfile(active, staging)
                    os.replace(staging, backup)
                finally:
                    staging.unlink(missing_ok=True)
            else:
                backup.unlink(missing_ok=True)
            os.replace(pending, active)
            _restart_required = True
            return json.dumps({"ok": True}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
        finally:
            pending.unlink(missing_ok=True)


def restore_builtin(directory):
    global _restart_required
    with _lock:
        try:
            if not _stopped():
                raise RuntimeError("请先停止游戏厅")
            (Path(directory) / ACTIVE).unlink(missing_ok=True)
            (Path(directory) / BACKUP).unlink(missing_ok=True)
            _restart_required = True
            return json.dumps({"ok": True}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)


def _load_game(directory=None):
    global game, _source, _warning
    if game is not None:
        return game
    if directory:
        path = Path(directory) / ACTIVE
        for attempt in range(2):
            if not path.is_file():
                break
            module = types.ModuleType("gamehall_imported")
            module.__file__ = str(path)
            try:
                code = _check_file(path)
                sys.modules[module.__name__] = module
                exec(code, module.__dict__)
                missing = [key for key in _REQUIRED_CLASSES | _REQUIRED_FUNCTIONS | _REQUIRED_VALUES
                           if not hasattr(module, key)]
                if missing:
                    raise ValueError("缺少运行接口: " + ", ".join(sorted(missing)))
                game = module
                _source = "imported"
                return game
            except Exception as exc:
                sys.modules.pop(module.__name__, None)
                _warning = f"导入版加载失败：{type(exc).__name__}: {exc}"
                try:
                    os.replace(path, Path(directory) / FAILED)
                except OSError:
                    pass
                backup = Path(directory) / BACKUP
                if attempt == 0 and backup.is_file():
                    try:
                        os.replace(backup, path)
                        _warning += "；已恢复上一个游戏版本"
                        continue
                    except OSError:
                        pass
                _warning += "；已使用内置版"
                break
    game = importlib.import_module(BUILTIN)
    _source = "builtin"
    return game


def start_server(first_port=8000, last_port=8010, directory=None):
    global _server, _thread, _port, _last_error
    with _lock:
        if _thread and _thread.is_alive() and _server:
            return _snapshot()
        _last_error = ""
        if _restart_required:
            _last_error = "游戏文件已更换，请重新打开 APP"
            return _snapshot()
        try:
            runtime = _load_game(directory)
        except Exception as exc:
            _last_error = f"游戏加载失败：{type(exc).__name__}: {exc}"
            return _snapshot()
        server = None
        bind_errors = []
        for port in range(int(first_port), int(last_port) + 1):
            try:
                server = runtime.ReliableThreadingHTTPServer((runtime.HOST, port), runtime.Handler)
                _port = int(server.server_address[1])
                break
            except OSError as exc:
                bind_errors.append(f"{port}: {exc}")
        if server is None:
            _port = None
            _last_error = "可用端口不足：" + "; ".join(bind_errors)
            return _snapshot()
        _server = server

        def run():
            global _server, _thread, _port, _last_error
            try:
                server.serve_forever(poll_interval=0.3)
            except BaseException as exc:
                with _lock:
                    _last_error = f"服务器异常停止：{type(exc).__name__}: {exc}"
            finally:
                try:
                    server.server_close()
                    runtime.flush_state()
                finally:
                    with _lock:
                        if _server is server:
                            _server = _thread = _port = None
        _thread = threading.Thread(target=run, name="GameHallHTTP", daemon=True)
        _thread.start()
        return _snapshot()


def _clear_room_for_explicit_stop():
    if game is None:
        return
    with game.LOCK:
        previous = game.STATE
        clean = game.fresh_state()
        clean["settings"] = dict(previous.get("settings", clean["settings"]))
        if previous.get("mode") in ("cards", "dice", "draw", "ddz", "chuanma"):
            clean["mode"] = previous["mode"]
        game.STATE = clean
        game.TOKENS.clear()
        game.ACTION_CACHE.clear()
        # New multi-room releases keep independent room records; old imports still work.
        rooms = getattr(game, 'ROOMS', None)
        if isinstance(rooms, dict):
            rooms.clear()
        siege_rooms = getattr(game, '_SIEGE_ROOMS', None)
        if isinstance(siege_rooms, dict):
            siege_rooms.clear()
        game.SAVE_EVENT.clear()
    game.flush_state()


def stop_server(clear_room=False):
    global _server, _thread, _port, _last_error
    with _lock:
        server, thread = _server, _thread
    if server is not None:
        server.shutdown()
    if thread is not None and thread is not threading.current_thread():
        thread.join(timeout=5.0)
    with _lock:
        if thread and thread.is_alive():
            _last_error = "服务器仍在退出，请稍后重试"
            return _snapshot()
        if _server is server:
            _server = _thread = _port = None
    if clear_room:
        _clear_room_for_explicit_stop()
    with _lock:
        return _snapshot()
