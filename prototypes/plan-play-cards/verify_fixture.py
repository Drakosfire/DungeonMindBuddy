import hashlib,json,pathlib,re
root=pathlib.Path(__file__).resolve().parents[2]
base=root/'corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep'
data=json.loads((pathlib.Path(__file__).with_name('content.json')).read_text())
for fixture,filename in zip(data,['Session 29 - Buddy Plan.md','IronVeilHouse.md']):
 raw=(base/filename).read_bytes();assert fixture['markdown'].encode()==raw;assert fixture['sha256']==hashlib.sha256(raw).hexdigest()
source=(base/'Campaign 2 Session 29.md').read_text();derived=data[0]['markdown']
assert re.sub(r'\[([^\]]+)\]\(dmb-node:[^)]+\)',r'\1',derived)==source
assert len(re.findall(r'<!-- dmb-playable-element:v2 .*? -->',source))==90
assert hashlib.sha256((base/'Campaign 2 Session 29.md').read_bytes()).hexdigest()=='7628ff052ebb87e2e3a074e9a11b3f96753aab50b16c20a93a284a5ec76fc8d5'
assert hashlib.sha256((base/'IronVeilHouse.md').read_bytes()).hexdigest()=='8fa097b221b93445629a3688e8ce086827cd77d491dc41edab8a49f60749dc43'
print('PASS: exact imported sources, reversible verified-link derivative, original hashes and 90 stable markers')
