import { expect, it, vi } from 'vitest';
import { buildBuildSurfaceInteractionPublication } from './buildBuildSurfaceInteractionPublication';
import { BUILD_FIND_EXISTING_TOOL_ID } from './buildReferenceIds';
it('retains Save, canvas identity and independent tools when native World identity is unavailable', async () => {
    const save = vi.fn();
    const p = buildBuildSurfaceInteractionPublication({ documentId: 'doc', acceptedDocument: { documentId: 'doc', worldId: null }, referenceContext: null, documentSave: { saveDisabled: false, save } });
    expect(p.canvas?.workObject).toEqual({ kind: 'document', id: 'doc' });
    expect(p.tools.find(t => t.id === BUILD_FIND_EXISTING_TOOL_ID)?.availability.status).toBe('disabled');
    expect(p.tools).toHaveLength(3);
    await p.editCommands[0]!.invoke();
    expect(save).toHaveBeenCalledOnce();
});
it('publishes no document command before document admission', () => {
    const p = buildBuildSurfaceInteractionPublication({ documentId: 'doc', acceptedDocument: null, referenceContext: null, documentSave: { saveDisabled: false, save: vi.fn() } });
    expect(p.canvas).toBeNull();
    expect(p.editCommands).toEqual([]);
    expect(p.tools).toHaveLength(2);
});
