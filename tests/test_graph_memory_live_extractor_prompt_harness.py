from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
import pytest
from evals.graph_memory_layer import live_extractor_prompt_harness as h


def test_prompt_manifest_validates():
    h.validate_prompt_manifest(h.load_manifest())
    h.validate_prompt_packet_manifest(h.load_sample_packet_manifest())


def test_one_shot_and_two_shot_render_deterministically():
    v=h.verify_run_bundle_and_source(Path(h.SESSION_23_RUN_BUNDLE),Path(h.SESSION_23_SOURCE_RECAP))
    one=h.render_prompts('one_shot',v)
    two=h.render_prompts('two_shot',v)
    assert one==h.render_prompts('one_shot',v)
    assert two==h.render_prompts('two_shot',v)
    joined='\n'.join([*one.values(), *two.values()])
    for needle in ['source_span_ref_id','Preserve uncertainty','High-risk claims','alias binding','identity binding','inferred relationships','cliffhanger outcomes','uncertain counts','unsupported canon promotion','do not approve memory','do not execute writes','do not emit runtime payloads','do not emit /plan payloads','do not emit Agent Interaction payloads']:
        assert needle in joined


def test_source_recap_identity_rejections(tmp_path):
    source=Path(h.SESSION_23_SOURCE_RECAP)
    bad=tmp_path/'bad.md'; bad.write_text(source.read_text().replace('Mireward', 'MirewardX', 1))
    with pytest.raises(h.HarnessValidationError, match='source_recap_sha256_mismatch'):
        h.verify_run_bundle_and_source(Path(h.SESSION_23_RUN_BUNDLE), bad)
    short=tmp_path/'short.md'; short.write_text('\n'.join(source.read_text().splitlines()[:-1]))
    with pytest.raises(h.HarnessValidationError, match='source_recap_sha256_mismatch|source_recap_line_count_mismatch'):
        h.verify_run_bundle_and_source(Path(h.SESSION_23_RUN_BUNDLE), short)
    with pytest.raises(h.HarnessValidationError, match='source_recap_missing'):
        h.validate_source_recap_path(tmp_path/'missing.md')
    d=tmp_path/'dir'; d.mkdir()
    with pytest.raises(h.HarnessValidationError, match='source_recap_is_directory'):
        h.validate_source_recap_path(d)
    with pytest.raises(h.HarnessValidationError, match='source_recap_is_glob'):
        h.validate_source_recap_path(Path('*.md'))


def test_output_guards_and_cli_render(tmp_path):
    root=h.repo_root()
    with pytest.raises(h.HarnessValidationError, match='output_outside_allowed_run_dir'):
        h.validate_output_path(tmp_path/'out')
    with pytest.raises(h.HarnessValidationError, match='output_outside_allowed_run_dir'):
        h.validate_output_path(Path(h.RUNS_DIR), allow_overwrite=True)
    out=Path(h.RUNS_DIR)/'pytest_one_shot'
    res=subprocess.run([sys.executable,'-m','evals.graph_memory_layer.render_live_extractor_prompt_harness','--mode','one_shot','--run-bundle',h.SESSION_23_RUN_BUNDLE,'--source-recap',h.SESSION_23_SOURCE_RECAP,'--out',str(out),'--allow-overwrite'],cwd=root,text=True,capture_output=True,check=True)
    assert res.returncode==0
    target=root/out
    assert (target/'prompt_packet_manifest.json').exists()
    assert (target/'source_packet_summary.json').exists()
    prompt=(target/'one_shot_prompt.md').read_text()
    assert 'spref:session-23:p001' in prompt and 'Candidate Graph Preview IR' in prompt


def test_candidate_output_validator_rejects_promoted_output():
    bad={section:[] for section in h.REQUIRED_SECTIONS}
    bad['proposed_writes']=[{'write_id':'w1','state':'approved_memory','evidence_refs':[{'source_span_ref_id':'spref:session-23:p001'}]}]
    with pytest.raises(h.HarnessValidationError, match='forbidden_candidate_output'):
        h.validate_candidate_output(bad, {'spref:session-23:p001'})



def test_candidate_output_validator_requires_evidence_refs():
    allowed={'spref:session-23:p001'}
    for section in h.CANDIDATE_EVIDENCE_SECTIONS:
        missing={name:[] for name in h.REQUIRED_SECTIONS}
        missing[section]=[{'candidate_id':'c1'}]
        with pytest.raises(h.HarnessValidationError, match=f'missing_evidence_refs:{section}:c1'):
            h.validate_candidate_output(missing, allowed)
        empty={name:[] for name in h.REQUIRED_SECTIONS}
        empty[section]=[{'candidate_id':'c1','evidence_refs':[]}]
        with pytest.raises(h.HarnessValidationError, match=f'missing_evidence_refs:{section}:c1'):
            h.validate_candidate_output(empty, allowed)


def test_candidate_output_validator_rejects_unknown_evidence_refs():
    bad={section:[] for section in h.REQUIRED_SECTIONS}
    bad['candidate_nodes']=[{'candidate_id':'c1','evidence_refs':[{'source_span_ref_id':'spref:session-23:missing'}]}]
    with pytest.raises(h.HarnessValidationError, match='unknown_source_span_ref:spref:session-23:missing'):
        h.validate_candidate_output(bad, {'spref:session-23:p001'})


def test_candidate_output_validator_accepts_evidenced_candidate_objects():
    good={section:[] for section in h.REQUIRED_SECTIONS}
    for section in h.CANDIDATE_EVIDENCE_SECTIONS:
        good[section]=[{'candidate_id':f'{section}:1','evidence_refs':[{'source_span_ref_id':'spref:session-23:p001'}]}]
    report=h.validate_candidate_output(good, {'spref:session-23:p001'})
    assert report['evidence_ref_count']==len(h.CANDIDATE_EVIDENCE_SECTIONS)

def test_validation_and_report_clis():
    root=h.repo_root()
    for mod in ['evals.graph_memory_layer.validate_live_extractor_prompt_harness','evals.graph_memory_layer.report_live_extractor_prompt_harness']:
        res=subprocess.run([sys.executable,'-m',mod],cwd=root,text=True,capture_output=True,check=True)
        assert res.returncode==0
