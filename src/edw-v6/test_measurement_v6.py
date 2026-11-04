"""Verify actual-camera measurement without importing or retaining engine objects."""
from pathlib import Path
import json
import math
import unittest

from lupa import LuaRuntime

PATH = Path(__file__).resolve().parent / 'package/bin/x64/plugins/cyber_engine_tweaks/mods/EDWRightCant/measurement.lua'

FIXTURE = r'''
calls = 0
world = {
  camera={X=100,Y=200,Z=3}, rightAxis={X=1,Y=0,Z=0},
  forwardAxis={X=0,Y=1,Z=0}, upAxis={X=0,Y=0,Z=1},
  leftPosition={X=99.7,Y=200.7,Z=2.9}, rightPosition={X=100.1,Y=200.6,Z=2.75},
  mode='mutable'
}
local function tick() calls=calls+1 end
Transform = {
 new=function() tick(); return {} end,
 GetPosition=function(t) tick(); return t.position end,
}
world.left = {GetWorldPosition=function() tick(); return world.leftPosition end}
world.right = {GetWorldPosition=function() tick(); return world.rightPosition end}
world.cameraObject = {
 GetActiveCameraWorldTransform=function(self,t)
   tick()
   if world.mode=='out' then
     if t~=nil then error('zero arguments required for out parameter') end
     return true,{position=world.camera}
   elseif world.mode=='returned' then
     return true,{position=world.camera}
   elseif world.mode=='false' then return false
   elseif world.mode=='exception' then error('unavailable')
   elseif world.mode=='badposition' then t.position=nil; return true
   else assert(t); t.position=world.camera; return true end
 end,
 GetActiveCameraRight=function() tick(); return world.rightAxis end,
 GetActiveCameraForward=function() tick(); return world.forwardAxis end,
 GetActiveCameraUp=function() tick(); return world.upAxis end,
}
player = {left=world.left,right=world.right}
GameObject = {
 GetLeftActiveWeapon=function(p) tick(); return p.left end,
 GetRightActiveWeapon=function(p) tick(); return p.right end,
}
Game = {GetCameraSystem=function() tick(); return world.cameraObject end}
'''


def fixture():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(FIXTURE)
    module = lua.execute(PATH.read_text())
    lua.globals().measurement = module
    return lua, module


class MeasurementTests(unittest.TestCase):
    def test_module_load_has_no_engine_calls_and_default_error_is_camera_relative(self):
        lua, m = fixture()
        self.assertEqual(lua.globals().calls, 0)
        err, reason, d = m.sample(lua.globals().player)
        self.assertEqual(reason, 'ok')
        for axis, expected in [('x', .2), ('y', .1), ('z', .15)]:
            self.assertAlmostEqual(err[axis], expected)
        self.assertAlmostEqual(d['left']['x'], -.3)
        self.assertAlmostEqual(d['right']['y'], .6)

    def test_output_parameter_variants(self):
        for mode in ('mutable', 'out', 'returned'):
            with self.subTest(mode=mode):
                lua, m = fixture()
                lua.globals().world['mode'] = mode
                err, reason, _ = m.sample(lua.globals().player)
                self.assertEqual(reason, 'ok')
                self.assertAlmostEqual(err['x'], .2)

    def test_arbitrary_camera_rotation_and_translation(self):
        for yaw, pitch in [(0,0),(.8,.4),(2.4,-.6),(-1.2,.9)]:
            lua, m = fixture()
            cy,sy,cp,sp=math.cos(yaw),math.sin(yaw),math.cos(pitch),math.sin(pitch)
            r=(cy,sy,0)
            f=(-sy*cp,cy*cp,sp)
            u=(sy*sp,-cy*sp,cp)
            c=(123,-87,12)
            w=lua.globals().world
            def vec(x): return lua.table_from(dict(zip('XYZ',x)))
            w.camera=vec(c); w.rightAxis=vec(r); w.forwardAxis=vec(f); w.upAxis=vec(u)
            def project(xyz): return tuple(c[i]+xyz[0]*r[i]+xyz[1]*f[i]+xyz[2]*u[i] for i in range(3))
            w.leftPosition=vec(project((-.31,.75,-.12)))
            w.rightPosition=vec(project((.19,.63,-.25)))
            err,reason,_=m.sample(lua.globals().player)
            self.assertEqual(reason,'ok')
            for axis,expected in [('x',.12),('y',.12),('z',.13)]:self.assertAlmostEqual(err[axis],expected,places=10)

    def test_lowercase_vector_bindings(self):
        lua,m=fixture()
        lua.execute('''for _,key in ipairs({'camera','rightAxis','forwardAxis','upAxis','leftPosition','rightPosition'}) do
          local v=world[key]; world[key]={x=v.X,y=v.Y,z=v.Z} end''')
        err,reason,_=m.sample(lua.globals().player)
        self.assertEqual(reason,'ok');self.assertAlmostEqual(err['z'],.15)

    def test_failures_return_reasons_without_retrying_false_success(self):
        for mode,reason in [('false','camera_transform_unavailable'),('exception','camera_transform_call_failed'),('badposition','camera_position_invalid')]:
            with self.subTest(mode=mode):
                lua,m=fixture();lua.globals().world['mode']=mode
                err,why,_=m.sample(lua.globals().player)
                self.assertIsNone(err);self.assertEqual(why,reason)
                if mode=='false':self.assertEqual(lua.globals().calls,5) # two weapon getters, camera getter, Transform.new, one camera read
        lua,m=fixture()
        lua.execute('GameObject.GetRightActiveWeapon=function() error("unavailable") end')
        self.assertEqual(m.sample(lua.globals().player),(None,'native_measurement_unavailable',None))

    def test_invalid_basis_positions_and_depth_are_rejected(self):
        cases=[
          ('world.rightAxis={X=2,Y=0,Z=0}','camera_basis_invalid'),
          ('world.rightAxis={X=1,Y=0.1,Z=0}','camera_basis_not_orthogonal'),
          ('world.leftPosition={X=0/0,Y=200,Z=3}','weapon_position_invalid'),
          ('world.rightPosition={X=100,Y=205,Z=3}','weapon_too_far_from_camera'),
          ('world.leftPosition={X=99.7,Y=199.9,Z=2.9}','weapon_depth_invalid'),
          ('world.rightPosition={X=100.1,Y=202.1,Z=3}','weapon_depth_invalid'),
          ('world.cameraObject=nil','camera_unavailable'),
          ('player.left=nil','two_weapons_required'),
        ]
        for change,reason in cases:
            with self.subTest(change=change):
                lua,m=fixture();lua.execute(change)
                self.assertEqual(m.sample(lua.globals().player),(None,reason,None))
        _,m=fixture();self.assertEqual(m.sample(None),(None,'no_player',None))

    def test_no_player_weapon_or_camera_retained(self):
        lua,m=fixture()
        lua.execute('weak=setmetatable({player,world.left,world.right,world.cameraObject},{__mode="v"})')
        result=m.sample(lua.globals().player)
        lua.execute('player=nil; world.left=nil; world.right=nil; world.cameraObject=nil; collectgarbage("collect")')
        self.assertTrue(lua.eval('weak[1]==nil and weak[2]==nil and weak[3]==nil and weak[4]==nil'))
        err,reason,d=result
        self.assertEqual(reason,'ok')
        self.assertAlmostEqual(d['left']['x'],-.3)
        self.assertEqual(lua.eval('type(measurement.sample)'), 'function')


if __name__=='__main__':unittest.main(verbosity=2)
