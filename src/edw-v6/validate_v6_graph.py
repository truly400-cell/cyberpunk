"""Validate V6 CR2W roundtrips against the untouched EDW3.7 graphs.

This checks serialized structure, links, registration, deliberate edits, and
packed bytes. It does not emulate the game's pose evaluator or prove visuals.
Run only after both v6-roundtrip-json and v6-reextracted files exist.
"""
from collections import Counter
import copy
import json
import math
from pathlib import Path
import random

R = Path(__file__).resolve().parent


def cname(value):
    return value['$value'] if isinstance(value, dict) and value.get('$type') == 'CName' else value


def flatten(doc):
    definitions = {}

    def visit(value):
        if isinstance(value, dict):
            if 'HandleId' in value:
                key = value['HandleId']
                assert key not in definitions, ('duplicate_handle', key)
                definitions[key] = None
                definitions[key] = visit(value['Data'])
                return {'@ref': key}
            if 'HandleRefId' in value:
                return {'@ref': value['HandleRefId']}
            return {key: visit(item) for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item) for item in value]
        return value

    root = visit(doc['Data']['RootChunk'])

    def check_references(value):
        if isinstance(value, dict):
            if '@ref' in value:
                assert value['@ref'] in definitions, ('unresolved_reference', value)
            else:
                for item in value.values():
                    check_references(item)
        elif isinstance(value, list):
            for item in value:
                check_references(item)

    check_references(root)
    for value in definitions.values():
        check_references(value)
    return root, definitions


def canonical(root, definitions):
    """Normalize handle numbering without losing aliasing or unreachable owners."""
    seen, output = {}, []

    def visit(value):
        if isinstance(value, dict):
            if '@ref' in value:
                key = value['@ref']
                if key not in seen:
                    seen[key] = len(output)
                    output.append(None)
                    output[seen[key]] = visit(definitions[key])
                return {'@ref': seen[key]}
            return {key: visit(item) for key, item in sorted(value.items())}
        if isinstance(value, list):
            return [visit(item) for item in value]
        return value

    normalized_root = visit(root)
    return normalized_root, output


def link_id(value):
    assert isinstance(value, dict) and '@ref' in value, ('expected_non_null_link', value)
    return value['@ref']


def identity_transform(value):
    rotation = value['Rotation']
    assert [rotation[key] for key in ('i', 'j', 'k', 'r')] == [0, 0, 0, 1]
    assert [value['Scale'][key] for key in ('X', 'Y', 'Z')] == [1, 1, 1]
    assert [value['Translation'][key] for key in ('X', 'Y', 'Z')] == [0, 0, 0]


def validate_zero_offset_math():
    """Check the three-helper geometry for either replace/add translation.

    This is a numerical design regression, not a native evaluator simulation.
    Camera C, identity-local offset T(d), and snapped shoulder C^-1*P give
    C*T(d)*C^-1*P = P + R_camera*d. T(0) preserves the existing shoulder.
    """
    def product(left, right):
        return [[sum(left[i][k] * right[k][j] for k in range(3))
                 for j in range(3)] for i in range(3)]

    def vector(matrix, value):
        return [sum(matrix[i][j] * value[j] for j in range(3)) for i in range(3)]

    def add(left, right):
        return [a + b for a, b in zip(left, right)]

    def subtract(left, right):
        return [a - b for a, b in zip(left, right)]

    def close(actual, expected):
        assert all(math.isclose(a, b, rel_tol=0, abs_tol=1e-10)
                   for a, b in zip(actual, expected)), (actual, expected)

    def rotation(x, y, z):
        cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
        rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
        ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
        rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
        return product(rz, product(ry, rx))

    rng = random.Random(20261104)
    cases = [(rotation(0, 0, math.pi / 2), [3, -4, 2], [3.4, -3.7, 1.6], [0.1, 0, 0])]
    for _ in range(128):
        basis = rotation(*(rng.uniform(-math.pi, math.pi) for _ in range(3)))
        origin = [rng.uniform(-10, 10) for _ in range(3)]
        shoulder = [rng.uniform(-10, 10) for _ in range(3)]
        delta = [rng.uniform(-0.15, 0.15) for _ in range(3)]
        cases.append((basis, origin, shoulder, delta))
    for basis, origin, shoulder, delta in cases:
        inverse = [list(row) for row in zip(*basis)]
        shoulder_local = vector(inverse, subtract(shoulder, origin))
        # The translated helper has identity rotation and zero local position.
        for mode in ('replace', 'add'):
            def evaluate(request):
                offset_local = list(request) if mode == 'replace' else add([0, 0, 0], request)
                offset_world = add(origin, vector(basis, offset_local))
                return add(offset_world, vector(basis, shoulder_local))
            close(evaluate([0, 0, 0]), shoulder)
            close(evaluate(delta), add(shoulder, vector(basis, delta)))
            close(subtract(evaluate(delta), evaluate([0, 0, 0])), vector(basis, delta))
    close(vector(cases[0][0], cases[0][3]), [0, 0.1, 0])
    return {'cameraPoseCases': len(cases), 'randomCameraPoseCases': 128,
            'translationModes': ['replace', 'add'], 'zeroOffsetBaselinePreserved': True,
            'cameraBasisDeltaMappingVerified': True, 'nativeEvaluationProven': False}


