#!/usr/bin/env python3
"""Section 4.3.1 Step 3, phase A: implementation inventory and existing test baseline.
This is NOT a complete formula/prefix/causality verification; it refuses to certify
unverified tests. No evaluation data are read or changed.
"""
from pathlib import Path
import ast, csv, hashlib, json, subprocess, sys, zipfile
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'section431_step3_verification'
TARGETS=['section4_3_1_candidates.py','section431_additions.py']
TESTS=['test_candidates.py','test_additions.py']

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    OUT.mkdir(exist_ok=True)
    search=[ROOT,ROOT/'section431_work']
    archive=ROOT/'section431_prototype.zip'
    if archive.exists():
        with zipfile.ZipFile(archive) as z:
            for name in TARGETS+TESTS:
                hits=[x for x in z.namelist() if Path(x).name==name]
                if len(hits)==1:
                    dest=OUT/'prototype_sources'/name
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_bytes(z.read(hits[0]))
        search.append(OUT/'prototype_sources')
    found={}
    for name in TARGETS+TESTS:
        paths=[base/name for base in search if (base/name).is_file()]
        if paths: found[name]=paths[0]
    inventory=[]
    for name in TARGETS:
        p=found.get(name)
        if not p: continue
        tree=ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
        funcs=[]
        for n in ast.walk(tree):
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
                funcs.append({'function':n.name,'line':n.lineno})
        inventory.append({'file':str(p),'sha256':sha(p),'functions':funcs})
    results=[]
    for name in TESTS:
        p=found.get(name)
        if not p:
            results.append({'test':name,'status':'NOT_FOUND'})
            continue
        try:
            run=subprocess.run([sys.executable,'-m','pytest',str(p),'-q'],cwd=str(p.parent),capture_output=True,text=True,timeout=120)
            status='PASS_EXISTING_TESTS' if run.returncode==0 else 'FAIL_EXISTING_TESTS'
            log=(run.stdout+'\n'+run.stderr)[-12000:]
        except Exception as exc:
            status='ERROR';log=str(exc)
        (OUT/(name+'.log')).write_text(log,encoding='utf-8')
        results.append({'test':name,'status':status,'source_sha256':sha(p),'log':str(OUT/(name+'.log'))})
    report={
      'generated_utc':datetime.now(timezone.utc).isoformat(),
      'scope':'Step 3 phase A: implementation inventory and existing test baseline',
      'inventory':inventory,'existing_tests':results,
      'verification_status':{
        '35_original_formulas':'NOT_INDEPENDENTLY_VERIFIED',
        '11_additional_family_formulas':'NOT_INDEPENDENTLY_VERIFIED',
        'real_TRAIN_random_prefix_invariance':'NOT_RUN',
        'session_and_provider_isolation':'NOT_RUN',
        'numerical_sanity_all_outputs':'NOT_RUN'},
      'next_requirement':'Identify the actual production feature-generator entry point, inputs, and output columns. Then construct independent numerical oracles and run real-data perturbation tests. No feature is approved by this baseline alone.'}
    (OUT/'step3_phaseA_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('STEP 3 PHASE A — INVENTORY / BASELINE ONLY')
    for i in inventory: print('SOURCE:',i['file'],'SHA256:',i['sha256'],'FUNCTIONS:',len(i['functions']))
    for t in results: print('TEST:',t['test'],t['status'])
    print('Formula verification: NOT DONE; real TRAIN prefix/isolation: NOT DONE')
    print('Report:',OUT/'step3_phaseA_report.json')
    if not inventory: print('ACTION REQUIRED: place the actual production feature source files next to this script.')

if __name__=='__main__': main()
