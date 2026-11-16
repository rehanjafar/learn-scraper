"""Verify a live Safari session without printing course data or pairing keys."""
import time
from safari_reader import Broker
broker=Broker();broker.start()
print('WAITING_FOR_SAFARI_PAIRING_AND_LEARN_HOME_TAB',flush=True)
try:
 end=time.monotonic()+1800
 while time.monotonic()<end:
  if time.monotonic()-broker.last_seen<5:
   try:
    data=broker.request('/d2l/api/lp/1.43/users/whoami')
    if isinstance(data,dict) and data.get('Identifier') is not None:
     print('LIVE_SAFARI_SESSION_VERIFIED; NO_COOKIES_EXPORTED',flush=True)
     break
   except Exception:
    print('SAFARI_CONNECTED; SIGNED_IN_LEARN_API_NOT_YET_VERIFIED',flush=True)
    time.sleep(15)
  else:time.sleep(1)
 else:print('LIVE_CHECK_TIMEOUT',flush=True)
finally:broker.stop()
