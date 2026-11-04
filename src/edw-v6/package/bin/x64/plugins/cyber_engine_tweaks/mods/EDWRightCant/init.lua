-- EDW3.7: bounded relative alignment; all engine access stays in attached gameplay updates.
local alignment = require('alignment')
local measurement = require('measurement')
local settings = { schema = 6, enabled = true, correction = 0, autoBalance = true }
local visible, elapsed, lastError, pendingTest = false, 0, nil, false
local playerAttached, stopping, wasAiming = false, false, false
local pendingCalibration, settleTicks = false, 0
local control = alignment.new()
local snapshot
local function resetAlignment()
  alignment.reset(control)
  wasAiming, settleTicks = false, 0
end
local function clearSession(reason)
  elapsed, pendingTest, pendingCalibration, lastError = 0, false, false, nil
  resetAlignment()
  snapshot = { effective='unavailable', reason=reason, lastAim='unavailable', input='unavailable',
    weight='unavailable', lastWeight='unavailable', balance='inactive', lastBalance='unavailable',
    x=0, y=0, z=0, lastX=0, lastY=0, lastZ=0, error='unavailable', measurement='unavailable' }
end
clearSession('not_attached')

local function readPrimitive(fn)
  local ok, value = pcall(fn)
  if ok and (type(value)=='number' or type(value)=='boolean' or type(value)=='string') then return tostring(value) end
  return 'unavailable'
end
local function bounded(v)
  v = tonumber(v)
  if not v or v~=v or v==math.huge or v==-math.huge then return 0 end
  return math.max(-20, math.min(20, v))
end
local function save()
  local f=io.open('settings.json','w')
  if f then f:write(json.encode(settings)); f:close() end
end
local function saveDiagnostic()
  -- Camera-relative numbers only; no engine objects or world-location data.
  pcall(function()
    local f=io.open('balance-status.json','w')
    if f then
      f:write(json.encode({version=6,status=snapshot.balance,measurement=snapshot.measurement,
        errorMeters=snapshot.error,left=snapshot.left,right=snapshot.right,
        offset={x=control.offset.x,y=control.offset.y,z=control.offset.z}}))
      f:close()
    end
  end)
end
local function setAngle(v) settings.correction=bounded(v); pendingCalibration=true; save() end
local function queueCalibration()
  if stopping or not playerAttached then return false end
  pendingCalibration=true
  print('[EDWRightCant v6] close CET; hold aim still to recalibrate')
  return true
end
local function apply()
  if stopping or not playerAttached then return end
  local ok,err=pcall(function()
    local p=Game.GetPlayer()
    if not p then clearSession('no_player'); return end
    if pendingCalibration then resetAlignment(); pendingCalibration=false end
    if pendingTest then p:EDWBeginRightCantTest(); pendingTest=false end
    local o=control.offset
    p:EDWConfigureRightCant(settings.correction,settings.enabled,
      settings.autoBalance and o.x or 0,settings.autoBalance and o.y or 0,settings.autoBalance and o.z or 0)
    local weight=tonumber(p:EDWGetRightCantWeight()) or 0
    if weight<=0 then
      resetAlignment(); snapshot.balance='inactive'
    elseif not settings.autoBalance then
      resetAlignment(); snapshot.balance='off'
    else
      if not wasAiming then resetAlignment(); wasAiming=true end
      if settleTicks<5 then
        settleTicks=settleTicks+1; snapshot.balance='settling'
      elseif not control.frozen then
        local e,why,diag=measurement.sample(p)
        snapshot.measurement=tostring(why)
        if diag then snapshot.left,snapshot.right=diag.left,diag.right end
        local nextOffset,status
        if e then
          snapshot.error=string.format('%.4f',math.sqrt(e.x*e.x+e.y*e.y+e.z*e.z))
          nextOffset,status=alignment.step(control,e)
        else
          nextOffset,status=alignment.step(control,{x=0/0,y=0,z=0})
        end
        snapshot.balance=status
        if control.frozen then saveDiagnostic() end
      else snapshot.balance=control.status end
      o=control.offset
      p:EDWConfigureRightCant(settings.correction,settings.enabled,o.x,o.y,o.z)
      snapshot.lastBalance=snapshot.balance
      snapshot.lastX,snapshot.lastY,snapshot.lastZ=o.x,o.y,o.z
    end
    o=control.offset
    snapshot.x,snapshot.y,snapshot.z=o.x,o.y,o.z
    snapshot.effective=readPrimitive(function() return p:EDWGetRightCantAngle() end)
    snapshot.reason=readPrimitive(function() return p:EDWGetRightCantReason() end)
    snapshot.lastAim=readPrimitive(function() return p:EDWGetRightCantLastAimAngle() end)
    snapshot.input=readPrimitive(function() return p:EDWGetRightCantInput() end)
    snapshot.weight=readPrimitive(function() return p:EDWGetRightCantWeight() end)
    snapshot.lastWeight=readPrimitive(function() return p:EDWGetRightCantLastAimWeight() end)
  end)
  if not ok then
    resetAlignment()
    if lastError~=tostring(err) then print('[EDWRightCant] script unavailable: '..tostring(err)) end
    lastError=tostring(err)
  else lastError=nil end
