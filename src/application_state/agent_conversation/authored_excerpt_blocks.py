"""Exact authored block selection. No model text, IO, folding or reserialization."""
from dataclasses import dataclass
from hashlib import sha256
import re

from markdown_it import MarkdownIt
from .rules_authority_types import canonical_sha256

PARTITION = 'markdown_source_blocks_v1'


@dataclass(frozen=True)
class AuthoredBlock:
    block_handle: str
    source_handle: str
    byte_start: int
    byte_end: int
    block_sha256: str
    text: str


def block_handle(source_handle, start, end, digest):
    return 'b' + canonical_sha256(dict(partition_version=PARTITION,
        source_handle=source_handle, byte_start=start, byte_end=end, block_sha256=digest))


def partition(text, source_handle):
    if not isinstance(text, str):
        raise ValueError('Authored body must be exact text')
    if not text:
        return ()
    # Match parser line boundaries without normalizing the frozen raw bytes.
    raw_lines = re.findall(r'.*?(?:\r\n|\n|\r|$)', text, flags=re.S)
    raw_lines = [line for line in raw_lines if line]
    offsets = [0]
    for line in raw_lines:
        offsets.append(offsets[-1] + len(line.encode('utf-8')))
    tokens = MarkdownIt('commonmark', {'html':True}).enable('table').parse(text)
    spans = [(token.map[0], token.map[1]) for token in tokens if token.level == 0 and token.map]
    fences = [token.map for token in tokens if token.type in {'fence','code_block'} and token.map]
    stack = []
    for index, line in enumerate(raw_lines):
        if any(start <= index < end for start, end in fences):
            continue
        marker = re.match(r'^ {0,3}:::[ \t]*(.*?)[\r\n]*$', line)
        if not marker:
            continue
        if marker.group(1).strip():
            stack.append(index)
        elif stack:
            start = stack.pop()
            if not stack:
                spans.append((start,index+1))
    if stack:
        spans.append((stack[0],len(raw_lines)))
    starts = {0, len(raw_lines)} | {start for start, _ in spans}
    starts = sorted(start for start in starts if not any(left < start < right for left,right in spans))
    encoded = text.encode('utf-8')
    if len(starts) > 2 and not encoded[:offsets[starts[1]]].strip():
        starts.pop(1)
    result = []
    for first, last in zip(starts,starts[1:]):
        left,right = offsets[first],offsets[last]
        if left == right:
            continue
        raw = encoded[left:right]; digest = sha256(raw).hexdigest()
        result.append(AuthoredBlock(block_handle(source_handle,left,right,digest),source_handle,left,right,digest,raw.decode('utf-8')))
    if ''.join(block.text for block in result) != text:
        raise ValueError('Authored block partition changed frozen text')
    return tuple(result)


def project_blocks(text, source_handle):
    return [dict(block_handle=block.block_handle,text=block.text) for block in partition(text,source_handle)]


def restore_blocks(rows):
    if not isinstance(rows,list) or any(not isinstance(row,dict) or set(row)!={'block_handle','text'}
            or not isinstance(row['text'],str) or not isinstance(row['block_handle'],str) for row in rows):
        raise ValueError('Authored block projection is malformed')
    return ''.join(row['text'] for row in rows)


def verify_blocks(rows, text, source_handle):
    expected=partition(text,source_handle)
    if rows != [dict(block_handle=block.block_handle,text=block.text) for block in expected]:
        raise ValueError('Authored block projection changed its exact source/span')
    return expected


@dataclass(frozen=True)
class AuthoredSelection:
    selection_id: str
    block: AuthoredBlock


def selection_catalog(sources, scope):
    """Short presentation IDs; immutable blocks and source ownership stay private.

    Sources are ordered (internal source handle, exact body) pairs. The complete
    ordered catalog and current submission determine the namespace. It supplies
    no authority without the owning captured-input/receipt checks.
    """
    sources=tuple(sources)
    if not isinstance(scope,str) or not scope or any(not isinstance(h,str) or not h for h,_ in sources):
        raise ValueError('Authored selector catalog lacks exact scope/owners')
    if len({h for h,_ in sources})!=len(sources):
        raise ValueError('Authored selector owners must be distinct')
    owners=[(handle,partition(text,handle)) for handle,text in sources]
    blocks=[block for _,values in owners for block in values]
    if len({b.block_handle for b in blocks})!=len(blocks):
        raise ValueError('Authored selector blocks must be distinct')
    digest=canonical_sha256({'scope':scope,'owners':[{'source_handle':h,
        'blocks':[b.block_handle for b in values]} for h,values in owners]})
    return tuple(AuthoredSelection(f'a-{digest[:12]}-{index}',block)
        for index,block in enumerate(blocks,1))


def project_selection_blocks(text, source_handle, catalog):
    if (len({row.selection_id for row in catalog})!=len(catalog)
            or len({row.block.block_handle for row in catalog})!=len(catalog)):
        raise ValueError('Authored selector catalog must be bijective')
    selectors={row.block.block_handle:row.selection_id for row in catalog}
    blocks=partition(text,source_handle)
    if any(block.block_handle not in selectors for block in blocks):
        raise ValueError('Authored projection lacks its complete exact catalog')
    return [dict(selection_id=selectors[block.block_handle],text=block.text) for block in blocks]


def restore_selection_blocks(rows):
    if not isinstance(rows,list) or any(not isinstance(row,dict) or set(row)!={'selection_id','text'}
            or not isinstance(row['text'],str) or not (
                isinstance(row['selection_id'],str) and row['selection_id']
                or row['selection_id'] is None and not row['text'].strip()) for row in rows):
        raise ValueError('Authored selector projection is malformed')
    return ''.join(row['text'] for row in rows)


def verify_selection_blocks(rows,text,source_handle,catalog):
    if rows!=project_selection_blocks(text,source_handle,catalog):
        raise ValueError('Authored selectors changed their exact source/span/catalog')
    return partition(text,source_handle)
