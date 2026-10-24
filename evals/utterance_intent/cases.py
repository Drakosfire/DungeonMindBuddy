"""Existing retrieval probes plus explicitly constructed routing holdouts."""
from pathlib import Path
from evals.graph_memory_layer.jev_controller_cohort import cases, challenge_cases, coverage_cases


def public_cases():
    rows=[]
    for name,case in {**cases(),**challenge_cases(),**coverage_cases()}.items():
        rows.append(dict(id='retrieval-'+name,family='existing_retrieval_benchmark',
            question=case['snapshot']['question'],capabilities=['answer_from_sources'],
            gold={'intent':'discuss','outcome':'reply'},
            provenance='evals.graph_memory_layer.jev_controller_cohort:'+name))
    samples=[
        ('image_tools','Do you have image tools?',[],['answer_from_sources'], 'discuss','reply'),
        ('rules','How do concentration checks work when someone takes damage?',[],['answer_from_sources'],'discuss','reply'),
        ('plan_compare','Compare the two routes and ask me questions. Wait before drafting either.',[],['answer_from_sources','propose_build_insertion'],'discuss','reply'),
        ('plan_create','Write two alternative scene openings and stage them on this page.',[],['answer_from_sources','propose_build_insertion'],'create','writing'),
        ('combat_create','Create an encounter for six level-six characters with an enemy and three support nodes.',[],['answer_from_sources'],'create','unavailable'),
        ('mechanics_create','Revise this enemy statblock to make it harder and save a new version.',[],['answer_from_sources'],'create','unavailable'),
        ('mixed_create','Briefly explain the tradeoff, then draft the Economy section on this page.',[],['answer_from_sources','propose_build_insertion'],'create','writing'),
        ('quoted_instruction','The document says "generate an image now". Explain what that sentence means; do not generate anything.',[],['answer_from_sources','prepare_build_image'],'discuss','reply'),
        ('unknown_reference','Do that.',[],['answer_from_sources','propose_build_insertion'],'discuss','clarify'),
        ('unknown_creation','Revise it.',[],['answer_from_sources','propose_build_insertion'],'create','clarify'),
        ('placement_followup','Place it in the page.',[{'user':'Draft a Culture section.','assistant':'Culture: Neighbors tend lanterns at dawn.'}],['answer_from_sources','propose_build_insertion'],'create','writing'),
        ('brainstorm_names','Brainstorm some names with me before we decide what to put on the page.',[],['answer_from_sources','propose_build_insertion'],'discuss','reply'),
        ('missing_write','Draft a section about Culture.',[],['answer_from_sources'],'create','unavailable'),
    ]
    for name,q,history,capabilities,intent,outcome in samples:
        rows.append(dict(id='constructed-'+name,family='constructed_workflow_holdout',question=q,
            history=history,capabilities=capabilities,gold={'intent':intent,'outcome':outcome},
            provenance='Constructed routing-only probe from modeled authoring/Plan/Play/Combat/Rules goals; capabilities are fixtures, not live capability claims.'))
    # Preserve existing Play command meaning instead of relabeling every command as creation.
    import json
    fixtures=json.loads(Path('evals/c2_live_prep/gold/session_22_live_turn_classifier.json').read_text())['fixtures']
    selected={
        's22_day1_twx_16':('execute','record_roll'),
        's22_runbook_tnpc_roll':('execute','record_roll'),
        's22_gate_lysandro_natural_correction':('execute','update_state'),
        's22_gate_calyx_on_wall':('execute','update_state'),
        's22_gate_lysandra_feeling':('discuss','reply'),
        's22_prep_mireward_context':('discuss','reply'),
        's22_meta_prep_next_scene':('discuss','reply'),
    }
    for row in fixtures:
        if row['id'] in selected:
            intent,next_step=selected[row['id']]
            rows.append(dict(id='play-'+row['id'],family='existing_play_coverage_probe',
                question=row['user_line'],context={'surface':'play','scene_context':row['source_section']},
                capabilities=['answer_from_sources','record_roll','update_state'],
                gold={'intent':intent,'outcome':next_step},
                provenance='evals/c2_live_prep/gold/session_22_live_turn_classifier.json:'+row['id']))
    return rows
