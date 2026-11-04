"""Build EDW3.7 v6 using original ADS helpers and bounded camera-relative translation.

Inputs are untouched WolvenKit JSON exports. This does not infer player frames from
an NPC rig and does not convert whole poses between LS/MS or capture float tracks.
"""
from pathlib import Path
import copy
import json

ROOT = Path(__file__).resolve().parent

def cn(value): return {'$type': 'CName', '$storage': 'string', '$value': value}
def bone(value): return {'$type': 'animTransformIndex', 'name': cn(value)}
def pose(node): return {'$type': 'animPoseLink', 'node': node}
def fl(node): return {'$type': 'animFloatLink', 'node': node}
def ref(node): return {'HandleRefId': node['HandleId']}
def clone(data):
    data = copy.deepcopy(data)
    data.pop('poseInfoLogger', None)
    return data

def index(tree):
    result = {}
    def visit(x):
        if isinstance(x, dict):
            if 'HandleId' in x:
                assert x['HandleId'] not in result, ('duplicate input handle', x['HandleId'])
                result[x['HandleId']] = x['Data']
            for v in x.values(): visit(v)
        elif isinstance(x, list):
            for v in x: visit(v)
    visit(tree)
    return result

def order_handle_definitions(doc):
    # WolvenKit JSON resolves references as it reads. A newly shared float input
    # must be defined at its first use, even if that use precedes its owning gate.
    definitions = index(doc)
    seen = set()
    def visit(x):
        if isinstance(x, dict):
            if 'HandleId' in x or 'HandleRefId' in x:
                key = x.get('HandleId', x.get('HandleRefId'))
                if key in seen:
                    return {'HandleRefId': key}
                seen.add(key)
                return {'HandleId': key, 'Data': visit(definitions[key])}
            return {k: visit(v) for k, v in x.items()}
        if isinstance(x, list): return [visit(v) for v in x]
        return x
    return visit(doc)

class Builder:
    def __init__(self, doc):
        self.doc = doc
        self.old = index(doc)
        self.next_id = max(map(int, self.old)) + 1
        self.created = {}
        self.runtime = []
    def add(self, data):
        key = str(self.next_id)
        self.next_id += 1
        self.created[key] = data
        if data['$type'].startswith('animAnimNode_'):
            self.runtime.append(key)
        return {'HandleId': key, 'Data': data}
    def feature_float(self, name):
        return self.add({'$type': 'animAnimNode_FloatInput', 'id': 4294967295,
                         'debugInput': 0, 'group': cn('EDWRightCant'), 'name': cn(name)})
    def register(self, owner_id):
        root = self.doc['Data']['RootChunk']
        start = len(root['nodesToInit'])
        self.old[owner_id]['nodes'].extend({'HandleRefId': key} for key in self.runtime)
        root['nodesToInit'].extend({'HandleRefId': key} for key in self.runtime)
        feature = clone(root['animFeatures'][0])
        feature['className'], feature['name'] = cn('EDWAnimFeature_RightCant'), cn('EDWRightCant')
        feature['forceAllocate'], feature['debugEnabled'] = 1, 0
        root['animFeatures'].append(feature)
        return {key: start + i + 2 for i, key in enumerate(self.runtime)}
    def validate(self):
        definitions = index(self.doc)
        def visit(x):
            if isinstance(x, dict):
                if 'HandleRefId' in x:
                    assert x['HandleRefId'] in definitions, ('unresolved reference', x)
                for v in x.values(): visit(v)
            elif isinstance(x, list):
                for v in x: visit(v)
        visit(self.doc)
        assert set(self.runtime) <= set(definitions)

parent_doc = json.loads((ROOT / 'mixed-json/player_base.animgraph.json').read_text())
child_doc = json.loads((ROOT / 'json/player_dualwield.animgraph.json').read_text())
parent, child = Builder(parent_doc), Builder(child_doc)
b, d = parent.old, child.old

