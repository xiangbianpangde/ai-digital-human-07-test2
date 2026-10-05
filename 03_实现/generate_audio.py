#!/usr/bin/env python3
"""
生成全片精准对位配音与完整音轨
"""
import os
import json
import subprocess

cues = [
    {
        "id": "cue_01_s1",
        "shot": "S1",
        "text": "约163平，进门先看30.9平大客厅，直连9.1平南向阳台。",
        "target_start": 0.2,
        "max_dur": 6.0,
        "speed": 1.18
    },
    {
        "id": "cue_02_s2",
        "shot": "S2",
        "text": "站在阳台回看，客餐厅的纵深就很直观了。",
        "target_start": 6.8,
        "max_dur": 4.0,
        "speed": 1.15
    },
    {
        "id": "cue_03_s3",
        "shot": "S3",
        "text": "北侧这间，可以做书房，也可以做多功能房。",
        "target_start": 11.3,
        "max_dur": 2.5,
        "speed": 1.18
    },
    {
        "id": "cue_04_s4a",
        "shot": "S4A",
        "text": "穿过动静分区——就是16.7平的主卧。",
        "target_start": 14.3,
        "max_dur": 3.0,
        "speed": 1.15
    },
    {
        "id": "cue_05_s4b",
        "shot": "S4B",
        "text": "另外带专属独立主卫，配独立浴缸。",
        "target_start": 17.8,
        "max_dur": 3.0,
        "speed": 1.15
    },
    {
        "id": "cue_06_s5",
        "shot": "S5",
        "text": "想看完整全屋，评论区留“沙湖九号”。",
        "target_start": 21.3,
        "max_dur": 3.0,
        "speed": 1.12
    }
]

os.makedirs("03_实现/audio", exist_ok=True)

for c in cues:
    out_file = f"03_实现/audio/{c['id']}.mp3"
    print(f"正在生成 {c['id']}: {c['text']}")
    cmd = [
        "mmx", "speech", "synthesize",
        "--text", c["text"],
        "--model", "speech-2.8-hd",
        "--voice", "Chinese (Mandarin)_Warm_Bestie",
        "--speed", str(c["speed"]),
        "--out", out_file,
        "--non-interactive", "--quiet", "--output", "json"
    ]
    subprocess.run(cmd, check=True)
    dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out_file
    ], text=True).strip())
    c["actual_dur"] = dur
    print(f" -> 实际时长: {dur:.2f}s (预算上限: {c['max_dur']}s)")

with open("03_实现/audio/cues_manifest.json", "w", encoding="utf-8") as f:
    json.dump(cues, f, indent=2, ensure_ascii=False)

print("全部配音片段生成完毕！")
