"""Offline, precomputed boundary player; never executes imported code."""
import argparse
import hashlib
import html
import itertools
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .core import schedule
from .__main__ import tz_fingerprint

MAX_BYTES = 16 * 1024 * 1024
SCRIPT = r'''"use strict";
const data = JSON.parse(document.getElementById('payload').textContent);
const $ = id => document.getElementById(id);
let slot = 0, timer = null;
function stop(){if(timer !== null) clearInterval(timer);timer=null;$('play').textContent='Play';}
function selected(){return data.variants.find(v=>v.month_end===$('month').value&&v.ambiguous===$('fold').value&&v.nonexistent===$('gap').value);}
function draw(){
 const row=selected().rows[slot];$('position').value=String(slot);$('position').setAttribute('aria-valuetext',`Slot ${slot+1} of ${data.count}`);
 $('step').textContent=`Slot ${slot+1} / ${data.count}`;
 $('requested').textContent=row.requested;
 $('outcome').textContent=row.status+' · '+row.kind+(row.calendar_adjusted?' · calendar clamped':'');
 $('adjustment').textContent=row.adjustment?'Gap adjustment: '+row.adjustment:'No gap shift';
 $('instant').replaceChildren();
 if(!row.utc.length){const p=document.createElement('p');p.textContent='No UTC instant. This slot is not scheduled.';$('instant').append(p);}
 row.utc.forEach((utc,i)=>{const section=document.createElement('section');section.className='instant';
  for(const [label,value] of [['Resolved source',row.wall[i]],['UTC',utc],['Target · '+data.target,row.target[i]]]){const p=document.createElement('p');const strong=document.createElement('strong');strong.textContent=label+'  ';p.append(strong,document.createTextNode(value));section.append(p);}$('instant').append(section);});
 $('previous').disabled=slot===0;$('next').disabled=slot===data.count-1;
 document.querySelectorAll('[data-slot]').forEach(tr=>tr.setAttribute('aria-current',Number(tr.dataset.slot)===slot?'step':'false'));
}
function table(){const body=$('rows');body.replaceChildren();selected().rows.forEach((r,i)=>{const tr=document.createElement('tr');tr.dataset.slot=String(i);for(const v of [String(i+1),r.requested,r.kind,r.status,r.utc.join(' / ')||'—']){const td=document.createElement('td');td.textContent=v;tr.append(td);}body.append(tr);});draw();}
function change(){stop();slot=0;table();}
for(const id of ['month','fold','gap']) $(id).addEventListener('change',change);
$('previous').addEventListener('click',()=>{stop();slot=Math.max(0,slot-1);draw();});
$('next').addEventListener('click',()=>{stop();slot=Math.min(data.count-1,slot+1);draw();});
$('position').addEventListener('input',()=>{stop();slot=Number($('position').value);draw();});
$('play').addEventListener('click',()=>{if(timer!==null){stop();return;}if(slot===data.count-1)slot=0;draw();$('play').textContent='Pause';timer=setInterval(()=>{if(slot<data.count-1){slot++;draw();}if(slot===data.count-1)stop();},1000);});
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
table();
'''

def build(start, zone, target, count=5, recurrence='daily'):
    if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=31:
        raise ValueError('count must be 1..31')
    origin=ZoneInfo(zone); destination=ZoneInfo(target)
    if not isinstance(start,str) or len(start)>40: raise ValueError('invalid start')
    local=datetime.fromisoformat(start)
    if local.tzinfo is not None: raise ValueError('start must be local without offset')
    variants=[]
    for month,fold,gap in itertools.product(('reject','skip','clamp'),('reject','earlier','later','both'),('reject','skip','shift-forward')):
        rows=schedule(local,count,zone,recurrence,month,fold,gap)
        for row in rows:
            row['target']=[datetime.fromisoformat(u).astimezone(destination).isoformat() for u in row['utc']]
        variants.append(dict(month_end=month,ambiguous=fold,nonexistent=gap,rows=rows))
    return dict(schema=1,start=start,zone=zone,target=target,count=count,recurrence=recurrence,
                tzfiles={zone:tz_fingerprint(zone),target:tz_fingerprint(target)},variants=variants)

