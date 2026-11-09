import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from reason_escape_reader import repair_reason,normalize_record,quality_for_jobs


def record(text,model='flash',key='one'):
    return {'model':model,'key':key,'state':'format_failure','reason':'completed_turn_invalid_output',
            'completed_turn_observed':True,'timed_out':False,'final_output':text,'parsed':None,
            'tools':{'calls':[],'stderr_evidence':[],'malformed_event_lines':0},
            'job':{'model':model,'key':key,'config':'R0','item_id':key,'batch':1}}


class RepairTests(unittest.TestCase):
    def test_repairs_only_illegal_escapes_and_preserves_original(self):
        text=r'{"verdict":"uncertain","reason":"Use \(\sqrt{x}\) and \\theta with \n newline"}'
        row=record(text);before=copy.deepcopy(row);fixed=normalize_record(row)
        self.assertEqual(row,before);self.assertEqual(fixed['final_output'],text)
        self.assertEqual(fixed['state'],'valid');self.assertEqual(fixed['parsed']['verdict'],'uncertain')
        self.assertEqual(fixed['parsed']['reason'],'Use \\(\\sqrt{x}\\) and \\theta with \n newline')
        audit=fixed['format_repair'];self.assertEqual(len(audit['inserted_backslash_offsets']),3)
        recovered=audit['repaired_output']
        for index,pos in reversed(list(enumerate(audit['inserted_backslash_offsets']))):
            shifted=pos+index;recovered=recovered[:shifted]+recovered[shifted+1:]
        self.assertEqual(recovered,text)

    def test_valid_output_unchanged_and_idempotent(self):
        text=json.dumps({'verdict':'faithful','reason':'\\sqrt{x}'})
        self.assertIsNone(repair_reason(text))
        row=record(r'{"verdict":"faithful","reason":"\sqrt{x}"}')
        fixed=normalize_record(row);self.assertEqual(normalize_record(fixed),fixed)
        valid={**row,'state':'valid'};self.assertIs(normalize_record(valid),valid)

    def test_refuses_other_fields_duplicate_keys_and_wrong_verdict(self):
        cases=[r'{"verdict":"f\aithful","reason":"ok"}',r'{"verdict":"faithful","reason":"\sqrt{x}","extra":1}',
               r'{"verdict":"faithful","reason":"\sqrt{x}","reason":"ok"}',
               r'{"verdict":"wrong","reason":"\sqrt{x}"}',r'{"reason":"\sqrt{x}"}',
               r'{"verdict":"faithful","reason":["\sqrt{x}"]}']
        for s in cases:
            with self.subTest(s=s):self.assertIsNone(repair_reason(s))

    def test_refuses_other_syntax_errors_and_unicode_errors(self):
        cases=[r'{"verdict":"faithful","reason":"\sqrt{x}",}',r'{"verdict":"faithful","reason":"\sqrt{x}',
               r'{"verdict":"faithful","reason":"\sqrt{x} \uZZZZ"}',
               r'{"verdict":"faithful","reason":"\sqrt{x}"} extra',
               '```json\n'+r'{"verdict":"faithful","reason":"\sqrt{x}"}'+'\n```',
               '{"verdict":"faithful","reason":"\\sqrt{x}\n"}']
        for s in cases:
            with self.subTest(s=s):self.assertIsNone(repair_reason(s))

    def test_accepts_reverse_key_order_unicode_and_escaped_quotes(self):
        s=r' {"reason":"\(x\) \"quote\" \u4e2d","verdict":"unfaithful"} '
        fixed=repair_reason(s);self.assertEqual(fixed['parsed']['reason'],'\\(x\\) "quote" 中')

    def test_never_promotes_tool_timeout_or_incomplete_outputs(self):
        row=record(r'{"verdict":"faithful","reason":"\sqrt{x}"}')
        variants=[{'state':'tool_contaminated'},{'state':'final_missing'},{'state':'quota_interrupted'},
                  {'timed_out':True},{'completed_turn_observed':False},{'pending_question':True},
                  {'tools':{'calls':[{'state':'unknown'}]}},{'tools':{'malformed_event_lines':1}}]
        for v in variants:
            candidate={**row,**v};self.assertIs(normalize_record(candidate),candidate)

    def test_same_rule_for_both_models(self):
        s=r'{"verdict":"uncertain","reason":"\sqrt{x}"}'
        self.assertEqual(normalize_record(record(s,'terra'))['parsed'],normalize_record(record(s,'flash'))['parsed'])

    def test_quality_retains_two_percent_boundary_and_completeness(self):
        rows=[]
        for i in range(50):
            r=record('bad',key=str(i));r['state']='valid' if i else 'format_failure';rows.append(r)
        jobs=[r['job'] for r in rows];labels={str(i):'true' for i in range(50)}
        self.assertTrue(quality_for_jobs(rows,jobs,labels)['passed'])
        rows[1]['state']='tool_contaminated';self.assertFalse(quality_for_jobs(rows,jobs,labels)['passed'])
        self.assertFalse(quality_for_jobs(rows[1:],jobs,labels)['complete'])

    def test_reader_and_prefix_use_repaired_view_without_rewriting_files(self):
        import analyze
        from common import save,write_jsonl
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);save(root/'ANALYSIS_INPUT_AMENDMENT_01.json',{})
            row=record(r'{"verdict":"uncertain","reason":"\sqrt{x}"}')
            path=root/'runs/main/generation-00/flash/one/result.json';save(path,row);original=path.read_bytes()
            save(root/'runs/main/generation-00/batch-1-quality.json',{'passed':False,'models':{'flash':{'passed':False}}})
            write_jsonl(root/'data/processed/items.jsonl',[{'id':'one','label':'true'}])
            with patch.object(analyze,'ROOT',root),patch.object(analyze,'main_jobs',side_effect=lambda b,g:[row['job']] if b==1 else []):
                rows=analyze.read_results('main/generation-00')
                self.assertEqual(rows[0]['state'],'valid');self.assertEqual(analyze.complete_prefix(rows,0,'flash',True),[1])
            self.assertEqual(path.read_bytes(),original)


if __name__=='__main__':unittest.main()
