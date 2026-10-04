import importlib.util,json,tempfile,unittest,hashlib
from pathlib import Path
spec=importlib.util.spec_from_file_location('capture',Path(__file__).with_name('capture_candidate.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class CandidateBoundary(unittest.TestCase):
 def test_exact_files_and_rejections(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'source';source.mkdir();renderer=root/'renderer';renderer.mkdir();pdf=b'synthetic PDF';(source/'source.pdf').write_bytes(pdf);pdfhash=hashlib.sha256(pdf).hexdigest()
   board={'id':'synthetic','pin':'pin','sourcePin':'source','pdfHash':pdfhash,'assets':[]};(source/'board.json').write_text(json.dumps(board));(source/'reference-manifest.json').write_text(json.dumps({'datasetPin':'pin','sourcePin':'source','pdfHash':pdfhash}));play=root/'play.json';play.write_text(json.dumps({'format':'dmb-private-board-play-v1','boardId':'synthetic','sourcePin':'pin','play':{'notes':'Synthetic writing'}}))
   for name in module.RENDERER_FILES:(renderer/name).write_text('synthetic renderer '+name)
   out=root/'.private'/'candidate';receipt=module.capture(source,play,renderer,out,'a'*40)
   self.assertEqual(receipt['status'],'candidate_not_accepted');self.assertEqual(receipt['acceptance']['operatorReview'],'pending')
   for rel,digest in receipt['files'].items():self.assertEqual(module.digest(out/rel),digest)
   with self.assertRaisesRegex(ValueError,'already exists'):module.capture(source,play,renderer,out,'a'*40)
   with self.assertRaisesRegex(ValueError,'private'):module.capture(source,play,renderer,root/'public','a'*40)
   d=json.loads(play.read_text());d['sourcePin']='other';play.write_text(json.dumps(d))
   with self.assertRaisesRegex(ValueError,'backup differs'):module.capture(source,play,renderer,root/'.private'/'wrong','a'*40)
   self.assertFalse((root/'.private'/'wrong').exists())
   self.assertEqual(module.verify_candidate(out),receipt)
   (out/'play.json').write_text('changed writing')
   with self.assertRaisesRegex(ValueError,'Candidate file changed'):module.verify_candidate(out)
   d['sourcePin']='pin';play.write_text(json.dumps(d));(source/'source.pdf').write_bytes(b'tampered')
   with self.assertRaisesRegex(ValueError,'digest mismatch'):module.capture(source,play,renderer,root/'.private'/'bad-source','a'*40)
if __name__=='__main__':unittest.main()
