"""Original deterministic boundary fixtures; actual local Python+Node, no network."""
import copy,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from timeedge import compare as c
ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples'/'compare'
@unittest.skipUnless(os.name=='posix' and shutil.which('node'),'POSIX and installed Node required; skip is not pass.')
class CompareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.base=Path(cls.temp.name);cls.bundle=cls.base/'bundle';cls.report=c.run(EX/'suite.json',EX/'python_adapter.py',EX/'node_adapter.js',cls.bundle,True,2)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
        for f in EX.iterdir():(self.p/f.name).write_bytes(f.read_bytes())
    def tiny(self):
        s=c.parse((self.p/'suite.json').read_bytes());s['cases']=s['cases'][:1];(self.p/'suite.json').write_bytes(c.canonical(s));return s
    def run_it(self,timeout=1):return c.run(self.p/'suite.json',self.p/'python_adapter.py',self.p/'node_adapter.js',self.p/'out',True,timeout)
    def test_real_seven_cases_expected(self):
        self.assertEqual(len(self.report['cases']),7);self.assertTrue(self.report['all_declared_expectations_match']);self.assertFalse(self.report['same_timezone_database_assumed']);self.assertEqual(c.verify(self.bundle),self.report)
    def test_gap_same_utc_different_wall(self):
        r=self.report['cases'][0];self.assertFalse(r['field_differences']['utc']);self.assertTrue(r['field_differences']['wall']);self.assertTrue(r['field_differences']['offset_seconds']);self.assertEqual(r['recorded_timeedge_reference']['rows'][0]['status'],'rejected');self.assertFalse(r['semantics']['equivalent_intent'])
    def test_fold_reference_two_instants(self):
        r=self.report['cases'][1];self.assertEqual(len(r['recorded_timeedge_reference']['rows'][0]['utc']),2);self.assertFalse(r['field_differences']['utc']);self.assertTrue(r['field_differences']['fold'])
    def test_month_and_leap_domain_error_not_runtime_error(self):
        for r in self.report['cases'][2:4]:
            self.assertEqual(r['sides']['python']['execution_status'],'complete');self.assertEqual(r['sides']['python']['observation']['error'],'invalid_calendar_date');self.assertEqual(r['sides']['node']['observation']['status'],'ok');self.assertIsNone(r['overall_language_correctness'])
    def test_calendar_vs_elapsed(self):
        calendar,native,elapsed=self.report['cases'][4:];self.assertEqual(calendar['sides']['node']['observation']['wall'],'2026-03-08T12:00:00');self.assertTrue(native['field_differences']['utc']);self.assertFalse(native['semantics']['equivalent_intent']);self.assertFalse(elapsed['field_differences']['utc']);self.assertEqual(elapsed['sides']['python']['observation']['wall'],'2026-03-08T13:00:00')
    def test_null_expected_unasserted_gate(self):
        s=self.tiny();s['cases'][0]['expected']={'python':None,'node':None};(self.p/'suite.json').write_bytes(c.canonical(s));r=self.run_it();self.assertFalse(r['all_declared_expectations_match']);self.assertEqual(r['cases'][0]['sides']['python']['assertion'],'unasserted');p=subprocess.run([sys.executable,'-m','timeedge.compare','verify',str(self.p/'out'),'--require-expected'],cwd=ROOT,capture_output=True);self.assertEqual(p.returncode,3)
    def test_nonzero_not_expected_domain_error(self):
        s=self.tiny();s['cases']=s['cases'][:1];(self.p/'node_adapter.js').write_text('process.exit(2);');r=self.run_it();self.assertEqual(r['cases'][0]['sides']['node']['assertion'],'execution_error');self.assertFalse(r['all_declared_expectations_match']);c.verify(self.p/'out')
    def test_invalid_protocol_not_domain_error(self):
        self.tiny();(self.p/'node_adapter.js').write_text('process.stdout.write("{}");');r=self.run_it();self.assertEqual(r['cases'][0]['sides']['node']['execution_status'],'invalid_response');c.verify(self.p/'out')
    def test_timeout(self):
        self.tiny();(self.p/'node_adapter.js').write_text('setTimeout(()=>{},10000);');r=self.run_it();self.assertEqual(r['cases'][0]['sides']['node']['execution_status'],'timeout');self.assertFalse(r['all_declared_expectations_match'])
    def test_output_overflow(self):
        self.tiny();(self.p/'node_adapter.js').write_text('process.stdout.write("x".repeat(100000));');r=self.run_it();self.assertEqual(r['cases'][0]['sides']['node']['execution_status'],'output_limit');c.verify(self.p/'out')
    def test_permission_preflight(self):
        with patch.object(c,'execute',side_effect=AssertionError('no execution')):
            for consent in (False,1,'yes',None):
                with self.assertRaises(ValueError):c.run(self.p/'suite.json',self.p/'python_adapter.py',self.p/'node_adapter.js',self.p/'out',consent)
            (self.p/'out').mkdir()
            with self.assertRaises(ValueError):self.run_it()
    def test_scripts_read_once_expected_hidden_env(self):
        self.tiny();source=(self.p/'node_adapter.js').read_text();source="if (process.env.NODE_OPTIONS || process.env.PYTHONPATH) throw new Error('unexpected env');\n"+source
        source=source.replace("const r = JSON.parse(fs.readFileSync(0, 'utf8'));", "const r = JSON.parse(fs.readFileSync(0, 'utf8')); if ('expected' in r) throw new Error('oracle in input');")
        (self.p/'node_adapter.js').write_text(source);original=c.execute;calls=[]
        def execute(*a,**kw):
            calls.append(1);(self.p/'node_adapter.js').write_text('process.exit(9);');return original(*a,**kw)
        with patch.object(c,'execute',side_effect=execute),patch.dict(os.environ,{'NODE_OPTIONS':'synthetic-invalid-flag','PYTHONPATH':'synthetic-private'}):r=self.run_it()
        self.assertTrue(r['all_declared_expectations_match']);self.assertEqual(len(calls),3)
    def test_verify_no_current_reference_or_process(self):
        with patch.object(c.core,'schedule',side_effect=AssertionError('no current reference')),patch.object(subprocess,'Popen',side_effect=AssertionError('no launch')):c.verify(self.bundle)
    def test_every_file_tamper_and_external_source(self):
        b=self.p/'bundle';shutil.copytree(self.bundle,b)
        for f in b.iterdir():
            raw=f.read_bytes();f.write_bytes(raw+b' ')
            with self.assertRaises(ValueError):c.verify(b)
            f.write_bytes(raw)
        (self.p/'node_adapter.js').write_text('process.exit(0)')
        with self.assertRaises(ValueError):c.verify(b,node_adapter=self.p/'node_adapter.js')
        (b/'extra').write_text('unexpected')
        with self.assertRaises(ValueError):c.verify(b)
    def test_receipt_type_returncode_epoch_tamper(self):
        raw=(self.bundle/'suite.json').read_bytes();r=c.parse((self.bundle/'receipt.json').read_bytes(),c.OUT_LIMIT)
        for field,value in (('returncode',True),('returncode',1),('status','nonzero_exit'),('case_id','other')):
            d=copy.deepcopy(r);d['records'][0][field]=value
            with self.assertRaises(ValueError):c.grade(raw,d)
        d=copy.deepcopy(r);d['records'].reverse()
        with self.assertRaises(ValueError):c.grade(raw,d)
    def test_reference_structure_rejected(self):
        raw=(self.bundle/'suite.json').read_bytes();r=c.parse((self.bundle/'receipt.json').read_bytes(),c.OUT_LIMIT);d=copy.deepcopy(r);d['references'][0]['rows'][0]['status']='resolved'
        with self.assertRaises(ValueError):c.grade(raw,d)
        d=copy.deepcopy(r);d['references'][0]['runner_zone_source']='same-as-node'
        with self.assertRaises(ValueError):c.grade(raw,d)
    def test_special_files(self):
        f=self.p/'suite.json';f.unlink();f.symlink_to(EX/'suite.json')
        with self.assertRaises(ValueError):self.run_it()
        f.unlink();os.mkfifo(f)
        with self.assertRaises(ValueError):self.run_it()
    def test_scriptfree_html(self):
        r=copy.deepcopy(self.report);r['cases'][0]['semantics']['note']='<script>bad</script>';h=c.render(r).decode();self.assertNotIn('<script>',h);self.assertIn('&lt;script&gt;',h);self.assertIn("default-src 'none'",h)
    def test_expected_mismatch_is_not_language_ranking(self):
        s=self.tiny();all_cases=c.parse((EX/'suite.json').read_bytes())['cases'];s['cases'][0]['expected']['python']=all_cases[-1]['expected']['python'];(self.p/'suite.json').write_bytes(c.canonical(s));r=self.run_it();self.assertEqual(r['cases'][0]['sides']['python']['assertion'],'mismatch');self.assertFalse(r['all_declared_expectations_match']);self.assertIsNone(r['cases'][0]['overall_language_correctness'])
    def test_same_group_child_cleanup(self):
        self.tiny();p=self.p/'node_adapter.js';original=p.read_text();p.write_text("require('node:child_process').spawn(process.execPath,['-e','setTimeout(()=>{},10000)'],{stdio:'inherit'}).unref();\n"+original);r=self.run_it();self.assertTrue(r['all_declared_expectations_match'])
    def test_output_size_preflight_before_file_writes(self):
        raw=(self.bundle/'suite.json').read_bytes();receipt=c.parse((self.bundle/'receipt.json').read_bytes(),c.OUT_LIMIT)
        with patch.object(c,'render',return_value=b'x'*(c.OUT_LIMIT+1)):
            with self.assertRaises(ValueError):c.products(raw,receipt)
    def test_input_year_edge_arithmetic_outputs_supported(self):
        s=self.tiny();case=s['cases'][0];case['request'].update(local='2099-12-31T12:00:00',zone='UTC',operation='calendar_day',argument=7);case['expected']={'python':None,'node':None};(self.p/'suite.json').write_bytes(c.canonical(s));r=self.run_it()
        for side in ('python','node'):self.assertEqual(r['cases'][0]['sides'][side]['observation']['wall'],'2100-01-07T12:00:00')
        c.verify(self.p/'out')
    def test_probe_required_node_v8(self):
        raw=(self.bundle/'suite.json').read_bytes();r=c.parse((self.bundle/'receipt.json').read_bytes(),c.OUT_LIMIT)
        for field in ('node','v8'):
            d=copy.deepcopy(r);d['runner_runtime']['runner_node_probe'][field]=None
            with self.assertRaises(ValueError):c.grade(raw,d)
    def test_real_cli(self):
        self.tiny();args=[sys.executable,'-m','timeedge.compare','run',str(self.p/'suite.json'),'--python-adapter',str(self.p/'python_adapter.py'),'--node-adapter',str(self.p/'node_adapter.js'),'--out',str(self.p/'out'),'--allow-execute','--require-expected'];p=subprocess.run(args,cwd=ROOT,capture_output=True);self.assertEqual(p.returncode,0,p.stderr);p=subprocess.run([sys.executable,'-m','timeedge.compare','verify',str(self.p/'out'),'--require-expected'],cwd=ROOT,capture_output=True);self.assertEqual(p.returncode,0,p.stderr)

