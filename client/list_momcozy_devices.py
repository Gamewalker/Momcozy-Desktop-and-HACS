from state import DATA, app_version
import json
import urllib.request
from pathlib import Path
from momcozy_login import NoRedirect
root = DATA
session = json.loads((root / 'direct-session.private.json').read_text())
request = urllib.request.Request(session['base'] + '/api/app/device/queryDevices?pageNum=1&pageSize=50', headers={
    'authorization': 'Bearer ' + session['login']['token'],
    'Client': 'Android', 'Version': app_version(), 'X-COZY-APPID': 'momcozy-0719', 'CountryCode': 'DE'})
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
with opener.open(request, timeout=20) as response:
    result = json.load(response)
(root / 'devices.private.json').write_text(json.dumps(result), encoding='utf-8')
print('Response code:', result.get('code'))
if str(result.get('code')) != '200':
    raise SystemExit('Device discovery failed.')
print('Devices discovered:', len(result['result']['deviceList']))