# Parent: camera/zero-offset/shoulder helpers replicate original ADS snap patterns.
# Camera's whole transform supplies the basis; TranslationOnly snapping keeps the
# shoulder helper orientation aligned with that basis rather than the arm frame.
# TranslateBone targets the zero helper, never the nonzero snapped shoulder:
# both additive and replacement translation semantics therefore preserve baseline.
original_input = b['1']['node']['node']
cam_name = 'edw_v6_camera_space'
offset_name = 'edw_v6_camera_offset'
shoulder_name = 'edw_v6_right_shoulder'
transform_tag = 'edw_v6_camera_translation'
extend = clone(d['1205'])
extend['inputLink'] = pose(original_input)
extend['transformInfos'] = [
    {'$type': 'animTransformInfo', 'name': cn(cam_name), 'parentName': cn('Root'),
     'referenceTransformLs': clone(d['1205']['transformInfos'][6]['referenceTransformLs'])},
    {'$type': 'animTransformInfo', 'name': cn(offset_name), 'parentName': cn(cam_name),
     'referenceTransformLs': clone(d['1205']['transformInfos'][1]['referenceTransformLs'])},
    {'$type': 'animTransformInfo', 'name': cn(shoulder_name), 'parentName': cn(offset_name),
     'referenceTransformLs': clone(d['1205']['transformInfos'][8]['referenceTransformLs'])},
]
extend['offsets'] = [clone(d['1205']['offsets'][i]) for i in (6, 1, 8)]
extend['offsetSpaceBones'] = [bone('None'), bone('None'), bone('None')]
extend['offsetToReferenceValues'] = [0, 0, 0]
extend['snapToReferenceValues'] = [0, 0, 0]
extend['snapMethods'] = ['WholeTransform', 'NoSnapping', 'TranslationOnly']
extend['snapTargetBones'] = [bone('Torso_fppCamera_Aim_JNT'), bone('None'), bone('RightShoulder')]
extend['tag'] = cn(transform_tag)
ext = parent.add(extend)

vector_inputs = [parent.feature_float('offset' + axis) for axis in 'XYZ']
compiled = parent.add({'$type': 'mathExprExpression', 'returnVarType': 2,
                       'tokenData': [2164293632, 2164293633, 2164293634, 2986344479],
                       'valuesData': []})
vector = clone(d['1220'])
vector['expressionString'] = 'Vec(x, y, z)'
vector['expressionData']['expression'] = compiled
vector['expressionData']['floatSockets'] = [
    {'$type': 'animAnimMathExpressionFloatSocket', 'expressionVarId': i,
     'inputFloatTrack': {'$type': 'animNamedTrackIndex', 'name': cn('None')},
     'link': fl(node)} for i, node in enumerate(vector_inputs)
]
vector['expressionData']['vectorSockets'] = []
vector['expressionData']['quaternionSockets'] = []
vec = parent.add(vector)
translation = clone(d['1211'])
translation['bone'], translation['inputNode'] = bone(offset_name), pose(ext)
translation['inputTranslation']['node'] = vec
translation['resetOnActivation'], translation['useIncrementalMode'] = 1, 0
trans = parent.add(translation)
copy_shoulder = clone(d['1144'])
entry = clone(d['1144']['entries'][2])
entry['sourceBone'], entry['transformToChange'] = bone(shoulder_name), bone('RightShoulder')
entry['setMethod'] = 'TranslationOnly'
copy_shoulder['entries'] = [entry]
copy_shoulder['inputLink'] = pose(trans)
copy_node = parent.add(copy_shoulder)
shrink = clone(d['1140'])
shrink['inputLink'], shrink['tag'] = pose(copy_node), cn(transform_tag)
shr = parent.add(shrink)
b['1']['node']['node'] = shr
parent_indices = parent.register('0')
extend['shrinkerNodeId'] = parent_indices[shr['HandleId']]
shrink['extenderNodeId'] = parent_indices[ext['HandleId']]

# Child: expand the existing, active long-gun ADS helper roll path. Its original
# A&!B expression remains intact; only A is enabled by the external context weight.
weight = child.feature_float('weight')
old_wrapper = d['1216']['expressionData']['floatSockets'][0]['link']['node']
def comparator(first, true_node, true_value, false_node, false_value):
    node = clone(d['1223'])
    node['firstInputLink'], node['firstValue'] = fl(first), 0
    node['secondInputLink'], node['secondValue'] = fl(None), 0.5
    node['operation'] = 'AGCF_Greater'
    node['trueInputLink'], node['trueValue'] = fl(true_node), true_value
    node['falseInputLink'], node['falseValue'] = fl(false_node), false_value
    return child.add(node)
