"""Exercise actual schema6 CET settings and deferred callbacks via the shared fixture."""
import json
from test_lifecycle_v4 import fixture

lua = fixture()
lua.execute('''
assert(nativeCalls==0)
observers.OnGameAttached()
events.onUpdate(0.06)
assert(configured==0 and configuredEnabled==true)
assert(configuredX==0 and configuredY==0 and configuredZ==0)
api.status()
assert(messages[#messages]:find('autoBalance=true',1,true))
api.trim(100)
events.onUpdate(0.06)
assert(configured==20)
api.angle(-100)
events.onUpdate(0.06)
assert(configured==-20)
api.enable(false)
events.onUpdate(0.06)
assert(configured==-20 and configuredEnabled==false)
api.enable(true)
events.onUpdate(0.06)
assert(configured==-20 and configuredEnabled==true)
api.angle(0/0)
events.onUpdate(0.06)
assert(configured==0)
api.balance(false)
for i=1,8 do events.onUpdate(.06) end
assert(samples==0 and configuredX==0 and configuredY==0 and configuredZ==0)
api.balance(true)
events.onOverlayOpen()
local prior=nativeCalls
api.trim(15)
assert(api.test()==true)
events.onUpdate(0.06)
assert(nativeCalls==prior and configured==0)
assert(testCalls==0)
events.onOverlayClose()
events.onUpdate(0.06)
assert(configured==15 and testCalls==1)
events.onUpdate(0.06)
assert(testCalls==1)
local writes=saves
prior=nativeCalls
nativeUp=false
events.onShutdown()
assert(nativeCalls==prior and saves==writes)
''')
stored = json.loads(lua.globals().savedSettings)
assert stored == {'schema': 6, 'enabled': True, 'correction': 15, 'autoBalance': True}, stored
print('CET schema6 default/trim/bounds, independent enable/balance, persistence, deferred test and shutdown: PASS')
