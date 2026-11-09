import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from common import ROOT,rng,save
from key_cases import choose_cases
from lean_checks import split_statement,extract_axioms
import lean_checks
from freeze import check_gates,check_pilot_review,check_model_catalog

class AnalysisCasesTests(unittest.TestCase):
    def test_model_catalog_drift_is_rejected(self):
        from common import sha
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'codex_home_flash/models.json';save(path,{'models':[{'slug':'synthetic'}]})
            save(root/'prompts/flash.catalog_manifest.json',{'source_path':'codex_home_flash/models.json','source_sha256':sha(path)})
            with patch('freeze.ROOT',root):
                check_model_catalog();save(path,{'models':[]})
                with self.assertRaisesRegex(AssertionError,'catalog changed'):check_model_catalog()
    def test_no_remaining_search_time_is_not_reported_as_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);save(root/'lean/compilation/synthetic/result.json',{'status':'compiled'})
            item={'id':'synthetic','formal_statement':'theorem synthetic (n : Nat) : True := by','header':''}
            with patch.object(lean_checks,'ROOT',root),patch.object(lean_checks.time,'monotonic',side_effect=[0,1,61,100,101,161]),patch.object(lean_checks,'run_file',return_value={'exit_code':0,'timed_out':False,'stdout':''}) as run:
                result=lean_checks.logic_item(item)
            self.assertEqual(run.call_count,2);self.assertEqual(result['status'],'not_checked')
            self.assertTrue(all(c['status']=='not_checked_no_search_time' for c in result['checks']))
    def items(self,n):return [{'id':str(i),'label':'true' if i%2 else 'false'} for i in range(n)]
    def test_case_directions_balanced_when_one_direction_absent(self):
        items=self.items(6);truth=np.array([i%2 for i in range(6)],float)[:,None]
        arrays={'terra':{'R1':np.repeat(truth,3,axis=1),'R0':np.repeat(1-truth,3,axis=1),'R1g':np.repeat(truth,3,axis=1)},'flash':{}}
        cases=choose_cases(items,arrays,[],[],rng('key_cases'))
        self.assertFalse(any(c['layer'].startswith('方案分歧') for c in cases))
    def test_no_incomplete_vote_case_enters_disagreement(self):
        items=self.items(4)
        a=np.array([[0,0,np.nan],[0,0,0],[0,0,0],[1,1,1]],float);b=1-a
        arrays={'terra':{'R1':a,'R0':b,'R1g':a},'flash':{}}
        cases=choose_cases(items,arrays,[],[],rng('key_cases'))
        self.assertFalse(any(c['id']=='0' and c['layer'].startswith('方案分歧') for c in cases))
        self.assertEqual(len({c['id'] for c in cases}),len(cases))
    def test_abstention_is_not_called_an_exact_opposite_verdict(self):
        items=[{'id':'abstention','label':'false'},{'id':'reverse','label':'true'}]
        a=np.array([[2,2,2],[0,0,0]],float);b=np.ones((2,3))
        cases=choose_cases(items,{'terra':{'R1':a,'R0':b,'R1g':a},'flash':{}},[],[],rng('key_cases'))
        selected=next(r for r in cases if r['id']=='abstention')
        self.assertIn('最大差值回退',selected['layer'])
    def test_lean_signature_preserves_binder_colons(self):
        parsed=split_statement('theorem sample (n : Nat) (h : n = 1) : n + 0 = 1 := by')
        self.assertEqual(parsed['binders'],'(n : Nat) (h : n = 1)');self.assertEqual(parsed['conclusion'],'n + 0 = 1')
    def test_unsupported_formal_definitions_are_not_silently_rewritten(self):
        self.assertIsNone(split_statement('def x := 2\ntheorem test : x = 2 := by'))
    def test_axiom_evidence_requires_machine_listing(self):
        self.assertIsNone(extract_axioms('Proof successful'))
        self.assertEqual(extract_axioms("'rc_anomaly' depends on axioms: [propext, Classical.choice]"),['propext','Classical.choice'])
        self.assertEqual(extract_axioms("'rc_anomaly' does not depend on any axioms"),[])
    def test_unconfirmed_candidate_cannot_freeze(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);(path/'experiment_control.json').write_text('{"choices_confirmed":false}')
            with patch('freeze.ROOT',path):
                with self.assertRaisesRegex(AssertionError,'pending'):check_gates()
    def test_empty_raw_review_file_does_not_satisfy_freeze_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);save(root/'runs/pilot/raw_output_review.json',{})
            with patch('freeze.ROOT',root):
                with self.assertRaisesRegex(AssertionError,'incomplete'):check_pilot_review({'models':{}})
    def test_control_anomaly_requires_diagnosis_after_output_review(self):
        from common import sha
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);sample=root/'runs/pilot/raw_output_sample.json';save(sample,[{'model':'terra','key':'one'}])
            review={'complete':True,'sample_sha256':sha(sample),'reviewed_calls':[{'model':'terra','key':'one','format_checked':True}]}
            save(root/'runs/pilot/raw_output_review.json',review)
            pilot={'models':{'terra':{'controls':{'R0':{'negative':{'program_check_required':True}}}}}}
            with patch('freeze.ROOT',root):
                with self.assertRaisesRegex(AssertionError,'diagnosis'):check_pilot_review(pilot)
                review['control_diagnostics']=[{'control':'terra/R0/negative','status':'program_verified_no_issue','evidence':'synthetic input-field audit'}]
                save(root/'runs/pilot/raw_output_review.json',review);check_pilot_review(pilot)

if __name__=='__main__':
    import io
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AnalysisCasesTests))
    (ROOT/'analysis/analysis_case_tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    save(ROOT/'analysis/analysis_case_tests.json',{'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'passed':r.wasSuccessful()})
    print(stream.getvalue());raise SystemExit(0 if r.wasSuccessful() else 1)