class Graph:
    def __init__(self, original_path, roundtrip_path, design):
        self.original_doc = json.loads(original_path.read_text())
        self.doc = json.loads(roundtrip_path.read_text())
        self.original, self.old = flatten(self.original_doc)
        self.root, self.nodes = flatten(self.doc)
        for key, value in self.original_doc['Data'].items():
            if key != 'RootChunk':
                assert self.doc['Data'][key] == value, ('changed_data_metadata', key)
        count = len(self.original['nodesToInit'])
        assert len(self.root['nodesToInit']) == count + len(design['newRuntimeInitializers'])
        old_ids = [link_id(value) for value in self.original['nodesToInit']]
        current_ids = [link_id(value) for value in self.root['nodesToInit']]
        assert len(current_ids) == len(set(current_ids)), 'duplicate_initializer'
        self.mapping = dict(zip(old_ids, current_ids[:count]))
        self.mapping[link_id(self.original['rootNode'])] = link_id(self.root['rootNode'])
        for before, after in self.mapping.items():
            assert self.old[before]['$type'] == self.nodes[after]['$type'], ('changed_original_type', before)
        self.new_ids = current_ids[count:]
        self.mapping.update(zip(design['newRuntimeInitializers'], self.new_ids))
        assert len(self.nodes) - len(self.old) == len(design['newHandles']), 'unexpected_handle_count'
        self.design = design
        self.original_init_count = count
        self.restore_root = copy.deepcopy(self.root)
        self.restore_nodes = copy.deepcopy(self.nodes)
        self.restore_root['nodesToInit'] = self.restore_root['nodesToInit'][:count]
        extra_feature = [value for value in self.root['animFeatures']
                         if cname(value['className']) == 'EDWAnimFeature_RightCant']
        assert len(extra_feature) == 1
        assert cname(extra_feature[0]['name']) == 'EDWRightCant'
        assert extra_feature[0]['forceAllocate'] == 1
        self.restore_root['animFeatures'] = [value for value in self.root['animFeatures']
                                           if cname(value['className']) != 'EDWAnimFeature_RightCant']
        owner_id = self.mapping[design['owner']]
        original_owner = self.old[design['owner']]
        owner = self.nodes[owner_id]
        added_owned = owner['nodes'][len(original_owner['nodes']):]
        assert added_owned == [{'@ref': key} for key in self.new_ids], 'owner_initializer_order_mismatch'
        self.restore_nodes[owner_id]['nodes'] = owner['nodes'][:len(original_owner['nodes'])]
        assert all(self.nodes[key]['$type'].startswith('animAnimNode_') for key in self.new_ids)

    def mapped(self, original_or_build_id):
        return self.mapping[original_or_build_id]

    def get(self, original_or_build_id):
        return self.nodes[self.mapped(original_or_build_id)]

    def feature_input(self, node, name):
        assert node['$type'] == 'animAnimNode_FloatInput'
        assert cname(node['group']) == 'EDWRightCant' and cname(node['name']) == name

    def finish_preservation(self):
        assert canonical(self.original, self.old) == canonical(self.restore_root, self.restore_nodes), \
            'original_graph_fields_or_links_changed_outside_deliberate_edits'


