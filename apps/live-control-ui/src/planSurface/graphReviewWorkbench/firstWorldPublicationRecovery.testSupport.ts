import type {ExactRunReviewPackage,FirstWorldGraphPlan} from '../../api/types';

/** Current server carrier fields for focused synthetic UI fixtures. */
export function withFirstWorldEffect(plan:FirstWorldGraphPlan,review:ExactRunReviewPackage):FirstWorldGraphPlan{
  const source={source_artifact_id:plan.sourceArtifactId,source_revision_id:plan.sourceRevisionId,campaign_scope:plan.worldId};
  const snapshot=plan.reviewedEffect.decision_snapshot as {assertion_id:string;decision:string}[];
  let accepted=0,rejected=0;
  const map=Object.fromEntries(snapshot.map(row=>[row.assertion_id,[row.decision==='reject'
    ?plan.rejectedAssertionIds[rejected++]:plan.acceptedAssertionIds[accepted++]]]));
  if(snapshot.length!==review.assertions.length||accepted!==plan.acceptedAssertionIds.length||rejected!==plan.rejectedAssertionIds.length)
    throw new Error('Synthetic candidate decisions must match materialized fixture assertions.');
  const proposal = (assertion_id: string, state: string) => {
    const candidateId = Object.keys(map).find(id => map[id].includes(assertion_id))!;
    const candidate = review.assertions.find(row => row.assertionId === candidateId)!;
    return {...source, assertion_id, acceptance_state: state,
      assertion_kind: candidate.kind === 'object' ? 'node' : 'edge', label: candidate.label,
      subject_node_id: candidate.kind === 'object' ? candidate.assertionId : candidate.fromCandidateNodeId,
      target_node_id: candidate.kind === 'relationship' ? candidate.toCandidateNodeId : null,
      predicate: candidate.relationshipType ?? null,
      value: candidate.kind === 'object' ? {kind: candidate.contributionKind}
        : {predicate: candidate.relationshipType, direction: 'outbound'}};
  };
  return {...plan,campaignScope:plan.worldId,sessionScope:null,reviewedEffect:{...plan.reviewedEffect,
    contribution_meta:{...source,source_kind:'source_extraction',extraction_profile:plan.extractionProfile,authored_by:'live_control:worldbuilding_write_plan'},
    accepted_proposals:plan.acceptedAssertionIds.map(id=>proposal(id,'accepted')),
    rejected_assertions:plan.rejectedAssertionIds.map(id=>proposal(id,'rejected')),candidate_effect_map:map}};
}


import type {NativeFirstWorldPlan, NativeFirstWorldReceipt} from '../../api/nativeFirstWorldPublicationTypes';

/** Synthetic signed-envelope fixture; client tests do not pretend to verify HMAC. */
export function withNativeFirstWorldPlan(plan:Omit<FirstWorldGraphPlan,'schema'>&{schema:FirstWorldGraphPlan['schema']|'dmb_native_first_world_plan_v1'},review:ExactRunReviewPackage):NativeFirstWorldPlan{
  const classic=withFirstWorldEffect({...plan,schema:'dmb_first_world_graph_plan_v3'},review);
  const bodySha256=classic.sourceRevisionId.slice(7);
  return {...classic,schema:'dmb_native_first_world_plan_v1',runRevision:1,campaignScope:classic.worldId,sessionScope:null,
    compilerIntentJson:JSON.stringify({world_id:classic.worldId,reviewed_effect:classic.reviewedEffect,source_body_sha256:bodySha256}),
    compilerIntentSha256:'e'.repeat(64),domainContractRef:{domain_id:'dungeonbuddy.world',domain_revision:'2',descriptor_sha256:'d'.repeat(64)},
    targetProfileRef:{profile_id:'dungeonbuddy.dnd5e',profile_revision:'2',descriptor_sha256:'f'.repeat(64)},
    sourceStage:{admissionState:'absent',admissionId:'admission:first',admissionReceiptSha256:null,nativeSourceArtifactId:null,
      nativeSourceRevisionId:null,wholeDocumentEvidenceRefId:null,documentId:classic.workspaceDocumentId,sourceRootRelpath:'corpus/source',
      documentRevision:Number(classic.workspaceDocumentRevision),documentUpdatedAt:'2026-11-19T12:00:00Z',bodySha256,
      origin:{namespace:'dungeonbuddy.workspace',object_id:classic.workspaceDocumentId,revision_id:'registry-revision:'+classic.workspaceDocumentRevision},
      genesisInitializationId:classic.nativeTarget.provisioningId,genesisCreatedAt:'2026-11-19T12:00:00Z',headRevisionId:null,headProfileRef:null,
      sourceAuthorityEpoch:0,extensionId:'extension:first',profileTransitionId:'transition:first',existingBindings:[]},
    publicationId:'publication:first',preparedBy:'operator',createdAt:'2026-11-19T12:00:00Z',expiresAt:'2026-11-19T13:00:00Z',
    policy:'dmb_native_first_world_compiler_v1',token:'synthetic-server-signed-plan'};
}
export function nativeFirstWorldReceipt(plan:NativeFirstWorldPlan,overrides:Partial<NativeFirstWorldReceipt>={}):NativeFirstWorldReceipt{
  const core={space_id:plan.nativeTarget.nativeWorldId,publication_id:plan.publicationId,published_revision_id:'rev:1'};
  return {schema:'dmb_native_first_world_confirm_v1',outcome:'initialized',worldId:plan.worldId,planId:plan.planId,
    planDigest:plan.planDigest,decisionDigest:plan.decisionDigest,sourceArtifactId:plan.sourceArtifactId,sourceRevisionId:plan.sourceRevisionId,
    contributionId:plan.contributionId,nativeContributionId:'native-contribution:first',nativeWorldId:plan.nativeTarget.nativeWorldId,
    publicationId:plan.publicationId,committedRevisionId:'rev:1',appliedAssertionCount:plan.acceptedAssertionIds.length,
    acceptedAssertionIds:plan.acceptedAssertionIds,rejectedAssertionIds:plan.rejectedAssertionIds,
    nativePublication:{publication_receipt:{...core},prospective_result:{...core}},activationStatus:'active',sourceStatus:'available',recovered:false,warnings:[],...overrides};
}

export function legacyFirstWorldPlan(plan:NativeFirstWorldPlan):FirstWorldGraphPlan{
  const keys=['sourceEvidenceSha256','planId','planDigest','decisionDigest','worldId','nativeTarget','runId','sourceArtifactId','sourceRevisionId',
    'workspaceDocumentId','workspaceDocumentRevision','campaignScope','sessionScope','extractionProfile','acceptedAssertionIds','rejectedAssertionIds',
    'contributionId','contributionPayloadSha256','reviewedEffect','summary','confirmable','diagnostics'] as const;
  return {schema:'dmb_first_world_graph_plan_v3',...Object.fromEntries(keys.map(key=>[key,plan[key]]))} as FirstWorldGraphPlan;
}
