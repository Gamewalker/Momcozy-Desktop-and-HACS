from state import DATA
import json, hmac, hashlib
from pathlib import Path
root=DATA
sign=json.loads((root/'signing.private.json').read_text())
login=json.loads((root/'tuya-session.private.json').read_text())['result']
devices=json.loads((root/'camera-config.private.json').read_text())
ch=hmac.new(sign['appKey'].encode(),'_'.join(sign['signingKey'].split('_')[:2]).encode(),hashlib.sha256).hexdigest()[8:16]
manifest=[]
for i,device in enumerate(devices,1):
    config={'signing-key':sign['signingKey'],'sid':login['sid'],'ecode':login['ecode'],
            'partner':login['partnerIdentity'],'app-key':sign['appKey'],
            'device-id':sign['deviceId']+str(i),'ch-key':ch,'package':'com.lute.momcozy',
            'app-version':sign.get('appVersion','3.3.0'),
            'camera-id':device['deviceId'],'camera-name':'bm04_'+str(i),'port':str(18553+i)}
    filename=f'bridge-{i}.private.json'
    (root/filename).write_text(json.dumps(config),encoding='utf-8')
    manifest.append(filename)
(root/'cameras.private.json').write_text(json.dumps(manifest),encoding='utf-8')
print(f'{len(manifest)} private bridge configurations prepared.')
