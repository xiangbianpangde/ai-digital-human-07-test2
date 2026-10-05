#!/usr/bin/env python3
"""Read-only library acceptance tests; optionally append a new JSON evidence file."""
import argparse
import ast
import copy
import hashlib
import io
import json
import subprocess
import unittest
from datetime import datetime
from pathlib import Path
import catalog
import render
import repair
import run

INDEX = json.loads((catalog.OUT/'方法库.json').read_text())
READY = [f'C{i:02d}' for i in range(1,11)]+['P01','P02','P04']+[f'N{i:02d}' for i in range(1,6)]
REJECTED = ['P03','P05','P06']
BLOCKED = ['P07','P08','P09','P10']

def changed(mid):
    c=copy.deepcopy(INDEX)
    return c,next(m for m in c['methods'] if m['id']==mid)

class Gates(unittest.TestCase):
    def test_inventory(self):
        self.assertEqual(INDEX['method_count'],25)
        self.assertEqual({m['id'] for m in INDEX['methods']},set(READY+REJECTED+BLOCKED))
        self.assertEqual([m['id'] for m in INDEX['methods'] if m['production_ready']],READY)

    def test_all_ready_select(self):
        for mid in READY:
            with self.subTest(mid=mid): self.assertTrue(catalog.choose(INDEX,mid))

    def test_rejected_cannot_be_promoted_by_flag(self):
        for mid in REJECTED:
            c,m=changed(mid);m['production_ready']=True
            with self.subTest(mid=mid),self.assertRaises(ValueError): catalog.choose(c,mid)

    def test_counterexamples_explicit_experiment_only(self):
        for mid in REJECTED:
            with self.subTest(mid=mid): self.assertTrue(catalog.choose(INDEX,mid,True))

    def test_blocked_even_in_experiment(self):
        for mid in BLOCKED:
            with self.subTest(mid=mid),self.assertRaises(ValueError): catalog.choose(INDEX,mid,True)

    def test_policy_drift(self):
        c,m=changed('P03');m['policy']='default';m['visual']='accept';m['production_ready']=True
        with self.assertRaisesRegex(ValueError,'Policy/type drift'):catalog.choose(c,'P03')

    def test_evidence_hash_drift(self):
        c,m=changed('C01');m['evidence'][0]['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Evidence drift'):catalog.choose(c,'C01')

    def test_recipe_drift(self):
        c,m=changed('C01');m['recipe']['start']['fov']=95
        with self.assertRaisesRegex(ValueError,'Recipe drift'):catalog.choose(c,'C01')

    def test_property_mismatch(self):
        c=copy.deepcopy(INDEX);c['property']['url']='https://example.com/another-property'
        with self.assertRaisesRegex(ValueError,'property/schema'):catalog.choose(c,'C01')

    def test_fact_drift(self):
        c=copy.deepcopy(INDEX);c['property']['fact_contract']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Fact drift'):catalog.choose(c,'N01')

    def test_station_drift(self):
        c=copy.deepcopy(INDEX);c['stations']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Scene/station drift'):catalog.choose(c,'C01')

    def test_input_refusal(self):
        for name in ['selling-01','door-02','../establish-03']:
            with self.subTest(name=name),self.assertRaises(ValueError):render.accepted(name)

    def test_append_only(self):
        with self.assertRaises(FileExistsError):
            run.capture(catalog.EVIDENCE/'establish-04/recipe.json','establish-04','methodlib')
        with self.assertRaises(FileExistsError):
            render.render(catalog.EVIDENCE/'identity-01/recipe.json','identity-01')
        with self.assertRaises(FileExistsError):
            run.review('establish-04','accept','must not overwrite')

    def test_unsafe_capture_id(self):
        with self.assertRaises(ValueError):
            run.capture(catalog.EVIDENCE/'establish-04/recipe.json','../unsafe','methodlib')

    def test_guard_results(self):
        g=json.loads((catalog.EVIDENCE/'browser-guards.json').read_text())['result']
        self.assertEqual(len(g['guards']),5)
        self.assertTrue(all(x['blocked'] for x in g['guards']))
        self.assertTrue(g['capture']['complete']);self.assertIsNone(g['capture']['error'])

    def test_safe_variant_selection(self):
        self.assertEqual(INDEX['variant_count'],6)
        for vid in repair.VARIANTS:
            with self.subTest(vid=vid):self.assertEqual(catalog.choose(INDEX,vid)['variant_id'],vid)

    def test_variant_parent_not_promoted(self):
        for vid,d in repair.VARIANTS.items():
            parent=next(m for m in INDEX['methods'] if m['id']==d['parent'])
            self.assertFalse(parent['production_ready']);self.assertIn(vid,parent['safe_alternatives'])
            with self.assertRaises(ValueError):catalog.choose(INDEX,d['parent'])

    def test_variant_executor_drift(self):
        c=copy.deepcopy(INDEX);c['variants'][0]['execution']['code']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'executor drift'):catalog.choose(c,'P03V1')

    def test_variant_identity_drift(self):
        c=copy.deepcopy(INDEX);c['variants'][0]['parent_method']='P01'
        with self.assertRaisesRegex(ValueError,'identity drift'):catalog.choose(c,'P03V1')

    def test_graphic_layer_limits(self):
        self.assertEqual(repair.layer('P03V1',60).getpixel((360,600))[3],0)
        self.assertEqual(repair.layer('P05V1',60).getpixel((24,600))[3],0)
        self.assertEqual(repair.layer('P05V1',60).getpixel((23,600))[3],190)
        self.assertEqual(repair.layer('P06V1',60).getpixel((360,600)),(255,255,255,8))
        self.assertEqual(repair.layer('P08V1',60).getpixel((360,600))[3],0)
        for vid in ['P07V1','P09V1']:
            alpha=repair.layer(vid,60).getchannel('A')
            self.assertEqual(alpha.getextrema(),(255,255))

    def test_superseded_variant_refused(self):
        for name in ['graphic-occlusion-01','tile-reveal-01']:
            with self.assertRaisesRegex(ValueError,'Superseded'):catalog.validate_take(catalog.EVIDENCE/name)

    def test_encoded_full_occlusion(self):
        for name in ['graphic-occlusion-02','tile-reveal-02']:
            p=subprocess.run(['ffmpeg','-v','error','-i',str(catalog.EVIDENCE/name/'layer.mov'),'-vf','select=eq(n\\,60)','-frames:v','1','-f','rawvideo','-pix_fmt','rgba','pipe:1'],capture_output=True,check=True)
            im=repair.Image.frombytes('RGBA',(720,1280),p.stdout)
            self.assertEqual(im.getchannel('A').getextrema(),(255,255))

    def test_station_mapping(self):
        s=json.loads((catalog.OUT/'点位.json').read_text())
        self.assertEqual(len(s['points']),27)
        self.assertEqual({p['pano'] for p in s['points']},set(range(27)))
        self.assertTrue(all(p['metric_clearance']=='unverified' for p in s['points']))
        self.assertTrue(all(abs(p['native_eye_height']-(p['position']['y']-p['standingPosition']['y']))<1e-6 for p in s['points']))
        self.assertAlmostEqual(min(p['native_eye_height'] for p in s['points']),1.155408)
        self.assertEqual([p['pano'] for p in s['points'] if p['accepted_methods']],[1,2,5,9,10,25])
        self.assertEqual(next(p['room'] for p in s['points'] if p['pano']==21),'衣帽间')

