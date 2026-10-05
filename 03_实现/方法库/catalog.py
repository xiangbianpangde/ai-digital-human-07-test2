#!/usr/bin/env python3
"""Deterministic merged index. Readiness is derived from immutable take evidence."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / '08-真人录制/介绍与转场方法库'
ASSETS = ROOT / '05_资产库/06_房产摄影运镜模式库'
OUT = ASSETS / 'AI执行'
EVIDENCE = ROOT / '04_测试与验收/方法库实测'
# Canonical id, title, policy, implementation, description. No untested paths invented.
DEFS = [
 ('C01','先建立空间全貌','default','capture','固定全貌，交代窗、墙、地面关系。'),
 ('C02','连续真实运镜','default','capture','已测P9→P1→P2为后退展开；只沿相邻点，不自动倒置为向前推镜。'),
 ('C03','穿门推进／穿门转场','default','capture','合并两个同义项；实际门框过渡必须核对，邻接不等于无碰撞。'),
 ('C04','娃娃屋俯视飞越','optional','capture','仅开放模型飞出总览→硬切卧室B；原生平滑俯冲有黑场已拒绝。必须标注三维户型示意，不是真人穿顶或碎片破面。'),
 ('C05','推进到卖点','default','capture','相邻点真实坐标位移，落幅停留；不能用FOV推拉冒称dolly。'),
 ('C06','回望空间关系','default','capture','原地缓慢回望，保留空间锚点，不凭方法名称推断房间尺寸。'),
 ('C07','定点微摇','default','capture','固定点位10°–15°小幅摇摄。'),
 ('C08','采光向心全景横扫','optional','capture','缓慢转向可见窗和室内；不保证所有房间适合大幅转头。'),
 ('C09','狭小空间轴线FOV微推','optional','capture','原地FOV 80°→75°；更正旧名中的定焦／微推，不发生dolly位移。'),
 ('C10','反打纵深透视','default','capture','从门口朝室内长轴定格；纵深是画面关系，不承诺12米长轴。'),
 ('P01','硬切','default','post','同房源实录片段直接拼接，最好保留共同空间锚点。'),
 ('P02','短叠化0.25秒','optional','post','30fps取8帧，实际0.267秒；两段真实素材短暂双影，不表示连续空间位移。'),
 ('P03','长叠化0.5秒反例','prohibited','post','保留为对照，不用于正式片。'),
 ('P04','缩放推拉转场','optional','post','已测中心5%数码缩放与硬切；不是相机推进，不开放任意缩放幅度。'),
 ('P05','滑动划像反例','prohibited','post','模板式划像，仅供对照。'),
 ('P06','白闪反例','prohibited','post','实测6帧白闪会抹掉建筑细节；仅供禁用反例。'),
 ('P07','遮挡转场','optional','post','必须实拍完整遮挡帧；不为制造遮挡故意靠墙或手部乱入。'),
 ('P08','甩镜转场','prohibited','post','与平稳看房约束冲突；不执行高速相机甩动。'),
 ('P09','碎片破面法','prohibited','post','与娃娃屋飞越区分；没有碎片处理实现和本房源凭据。'),
 ('P10','AI首尾帧插值','prohibited','post','几何一致性无保证；无模型／凭据时禁止自动调用生成服务。'),
 ('N01','身份与户型开场','default','narrative','房源身份、面积口径、户型图可读；不照搬0.67秒闪卡。'),
 ('N02','卖点交付','default','narrative','一句主张对应一处实录证据，随后留白。'),
 ('N03','互动提问','optional','narrative','单个简短问题，不遮门窗、不捏造家具。'),
 ('N04','补证与回望','default','narrative','用另一处实录支撑同一主张，不移植参考片江景卖点。'),
 ('N05','行动引导','optional','narrative','仅承诺现有可打开的完整VR户型，不许承诺未完成成片。'),
]
ALIASES = {'C03':['穿门转场','穿门推进'], 'C04':['三维破面穿梭法','娃娃屋俯视飞越'], 'C09':['狭小空间轴线微推定焦法'], 'C10':['反打长轴深远纵深透视法']}
SOURCE_IDS = ['C02','P01','P02','P03','C03','P04','P05','P06','C04','P07','P08','P09','P10','C01','C05','C06','C03','C07']
BLOCKS = {'P07':'本轮已验收片段未取得完整遮挡帧，不故意贴墙造遮挡；改用C03或P01。','P08':'平稳运镜政策禁止高速甩动；不现场冒险试拍。','P09':'未接入碎片合成器，历史素材实际是C04，不可冒充。','P10':'未接入生成服务，建筑几何一致性未验证。'}


def rel(path):
    return os.path.relpath(path, ROOT)


def file_record(path):
    return {'path':rel(path), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


PROPERTY = 'https://open.realsee.com/ke/rXel3aPEWkwD4JQn/qrz3DGWoeBMCwu3h2TOlxEYTR8Q0Xy65/'


def validate_take(take):
    if (take/'visual-superseded.json').exists():raise ValueError('Superseded take; original review retained for history')
    check=json.loads((take/'check.json').read_text())
    if check['technical']!='passed' or file_record(take/'take.mp4')['sha256']!=check['sha256']:
        raise ValueError('Video integrity mismatch')
    if check['width']!=720 or check['height']!=1280 or check['fps']!='30/1':
        raise ValueError('Video format mismatch')
    if (take/'telemetry.json').exists():
        t=json.loads((take/'telemetry.json').read_text())
        if not t['url'].startswith(PROPERTY) or t.get('error') or t.get('exportError'):
            raise ValueError('Capture property or completion mismatch')
    elif (take/'provenance.json').exists():
        p=json.loads((take/'provenance.json').read_text())
        if p['property']!=PROPERTY or file_record(ROOT/p['fact_source'])['sha256']!=p['fact_sha256']:
            raise ValueError('Render property or fact drift')
        for ref in p['inputs']:
            if file_record(ROOT/ref['path'])['sha256']!=ref['sha256']: raise ValueError('Render input drift')
            if Path(ref['path']).name=='take.mp4':
                original=(ROOT/ref['path']).parent
                if json.loads((original/'visual-review.json').read_text())['verdict']!='accept': raise ValueError('Render input not accepted')
                validate_take(original)
    else: raise ValueError('Missing capture/render provenance')
    return check


def build_stations(methods):
    scene=json.loads((EVIDENCE/'scene-runtime.json').read_text())
    if scene['origin']!=PROPERTY+'#lianjia': raise ValueError('Scene property mismatch')
    rooms=scene['result']['firstFloor']['rooms']
    by_pano={i:r['name'] for r in rooms for i in r['observerIndexs']}
    if len(by_pano)!=27 or set(by_pano)!=set(range(27)): raise ValueError('Unexpected room/point mapping')
    observers=json.loads((EVIDENCE/'establish-04/telemetry.json').read_text())['scene']['observers']
    points=[]
    for o in observers:
        tests=[]
        for m in methods:
            r=m['recipe']
            if m['type']=='capture' and m['production_ready'] and (r['start']['pano']==o['pano'] or any(s.get('pano')==o['pano'] for s in r['steps'])):
                tests.append(m['id'])
        points.append({**o,'room':by_pano[o['pano']], 'native_eye_height':round(o['position']['y']-o['standingPosition']['y'],6),
                       'accepted_methods':tests,'visual_scope':'tested_recipe_only' if tests else 'sdk_metadata_only','metric_clearance':'unverified'})
    result={'schema':'property-stations/v1','property':PROPERTY+'#lianjia','sources':[file_record(EVIDENCE/'scene-runtime.json'),file_record(EVIDENCE/'establish-04/telemetry.json')],
            'units':{'position':'SDK metres','pano':'zero-based','yaw':'radians'},'rooms':[{ 'name':r['name'],'panos':r['observerIndexs']} for r in rooms],
            'points':points,'warning':'SDK房间归属不是全屋逐点视觉验收；邻接不认证米级净空。卫生间A/B沿用SDK原名，不因历史别名改变点位。'}
    (OUT/'点位.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return file_record(OUT/'点位.json')


def build_variants():
    from repair import VARIANTS
    variants=[]
    for vid,definition in VARIANTS.items():
        item={'id':vid,'parent_method':definition['parent'],'title':definition['title'],'description':definition['semantic'],
              'type':'post','policy':'optional','verification':'pending','visual':'pending','production_ready':False,
              'recipe':None,'evidence':[],'sources':[],'tests':[],
              'execution':{'driver':'repair.py','code':file_record(Path(__file__).parent/'repair.py'),'batch_allowed':False},
              'verification_scope':'explicit_safe_variant_not_original_effect'}
        for take in sorted(EVIDENCE.iterdir()):
            if not take.is_dir() or not (take/'recipe.json').exists():continue
            r=json.loads((take/'recipe.json').read_text())
            if r.get('variant_id')!=vid:continue
            test={'path':rel(take),'technical':'failed','visual':'pending'}
            try:
                if r['method_id']!=definition['parent'] or r['id'].split('-')[0]!=vid:raise ValueError('Variant identity mismatch')
                validate_take(take);test['technical']='passed'
                if (take/'visual-review.json').exists():test['visual']=json.loads((take/'visual-review.json').read_text())['verdict']
            except (ValueError,KeyError,OSError) as e:test['error']=str(e)
            item['tests'].append(test)
            if test['technical']=='passed' and test['visual']=='accept':
                item.update(verification='passed',visual='accept',production_ready=True,recipe=r,
                            evidence=[file_record(p) for p in sorted(take.iterdir()) if p.is_file()])
        variants.append(item)
    return variants


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    old = json.loads((SOURCE / 'tools/手法清单.json').read_text())
    if len(old)!=len(SOURCE_IDS): raise ValueError('Source inventory changed; review mapping before merging')
    sources = {id_:[] for id_, *_ in DEFS}
    for entry, id_ in zip(old, SOURCE_IDS):
        path = SOURCE / entry['dir']
        sources[id_].append({'title':entry['title'], 'directory':rel(path), 'assets':[file_record(p) for p in sorted(path.rglob('*')) if p.is_file()]})
    for directory, id_ in zip(sorted(p for p in ASSETS.iterdir() if p.is_dir() and p.name[:2].isdigit()), ['C08','C09','C04','C10']):
        sources[id_].append({'title':directory.name, 'directory':rel(directory), 'assets':[file_record(p) for p in sorted(directory.rglob('*')) if p.is_file()]})
    intro = file_record(SOURCE / '03-房子介绍手法库.md')
    methods = []
    for id_, title, policy, kind, note in DEFS:
        item = {'id':id_, 'title':title, 'aliases':ALIASES.get(id_,[]), 'type':kind, 'policy':policy,
                'verification':'blocked' if id_ in BLOCKS else 'pending', 'visual':'pending', 'production_ready':False,
                'description':note, 'sources':sources[id_] if kind!='narrative' else [intro],
                'blocked_reason':BLOCKS.get(id_), 'recipe':None, 'evidence':[], 'tests':[]}
        for take in sorted(EVIDENCE.iterdir()):
            if not take.is_dir() or not (take/'recipe.json').exists(): continue
            recipe = json.loads((take/'recipe.json').read_text())
            if recipe['id'].split('-')[0] != id_: continue
            test = {'path':rel(take), 'technical':'failed', 'visual':'pending'}
            if (take/'check.json').exists():
                try:
                    check = validate_take(take); test['technical'] = check['technical']
                except (ValueError, KeyError, OSError) as e:
                    test['technical']='failed'; test['integrity_error']=str(e)
            if (take/'visual-review.json').exists():
                review = json.loads((take/'visual-review.json').read_text()); test['visual'] = review['verdict']; test['reason'] = review['reason']
            item['tests'].append(test)
            if test['technical']=='passed':
                item['verification']='passed'
                if test['visual']=='accept' or not item['evidence']:
                    item['visual']=test['visual']; item['recipe']=recipe
                    item['evidence']=[file_record(p) for p in sorted(take.iterdir()) if p.name in ['recipe.json','take.mp4','telemetry.json','check.json','visual-review.json','contact.png','start.png','middle.png','end.png','transition.png','provenance.json','overlay.png','command.json','filter.txt']]
        if id_ in BLOCKS:
            item['assessment']=file_record(EVIDENCE/'blocked-assessment.json')
        if id_=='P10' and (EVIDENCE/'P10-decision-01.json').exists():
            item['deferred_decision']=file_record(EVIDENCE/'P10-decision-01.json')
        item['verification_scope']='silent_text_pair_demo_not_voiceover' if kind=='narrative' else 'exact_recipe_current_property'
        item['execution']={'driver':'take.js via native agent_browser' if kind=='capture' else 'render.py', 'batch_allowed':False}
        item['production_ready'] = id_ not in BLOCKS and item['verification']=='passed' and item['visual']=='accept' and policy!='prohibited'
        methods.append(item)
    variants=build_variants()
    for m in methods:m['safe_alternatives']=[v['id'] for v in variants if v['parent_method']==m['id'] and v['production_ready']]
    catalog = {'schema':'property-methodlib/v1','property':{'name':'武汉沙湖九号','url':'https://open.realsee.com/ke/rXel3aPEWkwD4JQn/qrz3DGWoeBMCwu3h2TOlxEYTR8Q0Xy65/#lianjia','fact_contract':file_record(ROOT/'02_架构与合同/01_房产核心档案.md')},
      'path_base':'project_root','units':{'yaw':'radians','pitch':'radians','fov':'degrees','duration':'milliseconds','pano':'zero-based SDK index; P1 means index 1'},
      'gate':{'require':['verification=passed','visual=accept','policy!=prohibited','evidence hashes match','same property'], 'metric_clearance':'unverified; visual checks are not >=0.5m certification','native_vr_height_exception':'approved by user for this property only; do not offset panoramas; real camera remains 1.5–1.6m','allowed_fov':[75,85], 'unsupported':['unverified orbit route','arbitrary free-camera traversal','automatic full-film batch']},
      'scene_snapshot':file_record(EVIDENCE/'scene-runtime.json'),'stations':build_stations(methods),
      'method_count':len(methods),'methods':methods,'variant_count':len(variants),'variants':variants}
    (OUT/'方法库.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2))
    cards=[]
    for m in methods+variants:
        evidence = {Path(x['path']).name:x['path'] for x in m['evidence']}
        media=''
        if 'take.mp4' in evidence:
            video=os.path.relpath(ROOT/evidence['take.mp4'],OUT)
            image=os.path.relpath(ROOT/evidence['contact.png'],OUT)
            media=f'<video controls preload="none" src="{html.escape(video)}"></video><a href="{html.escape(image)}">逐半秒接触表</a>'
        cards.append(f'<article><h2>{m["id"]} {html.escape(m["title"])}</h2><p>{m["type"]} · {m["policy"]} · {m["verification"]} / {m["visual"]} · 本房源配方可复用（非净空认证）：{m["production_ready"]}</p><p>{html.escape(m["description"])}</p>{media}<details><summary>AI配置与凭据</summary><pre>{html.escape(json.dumps(m,ensure_ascii=False,indent=2))}</pre></details></article>')
    (OUT/'画廊.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>沙湖九号统一方法库</title><style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:16px;background:#fafafa}article{background:white;border:1px solid #ddd;padding:18px;margin:18px 0}video{width:240px;max-height:430px;display:block}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}</style><h1>沙湖九号 · 介绍、转场、运镜统一方法库</h1><p>工程素材画廊，不是全片分镜。通过仅限本条配方与本房源；安全距离未量测；禁止项保留反例，不允许自动用于正式视频。</p><p><a href="方法库.json">AI读取JSON</a> · <a href="点位.json">SDK点位与已测范围</a> · <a href="README.md">单项执行说明</a></p>'+''.join(cards)+'</html>')
    print(json.dumps({'count':len(methods),'ready':[m['id'] for m in methods if m['production_ready']], 'blocked':[m['id'] for m in methods if m['verification']=='blocked'], 'safe_variants':[v['id'] for v in variants if v['production_ready']]},ensure_ascii=False))


def choose(catalog, id_, experiment=False):
    if catalog['schema']!='property-methodlib/v1' or catalog['property']['url']!=PROPERTY+'#lianjia': raise ValueError('Catalog property/schema mismatch')
    for key in ['scene_snapshot','stations']:
        ref=catalog[key]
        if file_record(ROOT/ref['path'])['sha256']!=ref['sha256']: raise ValueError('Scene/station drift')
    fact=catalog['property']['fact_contract']
    if file_record(ROOT/fact['path'])['sha256']!=fact['sha256']: raise ValueError('Fact drift; revalidate affected methods')
    m=next(x for x in catalog['methods']+catalog.get('variants',[]) if x['id']==id_)
    if 'parent_method' in m:
        from repair import VARIANTS
        d=VARIANTS.get(id_)
        if not d or m['parent_method']!=d['parent'] or m['policy']!='optional' or m['type']!='post':raise ValueError('Variant policy/identity drift')
        code=m['execution']['code']
        if file_record(ROOT/code['path'])['sha256']!=code['sha256']:raise ValueError('Variant executor drift; rerun verification')
        if not m['recipe'] or m['recipe'].get('variant_id')!=id_ or m['recipe']['method_id']!=d['parent']:raise ValueError('Variant recipe identity mismatch')
    else:
        definition=next(x for x in DEFS if x[0]==id_)
        if m['policy']!=definition[2] or m['type']!=definition[3]: raise ValueError('Policy/type drift')
    if id_ in BLOCKS or not m['recipe'] or not m['evidence']: raise ValueError('No verified executable recipe')
    if not experiment and (m['policy']=='prohibited' or m['verification']!='passed' or m['visual']!='accept' or not m['production_ready']): raise ValueError('Not production ready')
    for ref in m['evidence']:
        p=ROOT/ref['path']
        if not p.is_file() or file_record(p)['sha256']!=ref['sha256']: raise ValueError('Evidence drift')
    record=next(x for x in m['evidence'] if Path(x['path']).name=='recipe.json')
    take=(ROOT/record['path']).parent
    if json.loads((take/'recipe.json').read_text())!=m['recipe']: raise ValueError('Recipe drift')
    validate_take(take)
    if not experiment and json.loads((take/'visual-review.json').read_text())['verdict']!='accept': raise ValueError('Visual evidence not accepted')
    return m['recipe']


def select(id_, experiment=False):
    print(json.dumps(choose(json.loads((OUT/'方法库.json').read_text()),id_,experiment),ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','select']);p.add_argument('id',nargs='?');p.add_argument('--experiment',action='store_true');a=p.parse_args()
    if a.action=='build':build()
    else:select(a.id,a.experiment)
