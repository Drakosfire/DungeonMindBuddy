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

def derive(source: str, owner: Path) -> str:
    start = source.index("it.each(['valid','offered_boundary','altered_boundary'")
    end = source.index('\n});', start) + len('\n});')
    case = source[start:end]
    header = case[:case.index('async mode=>{')]
    case = replace_once(case, header, "it.each(['offered_boundary','altered_boundary','stale_draft'] as const)(" + json.dumps(TITLE) + ',')
    case = replace_once(case, "const record=mockSavedPlanForAgent(savedAgentPlanId,7,7,'# Plan\\n\\nOriginal preparation.\\n');",
                        'const record=mockSavedPlanForAgent(savedAgentPlanId,7,7,' + json.dumps(MARKDOWN) + ');')
    case = replace_once(case, "if (mode === 'offered_boundary' || mode === 'altered_boundary')", "if (mode === 'offered_boundary' || mode === 'altered_boundary' || mode === 'stale_draft')")
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
    derived = source[:start] + case + source[end:]
    # Preserve all owner setup/mocks; resolve its relative module imports from the
    # original owner directory, not from this eval's generated-file directory.
    pattern = r'''(from\s*|import\s*\(|vi\.mock\s*\()(['"])(\.{1,2}/[^'"]+)\2'''
    return re.sub(pattern, lambda m: m[1]+m[2]+str((owner.parent/m[3]).resolve())+m[2], derived)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];owner=root/OWNER
    destination=root/'evals/inline_prose_targeting/plan_mounted.generated.test.tsx'
    if args.evidence.resolve().is_relative_to(root): raise ValueError('Evidence must be external')
    source=owner.read_text();derived=derive(source,owner)
    args.evidence.mkdir(parents=True,exist_ok=False)
    receipt={'source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
             'owner_file':OWNER,'owner_sha256':hashlib.sha256(source.encode()).hexdigest(),
             'derived_sha256':hashlib.sha256(derived.encode()).hexdigest(),
             'model':'scripted; no inference','persistence':'scripted transport; actual frontend Save owner',
             'test_filter':TITLE.replace(' (%s)','')}
    with destination.open('x') as stream:stream.write(derived)
    (args.evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (args.evidence/'derived.test.tsx').write_text(derived)
    print(destination)

if __name__=='__main__':main()
