"""Freeze private presentation review inputs; never marks a candidate accepted."""
import argparse,hashlib,json,re,shutil
from pathlib import Path

RENDERER_FILES=('boards.html','boards.js','boards.css','style.css','themes.css','theme-model.js','theme-ui.js','board-model.js','source-review.js','presentation-model.js','composer-ui.js','backup-model.js','backup-ui.js')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def capture(board_dir,play_file,renderer_dir,output,revision):
    board_dir,play_file,renderer_dir,output=map(Path,(board_dir,play_file,renderer_dir,output))
    if '.private' not in output.resolve().parts:raise ValueError('Candidate must stay in a private directory')
    if output.exists():raise ValueError('Candidate already exists; choose a new snapshot')
    if not re.fullmatch(r'[0-9a-f]{40}',revision):raise ValueError('Exact renderer Git revision required')
    board=json.loads((board_dir/'board.json').read_text());manifest=json.loads((board_dir/'reference-manifest.json').read_text());backup=json.loads(play_file.read_text())
    if manifest['datasetPin']!=board['pin'] or manifest['sourcePin']!=board['sourcePin']:raise ValueError('Manifest basis differs from board')
    if backup.get('format')!='dmb-private-board-play-v1' or backup.get('boardId')!=board['id'] or backup.get('sourcePin')!=board['pin']:raise ValueError('Play backup differs from candidate source revision')
    pdf=board_dir/'source.pdf'
    if digest(pdf)!=board['pdfHash'] or manifest['pdfHash']!=board['pdfHash']:raise ValueError('Source PDF digest mismatch')
    source_files=[(board_dir/'board.json','source/board.json'),(board_dir/'reference-manifest.json','source/reference-manifest.json'),(pdf,'source/source.pdf'),(play_file,'play.json')]
    for asset in board.get('assets',[]):
        prefix='/private/'+board['id']+'/'
        if not asset['url'].startswith(prefix):raise ValueError('Asset belongs to another source')
        name=asset['url'][len(prefix):]
        if not name or Path(name).name!=name:raise ValueError('Asset path must be a selected local file')
        path=board_dir/name
        if digest(path)!=asset['hash']:raise ValueError('Source asset digest mismatch')
        source_files.append((path,'source/'+name))
    all_files=source_files+[(renderer_dir/name,'renderer/'+name) for name in RENDERER_FILES]
    hashes={rel:digest(path) for path,rel in all_files}
    receipt={'status':'candidate_not_accepted','boardId':board['id'],'datasetPin':board['pin'],'sourcePin':board['sourcePin'],'rendererRevision':revision,'rendererHash':hashlib.sha256(json.dumps({k:v for k,v in hashes.items() if k.startswith('renderer/')},sort_keys=True).encode()).hexdigest(),'files':hashes,'acceptance':{'sourceReview':'pending','operatorReview':'pending','nativeWorldContract':'not_integrated'}}
    # All evidence is checked before creating output; existing snapshots are immutable.
    output.mkdir(parents=True)
    for path,rel in all_files:
        dest=output/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
        if digest(dest)!=hashes[rel]:raise ValueError('Input changed during capture; snapshot is incomplete')
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt
def verify_candidate(output):
    output=Path(output);receipt=json.loads((output/'receipt.json').read_text())
    if receipt.get('status')!='candidate_not_accepted':raise ValueError('Unsupported candidate status')
    for rel,expected in receipt['files'].items():
        path=output/rel
        if not path.resolve().is_relative_to(output.resolve()) or digest(path)!=expected:raise ValueError('Candidate file changed: '+rel)
    return receipt
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',help='Check an existing private candidate without changing it')
    for key in ['board-dir','play-file','renderer-dir','output','renderer-revision']:parser.add_argument('--'+key)
    args=parser.parse_args()
    if args.verify:receipt=verify_candidate(args.verify)
    else:
        if not all([args.board_dir,args.play_file,args.renderer_dir,args.output,args.renderer_revision]):parser.error('All capture arguments are required')
        receipt=capture(args.board_dir,args.play_file,args.renderer_dir,args.output,args.renderer_revision)
    print(json.dumps({'status':receipt['status'],'boardId':receipt['boardId'],'files':len(receipt['files']),'rendererHash':receipt['rendererHash']}))
