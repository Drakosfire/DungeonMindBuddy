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
