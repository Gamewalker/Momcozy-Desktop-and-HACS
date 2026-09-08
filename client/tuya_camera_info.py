from state import DATA
import json
from pathlib import Path
from tuya_mobile import call
ROOT=DATA
sid=json.loads((ROOT/'tuya-session.private.json').read_text())['result']['sid']
devices=json.loads((ROOT/'devices.private.json').read_text())['result']['deviceList']
results=[]
for number,device in enumerate(devices,1):
    dev_id=device['metadata']['extDeviceId']
    info=call('tuya.m.device.get',{'devId':dev_id},sid=sid)
    rtc=call('smartlife.m.rtc.config.get',{'devId':dev_id},sid=sid)
    results.append({'deviceId':dev_id,'info':info,'rtc':rtc})
    print('Camera',number,'info',info.get('success'),info.get('errorCode'),
          'RTC',rtc.get('success'),rtc.get('errorCode'))
    for name,value in [('info',info),('rtc',rtc)]:
        if isinstance(value.get('result'),dict): print(name,'fields:',list(value['result']))
(ROOT/'camera-config.private.json').write_text(json.dumps(results),encoding='utf-8')
