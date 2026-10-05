#!/usr/bin/env python3
"""One recipe per invocation; append-only captures, no arbitrary receiver paths."""
import argparse
import hashlib
import http.server
import json
import math
import secrets
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / '04_测试与验收/方法库实测'


def command(argv, timeout=120):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(p.stderr[-3000:] or p.stdout[-3000:])
    return p.stdout


def capture(recipe_path, take_id, session):
    recipe = json.loads(Path(recipe_path).read_text())
    if not take_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in take_id):
        raise ValueError('Unsafe take id')
    out = EVIDENCE / take_id
    out.mkdir(parents=True, exist_ok=False)
    (out / 'recipe.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2))
    token = secrets.token_hex(16)
    received = set()
    lock = threading.Lock()
    complete = threading.Event()

    class Receiver(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, status):
            self.send_response(status)
            self.send_header('Access-Control-Allow-Origin', 'https://open.realsee.com')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Access-Control-Allow-Private-Network', 'true')
            self.end_headers()

        def do_OPTIONS(self):
            self.respond(204)

        def do_GET(self):
            paths = {f'/{token}/script': Path(__file__).parent / 'take.js', f'/{token}/recipe': out / 'recipe.json'}
            path = paths.get(urlparse(self.path).path)
            if not path:
                self.respond(404)
                return
            self.respond(200)
            self.wfile.write(path.read_bytes())

        def do_POST(self):
            paths = {f'/{token}/video': 'take.webm', f'/{token}/telemetry': 'telemetry.json'}
            target = paths.get(urlparse(self.path).path)
            size = int(self.headers.get('Content-Length', '0'))
            if not target or not 0 < size < 100_000_000:
                self.respond(400)
                return
            with lock:
                if target in received:
                    self.respond(409)
                    return
                data = self.rfile.read(size)
                if target.endswith('.json'):
                    json.loads(data)
                with (out / target).open('xb') as file:
                    file.write(data)
                received.add(target)
            self.respond(200)
            self.wfile.write(b'OK')
            if target == 'telemetry.json':
                complete.set()

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Receiver)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f'http://127.0.0.1:{server.server_port}'
    expression = f'''(async()=>{{ const base={json.dumps(endpoint + '/' + token)}; (0,eval)(await (await fetch(base+'/script')).text()); return await methodTake(await (await fetch(base+'/recipe')).json(),{json.dumps(endpoint)},{json.dumps(token)}); }})()'''
    connection = {'endpoint': endpoint, 'token': token, 'session': session, 'eval': expression}
    (out / 'connection.json').write_text(json.dumps(connection, indent=2))
    print(json.dumps(connection), flush=True)
    try:
        if not complete.wait(180):
            raise RuntimeError('Timed out waiting for native agent_browser eval; inspect connection.json')
    finally:
        server.shutdown()
        server.server_close()
    if not (out / 'telemetry.json').exists():
        raise RuntimeError('Telemetry not received; inspect __methodTake.exportError')
    telemetry = json.loads((out / 'telemetry.json').read_text())
    if telemetry.get('error') or telemetry.get('exportError') or not (out / 'take.webm').exists():
        raise RuntimeError(str(telemetry.get('error') or telemetry.get('exportError')))
    video = out / 'take.mp4'
    command(['ffmpeg', '-v', 'error', '-n', '-i', str(out / 'take.webm'), '-an', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', '30', str(video)])
    finalize(out, {'native_height_exception': True, 'metric_clearance': 'unverified',
                   'browser_session': session, 'driver': 'Five SDK canvas captureStream / MediaRecorder'})


def finalize(out, metadata):
    video = out / 'take.mp4'
    # Decode every frame; contact sheets are visual sampling, not frame-by-frame review.
    command(['ffmpeg', '-v', 'error', '-xerror', '-i', str(video), '-f', 'null', '-'])
    probe = json.loads(command(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)]))
    stream = next(x for x in probe['streams'] if x['codec_type'] == 'video')
    duration = float(probe['format']['duration'])
    times = [0.1, duration/2, max(.1, duration-.2)]
    for name, seconds in zip(['start.png','middle.png','end.png'], times):
        command(['ffmpeg', '-v', 'error', '-n', '-ss', str(seconds), '-i', str(video), '-frames:v', '1', str(out / name)])
    # Contact sheet every half second, not only endpoints.
    rows = max(1, math.ceil(duration * 2 / 6))
    command(['ffmpeg', '-v', 'error', '-n', '-i', str(video), '-vf', f'fps=2,scale=180:-1,tile=6x{rows}:padding=4:margin=4:color=white', '-frames:v', '1', str(out / 'contact.png')])
    check = {'technical': 'passed', 'visual': 'pending', 'duration_sec': duration,
             'width': stream['width'], 'height': stream['height'], 'fps': stream['r_frame_rate'],
             'bytes': video.stat().st_size, 'sha256': hashlib.sha256(video.read_bytes()).hexdigest(),
             'decoded_all_frames': True, **metadata}
    if stream['width'] != 720 or stream['height'] != 1280 or duration < 1 or stream['r_frame_rate'] != '30/1':
        raise RuntimeError('Invalid video format')
    if (out / 'telemetry.json').exists() and len(json.loads((out / 'telemetry.json').read_text())['samples']) < 5:
        raise RuntimeError('Insufficient telemetry')
    (out / 'check.json').write_text(json.dumps(check, ensure_ascii=False, indent=2))
    print(json.dumps({'take': str(out.relative_to(ROOT)), **check}, ensure_ascii=False))


def review(take_id, verdict, reason, reviewed=None):
    out = EVIDENCE / take_id
    if out.parent.resolve() != EVIDENCE.resolve():
        raise ValueError('Unsafe take id')
    check = json.loads((out / 'check.json').read_text())
    if check['technical'] != 'passed':
        raise ValueError('Cannot accept unverified take')
    if not reason.strip():
        raise ValueError('Visual reason required')
    reviewed = reviewed or ['contact.png']
    if any(Path(p).name != p or not (out/p).is_file() or not p.endswith('.png') for p in reviewed):
        raise ValueError('Invalid reviewed image list')
    record = {'verdict': verdict, 'reason': reason, 'reviewed': reviewed, 'metric_clearance': 'unverified'}
    with (out / 'visual-review.json').open('x') as file:
        json.dump(record, file, ensure_ascii=False, indent=2)
    print(json.dumps(record, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('capture')
    p.add_argument('recipe'); p.add_argument('take_id'); p.add_argument('--session', default='methodlib')
    p = sub.add_parser('review')
    p.add_argument('take_id'); p.add_argument('verdict', choices=['accept','reject']); p.add_argument('reason'); p.add_argument('--reviewed',nargs='+',default=['contact.png'])
    args = parser.parse_args()
    if args.action == 'capture': capture(args.recipe, args.take_id, args.session)
    else: review(args.take_id, args.verdict, args.reason, args.reviewed)

if __name__ == '__main__':
    main()