def validate_parent(graph):
    d = graph.design
    fresh = [graph.nodes[key] for key in graph.new_ids]
    assert Counter(value['$type'] for value in fresh) == Counter({
        'animAnimNode_StackTransformsExtender': 1, 'animAnimNode_StackTransformsShrinker': 1,
        'animAnimNode_FloatInput': 3, 'animAnimNode_MathExpressionVector': 1,
        'animAnimNode_TranslateBone': 1, 'animAnimNode_SetBoneTransform': 1,
    }), 'unexpected_parent_runtime_nodes'
    ext, shrink = graph.get(d['extender']), graph.get(d['shrinker'])
    assert cname(ext['tag']) == cname(shrink['tag']) == 'edw_v6_camera_translation'
    init_ids = [link_id(value) for value in graph.root['nodesToInit']]
    assert ext['shrinkerNodeId'] == init_ids.index(graph.mapped(d['shrinker'])) + 2
    assert shrink['extenderNodeId'] == init_ids.index(graph.mapped(d['extender'])) + 2
    infos = ext['transformInfos']
    assert len(infos) == 3
    assert [(cname(value['name']), cname(value['parentName'])) for value in infos] == [
        ('edw_v6_camera_space', 'Root'), ('edw_v6_camera_offset', 'edw_v6_camera_space'),
        ('edw_v6_right_shoulder', 'edw_v6_camera_offset')]
    assert d['offsetHelper'] == 'edw_v6_camera_offset'
    assert ext['snapMethods'] == ['WholeTransform', 'NoSnapping', 'TranslationOnly']
    assert [cname(value['name']) for value in ext['snapTargetBones']] == ['Torso_fppCamera_Aim_JNT', 'None', 'RightShoulder']
    assert ext['offsetToReferenceValues'] == ext['snapToReferenceValues'] == [0, 0, 0]
    assert [cname(value['name']) for value in ext['offsetSpaceBones']] == ['None', 'None', 'None']
    assert len(ext['offsets']) == 3
    for value in ext['offsets']:
        identity_transform(value)
    for value in infos:
        identity_transform(value['referenceTransformLs'])
    vector = graph.get(d['vectorNode'])
    assert vector['expressionString'] == 'Vec(x, y, z)'
    expression = graph.nodes[link_id(vector['expressionData']['expression'])]
    assert expression['returnVarType'] == 2
    assert expression['tokenData'] == [2164293632, 2164293633, 2164293634, 2986344479]
    assert expression['valuesData'] == []
    sockets = vector['expressionData']['floatSockets']
    assert len(sockets) == 3
    for index, (socket, name) in enumerate(zip(sockets, ('offsetX', 'offsetY', 'offsetZ'))):
        assert socket['expressionVarId'] == index
        assert cname(socket['inputFloatTrack']['name']) == 'None'
        linked = link_id(socket['link']['node'])
        assert linked == graph.mapped(d['vectorInputs'][index])
        graph.feature_input(graph.nodes[linked], name)
    assert vector['expressionData']['quaternionSockets'] == vector['expressionData']['vectorSockets'] == []
    translate = graph.get(d['translateNode'])
    assert cname(translate['bone']['name']) == d['offsetHelper']
    assert cname(translate['bone']['name']) != d['shoulderHelper']
    assert translate['resetOnActivation'] == 1 and translate['useIncrementalMode'] == 0
    assert [translate['biasValue'][key] for key in ('X', 'Y', 'Z')] == [0, 0, 0]
    assert [translate['scale'][key] for key in ('X', 'Y', 'Z')] == [1, 1, 1]
    assert link_id(translate['inputTranslation']['node']) == graph.mapped(d['vectorNode'])
    assert link_id(translate['inputNode']['node']) == graph.mapped(d['extender'])
    copy_node = graph.get(d['shoulderCopy'])
    assert len(copy_node['entries']) == 1
    entry = copy_node['entries'][0]
    assert cname(entry['sourceBone']['name']) == d['shoulderHelper']
    assert cname(entry['transformToChange']['name']) == 'RightShoulder'
    assert entry['setMethod'] == 'TranslationOnly'
    assert cname(entry['offsetSpaceBone']['name']) == 'None'
    assert entry['snapToReference'] == entry['offsetToReference'] == 0
    identity_transform(entry['offset'])
    assert link_id(copy_node['inputLink']['node']) == graph.mapped(d['translateNode'])
    assert link_id(shrink['inputLink']['node']) == graph.mapped(d['shoulderCopy'])
    assert link_id(ext['inputLink']['node']) == graph.mapped(d['originalInput'])
    assert link_id(graph.get('1')['node']['node']) == graph.mapped(d['finalOutputInput']) == graph.mapped(d['shrinker'])
    graph.restore_nodes[graph.mapped('1')]['node']['node'] = {'@ref': graph.mapped(d['originalInput'])}
    graph.finish_preservation()


