from __future__ import annotations
import subprocess, sys
from pathlib import Path
import pytest
from evals.graph_memory_layer import live_recap_ingest_run_bundle as l


def test_manifest_and_bundle_validate():
    m=l.load_example_manifest(); b=l.load_example_run_bundle()
    assert m['schema']==l.LIVE_RECAP_INGEST_MANIFEST_SCHEMA
    assert m['fixture_id']==l.LIVE_RECAP_INGEST_FIXTURE_ID
    assert m['campaign_id']=='longmont-c2' and m['target_session']==23
    assert m['sample_run_id']==l.SESSION_23_SAMPLE_RUN_ID
    assert m['sample_run_dir']==l.SESSION_23_SAMPLE_DIR
    assert not any(v for k,v in m['diagnostics'].items() if k not in {'static_example_fixture','live_recap_ingest_runner_present'})
    l.validate_bundle_consistency(b)


def test_input_output_boundary_rejections(tmp_path):
    with pytest.raises(l.BundleValidationError, match='input_missing'):
        l.validate_explicit_input_path(tmp_path/'missing.md')
    d=tmp_path/'dir'; d.mkdir()
    with pytest.raises(l.BundleValidationError, match='input_is_directory'):
        l.validate_explicit_input_path(d)
    with pytest.raises(l.BundleValidationError, match='input_is_glob'):
        l.validate_explicit_input_path(Path('*.md'))
    corpus=l.repo_root()/'corpus'/'tmp_live_recap_test.md'; corpus.parent.mkdir(exist_ok=True); corpus.write_text('x')
    try:
        with pytest.raises(l.BundleValidationError, match='corpus_input_without_explicit_override'):
            l.validate_explicit_input_path(corpus)
        l.validate_explicit_input_path(corpus, allow_corpus_input=True)
    finally:
        corpus.unlink()
    with pytest.raises(l.BundleValidationError, match='output_outside_allowed_run_dir'):
        l.validate_output_path(tmp_path/'out')
    l.validate_output_path(Path(l.SESSION_23_SAMPLE_DIR), allow_example_output=True)


def test_units_spans_provenance_deterministic_and_safe():
    b=l.load_example_run_bundle(); expected=l.build_sample_bundle()
    assert b==expected
    units=b['source_units']['units']; spans=b['source_span_index']['spans']
    assert len({u['source_unit_id'] for u in units})==len(units)
    assert all(u['line_start']<=u['line_end'] and u['char_start']<u['char_end'] and len(u['text_preview'])<=96 and u['text_hash'] for u in units)
    assert len({s['source_span_ref_id'] for s in spans})==len(spans)
    known={u['source_unit_id'] for u in units}
    assert all(s['source_unit_id'] in known and s['openable'] and s['highlightable'] for s in spans)
    assert b['provenance_index']['input_provenance']['input_mode']=='explicit_file_path'
    assert b['provenance_index']['input_provenance']['input_sha256']
    assert b['run_manifest']['source']['input_path_record']==l.SAMPLE_INPUT_PATH
    l.validate_no_runtime_leakage(b)


def test_report_and_diagnostics_boundary_text():
    b=l.load_example_run_bundle(); report=b['recap_ingest_report']; d=b['diagnostics']
    assert d['status']=='ready'
    assert d['counts']['warnings']==len(d['warnings'])==0
    assert d['counts']['hard_failures']==len(d['hard_failures'])==0
    assert d['boundary']['explicit_input_only'] is True
    assert not any(v for k,v in d['boundary'].items() if k!='explicit_input_only')
    for text in ['does not call an LLM','does not execute extraction','does not generate a candidate graph','does not write graph memory','does not execute graph queries','does not connect /plan','does not connect Agent Interaction','does not scan or mutate corpus','future gated live extractor dogfood harness']:
        assert text in report


def test_clis_and_temp_run(tmp_path):
    root=l.repo_root(); recap=tmp_path/'recap.md'; before=None
    recap.write_text('# Session Test\n\nThe party reached the north gate.\n\nA messenger warned that something was coming.\n')
    before=recap.read_text()
    out=Path(l.LIVE_RECAP_RUNS_DIR)/'pytest_tmp_live_recap'
    for cmd in [
        [sys.executable,'-m','evals.graph_memory_layer.validate_live_recap_ingest_run_bundle'],
        [sys.executable,'-m','evals.graph_memory_layer.report_live_recap_ingest_run_bundle'],
        [sys.executable,'-m','evals.graph_memory_layer.run_live_recap_ingest','--campaign-id','longmont-c2','--session-id','session-test','--input',str(recap),'--out',str(out),'--allow-overwrite'],
    ]:
        res=subprocess.run(cmd,cwd=root,text=True,capture_output=True,check=True)
        assert res.returncode==0
    assert recap.read_text()==before
    bundle={
        'run_manifest': l.load_json(str(out/'run_manifest.json')),
        'source_artifact': l.load_json(str(out/'source_artifact.json')),
        'source_units': l.load_json(str(out/'source_units.json')),
        'source_span_index': l.load_json(str(out/'source_span_index.json')),
        'provenance_index': l.load_json(str(out/'provenance_index.json')),
        'diagnostics': l.load_json(str(out/'diagnostics.json')),
        'recap_ingest_report': (root/out/'recap_ingest_report.md').read_text(),
    }
    l.validate_bundle_consistency(bundle)
