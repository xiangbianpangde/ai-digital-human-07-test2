#!/usr/bin/env python3
import os
import sys
import json
import urllib.parse
import http.server

PORT = 8999

class ReceiverHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        target_file = params.get("file", [None])[0]
        
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)
        
        if not target_file:
            target_file = "04_测试与验收/default_output.bin"
            
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, "wb") as f:
            f.write(data)
        print(f"[Receiver] 成功落盘: {target_file} ({len(data)} 字节)")

        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"OK")

if __name__ == "__main__":
    server = http.server.HTTPServer(("127.0.0.1", PORT), ReceiverHandler)
    print(f"Direct receiver listening on {PORT}")
    server.serve_forever()
