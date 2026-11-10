import math
import unittest
from bjt import BiasInput, solve_base_loop
from independent import solve_nodal, compare


class TestIndependent(unittest.TestCase):
    def defaults(self):
        return BiasInput(vcc_v=12, r1_ohm=47000, r2_ohm=10000,
                         rc_ohm=2200, re_ohm=470, beta=150, vbe_v=0.7)

    def test_nodal_agrees_with_base_loop_active(self):
        bias = self.defaults()
        base = solve_base_loop(bias)
        nodal = solve_nodal(bias)
        report = compare(base, nodal)
        self.assertTrue(report["agree"])
        self.assertLess(report["max_rel_diff"], 1e-9)

    def test_nodal_agrees_with_base_loop_cutoff(self):
        bias = self.defaults()
        bias.r2_ohm = 100
        base = solve_base_loop(bias)
        nodal = solve_nodal(bias)
        report = compare(base, nodal)
        self.assertTrue(report["agree"])
        self.assertEqual(base.region, "cutoff")

    def test_nodal_agrees_with_base_loop_saturation(self):
        bias = self.defaults()
        bias.rc_ohm = 100000
        base = solve_base_loop(bias)
        nodal = solve_nodal(bias)
        report = compare(base, nodal)
        self.assertTrue(report["agree"])
        self.assertEqual(base.region, "saturation")

    def test_result_exposes_only_solved_quantities(self):
        nodal = solve_nodal(self.defaults())
        for attr in ("vbb_v", "rb_ohm", "region", "in_active"):
            self.assertFalse(hasattr(nodal, attr), attr)

    def test_non_finite_result_disagrees(self):
        bias = self.defaults()
        base = solve_base_loop(bias)
        nodal = solve_nodal(bias)
        nodal.vce_v = float("nan")
        report = compare(base, nodal)
        self.assertFalse(report["agree"])

    def test_extreme_ratios_do_not_crash(self):
        # This fixture is cutoff-by-construction; the test only asserts
        # that the solvers do not crash and produce finite values.
        bias = BiasInput(vcc_v=12, r1_ohm=1e9, r2_ohm=1, rc_ohm=1e6,
                         re_ohm=1, beta=1e5, vbe_v=0.7)
        base = solve_base_loop(bias)
        nodal = solve_nodal(bias)
        report = compare(base, nodal)
        self.assertIsInstance(report["agree"], bool)
        for value in (nodal.ib_a, nodal.ic_a, nodal.ie_a, nodal.vb_v,
                      nodal.vc_v, nodal.ve_v, nodal.vce_v):
            self.assertTrue(math.isfinite(value))


if __name__ == "__main__":
    unittest.main()
