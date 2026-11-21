import { webcrypto } from 'node:crypto';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import {
  BuildGraphReferenceReviewError, graphReferenceReview, type BuildGraphReferenceReviewRecord,
} from '../api/buildGraphReferenceReviewApi';
import type { BuildComposeBridge, PreparedBuildGraphReference } from './buildComposeBridge';
import { BuildGraphReferenceReview } from './BuildGraphReferenceReview';

vi.mock('../api/buildGraphReferenceReviewApi', async importOriginal => ({
  ...await importOriginal<typeof import('../api/buildGraphReferenceReviewApi')>(),
  graphReferenceReview: vi.fn(),
}));
vi.stubGlobal('crypto',webcrypto);

const digest = 'a'.repeat(64);
const action = 'reference-action';
const world = 'observatory';
const editing: BuildGraphReferenceReviewRecord = {
  schema:'dmb_build_graph_reference_review_v1', action_id:action, revision:1, state:'editing', apply:null, saved_revision:null,
  placement:{
    basis:{world_id:world,document_id:'moon-gallery',registry_revision:1,content_sha256:digest,visibility:'internal',
      caret:1,draft_sha256:digest,editor_sha256:digest,draft_generation:0,selection_generation:0},
    boundary:{schema:'dmb_build_prose_boundary_target_v1',alias:'passage1:insert_after',operation:'insert_after',
      from:9,to:9,catalog_sha256:digest,before_text_sha256:digest},
    reference:{schema:'dmb_authored_graph_reference_v1',managed_world_id:world,native_world_id:'native-vol',
      binding_version:1,graph_revision:'rev:current',node_id:'threat:lurker',label:'Moon Lurker'},
    entity_kind:'threat',
  },
};

function bridgeFixture() {
  const prepared = {
    captured:{editorJson:'before editor',draftMarkdown:'before draft'},
    placement:editing.placement,afterEditorJson:'after editor',afterDraft:'after draft',
    postimage:{editor_sha256:digest,draft_sha256:digest,content_sha256:digest,presentation_sha256:null},
  } as PreparedBuildGraphReference;
  return {
    prepareGraphReference:vi.fn().mockResolvedValue(prepared), applyGraphReference:vi.fn(),
    inspectProposal:vi.fn().mockResolvedValue({state:'before'}), saveProposal:vi.fn().mockResolvedValue(undefined),
  } satisfies Partial<BuildComposeBridge>;
}

beforeEach(() => vi.mocked(graphReferenceReview).mockReset());

it('opens an inert review and refuses a changed Graph before applying or saving', async () => {
  const bridge = bridgeFixture();
  vi.mocked(graphReferenceReview).mockImplementation(async (_world,_action,command) => {
    if (!command) return editing;
    if (command.operation === 'prepare') return {...editing,state:'applying',revision:2,apply:command.apply};
    throw new BuildGraphReferenceReviewError(409);
  });
  render(<BuildGraphReferenceReview world={world} action={action} bridge={bridge as unknown as BuildComposeBridge} />);
  const insert = await screen.findByRole('button',{name:'Insert and save reference'});
  expect(screen.getByText('Moon Lurker')).toBeTruthy();
  expect(graphReferenceReview).toHaveBeenCalledTimes(1);
  expect(bridge.prepareGraphReference).not.toHaveBeenCalled();
  fireEvent.click(insert);
  expect(await screen.findByRole('alert')).toHaveTextContent('page or Graph reference changed');
  expect(bridge.applyGraphReference).not.toHaveBeenCalled();
  expect(bridge.saveProposal).not.toHaveBeenCalled();
});

it('recovers a dropped prepare reply using its same apply ID and saves once', async () => {
  const bridge = bridgeFixture();
  const onComplete = vi.fn();
  let current = editing;
  let committed = false;
  bridge.saveProposal.mockImplementation(async () => { committed = true; });
  const prepareIds: string[] = [];
  vi.mocked(graphReferenceReview).mockImplementation(async (_world,_action,command) => {
    if (!command) return current;
    if (command.operation === 'prepare') {
      prepareIds.push(command.apply.apply_id);
      current = {...editing,state:'applying',revision:2,apply:command.apply};
      if (prepareIds.length === 1) throw new Error('The prepare acknowledgement was interrupted.');
      return current;
    }
    if (command.operation === 'authorize_save') return current;
    if (command.operation !== 'confirm') throw new Error('Unexpected Review command');
    if (!committed) throw new BuildGraphReferenceReviewError(409);
    return {...current,state:'applied',revision:3,saved_revision:2};
  });
  render(<BuildGraphReferenceReview world={world} action={action} bridge={bridge as unknown as BuildComposeBridge} onComplete={onComplete} />);
  fireEvent.click(await screen.findByRole('button',{name:'Insert and save reference'}));
  const finish = await screen.findByRole('button',{name:'Finish saving reference'});
  await waitFor(() => expect(finish).not.toBeDisabled());
  expect(bridge.applyGraphReference).not.toHaveBeenCalled();
  fireEvent.click(finish);
  expect(await screen.findByRole('status')).toHaveTextContent('Graph reference saved.');
  expect(prepareIds).toHaveLength(2);
  expect(prepareIds[0]).toBe(prepareIds[1]);
  expect(bridge.applyGraphReference).toHaveBeenCalledTimes(1);
  expect(bridge.saveProposal).toHaveBeenCalledTimes(1);
  expect(onComplete).toHaveBeenCalledExactlyOnceWith('applied');
});
