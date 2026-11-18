"""Derive a guarded synthetic witness from the existing mounted Plan fixture.

No owner-source edit: only the named test's fixture, request and assertions change.
The resulting test still uses the real PlanSurfacePage Save owner and the owner's
scripted transport. It is NOT a native database or model-routing witness.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

OWNER = 'apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx'
TITLE = 'contextual Plan boundary benchmark with unrelated top caret (%s)'
MARKDOWN = '''# Expedition

The expedition gathers beside the locked gate.

## Preparation objective

Keep the alternatives open until the scouts return.

<!-- dmb-playable-element:v2 kind=beat id=beat:opening beat_kind=spine -->
## Opening Beat

Ask the players which route they choose.

## Rumours

Keep the alternatives open until the scouts return.
'''

def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f'Owner fixture changed: expected one anchor {old[:90]!r}')
    return text.replace(old, new, 1)

def derive(source: str, owner: Path, *, typed_references: bool = False) -> str:
    start = source.index("it.each(['valid','offered_boundary','altered_boundary'")
    end = source.index('\n});', start) + len('\n});')
    case = source[start:end]
    header = case[:case.index('async mode=>{')]
    case = replace_once(case, header, "it.each(['offered_boundary','altered_boundary','stale_draft'] as const)(" + json.dumps(TITLE) + ',')
    case = replace_once(case, "const record=mockSavedPlanForAgent(savedAgentPlanId,7,7,'# Plan\\n\\nOriginal preparation.\\n');",
                        'const record=mockSavedPlanForAgent(savedAgentPlanId,7,7,' + json.dumps(MARKDOWN) + ');')
    case = replace_once(case, "if (mode === 'offered_boundary' || mode === 'altered_boundary')", "if (mode === 'offered_boundary' || mode === 'altered_boundary' || mode === 'stale_draft')")
    case = replace_once(case, "if (mode === 'altered_boundary') capture.draft_generation += 1;",
                        "if (mode === 'altered_boundary') { capture.from += 1; capture.to += 1; }")
    case = replace_once(case, "entries.find(entry => entry.kind === 'end_page')!", "entries.find(entry => entry.selector === 'after:2')!")
    case = replace_once(case, 'act(()=>editor.commands.setTextSelection(editor.state.doc.content.size-1));', '''act(()=>editor.commands.setTextSelection(1));
  expect(editor.state.selection.empty).toBe(true);
  const beforeJson=editor.getJSON(),beforeSelection=editor.state.selection.toJSON();''')
    case = replace_once(case, 'Invent a short section of possible visitors and put it on this Plan.',
                        'Add a possible-visitors briefing after the Preparation objective and before the Opening Beat. Leave the Rumours duplicate alone.')
    case = replace_once(case, "expect(capture.conversation_id).toBe(conversationId);", '''expect(request.plan_authoring_capture!.from).toBe(1);
    expect(request.plan_authoring_capture!.to).toBe(1);
    expect(capture.root_boundary).toBe(4);
    expect(capture.from).toBeGreaterThan(1);
    expect(capture.conversation_id).toBe(conversationId);''')
    case = replace_once(case, 'expect(commands).not.toHaveBeenCalled();\n    mounted.unmount();return;\n  }', '''expect(commands).not.toHaveBeenCalled();
    expect(editor.getJSON()).toEqual(beforeJson);
    expect(editor.state.selection.toJSON()).toEqual(beforeSelection);
    expect(ordinary).not.toHaveBeenCalled();
    mounted.unmount();return;
  }''')
    case = replace_once(case, "let suggestion=await screen.findByRole('textbox',{name:'Suggestion text'});", '''let suggestion=await screen.findByRole('textbox',{name:'Suggestion text'});
  expect(editor.getJSON()).toEqual(beforeJson);
  expect(editor.state.selection.toJSON()).toEqual(beforeSelection);
  expect(commands.mock.calls.filter(call=>['prepare','confirm'].includes(call[2].operation))).toHaveLength(0);
  if(mode==='stale_draft'){
    act(()=>editor.commands.insertContent('New author note. '));
    const humanJson=editor.getJSON();
    await waitFor(()=>expect(screen.queryByRole('textbox',{name:'Suggestion text'})).not.toBeInTheDocument());
    expect(editor.getJSON()).toEqual(humanJson);
    expect(commands.mock.calls.filter(call=>['prepare','confirm'].includes(call[2].operation))).toHaveLength(0);
    expect(ordinary).not.toHaveBeenCalled();mounted.unmount();return;
  }''')
    anchor = "  mounted.unmount();mounted=render(tree());await screen.findByTestId('world-owned-plan-markdown-editor');\n  expect(screen.getByTestId('world-owned-plan-markdown-editor')).toHaveTextContent('Keep this cue.');"
    case = replace_once(case, anchor, '''  const afterJson=editor.getJSON();
  expect(afterJson.content.slice(0,4)).toEqual(beforeJson.content.slice(0,4));
  expect(afterJson.content.slice(6)).toEqual(beforeJson.content.slice(4));
  expect(afterJson.content).toHaveLength(beforeJson.content.length+2);
  expect(afterJson.content[4].content[0].text).toBe('Proposed visitors');
  // jsdom has no layout rectangles; suppress only scroll geometry, not history.
  editor.setOptions({editorProps:{...editor.options.editorProps,handleScrollToSelection:()=>true}});
  act(()=>{expect(editor.commands.undo()).toBe(true);});
  expect(editor.getJSON()).toEqual(beforeJson);
  act(()=>{expect(editor.commands.redo()).toBe(true);});
  expect(editor.getJSON()).toEqual(afterJson);
  mounted.unmount();mounted=render(tree());await screen.findByTestId('world-owned-plan-markdown-editor');
  const reopened=(screen.getByTestId('world-owned-plan-markdown-editor').querySelector('.ProseMirror') as any).editor;
  expect(reopened.getJSON()).toEqual(afterJson);
  expect(screen.getByTestId('world-owned-plan-markdown-editor')).toHaveTextContent('Keep this cue.');''')
    if typed_references:
        case = replace_once(case, TITLE, 'typed-reference Plan contextual persistence (%s)')
        case = replace_once(case, "['offered_boundary','altered_boundary','stale_draft']", "['offered_boundary','altered_boundary','stale_draft','unadmitted_reference']")
        case = replace_once(case, "|| mode === 'stale_draft')", "|| mode === 'stale_draft' || mode === 'unadmitted_reference')")
        case = replace_once(case, json.dumps(MARKDOWN), json.dumps(MARKDOWN.replace(
            'The expedition gathers beside the locked gate.',
            'The expedition gathers beside [Warden](dmb-node:warden:river) at the locked gate.').replace(
            '## Rumours\n\nKeep the alternatives open until the scouts return.',
            '## Rumours\n\nKeep the alternatives open until the scouts return. Ask [Warden](dmb-node:warden:ridge).')))
        case = replace_once(case, "const markdown='## Proposed visitors", "const markdown=mode==='unadmitted_reference'?'Ask [Warden](dmb-node:warden:new).':'## Proposed visitors")
        case = replace_once(case,
            "  fireEvent.click(within(region).getByRole('button',{name:'Save',exact:true}));",
            """  fireEvent.click(within(region).getByRole('button',{name:'Save',exact:true}));
  if(mode==='unadmitted_reference'){
    await screen.findByText('Agent proposed unsupported markup, a path, or a graph identity.');
    expect(review.state).toBe('editing');expect(editor.getJSON()).toEqual(beforeJson);
    expect(commands.mock.calls.filter(call=>['prepare','confirm'].includes(call[2].operation))).toHaveLength(0);
    expect(ordinary).not.toHaveBeenCalled();mounted.unmount();return;
  }""")
        case = replace_once(case, "expect(suggestion).toHaveTextContent('A traveling keeper may ask about the lantern.');", "expect(suggestion).toHaveTextContent(mode==='unadmitted_reference'?'Warden':'A traveling keeper may ask about the lantern.');")
        case = replace_once(case, '  const afterJson=editor.getJSON();', """  const references=(doc:any)=>{
    const result:any[]=[];
    const visit=(node:any)=>{if(node.type==='graphNodeReference')result.push({nodeId:node.attrs.nodeId,label:node.attrs.label});for(const child of node.content??[])visit(child);};
    visit(doc);return result;
  };
  const expectedReferences=[{nodeId:'warden:river',label:'Warden'},{nodeId:'warden:ridge',label:'Warden'}];
  const afterJson=editor.getJSON();
  expect(references(afterJson)).toEqual(expectedReferences);
  // Oracle contrast only: a valid wrong identity is not a runtime refusal.
  const wrong=JSON.parse(JSON.stringify(afterJson));
  const swap=(node:any)=>{if(node.type==='graphNodeReference'&&node.attrs.nodeId==='warden:ridge')node.attrs.nodeId='warden:river';for(const child of node.content??[])swap(child);};swap(wrong);
  expect(references(wrong).map((row:any)=>row.label)).toEqual(['Warden','Warden']);
  expect(references(wrong)).not.toEqual(expectedReferences);
  expect(review.applications.at(-1).after_markdown).toContain('[Warden](dmb-node:warden:river)');
  expect(review.applications.at(-1).after_markdown).toContain('[Warden](dmb-node:warden:ridge)');""")
        case = replace_once(case, '  expect(reopened.getJSON()).toEqual(afterJson);',
            '  expect(reopened.getJSON()).toEqual(afterJson);\n  expect(references(reopened.getJSON())).toEqual(expectedReferences);')
    derived = source[:start] + case + source[end:]
    # Preserve all owner setup/mocks; resolve its relative module imports from the
    # original owner directory, not from this eval's generated-file directory.
    pattern = r'''(from\s*|import\s*\(|vi\.mock\s*\()(['"])(\.{1,2}/[^'"]+)\2'''
    return re.sub(pattern, lambda m: m[1]+m[2]+str((owner.parent/m[3]).resolve())+m[2], derived)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--typed-references',action='store_true')
    parser.add_argument('--owner-root',type=Path,help='Read-only pinned owner checkout; defaults to harness checkout')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];owner_root=(args.owner_root or root).resolve();owner=owner_root/OWNER
    destination=root/'evals/inline_prose_targeting/plan_mounted.generated.test.tsx'
    if args.evidence.resolve().is_relative_to(root): raise ValueError('Evidence must be external')
    source=owner.read_text();derived=derive(source,owner,typed_references=args.typed_references)
    args.evidence.mkdir(parents=True,exist_ok=False)
    receipt={'source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
             'harness_generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'harness_tracked_dirty':subprocess.run(['git','diff','--quiet','HEAD'],cwd=root).returncode!=0,
             'owner_source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=owner_root,text=True).strip(),
             'typed_references':args.typed_references,'owner_file':OWNER,'owner_sha256':hashlib.sha256(source.encode()).hexdigest(),
             'derived_sha256':hashlib.sha256(derived.encode()).hexdigest(),
             'model':'scripted; no inference','persistence':'scripted transport; actual frontend Save owner',
             'test_filter':'typed-reference Plan contextual persistence' if args.typed_references else TITLE.replace(' (%s)','')}
    with destination.open('x') as stream:stream.write(derived)
    (args.evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (args.evidence/'derived.test.tsx').write_text(derived)
    print(destination)

if __name__=='__main__':main()
