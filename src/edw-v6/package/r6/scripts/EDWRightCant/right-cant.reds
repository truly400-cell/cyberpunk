// EDW3.7 v6: native ADS helper cant and bounded camera-relative shoulder offsets.
public class EDWAnimFeature_RightCant extends AnimFeature {
  public let angle: Float;
  public let weight: Float;
  public let offsetX: Float;
  public let offsetY: Float;
  public let offsetZ: Float;
}

@addField(PlayerPuppet)
private let edwRightCantInitialized: Bool;
@addField(PlayerPuppet)
private let edwRightCantLastAngle: Float;
@addField(PlayerPuppet)
private let edwRightCantLastReason: String;
@addField(PlayerPuppet)
private let edwRightCantInputRegistered: Bool;
@addField(PlayerPuppet)
private let edwRightCantAimInput: Float;
@addField(PlayerPuppet)
private let edwRightCantLastAimAngle: Float;
@addField(PlayerPuppet)
private let edwRightCantTestUntil: Float;
@addField(PlayerPuppet)
private let edwRightCantLastWeight: Float;
@addField(PlayerPuppet)
private let edwRightCantLastAimWeight: Float;

@addField(PlayerPuppet)
private let edwRightCantLastX: Float;
@addField(PlayerPuppet)
private let edwRightCantLastY: Float;
@addField(PlayerPuppet)
private let edwRightCantLastZ: Float;

@wrapMethod(PlayerPuppet)
protected cb func OnAction(action: ListenerAction, consumer: ListenerActionConsumer) -> Bool {
  if Equals(ListenerAction.GetName(action), n"CameraAim") {
    this.edwRightCantAimInput = ClampF(ListenerAction.GetValue(action), 0.0, 1.0);
  }
  wrappedMethod(action, consumer);
}

// This is a pose add-on, independent of EDW's optional independent-input switch.
// EDWInput.PoseContext requires edwEnabled, which is false in the default controls.
@addMethod(PlayerPuppet)
private final func EDWRightCantContextReason() -> String {
  if !this.IsControlledByLocalPeer() { return "not_local_player"; }
  let ui = GameInstance.GetBlackboardSystem(this.GetGame()).Get(GetAllBlackboardDefs().UI_System);
  if ui.GetBool(GetAllBlackboardDefs().UI_System.IsInMenu) { return "menu"; }
  let bb = GameInstance.GetBlackboardSystem(this.GetGame()).GetLocalInstanced(this.GetEntityID(), GetAllBlackboardDefs().PlayerStateMachine);
  if bb.GetInt(GetAllBlackboardDefs().PlayerStateMachine.Vehicle) != 0 { return "vehicle"; }
  if bb.GetInt(GetAllBlackboardDefs().PlayerStateMachine.SceneTier) > 2 { return "scene"; }
  if bb.GetInt(GetAllBlackboardDefs().PlayerStateMachine.Vitals) != 0 { return "not_alive"; }
  if bb.GetInt(GetAllBlackboardDefs().PlayerStateMachine.RightWeapon) == EnumInt(gamePSMRangedWeaponStates.Reload)
    || bb.GetInt(GetAllBlackboardDefs().PlayerStateMachine.UpperBody) == EnumInt(gamePSMUpperBodyStates.Reload)
    || bb.GetInt(GetAllBlackboardDefs().PlayerStateMachine.UpperBody) == EnumInt(gamePSMUpperBodyStates.SwitchItems) {
    return "reload_or_switch";
  }
  let right = GameObject.GetRightActiveWeapon(this);
  let left = GameObject.GetLeftActiveWeapon(this);
  if !IsDefined(right) || !IsDefined(left) { return "two_weapons_required"; }
  if !WeaponObject.IsRanged(right.GetItemID()) || !WeaponObject.IsRanged(left.GetItemID()) {
    return "two_ranged_weapons_required";
  }
  if right.WeaponHasTag(n"Cyberware") || left.WeaponHasTag(n"Cyberware") { return "cyberware"; }
  let record = right.GetWeaponRecord();
  if !IsDefined(record) || !IsDefined(record.ItemType()) { return "missing_weapon_record"; }
  let weaponType = record.ItemType().Type();
  if Equals(weaponType, gamedataItemType.Wea_Handgun) || Equals(weaponType, gamedataItemType.Wea_Revolver) {
    return "pistol_pose_preserved";
  }
  return "active";
}

