#!/usr/bin/env python3
"""One approved silent trial only. Not a general renderer or production Skill.

--check performs readonly preflight; --run exclusively creates take01 once.
Pillow applies an absolute-yaw inverse camera homography to a real 90° face.
FFmpeg only decodes the source and encodes/decodes this one silent H.264 clip.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
from datetime import datetime, timezone, timedelta

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / '02_架构与合同/第二房源_104119325592/02_当前镜试验合同_01.json'
CONTRACT_SHA = 'e9ca332b1f31a96042a40e0bda278702f589c62119262e4c7a45a1459731568e'
OUT_PARENT = '04_测试与验收/02-武汉104119325592/S1_客厅原生定点转向'
ATTEMPT = 'take01_20261005'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump_new(path, data):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(c):
    """Fail closed on another house/point/action/cost or unapproved reuse."""
    a, s = c['approval'], c['shot']
    require(c['listing_id'] == '104119325592', 'wrong listing')
    require(c['source']['pano_index'] == a['approved_pano_index'] == 1, 'only pano1 approved')
    require(c['source']['face'] == 'front' and c['source']['pixel_size'] == [2048, 2048], 'wrong face')
    require(a['approved_once'] is True and a['native_view_exception'] is True, 'approval missing')
    require(a['next_shot_authorized'] is False, 'next shot must not be authorized by this trial')
    require(s['duration_sec'] == a['approved_duration_sec'] == 6, 'only six seconds')
    require(s['fps'] == 30 and s['frames'] == 180 and s['output_size'] == [720, 1280], 'wrong format')
    require(s['yaw_start_deg'] == -8 and s['yaw_end_deg'] == 8, 'wrong yaw limits')
    require(s['h_fov_deg'] == 50 and abs(s['v_fov_deg'] - 79.31687852038161) < 1e-8, 'wrong FOV')
    require(s['spatial_translation'] is False and s['pitch_deg'] == s['roll_deg'] == 0, 'movement not approved')
    require(s['physical_height_verified'] is False and s['clearance_0_5m_verified'] is False, 'metric claims not allowed')
    require(all(s[key] is None for key in ('voice', 'subtitles', 'cta')), 'silent uncaptioned trial only')
    require(s['digital_human'] is False and s['external_media_request'] is False, 'external media not approved')
    require(s['synthetic_room_pixels'] is False and s['new_paid_cost'] == 0, 'generation/cost not approved')
    require(c['output_parent'] == OUT_PARENT and c['output_attempt'] == ATTEMPT, 'wrong output boundary')
    require(all(c['guards'][key] is True for key in ('no_overwrite', 'hash_bound_source',
            'hash_bound_fact_contract', 'single_pano_only', 'yaw_must_stay_inside_source_face',
            'allow_one_run', 'stop_after_current_trial')), 'guard missing')


def yaw_for(index, count=180):
    return -8 * math.cos(math.pi * index / (count - 1))


def ray_to_source(x, y, yaw, width, height, source_n, h_fov, v_fov):
    u = (2 * (x + .5) / width - 1) * math.tan(math.radians(h_fov / 2))
    v = (2 * (y + .5) / height - 1) * math.tan(math.radians(v_fov / 2))
    cs, sn = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    z = cs - sn * u
    require(z > 0, 'ray behind source')
    return source_n / 2 * ((cs * u + sn) / z + 1) - .5, source_n / 2 * (v / z + 1) - .5


def coefficients(yaw, width=720, height=1280, source_n=2048, h_fov=50, v_fov=79.31687852038161):
    # Inverse homography: output pixel -> original source pixel, absolute pose.
    tx, ty = math.tan(math.radians(h_fov / 2)), math.tan(math.radians(v_fov / 2))
    sx, ux, sy, vy = 2 * tx / width, (1 / width - 1) * tx, 2 * ty / height, (1 / height - 1) * ty
    cs, sn = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    z0, n, center = cs - sn * ux, source_n / 2, source_n / 2 - .5
    require(z0 > 0, 'invalid homography')
    return ((n * cs * sx - center * sn * sx) / z0, 0.,
            (n * (cs * ux + sn) + center * z0) / z0,
            -center * sn * sx / z0, n * sy / z0,
            (n * vy + center * z0) / z0, -sn * sx / z0, 0.)


def preflight(c):
    validate(c)
    require(sha(CONTRACT) == CONTRACT_SHA, 'contract drift')
    require(sha(c['source']['path']) == c['source']['sha256'], 'source drift')
    require(sha(ROOT / c['fact_contract']['path']) == c['fact_contract']['sha256'], 'fact drift')
    for receipt in c['evidence'].values():
        require(sha(ROOT / receipt['path']) == receipt['sha256'], 'evidence drift')
    require(not (ROOT / OUT_PARENT / ATTEMPT).exists(), 'take exists; no overwrite/retry')
    bounds = []
    for i in range(180):
        xy = [ray_to_source(x, y, yaw_for(i), 720, 1280, 2048, 50, c['shot']['v_fov_deg'])
              for x, y in ((0, 0), (719, 0), (0, 1279), (719, 1279), (359.5, 639.5))]
        require(all(2 <= x < 2045 and 2 <= y < 2045 for x, y in xy), 'ray beyond face/interpolation margin')
        bounds.extend(xy)
    return {'source_hash_ok': True, 'fact_contract_hash_ok': True, 'contract_hash_ok': True,
            'all180_frame_rays_inside_real_face': True,
            'source_xy_bounds': [min(p[0] for p in bounds), min(p[1] for p in bounds),
                                 max(p[0] for p in bounds), max(p[1] for p in bounds)],
            'not_metric_height_clearance_or_visual_acceptance': True}


def run_json(argv):
    return json.loads(subprocess.check_output(argv))


def render(c, check):
    out = ROOT / OUT_PARENT / ATTEMPT
    out.mkdir(parents=True, exist_ok=False)
    dump_new(out / 'run_started.json', {'contract': str(CONTRACT.relative_to(ROOT)),
             'contract_sha256': CONTRACT_SHA, 'at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
             'only_once': True, 'check': check})
    video = out / '武汉104119325592-S1-原生定点静默试验01.mp4'
    try:
        raw = subprocess.check_output(['ffmpeg', '-hide_banner', '-v', 'error', '-i', c['source']['path'],
            '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'])
        require(len(raw) == 2048 * 2048 * 3, 'unexpected source size')
        original = Image.frombytes('RGB', (2048, 2048), raw)
        command = ['ffmpeg', '-hide_banner', '-v', 'warning', '-n', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                   '-video_size', '720x1280', '-framerate', '30', '-i', 'pipe:0', '-frames:v', '180',
                   '-an', '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                   '-movflags', '+faststart', '-metadata', 'comment=Internal native panorama fixed-point rotation; no translation', str(video)]
        with (out / 'encode.log').open('x') as log:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log)
            try:
                for i in range(180):
                    frame = original.transform((720, 1280), Image.Transform.PERSPECTIVE,
                                               coefficients(yaw_for(i)), Image.Resampling.BICUBIC)
                    process.stdin.write(frame.tobytes())
                process.stdin.close()
                require(process.wait() == 0, 'encoder failed')
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
        dump_new(out / 'render_recipe.json', {'schema': 'single-native-face-render/v1', 'contract_sha256': CONTRACT_SHA,
             'source_sha256': c['source']['sha256'], 'method': 'Pillow absolute-yaw inverse perspective; FFmpeg decode/encode',
             'ffmpeg_encode_argv': command, 'frames': [{'index': i, 'time': i / 30, 'yaw_deg': yaw_for(i)} for i in range(180)],
             'synthetic_space_or_spatial_translation': False, 'paid_cost': 0, 'only_this_trial': True})
        technical_qc(video, out, c, check)
        print(json.dumps({'video': str(video.relative_to(ROOT)), 'sha256': sha(video), 'technical_passed': True,
                          'human_review_passed': False, 'next_shot_started': False}, ensure_ascii=False))
    except Exception as error:
        dump_new(out / 'failed.json', {'error': str(error), 'stop_current_shot': True, 'no_automatic_retry_or_next_shot': True})
        raise


def technical_qc(video, out, c, check):
    info = run_json(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-show_frames', '-of', 'json', str(video)])
    streams, frames = info['streams'], info['frames']
    require(len(streams) == 1 and streams[0]['codec_type'] == 'video', 'must have no audio')
    st = streams[0]
    require(st['codec_name'] == 'h264' and st['width'] == 720 and st['height'] == 1280, 'codec/size mismatch')
    require(st['avg_frame_rate'] == '30/1' and len(frames) == 180, 'fps/count mismatch')
    require(abs(float(info['format']['duration']) - 6) < 1e-6, 'duration mismatch')
    pts = [float(f['best_effort_timestamp_time']) for f in frames]
    require(all(abs(t - i / 30) < 1.1e-6 for i, t in enumerate(pts)), 'PTS not CFR')
    with (out / 'decode.log').open('x') as log:
        subprocess.run(['ffmpeg', '-hide_banner', '-v', 'error', '-xerror', '-i', str(video), '-f', 'null', '-'],
                       stdout=subprocess.DEVNULL, stderr=log, check=True)
    # Encoded-media thumbnails, not pre-encode source mockups. Every frame appears once.
    decoder = subprocess.Popen(['ffmpeg', '-hide_banner', '-v', 'error', '-i', str(video), '-f', 'rawvideo',
                                '-pix_fmt', 'rgb24', 'pipe:1'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    selected = {0, 35, 71, 107, 143, 179}
    sheets = [Image.new('RGB', (900, 1440), '#141c22') for _ in range(6)]
    try:
        for i in range(180):
            buf = bytearray()
            while len(buf) < 720 * 1280 * 3:
                block = decoder.stdout.read(720 * 1280 * 3 - len(buf))
                require(bool(block), 'early decoded EOF')
                buf.extend(block)
            frame = Image.frombytes('RGB', (720, 1280), bytes(buf))
            if i in selected:
                frame.save(out / f'encoded-frame-{i:03}.png')
            thumb = frame.resize((144, 256), Image.Resampling.LANCZOS)
            sheet = sheets[i // 30]
            x, y = (i % 30 % 6) * 150 + 3, (i % 30 // 6) * 280 + 40
            sheet.paste(thumb, (x, y))
            ImageDraw.Draw(sheet).text((x, y + 257), f'{i:03} | {i/30:.3f}s', fill='white')
        require(not decoder.stdout.read(1), 'unexpected additional frame')
        require(decoder.wait() == 0, 'frame decoder failed')
    finally:
        if decoder.poll() is None:
            decoder.kill()
            decoder.wait()
    for n, sheet in enumerate(sheets):
        ImageDraw.Draw(sheet).text((8, 10), f'Encoded frames {n*30:03}-{n*30+29:03} | native pano1 | silent | not clearance approval', fill='#ffce69')
        sheet.save(out / f'encoded-contact-{n+1:02}.png')
    require(sha(c['source']['path']) == c['source']['sha256'], 'source changed during render')
    dump_new(out / 'technical_check.json', {'schema': 'single-shot-technical-qc/v1', 'video_sha256': sha(video),
        'streams': streams, 'duration_sec': 6, 'frames': 180, 'pts': pts, 'cfr_pts_passed': True,
        'full_decode_passed': True, 'source_before_after_identical': True, 'source_projection_bounds': check,
        'encoded_all180_frame_thumbnails': True, 'audio_stream_count': 0, 'technical_passed': True,
        'metric_height_clearance_verified': False, 'assistant_visual_review_completed': False,
        'user_review_completed': False, 'stop_after_this_trial': True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    flags = parser.add_mutually_exclusive_group(required=True)
    flags.add_argument('--check', action='store_true')
    flags.add_argument('--run', action='store_true')
    args = parser.parse_args()
    c = json.loads(CONTRACT.read_text(encoding='utf-8'))
    check = preflight(c)
    if args.check:
        print(json.dumps(check, ensure_ascii=False))
    else:
        render(c, check)


if __name__ == '__main__':
    main()
