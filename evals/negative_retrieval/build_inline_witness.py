"""Generate a scoped UI witness from the existing mounted conversation test.

Run only in a disposable copy of the UI source. Exact textual anchors must
match; the generated test uses scripted transport and saved history. It is not
an ordinary model, server persistence, browser, or deployment qualification.
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
    history_setup = "    setupApi({...history('conversation-a',1,[]),schema:'dmb_agent_conversation_history_v2',turns:[{...turn,knowledge_context:knowledge}]} as WorldAgentConversationHistoryResponse);"
    if test.count(mount) != 1 or test.count(assertion) != 1 or test.count(history_setup) != 1:
        raise ValueError("Clarification fixture body changed")
    saved_history = '''    let savedHistory={...history('conversation-a',1,[]),schema:'dmb_agent_conversation_history_v2',turns:[{...turn,knowledge_context:knowledge}]} as WorldAgentConversationHistoryResponse;
    const api=setupApi(savedHistory, false);
    api.getMessages.mockImplementation(async()=>{const page=api.messages(savedHistory);return {...page,messages:page.messages.map(row=>row.turn_id===turnId?{...row,reply_object:{kind:'questions' as const,questions:[{text:'Which shop should we develop?'}],source:{world_id:worldId,conversation_id:'conversation-a',turn_id:turnId,document_id:'other-work',surface_id:'build' as const}}}:row)};});'''
    setup = '''    const buildMode = {savedSource:{worldId, documentId:'other-work', revision:1,
      contentSha256, surfaceInstanceId:'other-work', title:'Working page', dirty:false}};
    render(conversationElement({buildMode}));
    await waitForConversationReady();
    const initialQuestion = await screen.findByText('Ask which shop I want to develop.');
    const initialDetails = initialQuestion.closest('article')?.querySelector('details');
    expect(initialDetails).toBeTruthy();
    if (!initialDetails!.open) fireEvent.click(initialDetails!.querySelector('summary')!);'''
    interaction = '''
    fireEvent.change(screen.getByLabelText('Answer 1'),{target:{value:'The harbour shop.'}});
    cleanup();
    render(conversationElement({buildMode}));
    await waitForConversationReady();
    expect(await screen.findByLabelText('Answer 1')).toHaveValue('The harbour shop.');
    fireEvent.click(screen.getByRole('button',{name:'Add to message'}));
    expect((screen.getByLabelText('Message DungeonBuddy') as HTMLTextAreaElement).value).toContain('My answer: The harbour shop.');
    const post=vi.spyOn(liveApi,'postWorldBuildAgentTurn').mockImplementation(async (request:any)=>{
      const savedAnswer=historyTurnForAsk(request as any, 'The harbour shop is ready for review.');
      savedAnswer.sequence=2;
      savedAnswer.provenance.primary_work={...savedAnswer.provenance.primary_work,kind:'build',object_id:'other-work',revision:'1',content_sha256:contentSha256,object_revision:null,work_revision_id:null,revision_n:null};
      savedHistory={...history('conversation-a',1,[{...turn,knowledge_context:knowledge} as any,savedAnswer]),schema:'dmb_agent_conversation_history_v2'} as WorldAgentConversationHistoryResponse; api.setCurrent(savedHistory);
      const response=agentResponse(request as any,'conversation-a','The harbour shop is ready for review.');
      return {...response,surface:{surface_id:'build',instance_id:'other-work',status:'resolved'},primary_work:{...response.primary_work,kind:'build',object_id:'other-work',content_basis:null}} as any;
    });
    fireEvent.click(screen.getByRole('button',{name:'Send message'}));
    await waitFor(()=>expect(post).toHaveBeenCalledTimes(1));
    expect(post.mock.calls[0]![0].surface.surface_id).toBe('build');
    expect(post.mock.calls[0]![0].message).toContain('My answer: The harbour shop.');
    await screen.findByText('The harbour shop is ready for review.');
    cleanup();
    render(conversationElement({buildMode}));
    await waitForConversationReady();
    const savedQuestion = await screen.findByText('Ask which shop I want to develop.');
    const details = savedQuestion.closest('article')?.querySelector('details');
    expect(details).toBeTruthy();
    if (!details!.open) fireEvent.click(details!.querySelector('summary')!);
    expect(await screen.findByLabelText('Question 1', {}, {timeout: 5000})).toHaveValue('Which shop should we develop?');
    expect(await screen.findByText(/My answer: The harbour shop/)).toBeInTheDocument();
    expect(await screen.findByText('The harbour shop is ready for review.')).toBeInTheDocument();
    expect(screen.queryByText(/Retry this saved request/)).not.toBeInTheDocument();

'''
    test = test.replace(history_setup, saved_history, 1).replace(mount, setup, 1).replace(assertion, assertion + interaction, 1)
    after = after.replace('\n  });', '\n  }, 15000);', 1)
    Path(output).write_text(before + test + after)
