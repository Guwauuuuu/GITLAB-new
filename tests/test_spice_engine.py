import math
import unittest

from spice_engine import (
    BASELINE_DEFAULTS,
    CECircuitParams,
    build_netlist,
    simulate_ce,
    validate_ce_params,
)


def baseline_params(**overrides) -> CECircuitParams:
    data = {
        "vcc_v": 12.0,
        "r1_ohm": 100e3,
        "r2_ohm": 22e3,
        "rc_ohm": 2.2e3,
        "re_ohm": 1e3,
        "rl_ohm": 10e3,
        "cin_f": 10e-6,
        "cout_f": 10e-6,
        "amp_v": 0.01,
        "freq_hz": 1000.0,
    }
    data.update(overrides)
    return CECircuitParams(**data)


class TestCEValidation(unittest.TestCase):
    def test_baseline_defaults_are_valid(self):
        self.assertEqual(BASELINE_DEFAULTS["vcc_v"], 12.0)
        self.assertEqual(validate_ce_params(baseline_params()), [])

    def test_rejects_zero_re(self):
        errors = validate_ce_params(baseline_params(re_ohm=0.0))
        self.assertTrue(any("RE" in e for e in errors))

    def test_rejects_negative_and_nonfinite_inputs(self):
        for field in ("vcc_v", "r1_ohm", "r2_ohm", "rc_ohm", "rl_ohm", "cin_f", "cout_f", "amp_v", "freq_hz"):
            with self.subTest(field=field):
                self.assertTrue(validate_ce_params(baseline_params(**{field: -1.0})))
                self.assertTrue(validate_ce_params(baseline_params(**{field: float("nan")})))
                self.assertTrue(validate_ce_params(baseline_params(**{field: float("inf")})))


class TestNetlistGeneration(unittest.TestCase):
    def test_netlist_contains_unbypassed_ce_elements_and_model(self):
        netlist = build_netlist(baseline_params(), "op")
        self.assertIn("Q1 c b e Q2N2222", netlist)
        self.assertIn(".model Q2N2222 NPN(", netlist)
        self.assertIn("RE e 0", netlist)
        self.assertIn("Cin in b", netlist)
        self.assertIn("Cout c out", netlist)
        self.assertIn("RL out 0", netlist)
        # No emitter bypass capacitor across node e
        self.assertNotIn("Ce ", netlist)


class TestNgspiceSimulation(unittest.TestCase):
    def test_op_simulation_returns_real_operating_point(self):
        res = simulate_ce(baseline_params(), "op")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["model_name"], "Q2N2222")
        self.assertEqual(res["analysis"], "op")
        op = res["data"]
        self.assertAlmostEqual(op["vb_v"], 2.016, delta=0.15)
        self.assertAlmostEqual(op["ve_v"], 1.364, delta=0.15)
        self.assertAlmostEqual(op["vc_v"], 9.017, delta=0.25)
        self.assertAlmostEqual(op["vce_v"], op["vc_v"] - op["ve_v"], places=4)
        self.assertGreater(op["ib_a"], 1e-6)
        self.assertAlmostEqual(op["ic_a"], 1.356e-3, delta=0.2e-3)
        self.assertEqual(op["region"], "active")

    def test_op_detects_cutoff_and_saturation(self):
        cutoff = simulate_ce(baseline_params(r2_ohm=100.0), "op")
        self.assertEqual(cutoff["status"], "success")
        self.assertEqual(cutoff["data"]["region"], "cutoff")

        sat = simulate_ce(baseline_params(rc_ohm=100e3), "op")
        self.assertEqual(sat["status"], "success")
        self.assertEqual(sat["data"]["region"], "saturation")

    def test_ac_simulation_returns_gain_and_phase_in_degrees(self):
        res = simulate_ce(baseline_params(), "ac")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["model_name"], "Q2N2222")
        ac = res["data"]
        freqs = ac["freq_hz"]
        gain_vv = ac["gain_vv"]
        gain_db = ac["gain_db"]
        phase_deg = ac["phase_deg"]
        self.assertGreater(len(freqs), 50)
        self.assertTrue(all(freqs[i] < freqs[i + 1] for i in range(len(freqs) - 1)))
        self.assertTrue(all(math.isfinite(x) for x in gain_vv + gain_db + phase_deg))
        # Midband ~ 10 kHz: unbypassed gain ~ (RC||RL)/(RE+re) ~ 1.77 V/V (~4.96 dB), phase ~ -180 deg
        mid_idx = min(range(len(freqs)), key=lambda i: abs(freqs[i] - 10e3))
        self.assertAlmostEqual(gain_vv[mid_idx], 1.77, delta=0.2)
        self.assertAlmostEqual(gain_db[mid_idx], 4.96, delta=0.8)
        self.assertTrue(-190.0 <= phase_deg[mid_idx] <= -170.0, f"got phase {phase_deg[mid_idx]}")
        self.assertEqual(ac["vin_reference"], "AC 1 V at input source node (before Cin)")

    def test_tran_simulation_shows_180_degree_inversion(self):
        res = simulate_ce(baseline_params(amp_v=0.01, freq_hz=1000.0), "tran")
        self.assertEqual(res["status"], "success")
        tran = res["data"]
        t = tran["time_s"]
        vin = tran["vin_v"]
        vout = tran["vout_v"]
        self.assertGreater(len(t), 100)
        self.assertAlmostEqual(max(vin), 0.01, delta=0.001)
        self.assertAlmostEqual(min(vin), -0.01, delta=0.001)
        # Skip initial 1 cycle transient settling, check inversion in steady cycles
        tail = [i for i, ti in enumerate(t) if ti >= 1.0e-3]
        dot = sum(vin[i] * vout[i] for i in tail)
        self.assertLess(dot, 0.0)
        self.assertGreater(tran["summary"]["vout_pp_v"], tran["summary"]["vin_pp_v"])
        self.assertTrue(tran["summary"]["phase_inverted"])

    def test_missing_executable_returns_error_without_fake_data(self):
        res = simulate_ce(baseline_params(), "op", executable="nonexistent_ngspice_con_xyz")
        self.assertEqual(res["status"], "error")
        self.assertIn("error", res)
        self.assertNotIn("data", res)

    def test_timeout_returns_error(self):
        res = simulate_ce(baseline_params(), "tran", timeout_s=0.0001)
        self.assertEqual(res["status"], "error")
        self.assertTrue("timed out" in res["error"].lower() or "timeout" in res["error"].lower())
        self.assertNotIn("data", res)

    def test_invalid_analysis_returns_error(self):
        res = simulate_ce(baseline_params(), "noise")
        self.assertEqual(res["status"], "error")
        self.assertNotIn("data", res)


if __name__ == "__main__":
    unittest.main()
