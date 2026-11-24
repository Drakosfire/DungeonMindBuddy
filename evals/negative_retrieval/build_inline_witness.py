"""Generate a scoped UI witness from the existing mounted conversation test.

Run only in a disposable copy of the UI source. Exact textual anchors must
match; the generated test is a scripted transport/component witness, not an
ordinary model, server persistence, browser, or deployment qualification.
"""
from pathlib import Path


def generate(source, output):
    if Path(source).resolve() == Path(output).resolve():
        raise ValueError("Witness output must not replace the owner fixture")
    text = Path(source).read_text()

    def replace_once(original, replacement):
        nonlocal text
        if text.count(original) != 1:
            raise ValueError("Mounted owner fixture anchor changed")
        text = text.replace(original, replacement, 1)

    replace_once('interface ConversationTestProps {',
                 'interface ConversationTestProps {\n  buildMode?: Parameters<typeof WorldPlanAgentConversation>[0]["buildMode"];')
    replace_once('      playMode={props.playMode}',
                 '      playMode={props.playMode}\n      buildMode={props.buildMode}')
    replace_once("it('rehydrates an intentional object-only clarification inline without a filler reply', async()=>{",
                 "it('negative retrieval Build inline question answer and send witness', async()=>{")
    start = text.index("it('negative retrieval Build inline question answer and send witness'")
    end = text.index('\n  });', start)
    before, test, after = text[:start], text[start:end], text[end:]
    mount = '    await mountComponent();'
    assertion = "    expect(screen.getByLabelText('Question 1')).toHaveValue('Which shop should we develop?');"
    if test.count(mount) != 1 or test.count(assertion) != 1:
        raise ValueError("Clarification fixture body changed")
    setup = '''    const buildMode = {savedSource:{worldId, documentId:'other-work', revision:1,
      contentSha256, surfaceInstanceId:'other-work', title:'Working page', dirty:false}};
    render(conversationElement({buildMode}));
    await waitForConversationReady();'''
    interaction = '''
    fireEvent.change(screen.getByLabelText('Answer 1'),{target:{value:'The harbour shop.'}});
    cleanup();
    render(conversationElement({buildMode}));
    await waitForConversationReady();
    expect(await screen.findByLabelText('Answer 1')).toHaveValue('The harbour shop.');
    fireEvent.click(screen.getByRole('button',{name:'Add to message'}));
    expect((screen.getByLabelText('Message DungeonBuddy') as HTMLTextAreaElement).value).toContain('My answer: The harbour shop.');
    const post=vi.spyOn(liveApi,'postWorldBuildAgentTurn').mockReturnValue(new Promise(()=>{}));
    fireEvent.click(screen.getByRole('button',{name:'Send message'}));
    await waitFor(()=>expect(post).toHaveBeenCalledTimes(1));
    expect(post.mock.calls[0]![0].surface.surface_id).toBe('build');
    expect(post.mock.calls[0]![0].message).toContain('My answer: The harbour shop.');
'''
    test = test.replace(mount, setup, 1).replace(assertion, assertion + interaction, 1)
    Path(output).write_text(before + test + after)
