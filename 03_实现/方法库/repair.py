#!/usr/bin/env python3
"""One explicitly named safe variant. Original rejected methods remain unchanged."""
import argparse
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from render import accepted, sha, FACTS, FONT, PROPERTY
from run import ROOT, EVIDENCE, command, finalize

VARIANTS={
 'P03V1':{'parent':'P03','title':'图形层长叠化＋实景硬切','semantic':'仅说明文字交叉0.5秒；建筑画面不叠化，不宣称原跨空间长叠化通过。'},
 'P05V1':{'parent':'P05','title':'边缘滑条提示＋实景硬切','semantic':'装饰条仅占左缘最多24像素；不横滑或拼接两幅建筑画面。'},
 'P06V1':{'parent':'P06','title':'低强度亮度脉冲＋实景硬切','semantic':'白色图层最大8/255透明度，7帧单次轻亮；不是全白闪屏。'},
 'P07V1':{'parent':'P07','title':'后期图形遮挡揭示','semantic':'明确标注后期双侧遮罩；完整遮挡1帧时换实景，不制造贴墙轨迹，不冒称现场真实遮挡。'},
 'P08V1':{'parent':'P08','title':'方向匹配微摇切镜','semantic':'卧室B两个已测向右慢摇片段方向匹配后硬切；不实施或模拟高速甩镜，不声称原甩镜解禁。'},
 'P09V1':{'parent':'P09','title':'二维分片遮罩揭示','semantic':'96块独立图形遮罩遮住底图时换实景，然后分片揭示；不打碎房屋，不生成或变形建筑，不冒称三维破面。'},
}

