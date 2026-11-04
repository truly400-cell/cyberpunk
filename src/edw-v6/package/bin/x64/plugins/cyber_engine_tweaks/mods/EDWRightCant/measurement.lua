-- Read actual weapon origins in the current camera basis. No native objects are retained.
-- NativeDB: gameCameraSystem.GetActiveCamera{Right,Forward,Up} and
-- GetActiveCameraWorldTransform(Transform) -> Bool. CET passes ordinary class
-- arguments by reference; isOut parameters instead follow the return value.
local M = {}

local function finite(n)
  return type(n) == 'number' and n == n and n ~= math.huge and n ~= -math.huge
end

local function coord(v, upper, lower)
  local ok, n = pcall(function() return v[upper] end)
  if ok and finite(n) then return n end
  ok, n = pcall(function() return v[lower] end)
  if ok and finite(n) then return n end
end

local function vector(v)
  if not v then return nil end
  local x, y, z = coord(v, 'X', 'x'), coord(v, 'Y', 'y'), coord(v, 'Z', 'z')
  if x == nil or y == nil or z == nil then return nil end
  return {x = x, y = y, z = z}
end

local function dot(a, b) return a.x*b.x + a.y*b.y + a.z*b.z end
local function sub(a, b) return {x = a.x-b.x, y = a.y-b.y, z = a.z-b.z} end
local function length(a) return math.sqrt(dot(a, a)) end
local function unit(a)
  if not a then return nil end
  local n = length(a)
  if not finite(n) or math.abs(n - 1) > 0.05 then return nil end
  return {x = a.x/n, y = a.y/n, z = a.z/n}
end

local function cameraPosition(cam)
  local t = Transform.new()
  local ok, success, returned = pcall(function() return cam:GetActiveCameraWorldTransform(t) end)
  if not ok then
    -- Official CET excludes isOut parameters from Lua arguments and returns them
    -- after the native result. This branch supports dumps with that flag set.
    ok, success, returned = pcall(function() return cam:GetActiveCameraWorldTransform() end)
  end
  if not ok then return nil, 'camera_transform_call_failed' end
  if success ~= true then return nil, 'camera_transform_unavailable' end
  local posOk, position = pcall(function() return Transform.GetPosition(returned or t) end)
  if not posOk then return nil, 'camera_position_unavailable' end
  local p = vector(position)
  if not p then return nil, 'camera_position_invalid' end
  return p
end

local function sample(p)
  if not p then return nil, 'no_player' end
  local right = GameObject.GetRightActiveWeapon(p)
  local left = GameObject.GetLeftActiveWeapon(p)
  if not right or not left then return nil, 'two_weapons_required' end
  local cam = Game.GetCameraSystem()
  if not cam then return nil, 'camera_unavailable' end
  local camera, why = cameraPosition(cam)
  if not camera then return nil, why end
  local r = unit(vector(cam:GetActiveCameraRight()))
  local f = unit(vector(cam:GetActiveCameraForward()))
  local u = unit(vector(cam:GetActiveCameraUp()))
  if not r or not f or not u then return nil, 'camera_basis_invalid' end
  if math.abs(dot(r,f)) > 0.05 or math.abs(dot(r,u)) > 0.05 or math.abs(dot(f,u)) > 0.05 then
    return nil, 'camera_basis_not_orthogonal'
  end
  local leftWorld, rightWorld = vector(left:GetWorldPosition()), vector(right:GetWorldPosition())
  if not leftWorld or not rightWorld then return nil, 'weapon_position_invalid' end
  local ldelta, rdelta = sub(leftWorld, camera), sub(rightWorld, camera)
  if length(ldelta) >= 3 or length(rdelta) >= 3 then return nil, 'weapon_too_far_from_camera' end
  local l = {x = dot(ldelta,r), y = dot(ldelta,f), z = dot(ldelta,u)}
  local q = {x = dot(rdelta,r), y = dot(rdelta,f), z = dot(rdelta,u)}
  if l.y <= 0.05 or l.y >= 2 or q.y <= 0.05 or q.y >= 2 then
    return nil, 'weapon_depth_invalid'
  end
  local error = {x = -l.x-q.x, y = l.y-q.y, z = l.z-q.z}
  if not finite(error.x) or not finite(error.y) or not finite(error.z) then
    return nil, 'measurement_not_finite'
  end
  -- Return only primitive copies. left/right/cam/t exist only during this call.
  return error, 'ok', {left = l, right = q}
end

function M.sample(p)
  local ok, error, reason, diagnostic = pcall(sample, p)
  if not ok then return nil, 'native_measurement_unavailable', nil end
  return error, reason, diagnostic
end

return M
