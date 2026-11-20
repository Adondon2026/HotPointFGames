"""V24 zombie direct-hit kinetic scaling uses actual contact speed and descent."""
import importlib.util,os,tempfile
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='siege_kinetic_')
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('g',root/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
scale=g._siege_projectile_kinetic_scale
assert .8<=scale(0,0)<scale(180,0)<scale(420,0)<scale(800,0)<=1.55
assert scale(420,320)>scale(420,-320), 'descent adds modest kinetic energy'
assert 1.0<scale(380,250)<1.5
assert scale(3000,3000)<=1.55
print('Siege zombie projectile kinetics: increasing contact speed, downward bonus, finite cap PASS')