def layer(mid,n):
    im=Image.new('RGBA',(720,1280));d=ImageDraw.Draw(im)
    font=ImageFont.truetype(str(FONT),26)
    d.text((360,1220),'后期变体示意 · VR实录',font=font,anchor='mt',fill='white',stroke_width=1,stroke_fill='black')
    if mid=='P03V1':
        x=max(0,min(1,(n-52)/15))
        d.rounded_rectangle((36,1090,300,1154),radius=12,fill=(15,20,30,190))
        a=Image.new('RGBA',im.size);b=Image.new('RGBA',im.size)
        ImageDraw.Draw(a).text((60,1106),'片段 A',font=font,fill=(255,255,255,round(255*(1-x))))
        ImageDraw.Draw(b).text((60,1106),'片段 B',font=font,fill=(255,255,255,round(255*x)))
        im=Image.alpha_composite(Image.alpha_composite(im,a),b)
    elif mid=='P05V1':
        if 54<=n<=66:
            import math
            width=round(24*math.sin(math.pi*(n-54)/12))
            if width:d.rectangle((0,0,width-1,1279),fill=(185,168,143,190))
    elif mid=='P06V1':
        if 57<=n<=63:
            import math
            alpha=round(8*math.sin(math.pi*(n-57)/6))
            pulse=Image.new('RGBA',im.size,(255,255,255,alpha))
            im=Image.alpha_composite(pulse,im)
    elif mid=='P07V1':
        if 48<=n<=72:
            w=round(360*(1-abs(n-60)/12))
            if w:
                d.rectangle((0,0,w-1,1279),fill=(176,159,137,255))
                d.rectangle((720-w,0,719,1279),fill=(176,159,137,255))
                for x in range(0,w,18):
                    d.line((x,0,x,1279),fill=(156,141,122,255),width=2)
                    d.line((719-x,0,719-x,1279),fill=(156,141,122,255),width=2)
        d.rounded_rectangle((36,60,684,118),radius=12,fill=(15,20,30,255 if n==60 else 185))
        d.text((360,74),'后期遮挡 · 非现场贴墙',font=font,anchor='mt',fill='white')
        d.text((360,1220),'后期变体示意 · VR实录',font=font,anchor='mt',fill='white',stroke_width=1,stroke_fill='black')
    elif mid=='P08V1':
        d.rounded_rectangle((36,60,684,118),radius=12,fill=(15,20,30,185))
        d.text((360,74),'方向匹配慢摇 · 非高速甩镜',font=font,anchor='mt',fill='white')
    elif mid=='P09V1':
        if 54<=n<=72:
            order=sorted(range(96),key=lambda i:(i*37)%97)
            for rank,i in enumerate(order):
                visible=(n>=54+rank//16) if n<60 else (n<=60+rank//8)
                if visible:
                    col,row=i%8,i//8
                    y1=round(row*1280/12);y2=round((row+1)*1280/12)-1
                    c=156+(i%4)*7
                    d.rectangle((col*90,y1,(col+1)*90-1,y2),fill=(c,c-14,c-30,255))
        d.rounded_rectangle((36,60,684,118),radius=12,fill=(15,20,30,255 if n==60 else 185))
        d.text((360,74),'二维分片遮罩 · 非建筑破面',font=font,anchor='mt',fill='white')
        d.text((360,1220),'后期变体示意 · VR实录',font=font,anchor='mt',fill='white',stroke_width=1,stroke_fill='black')
    else:raise ValueError('Undefined variant')
    return im

def render(recipe_path,take_id):
    r=json.loads(Path(recipe_path).read_text());mid=r['variant_id']
    if mid not in VARIANTS or r['method_id']!=VARIANTS[mid]['parent'] or r['id'].split('-')[0]!=mid:raise ValueError('Variant identity mismatch')
    if not take_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in take_id):raise ValueError('Unsafe take id')
    if len(r['inputs'])!=2:raise ValueError('Two accepted captures required')
    if mid=='P08V1' and r['inputs']!=['micro-01','sweep-01']:raise ValueError('Direction-match variant requires tested same-room captures')
    inputs=[accepted(x) for x in r['inputs']]
    out=EVIDENCE/take_id;out.mkdir(parents=True,exist_ok=False)
    (out/'recipe.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
    provenance={'property':PROPERTY,'method_id':r['method_id'],'variant_id':mid,'inputs':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in inputs],
                'fact_source':str(FACTS.relative_to(ROOT)),'fact_sha256':sha(FACTS),'font':{'path':str(FONT),'sha256':sha(FONT)},
                'counterexample':False,'scope':'explicit_safe_post_variant','audio':'none','definition':VARIANTS[mid], 'not_a_real_camera_path':True}
    (out/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
    cmd=['ffmpeg','-v','error','-n','-f','rawvideo','-pix_fmt','rgba','-s','720x1280','-r','30','-i','pipe:0','-an','-c:v','qtrle',str(out/'layer.mov')]
    (out/'layer-command.json').write_text(json.dumps(cmd,ensure_ascii=False,indent=2))
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for n in range(120):p.stdin.write(layer(mid,n).tobytes())
        p.stdin.close();err=p.stderr.read();code=p.wait()
        if code:raise RuntimeError(err.decode()[-3000:])
    except BaseException:
        p.kill();p.wait();raise
    chain='[0:v]trim=duration=2,setpts=PTS-STARTPTS,fps=30,format=yuv420p[a];[1:v]trim=duration=2,setpts=PTS-STARTPTS,fps=30,format=yuv420p[b];[a][b]concat=n=2:v=1:a=0[base];[base][2:v]overlay=shortest=1:format=auto,format=yuv420p[v]'
    args=['ffmpeg','-v','error','-n','-i',str(inputs[0]),'-i',str(inputs[1]),'-i',str(out/'layer.mov'),'-filter_complex',chain,'-map','[v]','-an','-c:v','libx264','-crf','18','-r','30','-threads','2',str(out/'take.mp4')]
    (out/'command.json').write_text(json.dumps(args,ensure_ascii=False,indent=2));(out/'filter.txt').write_text(chain)
    command(args)
    finalize(out,{'metric_clearance':'unverified','scope':'explicit_safe_post_variant','variant_id':mid,'driver':'accepted real captures + transparent graphic layer'})
    command(['ffmpeg','-v','error','-n','-i',str(out/'take.mp4'),'-vf','trim=start=1.4:end=2.6,setpts=PTS-STARTPTS,fps=30,scale=180:-1,tile=6x6:padding=4:margin=4:color=white','-frames:v','1',str(out/'transition.png')])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('recipe');p.add_argument('take_id');a=p.parse_args();render(a.recipe,a.take_id)
