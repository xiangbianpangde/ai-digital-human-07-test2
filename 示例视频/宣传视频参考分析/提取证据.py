#!/usr/bin/env python3
"""本参考片的证据提取：保留原文件，PNG时间轴及本地ASR（非人工听辨）。"""
import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'d585ed739ce9dafafbb0b31548d47846.mp4'
FONT='/System/Library/Fonts/STHeiti Medium.ttc'

def extract(sec):
    raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(sec),'-i',SOURCE,
        '-frames:v','1','-f','image2pipe','-vcodec','png','-'])
    return Image.open(io.BytesIO(raw)).convert('RGB')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--transcribe',action='store_true');parser.add_argument('--audio-only',action='store_true')
    parser.add_argument('--download-model',action='store_true');args=parser.parse_args()
    if args.audio_only:
        transcribe(args.download_model);return
    frame_names=[f'时间轴关键帧-{i:02}.png' for i in range(1,4)]+[
        '开场信息卡.png','卖点与画面配合.png','底部来源标记.png']
    if any((HERE/name).exists() for name in frame_names):
        raise SystemExit('已有证据PNG，禁止静默重导。仅检查音轨请使用 --audio-only。')
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries',
        'format=duration,size:stream=index,codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels','-of','json',SOURCE]))
    info.update(source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        video_scope='本地参考片的视觉设计分析，宣传文字并非房产真实性核验',
        audio_scope='本地ASR仅用于查找可能的人声；不是音乐识别，也不等于人工听音')
    (HERE/'参考视频信息.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    for page in range(3):
        times=list(range(page*12,min((page+1)*12,35)))
        image=Image.new('RGB',(960,math_ceil(len(times)/4)*456),'#101720')
        d=ImageDraw.Draw(image);font=ImageFont.truetype(FONT,18)
        for i,sec in enumerate(times):
            x,y=i%4*240,i//4*456
            image.paste(extract(sec).resize((240,426)),(x,y))
            d.text((x+7,y+430),f'{sec:02}s',fill='white',font=font)
        image.save(HERE/f'时间轴关键帧-{page+1:02}.png')
    extract(0).save(HERE/'开场信息卡.png')
    extract(25).save(HERE/'卖点与画面配合.png')
    extract(1).crop((0,1150,340,1280)).resize((1020,390)).save(HERE/'底部来源标记.png')
    if args.transcribe:transcribe(args.download_model)
    print('Saved reference evidence without modifying source',flush=True)

def transcribe(download=False):
    from faster_whisper import WhisperModel
    wav=HERE/'参考音轨.wav'
    subprocess.run(['ffmpeg','-y','-v','error','-i',SOURCE,'-vn','-ar','16000','-ac','1',wav],check=True)
    model=WhisperModel('tiny',device='cpu',compute_type='int8',local_files_only=not download)
    segments,meta=model.transcribe(str(wav),language='zh',vad_filter=True,beam_size=5,condition_on_previous_text=False)
    result=dict(method='faster-whisper/tiny, cpu int8, Chinese, VAD; local inference, no audio upload',
        warning='自动转写可能误认音乐歌词或幻觉，空结果不证明没有人声；不能用来断言BGM或音乐风格',
        language=meta.language,language_probability=meta.language_probability,
        duration=meta.duration,duration_after_vad=meta.duration_after_vad,
        segments=[dict(start=s.start,end=s.end,text=s.text,avg_logprob=s.avg_logprob,no_speech_prob=s.no_speech_prob) for s in segments])
    (HERE/'音轨自动转写.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

def math_ceil(n):
    import math
    return math.ceil(n)

if __name__=='__main__':main()
