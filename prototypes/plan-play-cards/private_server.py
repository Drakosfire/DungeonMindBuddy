"""Loopback-only prototype server: explicit files, no directory listings or root exposure."""
import argparse,json,mimetypes
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parent

def routes(catalog_path):
    public={('/'+str(p.relative_to(ROOT))):p for p in ROOT.rglob('*') if p.is_file() and not any(part.startswith('.') for part in p.relative_to(ROOT).parts) and p.suffix in {'.html','.js','.css','.json','.md','.png'}}
    public['/']=ROOT/'index.html'
    if catalog_path:
        catalog=json.loads(catalog_path.read_text())
        public['/private/catalog.json']=catalog_path
        for url,path in catalog['routes'].items():
            if not url.startswith('/private/') or '..' in url:raise ValueError('Private route must be explicit')
            file=Path(path).resolve()
            if not file.is_file():raise ValueError('Missing selected private file')
            public[url]=file
    return public

def handler(selected):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path=unquote(urlsplit(self.path).path)
            if path not in selected:self.send_error(404);return
            file=selected[path];data=file.read_bytes();self.send_response(200)
            self.send_header('Content-Type',mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
            self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
    return Handler
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path);p.add_argument('--port',type=int,default=5203);args=p.parse_args()
    ThreadingHTTPServer(('127.0.0.1',args.port),handler(routes(args.catalog))).serve_forever()
