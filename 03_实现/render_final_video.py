#!/usr/bin/env python3
"""
沙湖九号·核心卖点宣传短片 终极整编合成与渲染交付脚本 (对标参考视频全新字幕系统)
1. 拼接 Shot 1~5 真实实测高清原片母带
2. 精确毫秒级对位合成 MMX 亲切女声音频轨
3. 严格按照《参考视频设计思路》升级全新视觉包装：
   - 0.0s~0.67s 开场信息闪卡 (沙湖九号/约163㎡奢阔四房 + 深色磨砂圆角户型图卡片)
   - 核心大字：单行居中粗黑体 + 6px纯黑全向描边，核心卖点亮黄 (#FFE800)，辅助文案纯白 (#FFFFFF)
   - 彻底剔除黑底条、蓝色标签与冗余口播双层字幕，纯净悬浮在画幅 60% 视觉平衡区
   - 尾部采用与参考视频一致的单行行动引导: "评论留沙湖九号 看完整户型"
4. 输出至规范交付目录: 04_测试与验收/S6_全片终成片交付/沙湖九号-核心卖点宣传短片-终版成片.mp4 (严禁放在根目录)
"""
import os
import sys
import json
import subprocess
from PIL import Image, ImageDraw, ImageFont

def render_bicolor_subtitle(filename, segments, y=790, font_size=50, stroke_width=6):
    """
    渲染单行双色（黄色关键词 + 白色辅助文案）加粗黑描边大字
    segments: [("文字", (r,g,b)), ...]
    """
    im = Image.new("RGBA", (720, 1280), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", font_size)

    # 常驻左下角规范小字
    disclaimer = "如视VR实勘点位漫游 · 现状以现场为准"
    draw.text((28, 1245), disclaimer, fill=(255, 255, 255, 120),
              font=ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 14))

    # 计算文本整体宽度
    text_widths = [draw.textlength(seg_text, font=font) for seg_text, _ in segments]
    total_w = sum(text_widths)
    cur_x = (720 - total_w) / 2

    # 依次渲染带有全向厚实黑描边的文字
    for (seg_text, color), w in zip(segments, text_widths):
        draw.text((cur_x, y), seg_text, fill=color, font=font,
                  stroke_width=stroke_width, stroke_fill=(0, 0, 0, 255))
        cur_x += w

    im.save(filename)

