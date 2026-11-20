import { expect, it } from 'vitest';
import { readBuildReferenceContextBinding } from './BuildReferenceSearchProjection';
import { BUILD_REFERENCE_CONTEXT_BINDING_ID } from './buildReferenceIds';
it('rejects obsolete projection bindings rather than falling back to a different Graph', () => {
    expect(() => readBuildReferenceContextBinding({})).toThrow(/current World document/);
    expect(() => readBuildReferenceContextBinding({ [BUILD_REFERENCE_CONTEXT_BINDING_ID]: { schema: 'dmb_build_reference_context_v2' } })).toThrow(/current World document/);
});
