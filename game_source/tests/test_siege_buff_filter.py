"""Allowlist regression: initial items, maps, refills, rematches, and empty whitelist."""
import os, pathlib, tempfile, importlib.util, random
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
root=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
random.seed(40412)
ALL=set(g._SIEGE_ITEMS)
assert len(ALL)==16
for allowed in ([],['big'],['splitshot','shock'],['gunteleport','heal'],list(ALL)):
    for mode in ('classic','standard','random','sky','floating','movingwall'):
        r=g._siege_new('Alice','alice',True,13,mode,'off',0,'stock',allowed)
        assert set(g._siege_allowed(r))==set(allowed)
        assert len(r['items'])== (13 if allowed else 0)
        assert set(x['kind'] for x in r['items']).issubset(set(allowed))
        if allowed:
            r['items'].clear()
            r['respawns']=[dict(id=1,kind='shield',x=250,y=200,r=15,slot=1,readyAt=0)]
            g._siege_refill(r)
            assert len(r['items'])==1 and r['items'][0]['kind'] in allowed
        g._siege_rematch(r)
        assert set(x['kind'] for x in r['items']).issubset(set(allowed))
# Stored selections that contain only rare kinds must still generate items.
r=g._siege_new('Alice','alice',True,13,'classic','off',0,'auto',['blackhole'])
assert len(r['items'])==13 and all(x['kind']=='blackhole' for x in r['items'])
# No whitelist is backward-compatible with existing matches.
r=g._siege_new('Alice','alice',True)
assert set(g._siege_allowed(r))==ALL
print('Siege allowed-buffs tests passed.')
