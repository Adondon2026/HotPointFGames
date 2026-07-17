"""Small lifecycle bridge between Android and the existing game server."""

import json
import threading

import game_hall_lan_v6_2 as game

_lock = threading.RLock()
_server = None
_thread = None
_port = None
_last_error = ""


def _snapshot():
    alive = bool(_thread and _thread.is_alive() and _server)
    return json.dumps(
        {"running": alive, "port": _port if alive else None, "error": _last_error},
        ensure_ascii=False,
    )


def status():
    with _lock:
        return _snapshot()


def start_server(first_port=8000, last_port=8010):
    global _server, _thread, _port, _last_error
    with _lock:
        if _thread and _thread.is_alive() and _server:
            return _snapshot()

        _last_error = ""
        server = None
        bind_errors = []
        for port in range(int(first_port), int(last_port) + 1):
            try:
                server = game.ReliableThreadingHTTPServer((game.HOST, port), game.Handler)
                _port = int(server.server_address[1])
                break
            except OSError as exc:
                bind_errors.append(f"{port}: {exc}")

        if server is None:
            _port = None
            _last_error = "端口 8000-8010 均不可用：" + "; ".join(bind_errors)
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
                    game.flush_state()
                finally:
                    with _lock:
                        if _server is server:
                            _server = None
                            _thread = None
                            _port = None

        _thread = threading.Thread(target=run, name="GameHallHTTP", daemon=True)
        _thread.start()
        return _snapshot()


def _clear_room_for_explicit_stop():
    """End this gathering without losing the host's preferred settings."""
    with game.LOCK:
        previous = game.STATE
        clean = game.fresh_state()
        clean["settings"] = dict(previous.get("settings", clean["settings"]))
        if previous.get("mode") in ("cards", "dice", "draw", "ddz", "chuanma"):
            clean["mode"] = previous["mode"]
        game.STATE = clean
        game.TOKENS.clear()
        game.ACTION_CACHE.clear()
        game.SAVE_EVENT.clear()
    game.flush_state()


def stop_server(clear_room=False):
    global _server, _thread, _port
    with _lock:
        server = _server
        thread = _thread
    if server is not None:
        server.shutdown()
    if thread is not None and thread is not threading.current_thread():
        thread.join(timeout=5.0)
    with _lock:
        if _server is server:
            _server = None
            _thread = None
            _port = None
    if clear_room:
        _clear_room_for_explicit_stop()
    with _lock:
        return _snapshot()
