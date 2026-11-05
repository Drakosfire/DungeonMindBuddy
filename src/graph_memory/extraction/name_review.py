"""Generic, deterministic near-name suggestions. Never apply without a decision."""
import hashlib
import json
import re
from src.graph_memory.extraction.known_entity_registry import normalize_match_surface, is_unsafe_match_alias


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',', ':'),ensure_ascii=False).encode()).hexdigest()


def near_name(a, b):
    a,b=a.casefold(),b.casefold()
    if a==b or min(len(a),len(b))<5 or abs(len(a)-len(b))>1:
        return False
    if len(a)==len(b):
        differences=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
        return len(differences)==1 or (len(differences)==2 and differences[1]==differences[0]+1 and a[differences[0]]==b[differences[1]] and a[differences[1]]==b[differences[0]])
    short,long=sorted([a,b],key=len)
    return any(long[:i]+long[i+1:]==short for i in range(len(long)))


def review_names(text, catalog, scope):
    """Single edit/transposition, whole name windows; ties stay explicit options."""
    owners={}
    for entity in catalog.get('entities',[]):
        for name in entity['names']:
            if not is_unsafe_match_alias(name):
                owners.setdefault(name,set()).add(entity['entity_id'])
    normalized_owners={}
    for name,ids in owners.items():
        normalized_owners.setdefault(normalize_match_surface(name),set()).update(ids)
    ambiguous=set(catalog.get('ambiguous_names',[])) | {n for n,ids in normalized_owners.items() if len(ids)>1}
    targets={name for name,ids in owners.items() if len(ids)==1 and normalize_match_surface(name) not in ambiguous}
    tokens=list(re.finditer(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*",text,re.UNICODE))
    # Protect all exact known name surfaces, including ambiguous ones.
    exact=[]
    for name in owners:
        exact.extend(m.span() for m in re.finditer(r'(?<!\w)'+re.escape(name)+r'(?!\w)',text,re.IGNORECASE))
    windows={}
    for name in sorted(targets):
        size=len(re.findall(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*",name,re.UNICODE))
        if size<1 or size>5:
            continue
        for i in range(len(tokens)-size+1):
            start,end=tokens[i].start(),tokens[i+size-1].end()
            if any(start<b and end>a for a,b in exact):continue
            surface=text[start:end]
            if near_name(surface,name):windows.setdefault((start,end,surface),set()).add(name)
    suggestions=[]
    for (start,end,surface),options in sorted(windows.items()):
        item={'start':start,'end':end,'surface':surface,'options':sorted(options)}
        item['id']=digest(item)
        suggestions.append(item)
    result={'schema':'dmb_recap_name_review_v1','scope':scope,'source_sha256':hashlib.sha256(text.encode()).hexdigest(),
            'catalog_sha256':digest(catalog),'suggestions':suggestions,'exact_mention_count':len(set(exact))}
    result['review_id']=digest(result)
    return result


def apply_review(text, review, receipt):
    """Every suggestion needs an explicit replacement or keep-original decision."""
    if receipt is None:
        if review['suggestions']:raise ValueError('Review possible name typos before extraction.')
        receipt={'review_id':review['review_id'],'decisions':[]}
    if receipt['review_id']!=review['review_id']:raise ValueError('Name review is stale. Check names again.')
    decisions=receipt['decisions']
    if len({d['id'] for d in decisions})!=len(decisions) or {d['id'] for d in decisions}!={s['id'] for s in review['suggestions']}:
        raise ValueError('Decide every suggested name correction before extraction.')
    by_id={d['id']:d['replacement'] for d in decisions}
    edits=[]
    for item in review['suggestions']:
        replacement=by_id[item['id']]
        if replacement is not None:
            if replacement not in item['options']:raise ValueError('Name correction is outside the reviewed choices.')
            edits.append({**item,'replacement':replacement})
    edits.sort(key=lambda e:e['start'])
    if any(a['end']>b['start'] for a,b in zip(edits,edits[1:])):
        raise ValueError('Overlapping corrections need a new name review.')
    corrected=text
    for item in reversed(edits):corrected=corrected[:item['start']]+item['replacement']+corrected[item['end']:]
    return corrected,{'review':review,'decisions':decisions,'applied_edits':edits,'corrected_sha256':hashlib.sha256(corrected.encode()).hexdigest()}
