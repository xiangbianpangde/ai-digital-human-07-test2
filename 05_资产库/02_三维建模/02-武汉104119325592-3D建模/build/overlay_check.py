#!/usr/bin/env python3
"""Draw predicted 3D structure onto a real cube face to confirm the convention."""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from cube_convention import qmat, faces_for_candidate, FLOOR_Y, CAM_Y, RAW, SRC, FACES

def main():
    cam = int(sys.argv[1]); face = sys.argv[2]
    d, k, mir = sys.argv[3], int(sys.argv[4]), sys.argv[5] == '1'
    rooms = json.load(open(os.path.join(RAW,'rooms_vr.json')))
    work = json.load(open(os.path.join(SRC,'01-房源信息','work.json')))
    o = [x for x in work['observers'] if x['index']==cam][0]
    R = qmat(o['quaternion']); C = np.array(o['position'],float)
    r,u,fwd = faces_for_candidate(d,k,mir); r,u,fwd = R@r, R@u, R@fwd
    W=768; f=W/2.0
    im = Image.open(os.path.join(FACES,'%d-%s.png'%(cam,face))).convert('RGB').resize((W,W), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    def proj(p):
        w = np.array(p,float)-C
        a = w@fwd
        if a<=0.2: return None
        return (W/2+f*(w@r)/a, W/2-f*(w@u)/a)
    zs = np.linspace(FLOOR_Y, CAM_Y, 12)
    n=0
    for rm in rooms:
        pts=rm['pts_vr']
        for i in range(len(pts)):
            a=pts[i]; b=pts[(i+1)%len(pts)]
            # vertical edge at corner a, sampled along height
            seg=[proj([a[0],z,a[1]]) for z in zs]
            seg=[p for p in seg if p]
            if len(seg)>1:
                dr.line(seg, fill=(255,40,40), width=2); n+=1
            # floor-level edge a->b
            pa=proj([a[0],FLOOR_Y,a[1]]); pb=proj([b[0],FLOOR_Y,b[1]])
            if pa and pb: dr.line([pa,pb], fill=(40,255,255), width=2)
    print('drew %d vertical edges for cam %d face %s (dir=%s rot=%d mirror=%s)'%(n,cam,face,d,k,mir))
    im.save(os.path.join(RAW,'conv_%s_%d_%s.png'%(face,cam,d.replace('+','p').replace('-','m'))))

main()
