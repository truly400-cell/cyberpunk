"""Exercise actual CET Lua callbacks against an engine that becomes unavailable.

Requires lupa; no game/controller. These are lifecycle regressions, not crash reproduction.
"""
from pathlib import Path
import json
import unittest
from lupa import LuaRuntime, lua_type

SOURCE = Path(__file__).parent / 'package/bin/x64/plugins/cyber_engine_tweaks/mods/EDWRightCant/init.lua'


def json_value(value):
    if lua_type(value) == 'table':
        return {key: json_value(item) for key, item in value.items()}
    return value


def fixture(settings=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().moduleDirectory = str(SOURCE.parent)
    lua.execute("package.path=moduleDirectory..'/?.lua;'..package.path")
    lua.execute('''
events, observers, before = {}, {}, {}
nativeCalls, testCalls, saves, diagnosticSaves, samples = 0, 0, 0, 0, 0
nativeUp = true
messages, requests = {}, {}
configuredX, configuredY, configuredZ = 0, 0, 0
print=function(...)
 local out={}
 for i,v in ipairs({...}) do out[i]=tostring(v) end
 table.insert(messages,table.concat(out,' '))
end
local function native()
  nativeCalls=nativeCalls+1
  assert(nativeUp, 'native call during teardown')
end
livePlayer = {
 EDWConfigureRightCant=function(self,a,on,x,y,z)
  native(); configured=a; configuredEnabled=on
  assert(type(x)=='number' and type(y)=='number' and type(z)=='number')
  configuredX,configuredY,configuredZ=x,y,z
  table.insert(requests,{correction=a,enabled=on,x=x,y=y,z=z})
 end,
 EDWBeginRightCantTest=function() native(); testCalls=testCalls+1 end,
 EDWGetRightCantAngle=function() native(); return configured end,
 EDWGetRightCantReason=function() native(); return 'active' end,
 EDWGetRightCantLastAimAngle=function() native(); return configured end,
 EDWGetRightCantInput=function() native(); return 1 end,
 EDWGetRightCantWeight=function() native(); if overrideWeight~=nil then return overrideWeight end; return configuredEnabled and 1 or 0 end,
 EDWGetRightCantLastAimWeight=function() native(); if overrideLastWeight~=nil then return overrideLastWeight end; return 1 end,
}
-- Identity camera basis with a translated origin exercises actual measurement.lua.
-- The simulated native feature immediately moves the right weapon by its offset.
local cameraPosition={X=12,Y=-5,Z=2}
local leftWeapon={GetWorldPosition=function()
 native(); return {X=cameraPosition.X-.2,Y=cameraPosition.Y+.6,Z=cameraPosition.Z-.18}
end}
local rightWeapon={GetWorldPosition=function()
 native()
 local response=responseGain or 1
 return {X=cameraPosition.X+.11+configuredX*response,
         Y=cameraPosition.Y+.48+configuredY*response,
         Z=cameraPosition.Z-.12+configuredZ*response}
end}
local camera={
 GetActiveCameraWorldTransform=function(self,t) native(); samples=samples+1; t.position=cameraPosition; return true end,
 GetActiveCameraRight=function() native(); return {X=1,Y=0,Z=0} end,
 GetActiveCameraForward=function() native(); return {X=0,Y=1,Z=0} end,
 GetActiveCameraUp=function() native(); return {X=0,Y=0,Z=1} end,
}
Transform={new=function() native(); return {} end,GetPosition=function(t) native(); return t.position end}
GameObject={
 GetRightActiveWeapon=function(p) native(); return rightWeapon end,
 GetLeftActiveWeapon=function(p) native(); return leftWeapon end,
}
Game={GetPlayer=function() native(); return livePlayer end,
      GetCameraSystem=function() native(); return camera end}
registerForEvent=function(n,f) events[n]=f end
Observe=function(c,n,f) assert(c=='PlayerPuppet'); observers[n]=f end
ObserveBefore=function(c,n,f) assert(c=='PlayerPuppet'); before[n]=f end
io.open=function(n,m)
 assert(n=='settings.json' or n=='balance-status.json')
 if m=='r' then
  assert(n=='settings.json')
  if initialSettings==nil then return nil end
  return {read=function() return initialSettings end,close=function() end}
 end
 return {write=function(self,s)
  if n=='settings.json' then saves=saves+1; savedSettings=s
  else diagnosticSaves=diagnosticSaves+1; savedDiagnostic=s end
  return self
 end,close=function() end}
end
''')
    lua.globals().initialSettings = json.dumps(settings) if settings is not None else None
    lua.globals().json = lua.table_from({
        'encode': lambda table: json.dumps(json_value(table)),
        'decode': lambda text: lua.table_from(json.loads(text)),
    })
    lua.globals().api = lua.execute(SOURCE.read_text())
    lua.execute('events.onInit()')
    return lua


class LifecycleTests(unittest.TestCase):
    def test_detach_fences_updates_status_and_test(self):
        lua = fixture()
        lua.execute('''
assert(nativeCalls==0)
events.onUpdate(.1)
assert(nativeCalls==0) -- not attached yet
observers.OnGameAttached()
events.onUpdate(.1)
assert(configured==0 and configuredEnabled==true)
local prior=nativeCalls
nativeUp=false
before.OnDetach()
events.onUpdate(.1)
api.status()
assert(api.test()==false)
events.onShutdown()
events.onUpdate(.1)
assert(nativeCalls==prior)
''')

    def test_shutdown_without_detach_never_calls_engine(self):
        lua = fixture()
        lua.execute('''
observers.OnGameAttached()
events.onUpdate(.1)
local prior=nativeCalls
nativeUp=false
events.onShutdown()
api.status()
events.onUpdate(.1)
observers.OnGameAttached() -- must not reactivate after final shutdown
events.onUpdate(.1)
assert(nativeCalls==prior)
''')

    def test_player_userdata_not_retained_between_updates(self):
        lua = fixture()
        lua.execute('''
observers.OnGameAttached()
weakPlayer=setmetatable({livePlayer},{__mode='v'})
events.onUpdate(.1)
assert(weakPlayer[1]~=nil)
livePlayer=nil
collectgarbage('collect')
collectgarbage('collect')
assert(weakPlayer[1]==nil, 'module retained player outside update')
nativeUp=false
api.status() -- snapshot must not invoke methods on the expired player
''')

    def test_pending_test_does_not_cross_sessions(self):
        lua = fixture()
        lua.execute('''
observers.OnGameAttached()
events.onOverlayOpen()
assert(api.test()==true)
events.onUpdate(.1)
assert(testCalls==0)
before.OnDetach()
observers.OnGameAttached()
events.onOverlayClose()
events.onUpdate(.1)
assert(testCalls==0)
assert(configured==0 and configuredEnabled==true)
''')

    def test_startup_preferences_preserved_without_shutdown_writes(self):
        lua = fixture({'schema': 6, 'enabled': False, 'correction': -12, 'autoBalance': False})
        lua.execute('''
assert(nativeCalls==0 and saves==0)
observers.OnGameAttached()
events.onUpdate(.1)
assert(configured==-12 and configuredEnabled==false)
api.enable(true)
events.onUpdate(.1)
assert(configured==-12 and configuredEnabled==true)
for i=1,10 do events.onUpdate(.1) end
assert(samples==0 and configuredX==0 and configuredY==0 and configuredZ==0)
api.status()
assert(messages[#messages]:find('autoBalance=false',1,true))
local writes=saves
events.onShutdown()
assert(saves==writes)
''')

    def test_legacy_45_degree_cant_migrates_to_zero_trim(self):
        for settings in [
            {'enabled': True, 'angle': 45},
            {'schema': 3, 'enabled': True, 'angle': 45, 'correction': 18},
        ]:
            with self.subTest(settings=settings):
                lua = fixture(settings)
                lua.execute('''
observers.OnGameAttached()
events.onUpdate(.1)
assert(configured==0 and configuredEnabled==true)
api.trim(5)
events.onUpdate(.1)
assert(configured==5 and configuredEnabled==true)
''')
                saved = json.loads(lua.globals().savedSettings)
                self.assertEqual(saved, {'schema': 6, 'enabled': True, 'correction': 5, 'autoBalance': True})

    def test_zero_trim_still_enables_pose_weight_and_status_is_snapshot(self):
        lua = fixture()
        lua.execute('''
observers.OnGameAttached()
events.onUpdate(.1)
assert(configured==0 and configuredEnabled==true)
api.status()
assert(messages[#messages]:find('weight=1 lastWeight=1',1,true))
local prior=nativeCalls
overrideWeight=.25
overrideLastWeight=.75
api.status()
assert(nativeCalls==prior)
assert(messages[#messages]:find('weight=1 lastWeight=1',1,true)) -- last normal update, not fresh native access
events.onUpdate(.1)
api.status()
assert(messages[#messages]:find('weight=0.25 lastWeight=0.75',1,true))
nativeUp=false
before.OnDetach()
prior=nativeCalls
api.status()
assert(nativeCalls==prior)
assert(messages[#messages]:find('weight=unavailable lastWeight=unavailable',1,true))
''')

    def test_measured_feature_offsets_converge_then_freeze_and_recalibrate(self):
        lua = fixture()
        lua.execute('''
observers.OnGameAttached()
for i=1,5 do events.onUpdate(.06) end
assert(samples==0 and configuredX==0 and configuredY==0 and configuredZ==0)
local x,y,z=0,0,0
for i=1,20 do
 events.onUpdate(.06)
 local dx,dy,dz=configuredX-x,configuredY-y,configuredZ-z
 assert(math.sqrt(dx*dx+dy*dy+dz*dz)<=.035+1e-12)
 x,y,z=configuredX,configuredY,configuredZ
end
api.status()
assert(messages[#messages]:find('balance=aligned',1,true),messages[#messages])
assert(samples<=20)
assert(math.sqrt((.09-x)^2+(.12-y)^2+(-.06-z)^2)<=.01)
local sampled=samples
for i=1,8 do events.onUpdate(.06) end
assert(samples==sampled and configuredX==x and configuredY==y and configuredZ==z)
assert(diagnosticSaves==1)
-- Recalibration only queues work. An open overlay cannot move the feature.
events.onOverlayOpen()
local calls=nativeCalls
assert(api.recalibrate()==true)
events.onUpdate(.1)
assert(nativeCalls==calls and configuredX==x)
events.onOverlayClose()
events.onUpdate(.06)
assert(configuredX==0 and configuredY==0 and configuredZ==0)
assert(samples==sampled)
for i=1,4 do events.onUpdate(.06) end
assert(samples==sampled)
events.onUpdate(.06)
assert(samples==sampled+1 and configuredX>0 and configuredY>0 and configuredZ<0)
''')
        diagnostic = json.loads(lua.globals().savedDiagnostic)
        self.assertEqual(diagnostic['status'], 'aligned')
        self.assertEqual(diagnostic['measurement'], 'ok')
        self.assertLessEqual(float(diagnostic['errorMeters']), .01)

    def test_no_response_freezes_zero_until_aim_restarts(self):
        lua = fixture()
        lua.execute('''
responseGain=0
observers.OnGameAttached()
for i=1,25 do events.onUpdate(.06) end
api.status()
assert(messages[#messages]:find('balance=no_response',1,true),messages[#messages])
assert(samples==8 and configuredX==0 and configuredY==0 and configuredZ==0)
for i=1,10 do events.onUpdate(.06) end
assert(samples==8)
overrideWeight=0
events.onUpdate(.06)
overrideWeight=1
for i=1,5 do events.onUpdate(.06) end
assert(samples==8)
events.onUpdate(.06)
assert(samples==9 and configuredX>0)
''')

    def test_detach_after_calibration_never_uses_measurement_or_feature(self):
        lua = fixture()
        lua.execute('''
observers.OnGameAttached()
for i=1,7 do events.onUpdate(.06) end
assert(samples==2 and configuredX>0)
local calls,sampled,writes=nativeCalls,samples,diagnosticSaves
nativeUp=false
before.OnDetach()
api.status()
assert(api.recalibrate()==false and api.test()==false)
events.onUpdate(.1)
events.onShutdown()
assert(nativeCalls==calls and samples==sampled and diagnosticSaves==writes)
''')


if __name__ == '__main__':
    unittest.main(verbosity=2)
