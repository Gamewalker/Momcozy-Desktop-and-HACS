from state import DATA
import hashlib, hmac, json, time, uuid, urllib.request, urllib.parse
from pathlib import Path
from momcozy_login import NoRedirect
ROOT=DATA
WHITELIST=set('a v lat lon lang deviceId appVersion ttid isH5 h5Token os clientId postData time requestId et n4h5 sid chKey sp'.split())

def parameters():
    cache=ROOT/'signing.private.json'
    if cache.exists(): return json.loads(cache.read_text())
    meta=json.loads((ROOT/'apk-parameters.private.json').read_text())
    embedded=bytes.fromhex(json.loads((ROOT/'embedded-keys.private.json').read_text())[0]).decode()
    result={'appKey':meta['THING_SMART_APPKEY'],
            'signingKey':'_'.join([meta['package'],meta['certificateHash'],embedded,meta['THING_SMART_SECRET']]),
            'deviceId':uuid.uuid4().hex,'appVersion':meta['appVersion'],
            'appVersionCode':meta['appVersionCode']}
    cache.write_text(json.dumps(result),encoding='utf-8')
    return result

def call(action, body=None, sid=None, version='1.0'):
    config=parameters()
    params={'a':action,'v':version,'clientId':config['appKey'],'os':'Android',
            'appVersion':config.get('appVersion','3.3.0'),'deviceId':config['deviceId'],'lang':'en',
            'time':str(int(time.time())),'requestId':str(uuid.uuid4()),'et':'0.0.1'}
    package_cert='_'.join(config['signingKey'].split('_')[:2])
    params['chKey']=hmac.new(config['appKey'].encode(),package_cert.encode(),hashlib.sha256).hexdigest()[8:16]
    if body is not None: params['postData']=json.dumps(body,separators=(',',':'),ensure_ascii=False)
    if sid: params['sid']=sid
    signed=[]
    for key in sorted(params):
        if key not in WHITELIST: continue
        val=params[key]
        if key=='postData':
            digest=hashlib.md5(val.encode()).hexdigest()
            val=digest[8:16]+digest[:8]+digest[24:32]+digest[16:24]
        signed.append(key+'='+val)
    params['sign']=hmac.new(config['signingKey'].encode(),'||'.join(signed).encode(),hashlib.sha256).hexdigest()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    req=urllib.request.Request('https://a1.tuyaeu.com/api.json',data=urllib.parse.urlencode(params).encode())
    with opener.open(req,timeout=25) as response: result=json.load(response)
    return result

if __name__=='__main__':
    result=call('smartlife.p.time.get')
    (ROOT/'tuya-time.private.json').write_text(json.dumps(result),encoding='utf-8')
    print('Success:',result.get('success'),'errorCode:',result.get('errorCode'))
    print('Response field names:',list(result))
