#!/usr/bin/env python3
"""Render ONE post or narrative method from accepted takes, never a whole film."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from run import ROOT, EVIDENCE, command, finalize

FACTS = ROOT / '02_架构与合同/01_房产核心档案.md'
FONT = Path('/System/Library/Fonts/STHeiti Medium.ttc')
PROPERTY = 'https://open.realsee.com/ke/rXel3aPEWkwD4JQn/qrz3DGWoeBMCwu3h2TOlxEYTR8Q0Xy65/'
PROHIBITED = {'P03', 'P05', 'P06'}
POST = {'P01':'cut','P02':'fade','P03':'fade','P04':'zoom_cut','P05':'slideleft','P06':'fadewhite'}
# Tested wording is deliberately discrete, not a full-film script or voice-over.
TEXT = {
    'N01':['武汉 · 沙湖九号','建面约163平米 · 4室2厅'],
    'N02':['客厅，直通阳台'],
    'N03':['这里，你会怎么布置？'],
    'N04':['回望客餐厅','核对空间关系'],
    'N05':['打开完整VR，继续看房'],
}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def accepted(name):
    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in name):
        raise ValueError('Unsafe take id')
    p = EVIDENCE / name
    check = json.loads((p/'check.json').read_text())
    review = json.loads((p/'visual-review.json').read_text())
    video = p/'take.mp4'
    if check['technical'] != 'passed' or review['verdict'] != 'accept' or sha(video) != check['sha256']:
        raise ValueError('Input not accepted or hash drift')
    telemetry = p/'telemetry.json'
    if not telemetry.exists() or not json.loads(telemetry.read_text())['url'].startswith(PROPERTY):
        raise ValueError('Input property mismatch')
    return video

def render(recipe_path, take_id, experiment=False):
    r = json.loads(Path(recipe_path).read_text())
    mid = r['method_id']
    if mid not in POST and mid not in TEXT: raise ValueError('Unsupported method')
    if mid in PROHIBITED and not experiment: raise ValueError('Counterexamples require --experiment')
    if not take_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in take_id):
        raise ValueError('Unsafe output id')
    inputs = [accepted(n) for n in r.get('inputs',[])]
    if mid in POST and len(inputs) != 2: raise ValueError('Exactly two accepted inputs required')
    if mid in TEXT and len(inputs) != (0 if mid == 'N01' else 1): raise ValueError('Invalid narrative inputs')
    if mid in TEXT and r['text'] != TEXT[mid]: raise ValueError('Untested wording; define and verify a new variant')
    out = EVIDENCE / take_id
    out.mkdir(parents=True,exist_ok=False)
    (out/'recipe.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
    provenance = {'method_id':mid,'property':PROPERTY,'inputs':[{ 'path':str(p.relative_to(ROOT)), 'sha256':sha(p)} for p in inputs],
                  'fact_source':str(FACTS.relative_to(ROOT)),'fact_sha256':sha(FACTS),
                  'scope':'silent_text_pair_demo' if mid in TEXT else 'post_transition_demo',
                  'counterexample':mid in PROHIBITED,'audio':'none'}
    args = ['ffmpeg','-v','error','-n']
    if mid in POST:
        for p in inputs: args += ['-i',str(p)]
        chain = '[0:v]trim=duration=2,setpts=PTS-STARTPTS,fps=30,settb=AVTB,format=yuv420p[a];[1:v]trim=duration=2,setpts=PTS-STARTPTS,fps=30,settb=AVTB,format=yuv420p[b];'
        effect = POST[mid]
        if effect == 'cut': chain += '[a][b]concat=n=2:v=1:a=0[v]'
        elif effect == 'zoom_cut':
            # Digital crop only, capped at 5%; not physical motion or FOV telemetry.
            chain += "[a]zoompan=z='1+0.05*max(0,min(1,(on-48)/11))':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=720x1280:fps=30[za];[b]zoompan=z='1+0.05*max(0,1-on/11)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=720x1280:fps=30[zb];[za][zb]concat=n=2:v=1:a=0[v]"
        else:
            frames = {'P02':8,'P03':15,'P05':9,'P06':6}[mid]
            duration = frames/30
            chain += f'[a][b]xfade=transition={effect}:duration={duration:.9f}:offset={2-duration:.9f},format=yuv420p[v]'
            provenance['transition_frames'] = frames
            provenance['actual_transition_sec'] = duration
        args += ['-filter_complex',chain,'-map','[v]']
        (out/'filter.txt').write_text(chain)
    else:
        overlay = Image.new('RGBA',(720,1280),(0,0,0,0))
        d = ImageDraw.Draw(overlay)
        if mid == 'N01':
            overlay = Image.new('RGBA',(720,1280),'#171a20'); d = ImageDraw.Draw(overlay)
            fp = ROOT/'05_资产库/01_户型图/floorplan_cropped.png'
            img = Image.open(fp).convert('RGBA'); img.thumbnail((660,780))
            overlay.alpha_composite(img,((720-img.width)//2,350))
            provenance['inputs'].append({'path':str(fp.relative_to(ROOT)),'sha256':sha(fp)})
        lines = r['text']
        font = ImageFont.truetype(str(FONT),36)
        y = 140 if mid == 'N01' else 960
        h = 54*len(lines)+40
        d.rounded_rectangle((36,y-20,684,y+h),radius=16,fill=(10,16,25,215))
        for line in lines:
            box = d.textbbox((0,0),line,font=font)
            if box[2]-box[0]>630: raise ValueError('Text exceeds safe width')
            d.text((360,y),line,anchor='mt',font=font,fill='white'); y += 54
        small = ImageFont.truetype(str(FONT),24)
        d.text((360,1190),'单项方法测试 · VR实勘 / 非真人实拍',anchor='mt',font=small,fill='white',stroke_width=1,stroke_fill='black')
        overlay.save(out/'overlay.png')
        provenance['font'] = {'path':str(FONT),'sha256':sha(FONT)}
        if mid == 'N01':
            args += ['-loop','1','-framerate','30','-i',str(out/'overlay.png'),'-t','4']
        else:
            args += ['-i',str(inputs[0]),'-loop','1','-framerate','30','-i',str(out/'overlay.png'),'-filter_complex','[0:v]fps=30,tpad=stop_mode=clone:stop_duration=4,trim=duration=4,setpts=PTS-STARTPTS[a];[a][1:v]overlay=shortest=1[v]','-map','[v]','-t','4']
    args += ['-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-r','30','-threads','2',str(out/'take.mp4')]
    (out/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
    (out/'command.json').write_text(json.dumps(args,ensure_ascii=False,indent=2))
    command(args)
    finalize(out,{'metric_clearance':'unverified','driver':'ffmpeg accepted-input single-method render','scope':provenance['scope'],'counterexample':mid in PROHIBITED})
    if mid in POST:
        command(['ffmpeg','-v','error','-n','-i',str(out/'take.mp4'),'-vf','trim=start=1.4:end=2.1,setpts=PTS-STARTPTS,fps=30,scale=180:-1,tile=6x4:padding=4:margin=4:color=white','-frames:v','1',str(out/'transition.png')])

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('recipe');p.add_argument('take_id');p.add_argument('--experiment',action='store_true');a=p.parse_args()
    render(a.recipe,a.take_id,a.experiment)
