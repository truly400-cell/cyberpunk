"""Actual pure Lua controller with simulated, measured post-correction errors."""
from pathlib import Path
import math
import unittest
from lupa import LuaRuntime

SOURCE = Path(__file__).parent / 'package/bin/x64/plugins/cyber_engine_tweaks/mods/EDWRightCant/alignment.lua'


def length(v):
    return math.hypot(*v)


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def vec(v):
    return tuple(v[k] for k in ('x', 'y', 'z'))


class AlignmentTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.a = self.lua.execute(SOURCE.read_text())
        self.state = self.a.new()

    def step(self, error):
        return self.a.step(self.state, self.lua.table_from(dict(zip(('x', 'y', 'z'), error))))

    def simulate(self, target, response=lambda v: v):
        offset = (0, 0, 0)
        records = []
        for _ in range(25):
            error = sub(target, response(offset))
            output, status = self.step(error)
            next_offset = vec(output)
            records.append((error, offset, next_offset, status))
            if status != 'no_response':
                self.assertLessEqual(length(sub(next_offset, offset)), .035 + 1e-12)
            self.assertLessEqual(abs(next_offset[0]), .25 + 1e-12)
            self.assertLessEqual(abs(next_offset[1]), .18 + 1e-12)
            self.assertLessEqual(abs(next_offset[2]), .20 + 1e-12)
            self.assertLessEqual(length(next_offset), .30 + 1e-12)
            offset = next_offset
            if status != 'calibrating':
                return offset, status, records
        self.fail('controller did not freeze by twenty samples')

    def test_identity_converges_without_overshoot_or_large_steps(self):
        target = (.12, -.08, .10)
        offset, status, records = self.simulate(target)
        self.assertEqual(status, 'aligned')
        self.assertLessEqual(length(sub(target, offset)), .01)
        for error, old, new, _ in records:
            new_error = sub(target, new)
            self.assertLessEqual(length(new_error), length(error) + 1e-12)
            self.assertTrue(all(a * b >= -1e-12 for a, b in zip(target, new_error)))

    def test_camera_basis_rotations_plus_minus_twenty_degrees(self):
        for axis in ('yaw', 'pitch'):
            for degrees in (-20, 20):
                with self.subTest(axis=axis, degrees=degrees):
                    self.state = self.a.new()
                    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
                    if axis == 'yaw':
                        response = lambda v: (c*v[0] - s*v[1], s*v[0] + c*v[1], v[2])
                    else:
                        response = lambda v: (v[0], c*v[1] - s*v[2], s*v[1] + c*v[2])
                    target = (.10, .045, -.06)
                    offset, status, records = self.simulate(target, response)
                    self.assertEqual(status, 'aligned')
                    self.assertLessEqual(length(sub(target, response(offset))), .01)

    def test_depth_and_height_are_corrected(self):
        target = (0, .12, -.14)
        offset, status, _ = self.simulate(target)
        self.assertEqual(status, 'aligned')
        self.assertEqual(offset[0], 0)
        self.assertLessEqual(length(sub(target, offset)), .01)

    def test_limits_and_twenty_sample_budget(self):
        _, status, records = self.simulate((.6, .6, -.6))
        self.assertEqual(status, 'limited')
        self.assertEqual(len(records), 20)
        self.assertTrue(self.state.hitLimit)

    def test_constant_error_fails_safe_after_eight_samples(self):
        for _ in range(7):
            output, status = self.step((.12, 0, .02))
            self.assertEqual(status, 'calibrating')
        output, status = self.step((.12, 0, .02))
        self.assertEqual(status, 'no_response')
        self.assertEqual(vec(output), (0, 0, 0))
        self.assertTrue(self.state.frozen)
        output, status = self.step((0, 0, 0))
        self.assertEqual(status, 'no_response')

    def test_reversed_response_resets_zero(self):
        output, status, records = self.simulate((.10, 0, 0), lambda v: tuple(-x for x in v))
        self.assertEqual(status, 'no_response')
        self.assertEqual(output, (0, 0, 0))
        self.assertLessEqual(len(records), 8)

    def test_aligned_result_frozen_and_reset_releases_it(self):
        offset, status, _ = self.simulate((.12, -.04, .04))
        output, status = self.step((20, -15, 12))
        self.assertEqual(status, 'aligned')
        self.assertEqual(vec(output), offset)
        output.x = 100 # returned copies cannot mutate internal offset
        self.assertEqual(vec(self.state.offset), offset)
        zero, status = self.a.reset(self.state)
        self.assertEqual((vec(zero), status), ((0, 0, 0), 'calibrating'))
        self.assertFalse(self.state.frozen)
        output, status = self.step((.04, 0, 0))
        self.assertEqual(status, 'calibrating')
        self.assertGreater(output.x, 0)

    def test_invalid_measurements_always_return_zero(self):
        cases = [None, {}, {'x': 0, 'y': 0}, {'x': math.nan, 'y': 0, 'z': 0},
                 {'x': 0, 'y': math.inf, 'z': 0}, {'x': 0, 'y': 0, 'z': -math.inf},
                 {'x': '0.1', 'y': 0, 'z': 0}, {'x': 1.5e308, 'y': 1.5e308, 'z': 1.5e308}]
        for bad in cases:
            with self.subTest(error=bad):
                self.state = self.a.new()
                self.step((.1, 0, 0))
                table = self.lua.table_from(bad) if isinstance(bad, dict) else bad
                output, status = self.a.step(self.state, table)
                self.assertEqual((vec(output), status), ((0, 0, 0), 'invalid'))
        self.state = self.a.new()
        self.simulate((.1, 0, 0))
        output, status = self.a.step(self.state, None)
        self.assertEqual((vec(output), status), ((0, 0, 0), 'invalid'))

    def test_uppercase_measurement_and_huge_finite_step_are_bounded(self):
        output, status = self.a.step(self.state, self.lua.table_from({'X': .1, 'Y': 0, 'Z': 0}))
        self.assertEqual(status, 'calibrating')
        self.assertAlmostEqual(output.x, .035)
        self.state = self.a.new()
        output, status = self.step((1e300, -1e300, 1e300))
        self.assertEqual(status, 'calibrating')
        self.assertTrue(all(math.isfinite(x) for x in vec(output)))
        self.assertLessEqual(length(vec(output)), .035 + 1e-12)


if __name__ == '__main__':
    unittest.main(verbosity=2)
