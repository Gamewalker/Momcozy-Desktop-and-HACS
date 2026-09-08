from state import DATA
import json, hashlib
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from pathlib import Path
from tuya_mobile import call
ROOT=DATA
credentials=json.loads((ROOT/'direct-session.private.json').read_text())['tuya']['result']
result=call('thing.m.user.username.token.get',{'countryCode':credentials['region'],'username':credentials['uid'],'isUid':True},version='2.0')
(ROOT/'tuya-login-token.private.json').write_text(json.dumps(result),encoding='utf-8')
print('Token request:',result.get('success'),result.get('errorCode'))
if isinstance(result.get('result'),dict):
    print('Result field names:',list(result['result']))
if result.get('success'):
    token=result['result']
    public=rsa.RSAPublicNumbers(int(token['exponent']),int(token['publicKey'])).public_key()
    encrypted=public.encrypt(hashlib.md5(credentials['token'].encode()).hexdigest().encode(),padding.PKCS1v15()).hex()
    login=call('thing.m.user.uid.password.login.reg',{
        'countryCode':credentials['region'],'uid':credentials['uid'],
        'passwd':encrypted,'token':token['token'],'ifencrypt':1,
        'createGroup':False,'options':'{"group": 1}'})
    (ROOT/'tuya-session.private.json').write_text(json.dumps(login),encoding='utf-8')
    print('Tuya login:',login.get('success'),login.get('errorCode'))
    if isinstance(login.get('result'),dict): print('Session field names:',list(login['result']))

if not result.get("success") or not login.get("success"):
    raise SystemExit("Tuya authentication failed; no automatic retry.")
