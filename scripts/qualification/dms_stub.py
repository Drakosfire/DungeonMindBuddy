"""Disposable HTTPS DMS protocol fixture; no external identity/provider access."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import ssl


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        authenticated = self.headers.get("Cookie") == "dungeonmind_session=qualification-session"
        valid = self.path == "/api/auth/current-user" and authenticated
        payload = json.dumps({"sub": "qualification-user"} if valid else {"status": "signed_out"}).encode()
        self.send_response(200 if valid else 401)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cert", required=True)
    parser.add_argument("--key", required=True)
    args = parser.parse_args()
    server = HTTPServer(("0.0.0.0", 443), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(args.cert, args.key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()