def validate_child(graph):
    d = graph.design
    fresh = [graph.nodes[key] for key in graph.new_ids]
    assert Counter(value['$type'] for value in fresh) == Counter({
        'animAnimNode_FloatInput': 2, 'animAnimNode_FloatComparator': 2,
        'animAnimNode_MathExpressionFloat': 1,
    }), 'unexpected_child_runtime_nodes'
    weight_id = graph.mapped(d['weightInput'])
    graph.feature_input(graph.nodes[weight_id], 'weight')
    graph.feature_input(graph.get(d['angleInput']), 'angle')

    def gate(node):
        assert node['$type'] == 'animAnimNode_FloatComparator'
        assert node['operation'] == 'AGCF_Greater'
        assert link_id(node['firstInputLink']['node']) == weight_id
        assert node['secondInputLink']['node'] is None and node['secondValue'] == 0.5

    activation = graph.get(d['activationComparator'])
    gate(activation)
    assert activation['trueInputLink']['node'] is None and activation['trueValue'] == 1
    assert link_id(activation['falseInputLink']['node']) == graph.mapped('1218')
    a_socket = graph.get('1216')['expressionData']['floatSockets'][0]
    assert link_id(a_socket['link']['node']) == graph.mapped(d['activationComparator'])
    angle_gate = graph.get(d['angleComparator'])
    gate(angle_gate)
    assert link_id(angle_gate['falseInputLink']['node']) == graph.mapped('1215')
    assert graph.get('1215')['value'] == -45
    assert link_id(angle_gate['trueInputLink']['node']) == graph.mapped(d['negativeAngle'])
    negative = graph.get(d['negativeAngle'])
    expression = graph.nodes[link_id(negative['expressionData']['expression'])]
    # Negation comes byte-for-byte from the existing source expression1622.
    assert expression == graph.old['1622']
    assert expression['tokenData'] == [2164293632, 16777216, 2432696344, 2701131779]
    assert expression['valuesData'] == [1]
    sockets = negative['expressionData']['floatSockets']
    assert len(sockets) == 1 and sockets[0]['expressionVarId'] == 0
    assert cname(sockets[0]['inputFloatTrack']['name']) == 'None'
    assert link_id(sockets[0]['link']['node']) == graph.mapped(d['angleInput'])
    assert link_id(graph.get('1214')['angleNode']['node']) == graph.mapped(d['angleComparator'])
    assert link_id(graph.get('1214')['inputNode']['node']) == graph.mapped('1147')
    assert graph.get('1214')['axis'] == 'Y_Axis'
    assert cname(graph.get('1214')['bone']['name']) == 'procedural_ironsight_sway'
    assert graph.get('1214')['inModelSpace'] == 0
    # Restore exactly the three declared original-node links.
    restored_a = graph.restore_nodes[graph.mapped('1216')]['expressionData']['floatSockets'][0]
    restored_a['link']['node'] = {'@ref': graph.mapped('1218')}
    graph.restore_nodes[graph.mapped('1214')]['angleNode']['node'] = {'@ref': graph.mapped('1215')}
    graph.restore_nodes[graph.mapped('1214')]['inputNode']['node'] = {'@ref': graph.mapped('1148')}
    graph.finish_preservation()


def main():
    design = json.loads((R / 'v6-design.json').read_text())
    assert design['revision'] == 6
    parent = Graph(R / 'mixed-json/player_base.animgraph.json',
                   R / 'v6-roundtrip-json/player_base.animgraph.json', design['parent'])
    child = Graph(R / 'json/player_dualwield.animgraph.json',
                  R / 'v6-roundtrip-json/player_dualwield.animgraph.json', design['child'])
    validate_parent(parent)
    validate_child(child)
    geometry_checks = validate_zero_offset_math()
    for name in ('player_base.animgraph', 'player_dualwield.animgraph'):
        assert (R / 'v6-reextracted/base/gameplay/anim_graphs' / name).read_bytes() == \
               (R / 'v6-resources/base/gameplay/anim_graphs' / name).read_bytes(), ('reextract_mismatch', name)
    report = {
        'revision': 6,
        'allHandleDefinitionsUniqueAndReferencesResolved': True,
        'parentNewRuntimeNodesRegisteredInInitAndOwner': len(parent.new_ids),
        'childNewRuntimeNodesRegisteredInInitAndOwner': len(child.new_ids),
        'originalParentFieldsAndLinksPreservedExceptDeclaredFinalInsertion': True,
        'originalChildFieldsAndLinksPreservedExceptDeclaredThreeLinkEdits': True,
        'virtualTransformCount': 3,
        'virtualTransformPairInitIndicesVerifiedAfterRoundtrip': True,
        'cameraWholeTransformAndShoulderTranslationOnlySnapsVerified': True,
        'translationTargetsSeparateIdentityLocalOffsetHelper': True,
        'zeroOffsetAndCameraBasisGeometry': geometry_checks,
        'vectorSocketsUseThreeNonNullFeatureInputLinks': True,
        'onlyRealBoneModifiedByAddedParentNodes': 'RightShoulder translation only',
        'addedHandRotations': 0,
        'addedLsMsConversions': 0,
        'addedAbsoluteSetBonePositionNodes': 0,
        'addedFloatTrackCaptures': 0,
        'childOriginalCameraExclusionAndRasetsuSwitchPreserved': True,
        'childInactiveWrapperAndMinus45AnglePreserved': True,
        'bothPackedResourcesReextractBytesIdentical': True,
        'nativeScriptsCompiledInGame': False,
        'gameVisualTested': False,
        'positionAlignmentOrExitCrashEliminationProven': False,
    }
    (R / 'v6-graph-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