def render(data):
    # Escape script terminators and HTML-significant characters, including arbitrary labels.
    payload=json.dumps(data,ensure_ascii=True,separators=(',',':')).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
    import base64
    digest=base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    e=lambda s:html.escape(str(s),quote=True)
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'sha256-'''+digest+''''; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>TimeEdge · Boundary player</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#10141c;color:#eef3fc}*{box-sizing:border-box}body{margin:0}main{max-width:1160px;margin:auto;padding:36px 24px}header{border-bottom:1px solid #364154;padding-bottom:26px}.eyebrow{color:#a5b4fc;letter-spacing:.16em;font-size:12px}h1{font-size:clamp(2rem,5vw,3.7rem);line-height:1.1;max-width:800px;margin:18px 0}p{line-height:1.6}.muted{color:#adb9cc}.controls{display:flex;flex-wrap:wrap;gap:16px;margin:26px 0}label{display:grid;gap:8px;flex:1;min-width:160px}select,button{font:inherit;color:inherit;background:#202939;border:1px solid #52627c;border-radius:8px;padding:10px}button{cursor:pointer}button:disabled{opacity:.4;cursor:default}button:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid #7ae6c1;outline-offset:3px}.stage{border:1px solid #465570;border-radius:16px;padding:24px;background:linear-gradient(120deg,#1a2535,#171b2c)}.requested{font:clamp(1.2rem,3vw,2rem) ui-monospace,monospace;overflow-wrap:anywhere}.path{display:grid;grid-template-columns:1fr 42px 1.3fr;gap:14px;align-items:center}.arrow{font-size:28px;color:#7ae6c1}.instant{border-left:3px solid #7ae6c1;padding:4px 14px;margin:8px 0;background:#111c27;overflow-wrap:anywhere}.instant p{font-size:14px}.transport{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:24px}.transport input{flex:1;min-width:180px;accent-color:#7ae6c1}.status{color:#ffd58a}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:12px;text-align:left;border-bottom:1px solid #354154;white-space:nowrap}tr[aria-current=step]{background:#253b45}.scroll{overflow:auto}details{margin:26px 0}summary{cursor:pointer;padding:12px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}footer{border-top:1px solid #364154;margin-top:28px;padding-top:18px;color:#adb9cc;font-size:13px}@media(max-width:650px){main{padding:24px 14px}.path{grid-template-columns:1fr}.arrow{transform:rotate(90deg);justify-self:center}.stage{padding:16px}.controls{gap:12px}h1{font-size:2.25rem}}
</style></head><body><main><header><p class="eyebrow">WALKER512 / TIMEEDGE / OFFLINE LAB</p><h1>A wall clock can skip.<br>Or happen twice.</h1><p class="muted">Step through calendar slots. Change the policy. See which instants actually exist.</p><p>'''+e(data['zone'])+''' → '''+e(data['target'])+''' · '''+e(data['recurrence'])+''' · anchor '''+e(data['start'])+'''</p></header>
<div class="controls"><label>Invalid calendar day<select id="month"><option>reject</option><option>skip</option><option>clamp</option></select></label><label>Repeated wall time<select id="fold"><option>reject</option><option>earlier</option><option>later</option><option>both</option></select></label><label>Missing wall time<select id="gap"><option>reject</option><option>skip</option><option>shift-forward</option></select></label></div>
<section class="stage" aria-label="Boundary playback"><p id="step"></p><div class="path"><div><p class="eyebrow">REQUESTED LOCAL SLOT</p><p class="requested" id="requested"></p><p id="outcome" class="status"></p><p id="adjustment" class="muted"></p></div><div class="arrow" aria-hidden="true">→</div><div id="instant" aria-live="polite"></div></div><div class="transport"><button id="previous">Previous</button><button id="play">Play</button><button id="next">Next</button><input aria-label="Calendar slot" id="position" type="range" min="0" max="'''+str(data['count']-1)+'''" value="0" step="1"></div></section>
<p class="muted">Playback advances one requested slot per second, not real elapsed time. No autoplay. Changing a policy resets to slot 1 and pauses; hidden tabs pause. Monthly/yearly steps keep the original day anchor.</p>
<details open><summary>All slots under the selected policies</summary><div class="scroll" tabindex="0" aria-label="All slots table"><table><thead><tr><th>Slot</th><th>Requested</th><th>Boundary</th><th>Outcome</th><th>UTC instants</th></tr></thead><tbody id="rows"></tbody></table></div></details>
<details><summary>Generation evidence and limits</summary><p>Timezone results are precomputed by Python ZoneInfo using this machine’s data, not your browser’s timezone database. Hashes identify available files, not signed authenticity or a tzdb release. Regenerate after updates. Source and target zone conversion use the same instant. No leap seconds, real scheduling, automatic deployment or imported code execution.</p><pre>'''+e(json.dumps({k:v for k,v in data.items() if k!='variants'},indent=2))+'''</pre></details><noscript>This interactive report needs JavaScript. The companion playback.json contains every precomputed policy result; the original TimeEdge HTML mode remains script-free.</noscript><footer>Local educational model · no network, accounts, analytics or remote assets. “Skip” is not success. This report is not a guarantee that a real job will run. Inspect timing data before sharing.</footer></main><script id="payload" type="application/json">'''+payload+'''</script><script>'''+SCRIPT+'''</script></body></html>'''

def write_bundle(data,out):
    files={'playback.json':json.dumps(data,ensure_ascii=True,indent=2).encode(),'index.html':render(data).encode()}
    if any(len(v)>MAX_BYTES for v in files.values()):raise ValueError('output too large')
    out=Path(out);out.mkdir(mode=0o700)
    for name,content in files.items():
        fd=os.open(out/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(content)

def main():
    p=argparse.ArgumentParser(description='Generate a local precomputed interactive boundary player, no server.')
    p.add_argument('--start',required=True);p.add_argument('--zone',required=True);p.add_argument('--target',default='UTC');p.add_argument('--count',type=int,default=5)
    p.add_argument('--recurrence',choices=['daily','monthly','yearly'],default='daily');p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    try:
        write_bundle(build(a.start,a.zone,a.target,a.count,a.recurrence),a.out)
        print('Boundary player created. Open index.html; policies include rejected and skipped outcomes.')
        return 0
    except (ValueError,OverflowError,OSError,ZoneInfoNotFoundError):
        print('TimeEdge playback: invalid input, unavailable timezone, or unsafe/unwritable output. No existing output overwritten.',file=__import__('sys').stderr);return 1
if __name__=='__main__':raise SystemExit(main())
