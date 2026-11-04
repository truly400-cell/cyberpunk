-- Pure numeric calibration controller. Input is the remaining camera-space error
-- after the previous correction; positive error requests increasing that offset.
-- No game objects, callbacks, clocks, or userdata are retained here.
local A = {}
local GAIN, STEP_CAP, TOLERANCE, MAX_STEPS = 0.35, 0.035, 0.01, 20
local LIMIT_X, LIMIT_Y, LIMIT_Z, TOTAL_LIMIT = 0.25, 0.18, 0.20, 0.30

local function finite(v)
  return type(v) == 'number' and v == v and v ~= math.huge and v ~= -math.huge
end

local function vector(v)
  if type(v) ~= 'table' then return nil end
  local x = v.x ~= nil and v.x or v.X
  local y = v.y ~= nil and v.y or v.Y
  local z = v.z ~= nil and v.z or v.Z
  if not finite(x) or not finite(y) or not finite(z) then return nil end
  return { x = x, y = y, z = z }
end

local function norm(v)
  local scale = math.max(math.abs(v.x), math.abs(v.y), math.abs(v.z))
  if scale == 0 then return 0 end
  return scale * math.sqrt((v.x / scale)^2 + (v.y / scale)^2 + (v.z / scale)^2)
end

local function copy(v) return { x = v.x, y = v.y, z = v.z } end
local function zero() return { x = 0, y = 0, z = 0 } end
local function clamp(v, lo, hi) return math.max(lo, math.min(hi, v)) end

local function project(v)
  local p = { x = clamp(v.x, -LIMIT_X, LIMIT_X), y = clamp(v.y, -LIMIT_Y, LIMIT_Y), z = clamp(v.z, -LIMIT_Z, LIMIT_Z) }
  local length = norm(p)
  if length > TOTAL_LIMIT then
    local scale = TOTAL_LIMIT / length
    p.x, p.y, p.z = p.x * scale, p.y * scale, p.z * scale
  end
  local limited = math.abs(v.x - p.x) > 1e-12 or math.abs(v.y - p.y) > 1e-12 or math.abs(v.z - p.z) > 1e-12
  return p, limited
end

local function initialize(s)
  s.offset, s.status, s.frozen = zero(), 'calibrating', false
  s.steps, s.initialError, s.lastError, s.growthSamples = 0, 0, 0, 0
  s.hitLimit = false
end

local function freeze(s, status, clear)
  if clear then s.offset = zero() end
  s.status, s.frozen = status, true
  return copy(s.offset), status
end

function A.new()
  local s = {}
  initialize(s)
  return s
end

-- Mutate a previously created state. Return a copy so callers cannot alias offset.
function A.reset(s)
  assert(type(s) == 'table', 'alignment state must be a table')
  initialize(s)
  return copy(s.offset), s.status
end

function A.step(s, error)
  assert(type(s) == 'table', 'alignment state must be a table')
  local e, current = vector(error), vector(s.offset)
  local length = e and norm(e) or nil
  if not e or not finite(length) or not current or not finite(s.steps)
    or not finite(s.initialError) or not finite(s.growthSamples) then
    initialize(s)
    return freeze(s, 'invalid', true)
  end
  -- Invalid input always fails safe, even after a successful frozen calibration.
  -- Valid later samples cannot chase recoil or change a frozen result.
  if s.frozen then return copy(s.offset), s.status end

  s.steps = s.steps + 1
  if s.steps == 1 then s.initialError = length end
  s.lastError = length
  if length <= TOLERANCE then return freeze(s, 'aligned', false) end

  -- E > max(I*1.4, I+.05), expressed without overflowing I*1.4.
  local growing = s.initialError > 0 and length / s.initialError > 1.4
    and length - s.initialError > 0.05
  s.growthSamples = growing and s.growthSamples + 1 or 0
  if s.growthSamples >= 2 then return freeze(s, 'no_response', true) end
  if s.steps >= 8 and length > s.initialError * 0.9 then
    return freeze(s, 'no_response', true)
  end

  -- This normal movement is capped to 3.5 cm. Explicit reset/fail-safe releases
  -- intentionally return to zero immediately, even if the release is larger.
  local distance = math.min(GAIN * length, STEP_CAP)
  local nextOffset = {
    x = current.x + e.x / length * distance,
    y = current.y + e.y / length * distance,
    z = current.z + e.z / length * distance,
  }
  local limited
  s.offset, limited = project(nextOffset)
  s.hitLimit = s.hitLimit or limited
  if s.steps >= MAX_STEPS then return freeze(s, 'limited', false) end
  return copy(s.offset), s.status
end

return A
