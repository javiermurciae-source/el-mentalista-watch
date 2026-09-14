#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
import time

PORT = 8088
DIRECTORY = "/data/data/com.termux.launcher.nix/files/home/el_mentalista_app"

# Watch Party / Jam State en memoria
JAM_ROOMS = {}

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/episodes":
            json_file = os.path.join(DIRECTORY, "episodes.json")
            if os.path.exists(json_file):
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(json_file, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'{"error": "Episodes still scraping"}')
            return

        if self.path.startswith("/api/jam/poll"):
            # Poll status room: /api/jam/poll?room=XYZ
            query = self.path.split("?")[-1] if "?" in self.path else ""
            params = dict(p.split("=") for p in query.split("&") if "=" in p)
            room_id = params.get("room", "general")
            
            room_data = JAM_ROOMS.get(room_id, {
                "room": room_id,
                "current_ep": {"season": 1, "episode": 1},
                "server_url": "",
                "server_name": "Hyper",
                "playing": True,
                "timestamp": time.time(),
                "messages": [],
                "members": 1
            })

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(room_data).encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/jam/sync":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                room_id = data.get("room", "general")
                if room_id not in JAM_ROOMS:
                    JAM_ROOMS[room_id] = {
                        "room": room_id,
                        "current_ep": data.get("current_ep", {"season": 1, "episode": 1}),
                        "server_url": data.get("server_url", ""),
                        "server_name": data.get("server_name", ""),
                        "playing": data.get("playing", True),
                        "timestamp": time.time(),
                        "messages": [],
                        "members": 1
                    }
                else:
                    r = JAM_ROOMS[room_id]
                    if "current_ep" in data:
                        r["current_ep"] = data["current_ep"]
                    if "server_url" in data:
                        r["server_url"] = data["server_url"]
                    if "server_name" in data:
                        r["server_name"] = data["server_name"]
                    if "playing" in data:
                        r["playing"] = data["playing"]
                    r["timestamp"] = time.time()

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "room": JAM_ROOMS[room_id]}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'{{"error": "{str(e)}"}}\n'.encode("utf-8"))
            return

        if self.path == "/api/jam/chat":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
                room_id = data.get("room", "general")
                user = data.get("user", "Amigo")
                text = data.get("text", "")
                
                if room_id not in JAM_ROOMS:
                    JAM_ROOMS[room_id] = {
                        "room": room_id,
                        "current_ep": {"season": 1, "episode": 1},
                        "server_url": "",
                        "server_name": "",
                        "playing": True,
                        "timestamp": time.time(),
                        "messages": [],
                        "members": 1
                    }
                
                r = JAM_ROOMS[room_id]
                msg_entry = {
                    "user": user,
                    "text": text,
                    "time": time.strftime("%H:%M:%S")
                }
                r["messages"].append(msg_entry)
                if len(r["messages"]) > 60:
                    r["messages"] = r["messages"][-60:]

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "messages": r["messages"]}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'{{"error": "{str(e)}"}}\n'.encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def run():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"[*] Servidor corriendo en http://0.0.0.0:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    run()
