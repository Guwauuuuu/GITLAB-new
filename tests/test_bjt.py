import unittest
from bjt import BiasInput, validate, solve_base_loop


class TestBJT(unittest.TestCase):
    def defaults(self):
        return BiasInput(vcc_v=12, r1_ohm=47000, r2_ohm=10000,
                         rc_ohm=2200, re_ohm=470, beta=150, vbe_v=0.7)

    def test_known_active_point(self):
        result = solve_base_loop(self.defaults())
        self.assertAlmostEqual(result.vbb_v, 2.105263, places=6)
        self.assertAlmostEqual(result.rb_ohm, 8245.614, places=3)
        self.assertAlmostEqual(result.ib_a, 1.7740e-5, places=9)
        self.assertAlmostEqual(result.ic_a, 2.6610e-3, places=7)
        self.assertAlmostEqual(result.ie_a, 2.6787e-3, places=7)
        self.assertAlmostEqual(result.ve_v, 1.2590, places=4)
        self.assertAlmostEqual(result.vc_v, 6.1459, places=4)
        self.assertAlmostEqual(result.vb_v, 1.9590, places=4)
        self.assertAlmostEqual(result.vce_v, 4.8869, places=4)
        self.assertEqual(result.region, "active")
        self.assertTrue(result.in_active)

    def test_cutoff_region(self):
        bias = self.defaults()
        bias.r2_ohm = 100
        result = solve_base_loop(bias)
        self.assertEqual(result.region, "cutoff")
        self.assertFalse(result.in_active)

    def test_saturation_region(self):
        bias = self.defaults()
        bias.rc_ohm = 100000
        result = solve_base_loop(bias)
        self.assertEqual(result.region, "saturation")
        self.assertFalse(result.in_active)

    def test_validation_rejects_non_positive(self):
        bias = self.defaults()
        bias.vcc_v = 0
        self.assertIn("VCC", validate(bias)[0])

    def test_validation_rejects_beta_below_one(self):
        bias = self.defaults()
        bias.beta = 0
        self.assertIn("beta", validate(bias)[0])

    def test_validation_rejects_vbe_out_of_range(self):
        bias = self.defaults()
        bias.vbe_v = 13
        self.assertIn("VBE", validate(bias)[0])


class TestValidationFinite(unittest.TestCase):
    def defaults(self):
        return BiasInput(vcc_v=12, r1_ohm=47000, r2_ohm=10000,
                         rc_ohm=2200, re_ohm=470, beta=150, vbe_v=0.7)

    def test_nan_vcc_is_rejected(self):
        bias = self.defaults(); bias.vcc_v = float("nan")
        self.assertIn("VCC must be a finite number", validate(bias))

    def test_inf_r1_is_rejected(self):
        bias = self.defaults(); bias.r1_ohm = float("inf")
        self.assertIn("R1 must be a finite number", validate(bias))

    def test_nan_beta_is_rejected(self):
        bias = self.defaults(); bias.beta = float("nan")
        self.assertIn("beta must be a finite number", validate(bias))

    def test_nan_vbe_is_rejected(self):
        bias = self.defaults(); bias.vbe_v = float("nan")
        self.assertIn("VBE must be a finite number", validate(bias))


if __name__ == "__main__":
    unittest.main()
