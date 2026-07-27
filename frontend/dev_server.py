"""
简易开发服务器：提供前端静态文件 + API 代理到后端
"""
import http.server
import urllib.request
import urllib.error
import os
import sys

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
BACKEND_URL = "http://localhost:8000"
PORT = 3000


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_GET(self):
        # API 请求代理到后端
        if self.path.startswith("/api/"):
            self._proxy_request("GET")
            return
        # SPA 路由：非静态文件回退到 index.html
        file_path = os.path.join(FRONTEND_DIR, self.path.lstrip("/"))
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy_request("POST")
            return
        self.send_error(404)

    def do_PUT(self):
        if self.path.startswith("/api/"):
            self._proxy_request("PUT")
            return
        self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            self._proxy_request("DELETE")
            return
        self.send_error(404)

    def do_PATCH(self):
        if self.path.startswith("/api/"):
            self._proxy_request("PATCH")
            return
        self.send_error(404)

    def _proxy_request(self, method):
        target_url = BACKEND_URL + self.path
        if self.path.find("?") == -1:
            target_url = BACKEND_URL + self.path
        else:
            target_url = BACKEND_URL + self.path

        body = None
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length)

        req = urllib.request.Request(
            target_url,
            data=body,
            method=method,
        )

        # 转发相关 headers
        for header in ["Content-Type", "Authorization", "Accept"]:
            value = self.headers.get(header)
            if value:
                req.add_header(header, value)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                self.send_response(resp.status)
                for key, value in resp.getheaders():
                    if key.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except urllib.error.URLError as e:
            self.send_error(502, f"Backend unavailable: {e.reason}")


if __name__ == "__main__":
    print(f"🚀 标中宝前端开发服务器")
    print(f"   📂 静态文件: {FRONTEND_DIR}")
    print(f"   🔗 API 代理: /api/* -> {BACKEND_URL}")
    print(f"   🌐 访问地址: http://localhost:{PORT}")
    print()

    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.shutdown()