@addMethod(PlayerPuppet)
public final func EDWConfigureRightCant(requestedAngle: Float, enabled: Bool, offsetX: Float, offsetY: Float, offsetZ: Float) -> Void {
  if !this.edwRightCantInputRegistered {
    this.RegisterInputListener(this, n"CameraAim");
    this.edwRightCantInputRegistered = true;
  }
  let angle = 0.0;
  let weight = 0.0;
  let reason = this.EDWRightCantContextReason();
  if Equals(reason, "active") {
    let bb = GameInstance.GetBlackboardSystem(this.GetGame()).GetLocalInstanced(this.GetEntityID(), GetAllBlackboardDefs().PlayerStateMachine);
    let nativeAiming = bb.GetInt(GetAllBlackboardDefs().PlayerStateMachine.UpperBody) == 6;
    let now = EngineTime.ToFloat(GameInstance.GetSimTime(this.GetGame()));
    if this.edwRightCantAimInput > 0.1 || nativeAiming || now < this.edwRightCantTestUntil {
      if !enabled { reason = "disabled"; }
      else {
        angle = ClampF(45.0 + ClampF(requestedAngle, -20.0, 20.0), -60.0, 60.0);
        weight = 1.0;
        this.edwRightCantLastAimAngle = angle;
        this.edwRightCantLastAimWeight = weight;
        if now < this.edwRightCantTestUntil { reason = "test_pose"; }
      }
    } else { reason = "not_aiming"; }
  } else {
    this.edwRightCantAimInput = 0.0;
  }
  let x = 0.0;
  let y = 0.0;
  let z = 0.0;
  if weight > 0.0 {
    if offsetX == offsetX { x = ClampF(offsetX, -0.25, 0.25); }
    if offsetY == offsetY { y = ClampF(offsetY, -0.18, 0.18); }
    if offsetZ == offsetZ { z = ClampF(offsetZ, -0.20, 0.20); }
  }
  this.edwRightCantLastReason = reason;
  if !this.edwRightCantInitialized || this.edwRightCantLastAngle != angle || this.edwRightCantLastWeight != weight
    || this.edwRightCantLastX != x || this.edwRightCantLastY != y || this.edwRightCantLastZ != z {
    let feature = new EDWAnimFeature_RightCant();
    feature.angle = angle;
    feature.weight = weight;
    feature.offsetX = x;
    feature.offsetY = y;
    feature.offsetZ = z;
    AnimationControllerComponent.ApplyFeature(this, n"EDWRightCant", feature);
    this.edwRightCantLastAngle = angle;
    this.edwRightCantLastWeight = weight;
    this.edwRightCantLastX = x;
    this.edwRightCantLastY = y;
    this.edwRightCantLastZ = z;
    this.edwRightCantInitialized = true;
  }
}

@addMethod(PlayerPuppet)
public final func EDWGetRightCantAngle() -> Float {
  return this.edwRightCantLastAngle;
}

@addMethod(PlayerPuppet)
public final func EDWGetRightCantReason() -> String {
  return this.edwRightCantLastReason;
}

@addMethod(PlayerPuppet)
public final func EDWGetRightCantLastAimAngle() -> Float {
  return this.edwRightCantLastAimAngle;
}

@addMethod(PlayerPuppet)
public final func EDWGetRightCantInput() -> Float {
  return this.edwRightCantAimInput;
}

@addMethod(PlayerPuppet)
public final func EDWBeginRightCantTest() -> Void {
  this.edwRightCantTestUntil = EngineTime.ToFloat(GameInstance.GetSimTime(this.GetGame())) + 3.0;
}

@addMethod(PlayerPuppet)
public final func EDWGetRightCantWeight() -> Float {
  return this.edwRightCantLastWeight;
}

@addMethod(PlayerPuppet)
public final func EDWGetRightCantLastAimWeight() -> Float {
  return this.edwRightCantLastAimWeight;
}
