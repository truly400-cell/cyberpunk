# EDW3.7 v6 source and checks

V6 uses the original active `procedural_ironsight_sway` Y-axis cant path and a bounded camera-relative right-shoulder translation. The controller measures actual weapon entity origins, settles the ADS pose, corrects at most20samples, then freezes. No-response/divergence/invalid data releases the correction to zero. This does not establish actual game visual success.

The parent helper hierarchy is `Camera → zero Offset → snapped Shoulder`. Translation targets the separate zero-local Offset helper, so the saved Shoulder baseline is preserved whether the native translation operation adds or replaces local translation. The graph validator checks129camera poses under both hypotheses; this geometry test does not run the native pose evaluator.

The runtime sources are under `package/`. The installable ZIP also contains the built archive and instructions. Original Expanded Dual Wielding3.7 must remain installed; earlier cant patches must be disabled.

## Lua tests

Python3 with `lupa` is required. Run from this directory:

```sh
python test_cet_settings.py
python test_lifecycle_v4.py
python test_measurement_v6.py
python test_alignment_v6.py
```

The lifecycle filename is retained from the first lifecycle-fix revision; its fixtures now exercise actual V6 modules, schema6 settings, convergence/freeze/recalibration and zero native access after detach/shutdown. The tests use simulated native responses. They cannot prove that FPP graph movement affects weapon entity world origins in the actual game.

## Graph build

Use official WolvenKit8.18.0 ConsoleLinux and .NET8. Extract the original `player_base.animgraph` from EDW3.7 `edw_mixed_pose_004.archive` and `player_dualwield.animgraph` from `edw_right_pistol_reload_002.archive`. Serialize those untouched resources into these paths relative to this directory:

```text
mixed-json/player_base.animgraph.json
json/player_dualwield.animgraph.json
```

Run `python build_v6_graph.py`. It writes two JSONs under `patch-json/` and `v6-design.json`. Handle definitions are emitted at their first use because WolvenKit's JSON reader does not resolve forward references. Original initializer ordering is preserved; new entries are appended. All runtime nodes are registered in both initialization and owner arrays.

Deserialize both JSONs into `v6-resources/base/gameplay/anim_graphs/`, pack that directory tree, reextract into `v6-reextracted/`, and serialize the two reextracted resources into `v6-roundtrip-json/`. Run `python validate_v6_graph.py` to compare packed bytes, link/initializer registration and all original graph fields after restoring the deliberate edits. The builder and validator require the original graphs and do not include original game/mod source data here.

## API sources and validation limits

Camera and entity API names were checked against [NativeDB](https://github.com/rayshader/cp2077-nativedb). Mutable Transform and out-parameter calling conventions were checked in [Cyber Engine Tweaks](https://github.com/maximegmd/CyberEngineTweaks). V6 reads `CameraSystem.GetActiveCameraRight/Forward/Up`, `GetActiveCameraWorldTransform`, `Transform.GetPosition` and `Entity.GetWorldPosition`; it does not assume unverified WorldPosition convenience methods.

No player, weapon or camera userdata is retained between updates. onShutdown is pure Lua cleanup, and OnDetach fences updates beforehand. Original crash attribution and actual crash elimination remain unproven. Windows game execution, native script compilation, actual FPP pose/weapon-origin response and final alignment have not been validated in this cloud environment.
