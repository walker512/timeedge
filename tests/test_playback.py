import hashlib
import base64
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from timeedge.playback import build,render,write_bundle,SCRIPT

class PlaybackTests(unittest.TestCase):
    def variant(self,d,month='reject',fold='reject',gap='reject'):
        return next(v['rows'] for v in d['variants'] if (v['month_end'],v['ambiguous'],v['nonexistent'])==(month,fold,gap))
    def test_gap_and_target(self):
        d=build('2026-03-07T02:30','America/New_York','Asia/Shanghai',3)
        self.assertEqual(len(d['variants']),36)
        self.assertEqual(self.variant(d)[1]['utc'],[])
        r=self.variant(d,gap='shift-forward')[1]
        self.assertEqual(r['wall'],['2026-03-08T03:30:00-04:00']);self.assertEqual(r['target'],['2026-03-08T15:30:00+08:00'])
    def test_fold(self):
        d=build('2026-11-01T01:30','America/New_York','UTC',1)
        r=self.variant(d,fold='both')[0];self.assertEqual(len(r['utc']),2)
        self.assertEqual(r['utc'],['2026-11-01T05:30:00+00:00','2026-11-01T06:30:00+00:00'])
        self.assertEqual(self.variant(d,fold='later')[0]['utc'],r['utc'][1:])
    def test_leap_year(self):
        d=build('2024-02-29T09:00','UTC','UTC',5,'yearly')
        r=self.variant(d,month='clamp');self.assertIn('2025-02-28',r[1]['wall'][0]);self.assertIn('2028-02-29',r[4]['wall'][0])
        self.assertEqual(self.variant(d,month='skip')[1]['status'],'skipped')
    def test_month_anchor(self):
        d=build('2026-01-31T09:00','UTC','UTC',3,'monthly')
        r=self.variant(d,month='clamp');self.assertIn('2026-02-28',r[1]['wall'][0]);self.assertIn('2026-03-31',r[2]['wall'][0]);self.assertEqual(self.variant(d)[1]['kind'],'invalid-calendar-date')
    def test_non_hour_gap(self):
        d=build('2026-10-04T02:15','Australia/Lord_Howe','UTC',1)
        self.assertEqual(self.variant(d,gap='shift-forward')[0]['adjustment'],'0:30:00')
    def test_conversion_preserves_instant(self):
        from datetime import datetime
        d=build('2026-10-31T01:30','America/New_York','Pacific/Auckland',3)
        for v in d['variants']:
            for r in v['rows']:
                for a,b in zip(r['utc'],r['target']):self.assertEqual(datetime.fromisoformat(a),datetime.fromisoformat(b))
    def test_invalid_inputs(self):
        for kwargs in [dict(count=True),dict(count=0),dict(count=32),dict(start='2026-01-01T00:00Z'),dict(zone='../../secret'),dict(target='invalid'),dict(recurrence='hourly'),dict(start='9999-12-31T00:00')]:
            p=dict(start='2026-01-01T00:00',zone='UTC',target='UTC',count=3);p.update(kwargs)
            with self.assertRaises((ValueError,KeyError,OverflowError)):build(**p)
    def test_html_escaping_and_csp(self):
        d=build('2026-01-01','UTC','UTC',1);d['start']='</script><img src=x onerror=alert(1)>'
        h=render(d)
        self.assertNotIn('<img',h);self.assertEqual(h.count('</script>'),2)
        self.assertIn("script-src 'sha256-"+base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()+"'",h)
        self.assertNotIn('innerHTML',SCRIPT);self.assertNotIn('fetch(',SCRIPT)
        self.assertIn('\\u003c/script\\u003e',h)
    def test_private_new_output_and_preservation(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'out';old=os.umask(0o022)
            try:write_bundle(build('2026-01-01','UTC','UTC',1),out)
            finally:os.umask(old)
            self.assertEqual(stat.S_IMODE(out.stat().st_mode),0o700)
            self.assertEqual(stat.S_IMODE((out/'index.html').stat().st_mode),0o600)
            before=(out/'index.html').read_bytes()
            with self.assertRaises(FileExistsError):write_bundle(build('2026-01-01','UTC','UTC',1),out)
            self.assertEqual((out/'index.html').read_bytes(),before)
    def test_cli(self):
        with tempfile.TemporaryDirectory() as t:
            args=[sys.executable,'-m','timeedge.playback','--start','2026-03-07T02:30','--zone','America/New_York','--out',str(Path(t)/'out')]
            p=subprocess.run(args,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(len(json.loads((Path(t)/'out/playback.json').read_text())['variants']),36)
            p=subprocess.run(args,capture_output=True,text=True);self.assertEqual(p.returncode,1);self.assertNotIn(t,p.stderr)
    def test_real_javascript_controls(self):
        import shutil
        if not shutil.which('node'):self.skipTest('Node unavailable; controller untested')
        fixture=build('2026-03-07T02:30','America/New_York','UTC',3)
        harness=r'''
const assert=require('node:assert/strict');
class Element{
 constructor(id=''){this.id=id;this.value=['month','fold','gap'].includes(id)?'reject':'0';this.textContent='';this.children=[];this.events={};this.dataset={};this.attrs={};}
 append(...xs){this.children.push(...xs)} replaceChildren(){this.children=[]} setAttribute(k,v){this.attrs[k]=v}
 addEventListener(k,fn){this.events[k]=fn} fire(k){this.events[k]()}
}
const ids=['payload','month','fold','gap','previous','next','play','position','step','requested','outcome','adjustment','instant','rows'];
const elements=Object.fromEntries(ids.map(k=>[k,new Element(k)]));
elements.payload.textContent=JSON.stringify(FIXTURE);
let intervals=new Map(),serial=0;
const setInterval=fn=>{intervals.set(++serial,fn);return serial};const clearInterval=id=>intervals.delete(id);
const document={hidden:false,events:{},getElementById:id=>elements[id],createElement:()=>new Element(),createTextNode:text=>({textContent:text}),querySelectorAll:()=>elements.rows.children,addEventListener(k,fn){this.events[k]=fn}};
'''
        checks=r'''
assert.equal(elements.step.textContent,'Slot 1 / 3');assert.equal(intervals.size,0);
elements.next.fire('click');assert.equal(elements.outcome.textContent,'rejected · nonexistent');assert.equal(elements.instant.children[0].textContent,'No UTC instant. This slot is not scheduled.');
elements.gap.value='shift-forward';elements.gap.fire('change');assert.equal(elements.step.textContent,'Slot 1 / 3');
elements.next.fire('click');assert.match(elements.outcome.textContent,/adjusted/);assert.equal(elements.instant.children.length,1);
elements.play.fire('click');assert.equal(intervals.size,1);elements.play.fire('click');assert.equal(intervals.size,0);
elements.play.fire('click');elements.position.value='0';elements.position.fire('input');assert.equal(intervals.size,0);assert.equal(elements.step.textContent,'Slot 1 / 3');
elements.play.fire('click');[...intervals.values()][0]();assert.equal(elements.step.textContent,'Slot 2 / 3');[...intervals.values()][0]();assert.equal(elements.step.textContent,'Slot 3 / 3');assert.equal(intervals.size,0);
elements.play.fire('click');assert.equal(elements.step.textContent,'Slot 1 / 3');document.hidden=true;document.events.visibilitychange();assert.equal(intervals.size,0);
elements.play.fire('click');elements.fold.value='both';elements.fold.fire('change');assert.equal(intervals.size,0);assert.equal(elements.rows.children.length,3);
'''
        proc=subprocess.run(['node','-e','const FIXTURE='+json.dumps(fixture)+';'+harness+SCRIPT+checks],capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
    def test_symlink_destination_not_followed(self):
        with tempfile.TemporaryDirectory() as t:
            target=Path(t)/'target';target.mkdir();out=Path(t)/'out';out.symlink_to(target,target_is_directory=True)
            with self.assertRaises(FileExistsError):write_bundle(build('2026-01-01','UTC','UTC',1),out)
            self.assertEqual(list(target.iterdir()),[])
    def test_preflight_no_output(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'out'
            with patch('timeedge.playback.MAX_BYTES',10):
                with self.assertRaises(ValueError):write_bundle(build('2026-01-01','UTC','UTC',1),out)
            self.assertFalse(out.exists())
    def test_partial_failure_private(self):
        from unittest.mock import patch
        original=os.open
        def fail(path,flags,mode):
            if str(path).endswith('index.html'):raise OSError('synthetic')
            return original(path,flags,mode)
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'out'
            with patch('timeedge.playback.os.open',fail):
                with self.assertRaises(OSError):write_bundle(build('2026-01-01','UTC','UTC',1),out)
            self.assertEqual(stat.S_IMODE(out.stat().st_mode),0o700)
            self.assertEqual(stat.S_IMODE((out/'playback.json').stat().st_mode),0o600)
            self.assertFalse((out/'index.html').exists())
