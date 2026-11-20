"""Falling debris crushes stationary zombies according to vertical impact speed."""
import importlib.util
import os
import tempfile
from pathlib import Path

os.environ['GAMEHALL_DATA_DIR'] = tempfile.mkdtemp(prefix='siege_crush_')
root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('game', root / 'dist/game_hall_lan_v6_2.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

stone = dict(id=5002, kind='stone', side=0, x=480., y=310.,
             w=36, h=44, hp=75., max=75., vx=0., vy=280., generated=True)
wood = dict(stone, kind='wood', h=38, hp=42., max=42.)
assert g._siege_falling_crush_damage(stone, 119) == 0
assert g._siege_falling_crush_damage(stone, 240) > g._siege_falling_crush_damage(wood, 240)
assert g._siege_falling_crush_damage(stone, 440) > g._siege_falling_crush_damage(stone, 240)
assert g._siege_falling_crush_damage(stone, 20000) <= 90

def trial(initial_velocity):
    r = g._siege_new('crush', 'test', True, 0, 'classic', 'off', 0)
    g._siege_v24_setup(r)
    g._siege_trial_reset(r)
    r['items'] = []
    r['wind'] = 0
    r['bodies'] = [b for b in r['bodies'] if b['kind'] in ('core', 'cannon')]
    ground = g._siege_floor_body(r, 480, 28)
    zombie = dict(id=5001, side=2, kind='zombie', zombieType='walker',
                  x=480., y=ground-14., w=28, h=28,
                  hp=160., max=160., vx=0., vy=0., fixed=True)
    block = dict(stone)
    block['y'] = zombie['y']-zombie['h']/2-block['h']/2-(40 if initial_velocity else 1)
    block['vy'] = initial_velocity
    r['bodies'].extend([zombie, block])
    g._siege_trial_fire(r, 85, 15, {})
    return zombie['hp'], r['event']

high, event = trial(280.)
low, _ = trial(0.)
assert high < 160., f'fast overhead stone must damage zombie, got {high}'
assert low == 160., f'resting/short drop should not damage zombie, got {low}'
assert any(x[0]=='crush' for x in event.get('behaviorEvents',[])), 'replay should record impact'
print('Siege debris crush: height/speed, stone vs wood, real fixed-zombie impact, resting threshold PASS')