def integrity():
    refs=[INDEX['property']['fact_contract'],INDEX['scene_snapshot'],INDEX['stations']]
    videos=set()
    for m in INDEX['methods']+INDEX.get('variants',[]):
        refs+=m['evidence']
        if 'code' in m.get('execution',{}):refs.append(m['execution']['code'])
        if 'assessment' in m:refs.append(m['assessment'])
        if 'deferred_decision' in m:refs.append(m['deferred_decision'])
        for source in m['sources']:refs+=source.get('assets',[source])
        for t in m['tests']:
            if t['technical']=='passed': videos.add(catalog.ROOT/t['path']/'take.mp4')
    unique={r['path']:r['sha256'] for r in refs}
    for path,sha in unique.items():
        if catalog.file_record(catalog.ROOT/path)['sha256']!=sha:raise ValueError('Hash drift: '+path)
    decoded=[]
    for video in sorted(videos):
        run.command(['ffmpeg','-v','error','-xerror','-i',str(video),'-f','null','-'])
        decoded.append(str(video.relative_to(catalog.ROOT)))
    endpoints=[]
    for mid in READY:
        m=next(m for m in INDEX['methods'] if m['id']==mid)
        if m['type']!='capture':continue
        take=(catalog.ROOT/next(r['path'] for r in m['evidence'] if Path(r['path']).name=='telemetry.json')).parent
        t=json.loads((take/'telemetry.json').read_text());r=m['recipe'];end=t['marks'][-1]
        if t['running'] or t.get('error') or t.get('exportError') or len(t['samples'])<5:raise ValueError('Incomplete capture: '+mid)
        expected=dict(r['start'])
        for step in r['steps']:
            for k in ('pano','yaw','fov'):
                if k in step:expected[k]=step[k]
        if end['mode']!='Panorama' or end['pano']!=expected['pano']:raise ValueError('Terminal point mismatch: '+mid)
        delta=(end['pose']['longitude']-expected['yaw']+3.141592653589793)%(2*3.141592653589793)-3.141592653589793
        if abs(delta)>.05 or abs(end['pose']['fov']-expected['fov'])>.1:raise ValueError('Terminal pose mismatch: '+mid)
        if any(not 75<=s['pose']['fov']<=85 for s in t['samples']):raise ValueError('FOV outside range: '+mid)
        endpoints.append({'method':mid,'take':take.name,'terminal_pano':end['pano'],'terminal_yaw':end['pose']['longitude'],'fov':end['pose']['fov']})
    for p in Path(__file__).parent.glob('*.py'):ast.parse(p.read_text())
    run.command(['node','--check',str(Path(__file__).parent/'take.js')])
    return {'hashes_verified':len(unique),'decoded_all_frames':decoded,'capture_endpoints':endpoints}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out');a=p.parse_args()
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Gates))
    if not result.wasSuccessful():raise RuntimeError(stream.getvalue())
    checks=integrity()
    report={'schema':'methodlib-acceptance/v1','at':datetime.now().astimezone().isoformat(),'passed':True,'unit_tests':result.testsRun,'unit_log':stream.getvalue(),
            'ready':READY,'safe_variants_ready':[v['id'] for v in INDEX.get('variants',[]) if v['production_ready']],'visual_rejected':REJECTED,'blocked_not_runtime_tested':BLOCKED,**checks,
            'code':[{ 'path':str(f.relative_to(catalog.ROOT)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(Path(__file__).parent.iterdir()) if f.suffix in ['.py','.js']],
            'limits':['P10 explicitly deferred by user: no paid calls, no neural-interpolation acceptance','safe variants do not promote original prohibited effects','metric_clearance remains unverified','visual contact sheets are sampled, not full-frame human playback','N methods are silent text demos, not voice-over','Shot4 approval and Shot5 authorization unchanged']}
    if a.out:
        dest=Path(a.out)
        with dest.open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
