"""Real trusted Python/Node boundary observations, not a universal correctness score."""
import argparse,hashlib,html,importlib.metadata,json,os,platform,re,selectors,shutil,signal,subprocess,sys,tempfile,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo,TZPATH
from . import core,__version__ as CORE_VERSION
from .__main__ import tz_fingerprint
VERSION='0.2.0'
LIMIT=1024*1024
OUT_LIMIT=16*1024*1024
CAP=65536
FIELDS=('utc','epoch_ms','wall','roundtrip_wall','offset_seconds','roundtrip_offset_seconds','fold','wall_fields')
RUNTIME=('engine','version','icu','tz_version','zone_resolved','tzfile_sha256','tzdata_package_version')
FILES={'suite.json','receipt.json','report.json','review.html'}
class Invalid(ValueError):pass
def canonical(x):return (json.dumps(x,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('ascii')
def sha(b):return hashlib.sha256(b).hexdigest()
def exact(d,keys):
    if type(d) is not dict or set(d)!=set(keys):raise Invalid('Exact object fields required.')
def integer(x,a,b):
    if type(x) is not int or not a<=x<=b:raise Invalid('Expected integer, not boolean.')
def text(x,n=500):
    if type(x) is not str or not 1<=len(x)<=n or any(ord(c)<32 for c in x):raise Invalid('Bounded plain text required.')
    x.encode('utf8');return x

def read(path,limit=LIMIT):
    import stat
    p=Path(path)
    if not stat.S_ISREG(p.lstat().st_mode):raise Invalid('Regular nonsymlink file required.')
    fd=os.open(p,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)|getattr(os,'O_BINARY',0))
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_size>limit:raise Invalid('Bounded regular input required.')
        with os.fdopen(fd,'rb') as f:fd=None;b=f.read(limit+1)
    finally:
        if fd is not None:os.close(fd)
    if len(b)>limit:raise Invalid('Input exceeds bound.')
    b.decode('utf8');return b

def parse(b,limit=LIMIT):
    if len(b)>limit:raise Invalid('JSON bound exceeded.')
    def pairs(ps):
        d={}
        for k,v in ps:
            if k in d:raise Invalid('Duplicate JSON key.')
            k.encode('utf8');d[k]=v
        return d
    def bad(x):raise Invalid('Only integer numeric fields allowed.')
    try:
        d=json.loads(b.decode('utf8'),object_pairs_hook=pairs,parse_float=bad,parse_constant=bad);todo=[(d,0)]
        while todo:
            x,n=todo.pop()
            if n>16:raise Invalid('JSON depth exceeded.')
            if type(x) is dict:todo.extend((v,n+1) for v in x.values())
            elif type(x) is list:todo.extend((v,n+1) for v in x)
            elif type(x) is str:x.encode('utf8')
        return d
    except (ValueError,UnicodeError,RecursionError):raise Invalid('Invalid strict JSON.') from None

def local(x,output=False):
    if type(x) is not str or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d',x):raise Invalid('Second-precision local ISO required.')
    d=datetime.fromisoformat(x)
    lo,hi=(1899,2100) if output else (1900,2099)
    if not lo<=d.year<=hi:raise Invalid('Date outside explicit input/output protocol year range.')
    return d

def observation(o):
    exact(o,('status','error',*FIELDS))
    if o['status']=='domain_error':
        if o['error'] not in ('invalid_calendar_date','unsupported_operation','unknown_zone') or any(o[k] is not None for k in FIELDS):raise Invalid('Domain error must have a fixed label and no time result.')
        return o
    if o['status']!='ok' or o['error'] is not None:raise Invalid('Invalid observation status.')
    wall=local(o['wall'],True);rt=local(o['roundtrip_wall'],True)
    if type(o['utc']) is not str or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',o['utc']):raise Invalid('UTC must use exact second precision Z format.')
    utc=datetime.fromisoformat(o['utc'].replace('Z','+00:00'));integer(o['epoch_ms'],int(datetime(1898,12,31,tzinfo=timezone.utc).timestamp())*1000,int(datetime(2101,1,2,tzinfo=timezone.utc).timestamp())*1000-1000)
    if o['epoch_ms']!=int(utc.timestamp())*1000:raise Invalid('Epoch/UTC mismatch.')
    for k in ('offset_seconds','roundtrip_offset_seconds'):integer(o[k],-86400,86400)
    if (wall-timedelta(seconds=o['offset_seconds'])).replace(tzinfo=timezone.utc)!=utc or (rt-timedelta(seconds=o['roundtrip_offset_seconds'])).replace(tzinfo=timezone.utc)!=utc:raise Invalid('Wall/UTC/offset fields disagree.')
    if o['fold'] is not None:integer(o['fold'],0,1)
    fields=[wall.year,wall.month,wall.day,wall.hour,wall.minute,wall.second]
    if canonical(o['wall_fields'])!=canonical(fields):raise Invalid('Wall field list disagrees with ISO.')
    return o

def response(b,side):
    d=parse(b);exact(d,('observation','adapter_runtime'));observation(d['observation']);r=d['adapter_runtime'];exact(r,RUNTIME)
    if r['engine']!=side:raise Invalid('Adapter runtime engine label differs.')
    for k,v in r.items():
        if v is not None:text(v,500)
    if r['version'] is None:raise Invalid('Adapter must report a version label.')
    if r['tzfile_sha256'] is not None and not re.fullmatch('[0-9a-f]{64}',r['tzfile_sha256']):raise Invalid('Invalid timezone fingerprint.')
    return d

def suite(raw):
    s=parse(raw);exact(s,('schema','cases'));integer(s['schema'],1,1)
    if type(s['cases']) is not list or not 1<=len(s['cases'])<=12:raise Invalid('Supply 1..12 cases.')
    ids=set()
    for c in s['cases']:
        exact(c,('id','request','semantics','expected','reference'))
        if type(c['id']) is not str or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',c['id']) or c['id'] in ids:raise Invalid('Unique safe case IDs required.')
        ids.add(c['id']);r=c['request'];exact(r,('local','zone','operation','argument'));local(r['local'])
        if type(r['zone']) is not str or not re.fullmatch(r'[A-Za-z0-9_+-]+(?:/[A-Za-z0-9_+-]+)*',r['zone']) or len(r['zone'])>100:raise Invalid('Bounded IANA zone label required.')
        op=r['operation']
        if op in ('construct','native_24h','elapsed_24h'):
            if r['argument'] is not None:raise Invalid('Operation has no argument.')
        elif op=='replace_month':integer(r['argument'],1,12)
        elif op=='replace_year':integer(r['argument'],1900,2099)
        elif op=='calendar_day':integer(r['argument'],-7,7)
        else:raise Invalid('Unsupported boundary operation.')
        exact(c['semantics'],('python','node','equivalent_intent','note'))
        for k in ('python','node','note'):text(c['semantics'][k],1000)
        if type(c['semantics']['equivalent_intent']) is not bool:raise Invalid('Explicit intent equivalence declaration required.')
        exact(c['expected'],('python','node'))
        for expected in c['expected'].values():
            if expected is not None:observation(expected)
        ref=c['reference'];exact(ref,('recurrence','count','month_end','ambiguous','nonexistent'))
        if ref['recurrence'] not in ('daily','monthly','yearly') or ref['month_end'] not in ('reject','skip','clamp') or ref['ambiguous'] not in ('reject','earlier','later','both') or ref['nonexistent'] not in ('reject','skip','shift-forward'):raise Invalid('Invalid TimeEdge reference policy.')
        integer(ref['count'],1,3)
    return s

def execute(command,request,zone,timeout):
    stdout=bytearray();stderr=bytearray();status=None
    with tempfile.TemporaryFile() as source:
        source.write(canonical(request));source.seek(0)
        try:p=subprocess.Popen(command,stdin=source,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={'PATH':os.defpath,'LANG':'C.UTF-8','TZ':zone},cwd=str(Path(command[-1]).parent) if command[-1].endswith(('.py','.js')) else None,start_new_session=True)
        except OSError:return {'status':'launch_error','returncode':None,'stdout_bytes':0,'stderr_bytes':0,'stdout_sha256':sha(b''),'stderr_sha256':sha(b''),'stdout_text':None}
        deadline=time.monotonic()+timeout
        def kill():
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        try:
            with selectors.DefaultSelector() as sel:
                for f,buf in ((p.stdout,stdout),(p.stderr,stderr)):os.set_blocking(f.fileno(),False);sel.register(f,selectors.EVENT_READ,buf)
                while sel.get_map() or p.poll() is None:
                    if time.monotonic()>deadline:status='timeout';break
                    if p.poll() is not None:kill()
                    for k,_ in sel.select(.05):
                        b=os.read(k.fileobj.fileno(),8192)
                        if not b:sel.unregister(k.fileobj);continue
                        left=CAP-len(stdout)-len(stderr);k.data.extend(b[:left])
                        if len(b)>left:status='output_limit';break
                    if status:break
        finally:
            kill();p.wait(timeout=2);p.stdout.close();p.stderr.close()
        if status is None:status='complete' if p.returncode==0 else 'nonzero_exit'
        try:decoded=bytes(stdout).decode('utf8') if status=='complete' else None
        except UnicodeError:decoded=None;status='invalid_response'
        return {'status':status,'returncode':p.returncode,'stdout_bytes':len(stdout),'stderr_bytes':len(stderr),'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr),'stdout_text':decoded}

def probe_runtime(node):
    expr="process.stdout.write(JSON.stringify({node:process.version,v8:process.versions.v8,icu:process.versions.icu??null,tz:process.versions.tz??null}))"
    r=execute([node,'-e',expr],{},'UTC',5)
    if r['status']!='complete':raise Invalid('Node runtime probe failed.')
    d=parse(r['stdout_text'].encode());exact(d,('node','v8','icu','tz'))
    for v in d.values():
        if v is not None:text(v)
    text(d['node']);text(d['v8'])
    return {'runner_python':platform.python_version(),'runner_node_probe':d,'scope':'Runner probe of selected interpreters, separate from untrusted adapter self-description. No equal tzdb-version claim.'}

def reference_record(c):
    r=c['request'];p=c['reference'];rows=core.schedule(local(r['local']),p['count'],r['zone'],p['recurrence'],p['month_end'],p['ambiguous'],p['nonexistent'])
    fingerprint=tz_fingerprint(r['zone'])
    source_kind='system_tzif' if any((Path(base)/r['zone']).is_file() for base in TZPATH) else ('tzdata_package_resource' if fingerprint else 'unknown')
    try:package_version=importlib.metadata.version('tzdata')
    except importlib.metadata.PackageNotFoundError:package_version=None
    return {'case_id':c['id'],'policy':p,'rows':rows,'core_version':CORE_VERSION,'core_sha256':sha(read(Path(core.__file__))), 'runner_zone_fingerprint':fingerprint,'runner_zone_source':source_kind,'installed_tzdata_package_version':package_version,'scope':'Recorded TimeEdge calendar policy, not an oracle for a different adapter operation. No timezone database equivalence claimed.'}

def validate_reference(ref,c):
    exact(ref,('case_id','policy','rows','core_version','core_sha256','runner_zone_fingerprint','runner_zone_source','installed_tzdata_package_version','scope'))
    if ref['case_id']!=c['id'] or canonical(ref['policy'])!=canonical(c['reference']):raise Invalid('Reference binding mismatch.')
    text(ref['core_version']);text(ref['scope'],500)
    if ref['runner_zone_source'] not in ('system_tzif','tzdata_package_resource','unknown'):raise Invalid('Unknown timezone source declaration.')
    if ref['installed_tzdata_package_version'] is not None:text(ref['installed_tzdata_package_version'])
    if (ref['runner_zone_source']=='unknown')!=(ref['runner_zone_fingerprint'] is None):raise Invalid('Timezone source/fingerprint inconsistent.')
    for k in ('core_sha256','runner_zone_fingerprint'):
        if ref[k] is None and k=='runner_zone_fingerprint':continue
        if type(ref[k]) is not str or not re.fullmatch('[0-9a-f]{64}',ref[k]):raise Invalid('Invalid recorded core/tz hash.')
    if type(ref['rows']) is not list or len(ref['rows'])!=c['reference']['count']:raise Invalid('Reference slot count differs.')
    for row in ref['rows']:
        if type(row) is not dict or not {'requested','zone','kind','status','utc','wall','adjustment'}<=set(row) or set(row)-{'requested','zone','kind','status','utc','wall','adjustment','calendar_adjusted'}:raise Invalid('Reference row schema differs.')
        if row['zone']!=c['request']['zone'] or row['kind'] not in ('normal','ambiguous','nonexistent','invalid-calendar-date') or row['status'] not in ('resolved','rejected','skipped','adjusted'):raise Invalid('Invalid reference classification.')
        text(row['requested'],30)
        if not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d',row['requested']):raise Invalid('Invalid requested reference format.')
        if 'calendar_adjusted' in row and type(row['calendar_adjusted']) is not bool:raise Invalid('Invalid calendar adjustment flag.')
        if row['adjustment'] is not None:text(row['adjustment'],100)
        if type(row['utc']) is not list or type(row['wall']) is not list or len(row['utc'])!=len(row['wall']) or len(row['utc'])>2:raise Invalid('Invalid reference instant lists.')
        allowed={'normal':('resolved',),'ambiguous':('resolved','rejected'),'nonexistent':('adjusted','rejected','skipped'),'invalid-calendar-date':('rejected','skipped')}
        if row['status'] not in allowed[row['kind']]:raise Invalid('Reference kind/status impossible.')
        if row['status'] in ('rejected','skipped') and row['utc']:raise Invalid('Rejected reference has instant.')
        if row['status'] in ('resolved','adjusted') and not row['utc']:raise Invalid('Resolved reference needs an instant.')
        for u,v in zip(row['utc'],row['wall']):
            a=datetime.fromisoformat(u);b=datetime.fromisoformat(v)
            if a.utcoffset()!=timedelta(0) or b.tzinfo is None or a!=b:raise Invalid('Reference UTC/wall instant mismatch.')

def grade(raw,receipt):
    s=suite(raw);exact(receipt,('schema','version','suite_sha256','script_hashes','runner_runtime','timeout_seconds','records','references'));integer(receipt['schema'],1,1)
    if receipt['version']!=VERSION or receipt['suite_sha256']!=sha(raw):raise Invalid('Suite/version binding mismatch.')
    exact(receipt['script_hashes'],('python','node'))
    for v in receipt['script_hashes'].values():
        if type(v) is not str or not re.fullmatch('[0-9a-f]{64}',v):raise Invalid('Invalid adapter hash.')
    integer(receipt['timeout_seconds'],1,5);rt=receipt['runner_runtime'];exact(rt,('runner_python','runner_node_probe','scope'));text(rt['runner_python']);text(rt['scope']);exact(rt['runner_node_probe'],('node','v8','icu','tz'))
    for v in rt['runner_node_probe'].values():
        if v is not None:text(v)
    text(rt['runner_node_probe']['node']);text(rt['runner_node_probe']['v8'])
    if type(receipt['records']) is not list or len(receipt['records'])!=2*len(s['cases']) or type(receipt['references']) is not list or len(receipt['references'])!=len(s['cases']):raise Invalid('Complete ordered coverage required.')
    reports=[];index=0
    for c,ref in zip(s['cases'],receipt['references']):
        validate_reference(ref,c);sides={}
        for side in ('python','node'):
            r=receipt['records'][index];index+=1;exact(r,('case_id','side','status','returncode','stdout_bytes','stderr_bytes','stdout_sha256','stderr_sha256','stdout_text'))
            if r['case_id']!=c['id'] or r['side']!=side or r['status'] not in ('complete','nonzero_exit','timeout','output_limit','invalid_response','launch_error'):raise Invalid('Record identity/status differs.')
            for k in ('stdout_bytes','stderr_bytes'):integer(r[k],0,CAP)
            if r['stdout_bytes']+r['stderr_bytes']>CAP:raise Invalid('Stream limit inconsistent.')
            for stream in ('stdout','stderr'):
                v=r[stream+'_sha256']
                if type(v) is not str or not re.fullmatch('[0-9a-f]{64}',v) or (r[stream+'_bytes']==0 and v!=sha(b'')):raise Invalid('Stream hash inconsistent.')
            code=r['returncode']
            if code is not None:integer(code,-2**31,2**31-1)
            if r['status']=='launch_error':
                if code is not None or r['stdout_bytes'] or r['stderr_bytes']:raise Invalid('Launch error cannot have captured execution.')
            elif code is None:raise Invalid('Execution needs returncode.')
            if r['status']=='complete':
                if code!=0 or type(r['stdout_text']) is not str:raise Invalid('Successful response requires zero exit.')
                b=r['stdout_text'].encode('utf8')
                if len(b)!=r['stdout_bytes'] or sha(b)!=r['stdout_sha256']:raise Invalid('Recorded stdout mismatch.')
                d=response(b,side);expected=c['expected'][side];assertion='unasserted' if expected is None else ('match' if canonical(expected)==canonical(d['observation']) else 'mismatch')
                sides[side]={'execution_status':'complete','assertion':assertion,**d}
            else:
                if r['stdout_text'] is not None or (r['status']=='nonzero_exit' and code==0) or (r['status']=='invalid_response' and code!=0) or (r['status']=='output_limit' and r['stdout_bytes']+r['stderr_bytes']!=CAP):raise Invalid('Invalid execution-failure receipt.')
                sides[side]={'execution_status':r['status'],'assertion':'execution_error','observation':None,'adapter_runtime':None}
        diffs={k:(sides['python']['observation'][k]!=sides['node']['observation'][k]) for k in ('status','error',*FIELDS)} if all(sides[x]['observation'] for x in sides) else None
        reports.append({'case_id':c['id'],'request':c['request'],'semantics':c['semantics'],'sides':sides,'field_differences':diffs,'recorded_timeedge_reference':ref,'overall_language_correctness':None})
    return {'schema':1,'version':VERSION,'receipt_sha256':sha(canonical(receipt)),'cases':reports,'all_declared_expectations_match':all(row['sides'][side]['assertion']=='match' for row in reports for side in ('python','node')),'execution_authenticated':False,'reference_reexecuted_by_verify':False,'same_timezone_database_assumed':False,'nominal_adapter_timeout_budget_seconds':2*len(s['cases'])*receipt['timeout_seconds'],'nominal_runtime_probe_budget_seconds':5,'maximum_cleanup_wait_seconds':2*(2*len(s['cases'])+1),'hard_wall_clock_guarantee':False}

def render(report):
    esc=lambda x:html.escape(str(x),quote=True)
    body='<h1>Python / JavaScript time boundaries</h1><p>Recorded trusted-script observations, not language correctness rankings or authenticated history. No same-tzdb assumption. Full inputs/outputs may be sensitive.</p>'
    for c in report['cases']:
        body+='<h2>'+esc(c['case_id'])+'</h2><p>'+esc(c['semantics']['note'])+'</p><pre>'+esc(json.dumps(c,sort_keys=True,ensure_ascii=False,indent=2))+'</pre>'
    return ('<!doctype html><html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><title>TimeEdge boundary comparison</title><style>body{max-width:1100px;margin:2rem auto;padding:1rem;background:#13202b;color:#def;font:16px system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;border:1px solid #456;padding:1rem}</style>'+body+'</html>').encode('utf8')

def products(raw,receipt):
    report=grade(raw,receipt);files={'suite.json':raw,'receipt.json':canonical(receipt),'report.json':canonical(report),'review.html':render(report)}
    if any(len(b)>OUT_LIMIT for b in files.values()):raise Invalid('Output serialization exceeds bounds.')
    return report,files

def run(suite_path,python_adapter,node_adapter,out,allow_execute=False,timeout=3):
    if allow_execute is not True:raise Invalid('Explicit trusted-code execution consent required.')
    if os.name!='posix':raise Invalid('Execution requires POSIX; no fallback sandbox claim.')
    integer(timeout,1,5);dest=Path(out)
    if dest.exists() or dest.is_symlink():raise Invalid('Output must not exist.')
    raw=read(suite_path);s=suite(raw);scripts={'python':read(python_adapter),'node':read(node_adapter)};node=shutil.which('node')
    if node is None:raise Invalid('Trusted local Node runtime required.')
    for b in scripts.values():
        if not b.strip() or b'\0' in b:raise Invalid('Nonempty standalone source required.')
    try:compile(scripts['python'],'reviewed-adapter.py','exec')
    except (ValueError,SyntaxError):raise Invalid('Python adapter syntax invalid.') from None
    # Compute the explicit reference now, before launching user-provided code.
    refs=[reference_record(c) for c in s['cases']];dest.mkdir(exist_ok=False)
    runtime=probe_runtime(node);receipt={'schema':1,'version':VERSION,'suite_sha256':sha(raw),'script_hashes':{k:sha(v) for k,v in scripts.items()},'runner_runtime':runtime,'timeout_seconds':timeout,'records':[],'references':refs}
    for c in s['cases']:
        for side in ('python','node'):
            with tempfile.TemporaryDirectory(prefix='timeedge-compare-') as td:
                f=Path(td)/('adapter.py' if side=='python' else 'adapter.js');f.write_bytes(scripts[side]);command=[sys.executable,'-I',str(f)] if side=='python' else [node,str(f)]
                r=execute(command,c['request'],c['request']['zone'],timeout)
                if r['status']=='complete':
                    try:response(r['stdout_text'].encode('utf8'),side)
                    except (ValueError,TypeError,KeyError,OverflowError):r['status']='invalid_response';r['stdout_text']=None
                receipt['records'].append({'case_id':c['id'],'side':side,**r})
    report,files=products(raw,receipt)
    for n,b in files.items():(dest/n).write_bytes(b)
    return report

def verify(folder,python_adapter=None,node_adapter=None):
    p=Path(folder)
    if p.is_symlink() or not p.is_dir() or set(x.name for x in p.iterdir())!=FILES:raise Invalid('Exact bundle files required.')
    data={n:read(p/n,LIMIT if n=='suite.json' else OUT_LIMIT) for n in FILES};receipt=parse(data['receipt.json'],OUT_LIMIT)
    report,files=products(data['suite.json'],receipt)
    if data!=files:raise Invalid('Offline regenerated records/differences differ.')
    for side,path in (('python',python_adapter),('node',node_adapter)):
        if path and sha(read(path))!=receipt['script_hashes'][side]:raise Invalid('External adapter source differs.')
    return report

def main():
    p=argparse.ArgumentParser(description='Trusted Python/Node time-boundary experiments, not a sandbox or correctness ranking.');sub=p.add_subparsers(dest='cmd',required=True);a=sub.add_parser('run');a.add_argument('suite');a.add_argument('--python-adapter',required=True);a.add_argument('--node-adapter',required=True);a.add_argument('--out',required=True);a.add_argument('--allow-execute',action='store_true');a.add_argument('--timeout',type=int,default=3);a.add_argument('--require-expected',action='store_true');a=sub.add_parser('verify');a.add_argument('folder');a.add_argument('--python-adapter');a.add_argument('--node-adapter');a.add_argument('--require-expected',action='store_true');a=p.parse_args()
    try:
        r=run(a.suite,a.python_adapter,a.node_adapter,a.out,a.allow_execute,a.timeout) if a.cmd=='run' else verify(a.folder,a.python_adapter,a.node_adapter)
        print(json.dumps({'cases':len(r['cases']),'all_declared_expectations_match':r['all_declared_expectations_match'],'execution_authenticated':False,'same_timezone_database_assumed':False}));return 3 if a.require_expected and not r['all_declared_expectations_match'] else 0
    except (ValueError,OSError,TypeError,KeyError,OverflowError,RecursionError,subprocess.SubprocessError):
        print('Time comparison failed. Check trusted execution consent, supported cases/protocol, runtime availability, bounds and new output. Side effects cannot be undone; no input or paths echoed.',file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
