import unittest
from unittest.mock import patch

from app import app


FORM_DEFAULTS = {
    "analysis": "op",
    "vcc_v": "12",
    "r1": "100", "r1_unit": "kohm",
    "r2": "22", "r2_unit": "kohm",
    "rc": "2.2", "rc_unit": "kohm",
    "re": "1", "re_unit": "kohm",
    "rl": "10", "rl_unit": "kohm",
    "cin": "10", "cin_unit": "uf",
    "cout": "10", "cout_unit": "uf",
    "source_amp": "10", "source_amp_unit": "mv",
    "source_freq": "1", "source_freq_unit": "khz",
    "beta": "100",
    "vbe_v": "0.7",
}


class TestCESimulatorPage(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_page_loads_with_baseline_defaults(self):
        response = self.client.get("/ce-simulator")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        for value in ("12", "100", "22", "2.2", "10", "0.7"):
            self.assertIn(f'value="{value}"', html)
        self.assertIn('value="kohm" selected', html)
        self.assertIn('value="uf" selected', html)
        self.assertIn('value="mv" selected', html)
        self.assertIn('value="khz" selected', html)

    def test_page_links_back_to_lab3_and_shows_engine_controls(self):
        html = self.client.get("/ce-simulator").data.decode("utf-8")
        self.assertIn('href="/"', html)
        for analysis in ("op", "ac", "tran"):
            self.assertIn(f'value="{analysis}"', html)
        self.assertIn("ngspice", html.lower())
        self.assertIn("Q2N2222", html)


class TestCEFrontendAssets(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_lab3_header_links_to_ce_simulator(self):
        html = self.client.get("/").data.decode("utf-8")
        self.assertIn('href="/ce-simulator"', html)

    def test_ce_page_has_plot_status_and_error_hooks(self):
        html = self.client.get("/ce-simulator").data.decode("utf-8")
        for element_id in (
            "engine-status", "engine-state", "sim-errors", "results-empty",
            "op-results", "ac-results", "tran-results",
            "ac-mag-plot", "ac-phase-plot", "tran-plot",
            "analytical-card", "ce-form",
        ):
            self.assertIn(f'id="{element_id}"', html)

    def test_ce_js_posts_to_api_and_clears_stale_results(self):
        import pathlib
        js = pathlib.Path("static/ce_sim.js").read_text(encoding="utf-8")
        for token in (
            "/api/ce-simulate", "fetch(", "clearResults", "renderResults",
            "showError", "engine-status", "textContent",
        ):
            self.assertIn(token, js)
        self.assertIn("body.spice", js)

    def test_stylesheet_has_ce_plot_and_status_styles(self):
        import pathlib
        css = pathlib.Path("static/style.css").read_text(encoding="utf-8")
        for token in (".engine-status", ".compare-grid", ".summary-row", ".plot", ".app-nav"):
            self.assertIn(token, css)


class TestCEApi(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def post(self, **overrides):
        data = dict(FORM_DEFAULTS)
        data.update(overrides)
        return self.client.post("/api/ce-simulate", data=data)

    def test_op_returns_real_spice_and_lab3_analytical_reference(self):
        response = self.post(analysis="op")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["model_name"], "Q2N2222")
        self.assertEqual(body["engine"]["name"], "ngspice_con")

        spice = body["spice"]
        self.assertEqual(spice["region"], "active")
        self.assertAlmostEqual(spice["vb_v"], 2.016, delta=0.2)
        self.assertAlmostEqual(spice["vce_v"], spice["vc_v"] - spice["ve_v"], places=4)
        self.assertGreater(spice["ib_a"], 0)
        self.assertGreater(spice["ic_a"], 0)

        analytical = body["analytical"]
        self.assertEqual(analytical["source"], "Lab 3 analytical (bjt.py)")
        self.assertEqual(analytical["region"], "active")
        self.assertGreater(analytical["ic_a"], 0)
        # The two paths are independent: SPICE uses the 2N2222 Gummel-Poon
        # model, the reference uses the Lab 3 beta/VBE equations.
        self.assertNotAlmostEqual(spice["ic_a"], analytical["ic_a"], places=6)
        self.assertEqual(body["units"]["voltage"], "V")
        self.assertEqual(body["units"]["current"], "A")

    def test_ac_returns_gain_and_phase_with_units(self):
        response = self.post(analysis="ac")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "success")
        spice = body["spice"]
        self.assertGreater(len(spice["freq_hz"]), 50)
        self.assertEqual(spice["vin_reference"], "AC 1 V at input source node (before Cin)")
        self.assertEqual(body["units"]["phase"], "deg")
        self.assertEqual(body["units"]["gain_db"], "dB")
        self.assertTrue(-190.0 <= spice["midband_phase_deg"] <= -170.0)
        self.assertAlmostEqual(spice["midband_gain_db"], 4.9, delta=0.8)

    def test_tran_returns_vin_and_vout_with_adjustable_source(self):
        response = self.post(analysis="tran", source_amp="20", source_amp_unit="mv",
                             source_freq="2", source_freq_unit="khz")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "success")
        spice = body["spice"]
        self.assertGreater(len(spice["time_s"]), 100)
        self.assertAlmostEqual(max(spice["vin_v"]), 0.02, delta=0.002)
        self.assertTrue(spice["summary"]["phase_inverted"])
        self.assertGreater(spice["summary"]["vout_pp_v"], spice["summary"]["vin_pp_v"])

    def test_zero_re_returns_400_without_running_spice(self):
        with patch("app.simulate_ce") as fake:
            response = self.post(analysis="op", re="0")
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["status"], "error")
        self.assertTrue(any("RE" in error for error in body["errors"]))
        self.assertNotIn("spice", body)
        fake.assert_not_called()

    def test_unknown_analysis_returns_400(self):
        response = self.post(analysis="noise")
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["status"], "error")
        self.assertIn("analysis", " ".join(body["errors"]).lower())

    def test_non_string_json_analysis_returns_400(self):
        response = self.client.post(
            "/api/ce-simulate",
            json={"analysis": ["op"], "re": 1, "re_unit": "kohm"},
        )
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["status"], "error")
        self.assertIn("analysis", " ".join(body["errors"]).lower())

    def test_non_numeric_input_returns_400(self):
        response = self.post(analysis="op", r1="abc")
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertTrue(any("R1" in error for error in body["errors"]))

    def test_invalid_beta_or_vbe_returns_400(self):
        response = self.post(analysis="op", beta="0")
        self.assertEqual(response.status_code, 400)
        self.assertIn("beta", " ".join(response.get_json()["errors"]))

        response = self.post(analysis="op", vbe_v="13")
        self.assertEqual(response.status_code, 400)
        self.assertIn("VBE", " ".join(response.get_json()["errors"]))

    def test_engine_error_returns_500_without_fake_data(self):
        failure = {
            "status": "error",
            "analysis": "op",
            "model_name": "Q2N2222",
            "engine": "ngspice_con",
            "error": "ngspice exited with code 1",
            "stderr": "boom",
        }
        with patch("app.simulate_ce", return_value=failure) as fake:
            response = self.post(analysis="op")
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["status"], "error")
        self.assertEqual(body["error"], "ngspice exited with code 1")
        self.assertNotIn("spice", body)
        fake.assert_called_once()


if __name__ == "__main__":
    unittest.main()