class ProtocolTests(unittest.TestCase):
    def test_observation_type_and_consistency(self):
        o=c.parse((EX/'suite.json').read_bytes())['cases'][0]['expected']['python']
        for k,v in (('epoch_ms',True),('epoch_ms',0),('offset_seconds',True),('fold',False),('wall_fields',[2026,3,8,2,30,False]),('utc','2026-03-08T07:30:00.000Z')):
            d=copy.deepcopy(o);d[k]=v
            with self.assertRaises(ValueError):c.observation(d)
    def test_suite_limits_and_policies(self):
        s=c.parse((EX/'suite.json').read_bytes())
        for change in ({'schema':True},{'cases':[]},{'cases':s['cases']*2}):
            d=copy.deepcopy(s);d.update(change)
            with self.assertRaises(ValueError):c.suite(c.canonical(d))
        for k,v in (('zone','../../etc/passwd'),('local','0099-01-01T00:00:00'),('argument',True),('operation','eval')):
            d=copy.deepcopy(s);d['cases'][0]['request'][k]=v
            with self.assertRaises(ValueError):c.suite(c.canonical(d))
    def test_strict_json(self):
        for raw in (b'{"x":1,"x":2}',b'[NaN]',b'[1.5]',b'["\\ud800"]',b'['*20+b'1'+b']'*20,b'x'*(c.LIMIT+1)):
            with self.assertRaises(ValueError):c.parse(raw)
if __name__=='__main__':unittest.main()
