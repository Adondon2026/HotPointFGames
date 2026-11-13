#!/usr/bin/env python3
"""Run the local preview from its folder, open default browser automatically."""
from pathlib import Path
import os, sys, socket, threading, webbrowser, runpy, time
root=Path(__file__).resolve().parent
os.environ.setdefault('GAMEHALL_DATA_DIR',str(root/'local_data'))
for port in range(8000,8011):
    with socket.socket() as sock:
        try: sock.bind(('0.0.0.0',port)); break
        except OSError: continue
else: raise SystemExit('8000–8010 均被占用，请停止旧游戏厅后再运行。')
os.environ['GAMEHALL_PORT']=str(port)
url=f'http://127.0.0.1:{port}/'
def open_when_ready():
    for _ in range(60):
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.3): pass
            webbrowser.open(url); return
        except OSError: time.sleep(.2)
threading.Thread(target=open_when_ready,daemon=True).start()
print('HotPointFGames Lite: '+url,flush=True)
runpy.run_path(str(root/'dist'/'game_hall_lan_v6_2.py'),run_name='__main__')
