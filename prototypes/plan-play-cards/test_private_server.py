import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('private_server',Path(__file__).with_name('private_server.py'))
server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
class RouteBoundary(unittest.TestCase):
 def test_private_is_explicit_and_no_directory(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'index.html').write_text('public');(root/'.private').mkdir();secret=root/'.private'/'selected.json';secret.write_text('{}');(root/'.private'/'not-selected.json').write_text('{}')
   catalog=root/'.private'/'catalog.json';catalog.write_text(json.dumps({'routes':{'/private/selected.json':str(secret)}}))
   original=server.ROOT;server.ROOT=root
   try:
    routes=server.routes(catalog);self.assertIn('/private/selected.json',routes);self.assertNotIn('/.private/not-selected.json',routes);self.assertNotIn('/private/not-selected.json',routes);self.assertNotIn('/.private/',routes);self.assertNotIn('/../',routes)
   finally:server.ROOT=original
 def test_invalid_route_fails(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'catalog.json';p.write_text(json.dumps({'routes':{'/private/../escape':'/tmp/missing'}}))
   with self.assertRaises(ValueError):server.routes(p)
if __name__=='__main__':unittest.main()
