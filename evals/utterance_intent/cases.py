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


def fresh_holdout():
    """Unscored, context-complete v2 cases; frozen before first provider call."""
    samples=[
        ('lookup','Read the saved North Gate source and bring in its connections to Lantern Hill.','retrieve','discuss','reply',[],{}),
        ('explain','Explain the sentence "The gate opens at dawn". Do not look anything up.','answer','discuss','reply',[],{}),
        ('ideas','Explore possible traditions with me; ask questions before drafting any section.','brainstorm','discuss','reply',[],{}),
        ('rules','Look up the rules for maintaining concentration after taking damage.','rules','discuss','reply',[],{}),
        ('section','Write a Market section on this page about the lantern trade.','writing','create','writing',[],{}),
        ('table','Make a table of twelve invented market vendors and their wares.','writing','create','writing',[],{}),
        ('image','Generate an image of this scene: a flooded market with floating lanterns.','image','create','image',[],{}),
        ('enemy','Increase this selected enemy to AC 17 and 90 HP; save a new statblock version.','mechanics','create','unavailable',[],{'selected_enemy':{'name':'Marsh Watcher','ac':14,'hp':55}}),
        ('encounter','Compose a new encounter with two Marsh Watchers and four lantern thieves.','encounter','create','unavailable',[],{}),
        ('place','Put that paragraph on the page.','placement','create','writing',[{'user':'Write a market description.','assistant':'The market floats on lashed timber beneath amber lanterns.'}],{}),
        ('missing','Make that change.','clarify','discuss','clarify',[],{}),
        ('compare','Compare these two approaches and discuss before writing.','brainstorm','discuss','reply',[],{'routes':['Talk to the gatekeeper for safe passage.','Sneak through the flooded cellar.']}),
    ]
    return [dict(id='holdout-v2-'+name,family='fresh_context_complete_v2',question=q,history=h,context=context,
                 capabilities=['answer_from_sources','propose_build_insertion','prepare_build_image'],
                 gold={'intent':intent,'outcome':result,'branches':[branch]},
                 provenance='Fresh constructed routing probe, not product execution evidence.')
            for name,q,branch,intent,result,h,context in samples]