end
local function queueTest()
  if stopping or not playerAttached then pendingTest=false; return false end
  pendingTest=true; pendingCalibration=true
  print('[EDWRightCant v6] close CET: test pose and balance run for3s with two ranged weapons')
  return true
end

registerForEvent('onInit',function()
  local f=io.open('settings.json','r')
  if f then
    local ok,data=pcall(json.decode,f:read('*a')); f:close()
    if ok and type(data)=='table' then
      settings.enabled=data.enabled~=false
      settings.correction=(data.schema==4 or data.schema==6) and bounded(data.correction) or 0
      settings.autoBalance=data.schema~=6 or data.autoBalance~=false
    end
  end
  Observe('PlayerPuppet','OnGameAttached',function()
    if stopping then return end
    playerAttached=true; clearSession('awaiting_game_update')
  end)
  ObserveBefore('PlayerPuppet','OnDetach',function()
    playerAttached=false; clearSession('detached')
  end)
  print('[EDWRightCant v6] native ADS helper cant; bounded measured auto balance; safe lifecycle')
end)
registerForEvent('onUpdate',function(dt)
  if stopping or not playerAttached or visible then return end
  elapsed=elapsed+(tonumber(dt) or 0)
  if elapsed>=0.05 then elapsed=0; apply() end
end)
registerForEvent('onOverlayOpen',function() if not stopping then visible=true end end)
registerForEvent('onOverlayClose',function() visible=false end)
registerForEvent('onShutdown',function()
  -- Entity destruction may already be in progress. Pure Lua state only.
  stopping,playerAttached,visible=true,false,false
  clearSession('shutdown')
end)
registerForEvent('onDraw',function()
  if stopping or not visible then return end
  ImGui.Begin('EDW Dual-Gun Balance v6')
  local on,changed=ImGui.Checkbox('Enable while aiming',settings.enabled)
  if changed then settings.enabled=on; pendingCalibration=true; save() end
  local auto,changedAuto=ImGui.Checkbox('Auto-balance right-hand position',settings.autoBalance)
  if changedAuto then settings.autoBalance=auto; pendingCalibration=true; save() end
  local angle,changedAngle=ImGui.SliderFloat('Extra cant trim',settings.correction,-20,20,'%.1f deg')
  if changedAngle then setAngle(angle) end
  if ImGui.Button('Reset trim to zero') then setAngle(0) end
  if ImGui.Button('Recalibrate after closing CET') then queueCalibration() end
  if ImGui.Button('Test pose for3s after closing CET') then queueTest() end
  ImGui.Text('Close CET; hold aim still for about1.3s. Position then stays locked until aim ends.')
  ImGui.Text('Balance: '..snapshot.balance..' / last: '..snapshot.lastBalance)
  if lastError then ImGui.TextWrapped(lastError) end
  ImGui.End()
end)
return {
  angle=setAngle,trim=setAngle,
  enable=function(v) settings.enabled=v~=false; pendingCalibration=true; save() end,
  balance=function(v) settings.autoBalance=v~=false; pendingCalibration=true; save() end,
  recalibrate=queueCalibration,test=queueTest,
  status=function()
    print('[EDWRightCant v6] enabled='..tostring(settings.enabled)..' autoBalance='..tostring(settings.autoBalance)
      ..' trim='..tostring(settings.correction)..' weight='..snapshot.weight..' lastWeight='..snapshot.lastWeight
      ..' reason='..snapshot.reason..' effectiveAngle='..snapshot.effective..' input='..snapshot.input
      ..' balance='..snapshot.balance..' lastBalance='..snapshot.lastBalance
      ..string.format(' offset=(%.4f,%.4f,%.4f) lastOffset=(%.4f,%.4f,%.4f)',snapshot.x,snapshot.y,snapshot.z,snapshot.lastX,snapshot.lastY,snapshot.lastZ)
      ..' errorMeters='..snapshot.error..' measurement='..snapshot.measurement..' scriptError='..tostring(lastError))
  end,
}
