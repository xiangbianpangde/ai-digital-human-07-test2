#!/usr/bin/env python3
"""
Shot 1 实测运行与验证脚本
通过 Five SDK 真实物理点位驱动 P1 -> P9 -> P10 -> P11 (时长 6.5s)
并通过 canvas.captureStream(30) + MediaRecorder 无损录制视频流传输落盘。
"""
import os
import sys
import json
import time
import subprocess
import threading
import http.server

PORT = 8999
DATA_RECEIVED = {}
RECEIVED_EVENT = threading.Event()

class ReceiverHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # 静默标准日志

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_POST(self):
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(content_length)
        
        path = self.path
        if "video" in path:
            DATA_RECEIVED["video"] = data
            print(f"[Server] 成功接收视频流: {len(data)} 字节")
        elif "telemetry" in path:
            DATA_RECEIVED["telemetry"] = json.loads(data.decode("utf-8"))
            print(f"[Server] 成功接收遥测数据: {len(data)} 字节")
        
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"OK")
        
        if "video" in DATA_RECEIVED and "telemetry" in DATA_RECEIVED:
            RECEIVED_EVENT.set()

def start_server():
    server = http.server.HTTPServer(("127.0.0.1", PORT), ReceiverHandler)
    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()
    return server

def main():
    print("=== 开始 Shot 1 真实漫游与录制实测 ===")
    os.makedirs("04_测试与验收", exist_ok=True)
    server = start_server()
    print(f"[1/4] 本地接收服务已就绪 (127.0.0.1:{PORT})")

    # JavaScript 注入脚本
    js_code = """
    (() => {
      const F = window.Five;
      const f = Object.values(window.__FIVE_DEBUG__?.instances || {}).filter(x => x instanceof F)[0];
      if (!f) return JSON.stringify({ error: 'No Five instance' });

      const canvas = f.renderer.domElement;
      const sleep = ms => new Promise(r => setTimeout(r, ms));
      const H_YAW = 3.1798714670236343; // 黄金朝向 3.18rad

      (async () => {
        try {
          // 1. 先复位并预加载至 P1
          await f.preloadPano(1);
          await new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error('Reset timeout')), 10000);
            f.moveToPano(1, {
              effect: 'fly',
              duration: 600,
              longitude: H_YAW,
              latitude: 0,
              fov: 95,
              moveEndCallback: () => { clearTimeout(timer); resolve(); }
            });
          });
          await f.ready({ tile: true });
          await sleep(500);

          // 2. 准备录制
          const stream = canvas.captureStream(30);
          const recorder = new MediaRecorder(stream, {
            mimeType: 'video/webm;codecs=vp9',
            videoBitsPerSecond: 8000000
          });
          const chunks = [];
          recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
          const stoppedPromise = new Promise(r => recorder.onstop = r);

          const telemetry = {
            shot: "S1",
            startTime: performance.now(),
            marks: [],
            canvas: [canvas.width, canvas.height]
          };

          const recordMark = (name) => {
            telemetry.marks.push({
              name,
              time: performance.now() - telemetry.startTime,
              panoIndex: f.state.panoIndex,
              pose: f.getPose()
            });
          };

          recorder.start(500);
          recordMark("START_P1");

          // 3. 执行真实运镜流线：P1 -> P9 (1500ms) -> P10 (1500ms) -> P11 (2000ms)
          const moves = [
            { pano: 9, dur: 1500, label: "MOVE_TO_P9" },
            { pano: 10, dur: 1500, label: "MOVE_TO_P10" },
            { pano: 11, dur: 2000, label: "MOVE_TO_P11" }
          ];

          for (const m of moves) {
            await f.preloadPano(m.pano);
            recordMark(m.label + "_START");
            await new Promise((resolve, reject) => {
              const timer = setTimeout(() => reject(new Error(m.label + ' timeout')), m.dur + 5000);
              f.moveToPano(m.pano, {
                effect: 'fly',
                duration: m.dur,
                longitude: H_YAW,
                latitude: 0,
                fov: 95,
                moveEndCallback: () => { clearTimeout(timer); resolve(); }
              });
            });
            await f.ready({ tile: true });
            recordMark(m.label + "_END");
          }

          // 4. 到达 P11 阳台落地窗后停留 1500ms (呼吸留白)
          recordMark("HOLD_P11_START");
          await sleep(1500);
          recordMark("HOLD_P11_END");

          // 5. 停止录制
          recorder.stop();
          await stoppedPromise;
          stream.getTracks().forEach(t => t.stop());
          telemetry.totalTime = performance.now() - telemetry.startTime;

          const blob = new Blob(chunks, { type: 'video/webm' });

          // 6. 发送数据到本地 Server
          await fetch('http://127.0.0.1:8999/video', {
            method: 'POST',
            headers: { 'Content-Type': 'video/webm' },
            body: blob
          });

          await fetch('http://127.0.0.1:8999/telemetry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(telemetry)
          });

        } catch (err) {
          console.error("Shot1 execution error:", err);
        }
      })();

      return JSON.stringify({ status: "STARTED" });
    })()
    """

    print("[2/4] 向浏览器注入并启动 Shot 1 实测序列...")
    cmd = ["agent-browser", "eval", js_code]
    p = subprocess.run(cmd, capture_output=True, text=True)
    print("注入返回值:", p.stdout.strip())

    print("[3/4] 等待运镜完成与数据回传 (预估耗时约 7~8 秒)...")
    success = RECEIVED_EVENT.wait(timeout=25)
    server.shutdown()

    if not success:
        print("错误: 超时未收到录制数据！")
        sys.exit(1)

    # 4. 落盘并验收
    webm_path = "04_测试与验收/shot1_take.webm"
    mp4_path = "04_测试与验收/shot1_take.mp4"
    json_path = "04_测试与验收/shot1_telemetry.json"

    with open(webm_path, "wb") as f:
        f.write(DATA_RECEIVED["video"])
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(DATA_RECEIVED["telemetry"], f, indent=2, ensure_ascii=False)

    print(f"[4/4] 录制原片已落盘: {webm_path} ({len(DATA_RECEIVED['video'])} 字节)")

    # 转换 MP4 并抽帧
    print("正在通过 ffmpeg 转封装 MP4 并抽取 4 个关键验证帧...")
    subprocess.run([
        "ffmpeg", "-y", "-i", webm_path, "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", "30", mp4_path
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 抽帧点：0.5s (P1起跑), 2.5s (P9过渡), 4.0s (P10进阳台), 6.0s (P11落地窗终点)
    frame_times = [
        ("04_测试与验收/shot1_frame_01_p1_start.png", "0.5"),
        ("04_测试与验收/shot1_frame_02_p9_mid.png", "2.2"),
        ("04_测试与验收/shot1_frame_03_p10_door.png", "4.0"),
        ("04_测试与验收/shot1_frame_04_p11_window.png", "6.0")
    ]
    for out_img, ss in frame_times:
        subprocess.run([
            "ffmpeg", "-y", "-ss", ss, "-i", mp4_path, "-vframes", "1", out_img
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("=== Shot 1 实测与证据抽取全部完成！ ===")

if __name__ == "__main__":
    main()