activation = comparator(weight, None, 1, old_wrapper, 0)
d['1216']['expressionData']['floatSockets'][0]['link']['node'] = activation

angle = child.feature_float('angle')
negative = clone(d['1621'])
negative_expr = child.add(clone(d['1622']))
negative['expressionData']['expression'] = negative_expr
negative['expressionData']['floatSockets'][0]['link']['node'] = angle
negative['expressionData']['floatSockets'][0]['inputFloatTrack']['name'] = cn('None')
neg = child.add(negative)
old_angle = d['1214']['angleNode']['node']
angle_selection = comparator(ref(weight), neg, 0, old_angle, -45)
d['1214']['angleNode']['node'] = angle_selection
# The former direct1148 input skipped the original Rasetsu translation1211.
# Reusing1147 preserves it when applying this original helper roll to other guns.
d['1214']['inputNode']['node'] = {'HandleRefId': '1147'}
child.register('28')

parent.doc = parent_doc = order_handle_definitions(parent_doc)
child.doc = child_doc = order_handle_definitions(child_doc)
parent.validate()
child.validate()
output_dir = ROOT / 'patch-json'
output_dir.mkdir(exist_ok=True)
(output_dir / 'player_base.animgraph.json').write_text(json.dumps(parent_doc, indent=2))
(output_dir / 'player_dualwield.animgraph.json').write_text(json.dumps(child_doc, indent=2))
design = {
    'revision': 6,
    'parent': {
        'newHandles': list(parent.created), 'newRuntimeInitializers': parent.runtime,
        'owner': '0', 'originalInput': original_input['HandleId'],
        'finalOutputInput': shr['HandleId'], 'cameraHelper': cam_name, 'offsetHelper': offset_name,
        'shoulderHelper': shoulder_name, 'transformTag': transform_tag,
        'extender': ext['HandleId'], 'shrinker': shr['HandleId'],
        'shrinkerNodeId': extend['shrinkerNodeId'], 'extenderNodeId': shrink['extenderNodeId'],
        'vectorInputs': [v['HandleId'] for v in vector_inputs], 'vectorNode': vec['HandleId'],
        'translateNode': trans['HandleId'], 'shoulderCopy': copy_node['HandleId'],
        'onlyRealBoneModified': 'RightShoulder',
        'zeroOffsetBehavior': 'Translate identity zero helper; snapped shoulder child retains its baseline under both additive and replacement translation semantics',
        'zeroOffsetProof': 'C * T(0) * C^-1 * P = P; offset helper is identity and shoulder snapshot is stored on its separate child',
    },
    'child': {
        'newHandles': list(child.created), 'newRuntimeInitializers': child.runtime,
        'owner': '28', 'weightInput': weight['HandleId'], 'angleInput': angle['HandleId'],
        'activationComparator': activation['HandleId'], 'negativeAngle': neg['HandleId'],
        'angleComparator': angle_selection['HandleId'],
        'modifiedOriginalNodes': ['1216', '1214'],
        'originalWrapperHandle': old_wrapper['HandleId'], 'originalAngleHandle': old_angle['HandleId'],
        'preservedCameraGate': 'Original1216 A&!B; procedural_ironsight_camera B remains unchanged',
        'preservedRasetsuInput': '1214 input1147 retains original1211 translation',
    },
    'scope': 'Native feature enables only eligible two-ranged-weapon aim/test; offsets zero while inactive',
    'removed': 'V3 final local-Hand rotation and V4 absolute mirror/LS-MS/float-track capture',
    'limitation': 'Original node patterns reused; native game evaluation and balanced offset values still require gameplay verification',
}
(ROOT / 'v6-design.json').write_text(json.dumps(design, indent=2) + '\n')
print(f"V6 parent: {len(parent.created)} new handles, {len(parent.runtime)} runtime initializers")
print(f"V6 child: {len(child.created)} new handles, {len(child.runtime)} runtime initializers")
print('All owned handle IDs are unique and references resolve in both generated graphs.')
