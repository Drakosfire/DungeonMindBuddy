"""Preserve canonical Markdown while indexing marked scenes, beats and choices."""
import hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=ROOT/'corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep'
def index(name,path):
 text=path.read_text();marks=list(re.finditer(r'<!-- dmb-playable-element:v2 (.*?) -->',text));elements=[]
 for i,m in enumerate(marks):
  attrs=dict(re.findall(r'(\w+)=(\S+)',m[1]));end=marks[i+1].start() if i+1<len(marks) else len(text)
  elements.append({**attrs,'start':m.start(),'bodyStart':m.end(),'end':end})
 assert len({e['id'] for e in elements})==len(elements)
 return {'name':name,'markdown':text,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'elements':elements}
data=[index('Session 29',BASE/'Session 29 - Buddy Plan.md'),index('Ironveil House',BASE/'IronVeilHouse.md')]
(ROOT/'prototypes/plan-play-cards/content.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
print([(d['name'],len(d['elements'])) for d in data])