def render_hero_flashcard(filename):
    """
    渲染开场信息闪卡 (0.0s ~ 0.67s):
    顶部黄色大字【沙湖九号】+ 白色大字【约163㎡ 奢阔四房】+ 深色磨砂圆角户型底卡
    """
    im = Image.new("RGBA", (720, 1280), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    font_title = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 54)
    font_sub = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 58)

    # 1. 顶部标题
    t1 = "沙湖九号"
    w1 = draw.textlength(t1, font=font_title)
    draw.text(((720 - w1)/2, 80), t1, fill=(255, 235, 0), font=font_title, stroke_width=6, stroke_fill=(0, 0, 0, 255))

    t2 = "约163㎡ 奢阔四房"
    w2 = draw.textlength(t2, font=font_sub)
    draw.text(((720 - w2)/2, 155), t2, fill=(255, 255, 255), font=font_sub, stroke_width=6, stroke_fill=(0, 0, 0, 255))

    # 2. 中部圆角卡片
    fp = Image.open("03_实现/fp_clean.png").convert("RGBA")
    card_w, card_h = 640, 680
    card_x, card_y = (720 - card_w)//2, 250

    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card)
    card_draw.rounded_rectangle([0, 0, card_w, card_h], radius=24, fill=(28, 30, 34, 235), outline=(255, 255, 255, 200), width=2)

    fp_target_w = card_w - 40
    fp_target_h = card_h - 40
    scale = min(fp_target_w / fp.width, fp_target_h / fp.height)
    new_w = int(fp.width * scale)
    new_h = int(fp.height * scale)
    fp_resized = fp.resize((new_w, new_h), Image.LANCZOS)

    card.paste(fp_resized, ((card_w - new_w)//2, (card_h - new_h)//2), fp_resized)
    im.paste(card, (card_x, card_y), card)

    # 常驻左下角规范小字
    disclaimer = "如视VR实勘点位漫游 · 现状以现场为准"
    draw.text((28, 1245), disclaimer, fill=(255, 255, 255, 120),
              font=ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 14))

    im.save(filename)

def main():
    print("=== 开始全片整编拍摄与合成交付 (对标参考视频新版字幕) ===")

    # 保证目录规范
    delivery_dir = "04_测试与验收/S6_全片终成片交付"
    os.makedirs(delivery_dir, exist_ok=True)
    os.makedirs("03_实现/overlays_v2", exist_ok=True)

    # 1. 拼接画面纯净母带
    concat_list = "03_实现/video_concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        f.write("file '../04_测试与验收/S1_客厅平滑推向阳台/原片与遥测/shot1_take.mp4'\n")
        f.write("file '../04_测试与验收/S2_阳台门口看客餐厅纵深/原片与遥测/shot2_take.mp4'\n")
        f.write("file '../04_测试与验收/S3_北向书房呼应生活代入/原片与遥测/shot3_take.mp4'\n")
        f.write("file '../04_测试与验收/S4_主卧套间证据链/原片与遥测/shot4_take.mp4'\n")
        f.write("file '../04_测试与验收/S5_全屋带看引导CTA/原片与遥测/shot5_take.mp4'\n")

    video_clean = "03_实现/video_track_clean.mp4"
    print("[1/5] 正在检查/拼接 Shot 1~5 画面纯净母带...")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy", video_clean
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    total_dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video_clean
    ], text=True).strip())
    print(f" -> 画面母带总时长: {total_dur:.2f} 秒 (720x1280 竖屏, 30fps)")

    # 2. 检查音轨
    audio_final = "03_实现/final_audio.wav"
    if not os.path.exists(audio_final):
        print("[2/5] 正在生成完整音频轨...")
        audio_inputs = [
            "03_实现/audio/cue_01_s1.mp3",
            "03_实现/audio/cue_02_s2.mp3",
            "03_实现/audio/cue_03_s3.mp3",
            "03_实现/audio/cue_04_s4a.mp3",
            "03_实现/audio/cue_05_s4b.mp3",
            "03_实现/audio/cue_06_s5.mp3"
        ]
        delays = [300, 6800, 11200, 14200, 17700, 21300]
        filter_complex = ""
        for i, d in enumerate(delays):
            filter_complex += f"[{i}:a]adelay={d}|{d}[a{i}];"
        filter_complex += "".join([f"[a{i}]" for i in range(len(delays))]) + f"amix=inputs={len(delays)}:normalize=0[aout]"
        cmd = ["ffmpeg", "-y"]
        for a in audio_inputs:
            cmd.extend(["-i", a])
        cmd.extend(["-filter_complex", filter_complex, "-map", "[aout]", "-t", str(total_dur), audio_final])
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("[2/5] 完整音频轨已就绪！")

    # 3. 生成全新对标参考视频的字幕包装图层
    print("[3/5] 正在生成全新单行双色粗黑描边字幕图层...")
    YELLOW = (255, 235, 0)
    WHITE = (255, 255, 255)

    # 0.0s ~ 0.67s 开场闪卡
    render_hero_flashcard("03_实现/overlays_v2/ol_01_hero.png")

    # 0.67s ~ 4.2s: 约163平 (黄) 进门30.9平大客厅 (白)
    render_bicolor_subtitle("03_实现/overlays_v2/ol_02_s1a.png", [
        ("约163平 ", YELLOW),
        ("进门30.9平大客厅", WHITE)
    ])

    # 4.2s ~ 6.5s: 直连 (白) 9.1平巨幕阳台 (黄)
    render_bicolor_subtitle("03_实现/overlays_v2/ol_03_s1b.png", [
        ("直连 ", WHITE),
        ("9.1平巨幕阳台", YELLOW)
    ])

    # 6.8s ~ 10.2s: 阳台回看 (黄) 客餐厅12米深远纵深 (白)
    render_bicolor_subtitle("03_实现/overlays_v2/ol_04_s2.png", [
        ("阳台回看 ", YELLOW),
        ("客餐厅12米深远纵深", WHITE)
    ])

    # 11.2s ~ 13.8s: 北向房间 (黄) 可做书房多功能房 (白)
    render_bicolor_subtitle("03_实现/overlays_v2/ol_05_s3.png", [
        ("北向房间 ", YELLOW),
        ("可做书房多功能房", WHITE)
    ])

    # 14.2s ~ 17.2s: 16.7平主卧 (黄) 空间全貌一览无余 (白)
    render_bicolor_subtitle("03_实现/overlays_v2/ol_06_s4a.png", [
        ("16.7平主卧 ", YELLOW),
        ("空间全貌一览无余", WHITE)
    ])

    # 17.7s ~ 20.7s: 专属独立主卫 (白) 配独立大浴缸 (黄)
    render_bicolor_subtitle("03_实现/overlays_v2/ol_07_s4b.png", [
        ("专属独立主卫 ", WHITE),
        ("配独立大浴缸", YELLOW)
    ])

    # 21.2s ~ 24.5s: 评论留 (白) 沙湖九号 (黄) 看完整户型 (白)
    render_bicolor_subtitle("03_实现/overlays_v2/ol_08_s5.png", [
        ("评论留", WHITE),
        ("沙湖九号", YELLOW),
        (" 看完整户型", WHITE)
    ])
    print(" -> 全新高规格字幕图层生成完成！")

    # 4. 终极合成渲染
    output_final = os.path.join(delivery_dir, "沙湖九号-核心卖点宣传短片-终版成片.mp4")
    print(f"[4/5] 正在渲染合成终版商业短片至交付目录: {output_final}...")

    # 滤镜链：
    # 0.00 ~ 0.67s: ol_01_hero
    # 0.67 ~ 4.20s: ol_02_s1a
    # 4.20 ~ 6.50s: ol_03_s1b
    # 6.80 ~ 10.20s: ol_04_s2
    # 11.20 ~ 13.80s: ol_05_s3
    # 14.20 ~ 17.20s: ol_06_s4a
    # 17.70 ~ 20.70s: ol_07_s4b
    # 21.20 ~ 24.50s: ol_08_s5
    filter_complex_video = (
        "[0:v][1:v]overlay=enable='between(t,0,0.67)'[v1];"
        "[v1][2:v]overlay=enable='between(t,0.67,4.2)'[v2];"
        "[v2][3:v]overlay=enable='between(t,4.2,6.5)'[v3];"
        "[v3][4:v]overlay=enable='between(t,6.8,10.2)'[v4];"
        "[v4][5:v]overlay=enable='between(t,11.2,13.8)'[v5];"
        "[v5][6:v]overlay=enable='between(t,14.2,17.2)'[v6];"
        "[v6][7:v]overlay=enable='between(t,17.7,20.7)'[v7];"
        "[v7][8:v]overlay=enable='between(t,21.2,24.5)'[vout]"
    )

    cmd_final = [
        "ffmpeg", "-y",
        "-i", video_clean,
        "-i", "03_实现/overlays_v2/ol_01_hero.png",
        "-i", "03_实现/overlays_v2/ol_02_s1a.png",
        "-i", "03_实现/overlays_v2/ol_03_s1b.png",
        "-i", "03_实现/overlays_v2/ol_04_s2.png",
        "-i", "03_实现/overlays_v2/ol_05_s3.png",
        "-i", "03_实现/overlays_v2/ol_06_s4a.png",
        "-i", "03_实现/overlays_v2/ol_07_s4b.png",
        "-i", "03_实现/overlays_v2/ol_08_s5.png",
        "-i", audio_final,
        "-filter_complex", filter_complex_video,
        "-map", "[vout]",
        "-map", "9:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(total_dur),
        output_final
    ]

    subprocess.run(cmd_final, check=True)
    print(" -> 终版成片渲染完成！")

    # 5. 抽取全片 8 帧接触表
    print("[5/5] 正在生成全新 8 帧全流程接触表...")
    sheet_times = [0.4, 2.5, 5.2, 8.5, 12.5, 15.5, 19.2, 23.0]
    sheet_labels = [
        "0.4s 开场闪卡定题",
        "2.5s 约163平进门客厅",
        "5.2s 直连9.1平巨幕阳台",
        "8.5s 阳台回看12米深远",
        "12.5s 北向多功能房",
        "15.5s 16.7平主卧全貌",
        "19.2s 专属主卫配浴缸",
        "23.0s 评论留沙湖九号CTA"
    ]
    imgs = []
    for i, t in enumerate(sheet_times):
        out_p = os.path.join(delivery_dir, f"final_seq_{i:02d}.png")
        subprocess.run(["ffmpeg", "-y", "-ss", str(t), "-i", output_final, "-vframes", "1", out_p],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        imgs.append(Image.open(out_p))

    w, h = imgs[0].size
    thumb_w = 260
    thumb_h = int(h * (thumb_w / w))
    contact = Image.new("RGB", (thumb_w * 4, thumb_h * 2 + 70), (18, 25, 38))

    draw = ImageDraw.Draw(contact)
    font = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 16)
    font_head = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 22)

    draw.text((20, 15), "沙湖九号 · 核心卖点宣传短片 全新对标字幕 8 帧接触表 (终审交付版)", fill=(0, 220, 255), font=font_head)

    for i, im in enumerate(imgs):
        col = i % 4
        row = i // 4
        rim = im.resize((thumb_w, thumb_h), Image.LANCZOS)
        x = col * thumb_w
        y = row * (thumb_h + 35) + 50
        contact.paste(rim, (x, y))
        draw.text((x + 10, y + thumb_h + 6), f"{sheet_labels[i]}", fill=(255, 220, 0), font=font)

    contact_path = os.path.join(delivery_dir, "final_video_contact_sheet.png")
    contact.save(contact_path)
    print(f" -> 全新接触表已保存: {contact_path}")
    print("=== 全片全新字幕合成与规范归档大功告成！ ===")

if __name__ == "__main__":
    main()
