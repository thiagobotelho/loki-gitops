"""Exercita o hook de imagens com API simulada, sem kubeconfig ou cluster."""
from pathlib import Path
import copy
import json
import os
import subprocess
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
objects = [o for o in yaml.safe_load_all(subprocess.check_output(['kubectl', 'kustomize', str(ROOT / 'overlays/desenvolvimento')], text=True)) if o]
job = next(o for o in objects if o['kind'] == 'Job' and o['metadata']['name'] == 'crc-minio-images')
code = job['spec']['template']['spec']['containers'][0]['args'][0]
wave = lambda o: int(o.get('metadata', {}).get('annotations', {}).get('argocd.argoproj.io/sync-wave', 0))
buildconfigs = [o for o in objects if o['kind'] == 'BuildConfig']
assert {o['metadata']['name'] for o in buildconfigs} == {'minio-crc', 'mc-crc'}
assert all(wave(o) < wave(job) for o in buildconfigs)
assert all(not o['spec'].get('triggers') for o in buildconfigs), 'O hook deve ser o único iniciador automático'
deployment = next(o for o in objects if o['kind'] == 'Deployment' and o['metadata']['name'] == 'minio')
pvc = next(o for o in objects if o['kind'] == 'PersistentVolumeClaim' and o['metadata']['name'] == 'minio-data')
assert wave(job) < wave(deployment) == wave(pvc), 'PVC WaitForFirstConsumer não pode bloquear antes do consumidor'
assert job['metadata']['annotations']['argocd.argoproj.io/hook'] == 'Sync'
assert job['spec']['backoffLimit'] == 0 and job['spec']['activeDeadlineSeconds'] > 0
role = next(o for o in objects if o['kind'] == 'Role' and o['metadata']['name'] == 'crc-minio-images')
assert all('*' not in r['resources'] and not {'delete', 'patch', 'update', 'list', 'watch'} & set(r['verbs']) for r in role['rules'])
assert not any('secrets' in r['resources'] for r in role['rules'])
instantiate = next(r for r in role['rules'] if 'buildconfigs/instantiate' in r['resources'])
assert set(instantiate['resourceNames']) == {'minio-crc', 'mc-crc'}
for env in ('aceite', 'producao'):
    rendered = subprocess.check_output(['kubectl', 'kustomize', str(ROOT / 'overlays' / env)], text=True)
    assert 'crc-minio-images' not in rendered, 'Automação CRC vazou para outro ambiente'

MOCK = r'''#!/usr/bin/env python3
import sys,os,json,pathlib
p=pathlib.Path(os.environ['MOCK_STATE']);s=json.loads(p.read_text());a=sys.argv[1:]
assert a[:4]==['--request-timeout=15s','--cache-dir=/tmp/oc-cache','-n','openshift-logging']
a=a[4:];s['calls'].append(a)
def end(value='',error=False):
 p.write_text(json.dumps(s));print(value,file=sys.stderr if error else sys.stdout,end='');sys.exit(1 if error else 0)
if a[:2]==['get','imagestreamtag']:
 name=a[2].split(':',1)[0];v=s['images'][name]
 if s.get('deny')=='image':end('Forbidden',True)
 if v['available']:
  if v.get('delay',0):v['delay']-=1;end()
  end('imagestreamtag.image.openshift.io/'+a[2])
 end()
elif a[:2]==['get','buildconfig']:
 if s.get('deny')=='config':end('Forbidden',True)
 end(str(s['images'][a[2]]['version']))
elif a[:2]==['get','build']:
 if s.get('deny')=='build':end('Forbidden',True)
 name=a[2].rsplit('-',1)[0];v=s['images'][name]
 phase=v['phases'][0]
 if len(v['phases'])>1:v['phases'].pop(0)
 if phase=='Complete' and not v.get('no_publish'):v['available']=True
 end(phase)
elif a[0]=='start-build':
 if s.get('deny')=='start':end('Forbidden',True)
 name=a[1];v=s['images'][name];v['version']+=1;v['phases']=list(v['new_phases']);s['started'].append(name)
 end(name+'-'+str(v['version']))
else:end('Comando não permitido no teste',True)
'''

def image(**overrides):
    return dict(available=False, version=0, phases=['Complete'], new_phases=['Pending', 'Running', 'Complete'], **overrides)

base = {'images': {'minio-crc': image(), 'mc-crc': image()}, 'calls': [], 'started': []}
cases = []
def case(name, change, expected_ok, started):
    state=copy.deepcopy(base);change(state);cases.append((name,state,expected_ok,started))
case('cluster vazio', lambda s: None, True, ['minio-crc','mc-crc'])
case('imagens existentes', lambda s: [v.update(available=True) for v in s['images'].values()], True, [])
case('builds ativos', lambda s: [v.update(version=1,phases=['Running','Complete']) for v in s['images'].values()], True, [])
case('primeiro pronto, segundo ausente', lambda s: s['images']['minio-crc'].update(available=True), True, ['mc-crc'])
case('falha anterior recuperável no novo sync', lambda s: [v.update(version=1,phases=['Failed']) for v in s['images'].values()], True, ['minio-crc','mc-crc'])
case('publicação eventual', lambda s: [v.update(delay=1) for v in s['images'].values()], True, ['minio-crc','mc-crc'])
for phase in ['Failed','Error','Cancelled','Inesperado']:
    case('novo build '+phase, lambda s,p=phase: s['images']['minio-crc'].update(new_phases=['Running',p]), False, ['minio-crc'])
case('build sem imagem publicada', lambda s: s['images']['minio-crc'].update(new_phases=['Complete'],no_publish=True), False, ['minio-crc'])
case('build ativo não finaliza', lambda s: s['images']['minio-crc'].update(version=1,phases=['Running']), False, [])
for target in ['image','config','start','build']:
    case('permissão negada '+target, lambda s,t=target: s.update(deny=t), False, ['minio-crc'] if target=='build' else [])

with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp);(path/'oc').write_text(MOCK);(path/'oc').chmod(0o755)
    (path/'sleep').write_text('#!/bin/sh\nexit 0\n');(path/'sleep').chmod(0o755)
    for name,state,ok,started in cases:
        statefile=path/'state.json';statefile.write_text(json.dumps(state))
        env={**os.environ,'PATH':tmp+':'+os.environ['PATH'],'MOCK_STATE':str(statefile),'POD_NAMESPACE':'openshift-logging','MAX_ATTEMPTS':'4','POLL_SECONDS':'0'}
        result=subprocess.run(['sh','-ec',code],env=env,capture_output=True,text=True,timeout=10)
        actual=json.loads(statefile.read_text())
        assert (result.returncode==0)==ok,(name,result.stderr,result.stdout)
        assert actual['started']==started,(name,actual['started'])
        # O segundo build nunca inicia antes de a primeira imagem ser recuperada.
        if actual['started']==['minio-crc','mc-crc']:
            second=next(i for i,c in enumerate(actual['calls']) if c[:2]==['start-build','mc-crc'])
            assert any(c[:3]==['get','imagestreamtag','minio-crc:RELEASE.2025-09-07T16-13-09Z'] for c in actual['calls'][1:second])
        print('PASS:',name)
print(f'PASS: {len(cases)} cenários sem API real; ordem das waves, RBAC e isolamento dos perfis')
