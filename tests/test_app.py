import unittest
from app import app


class TestAppRoutes(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_form_contains_example_circuit(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("svg", html)
        self.assertIn("Circuit: Common-Emitter Amplifier", html)

    def test_get_form_has_empty_defaults(self):
        html = self.client.get("/").data.decode("utf-8")
        self.assertIn('name="vcc_v" value=""', html)
        self.assertIn("Enter the circuit values", html)

    def test_get_form_returns_200_and_has_inputs(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        for name in ("vcc_v", "r1_ohm", "r2_ohm", "rc_ohm", "re_ohm", "beta", "vbe_v"):
            self.assertIn(name, html)

    def test_get_calculate_redirects_to_form(self):
        response = self.client.get("/calculate")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        followed = self.client.get("/calculate", follow_redirects=True)
        self.assertEqual(followed.status_code, 200)
        self.assertIn("Input Parameters", followed.data.decode("utf-8"))

    def test_valid_post_returns_results_with_units(self):
        data = dict(vcc_v="12", r1_ohm="47000", r2_ohm="10000",
                    rc_ohm="2200", re_ohm="470", beta="150", vbe_v="0.7")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("4.887 V", html)
        # VBB is pinned at the %.3f format; it must not widen to %.4f ("2.1050").
        self.assertIn("2.105 V", html)
        self.assertNotIn("2.1050", html)
        self.assertIn("agree pass", html)
        self.assertIn("mA", html)
        self.assertIn("active", html.lower())

    def test_kohm_units_are_converted(self):
        data = dict(vcc_v="12", r1_ohm="100", r1_ohm_unit="kohm",
                    r2_ohm="22", r2_ohm_unit="kohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm",
                    re_ohm="1.0", re_ohm_unit="kohm", beta="100", vbe_v="0.70")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("2.164 V", html)   # VBB
        self.assertIn("8.052 V", html)   # VCE

    def test_invalid_post_returns_400_and_retains_values(self):
        data = dict(vcc_v="abc", r1_ohm="0", r2_ohm="10000",
                    rc_ohm="2200", re_ohm="470", beta="150", vbe_v="0.7")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 400)
        html = response.data.decode("utf-8")
        self.assertIn("VCC", html)
        self.assertIn('value="0"', html)

    def test_nan_input_returns_400(self):
        data = dict(vcc_v="nan", r1_ohm="47000", r2_ohm="10000",
                    rc_ohm="2200", re_ohm="470", beta="150", vbe_v="0.7")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("finite number", response.data.decode("utf-8"))

    def test_overflow_scale_input_returns_400(self):
        data = dict(vcc_v="12", r1_ohm="1e308", r2_ohm="1e308",
                    rc_ohm="2200", re_ohm="470", beta="150", vbe_v="0.7")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("representable numeric range", response.data.decode("utf-8"))

    def test_subnormal_resistance_returns_400(self):
        data = dict(vcc_v="12", r1_ohm="5e-324", r2_ohm="10000",
                    rc_ohm="2200", re_ohm="470", beta="150", vbe_v="0.7")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("representable numeric range", response.data.decode("utf-8"))

    def test_cutoff_post_warns(self):
        data = dict(vcc_v="12", r1_ohm="47000", r2_ohm="100",
                    rc_ohm="2200", re_ohm="470", beta="150", vbe_v="0.7")
        html = self.client.post("/calculate", data=data).data.decode("utf-8")
        self.assertIn("cutoff", html)
        self.assertIn("not a usable bias point", html)

    def test_saturation_post_warns(self):
        data = dict(vcc_v="12", r1_ohm="47000", r2_ohm="10000",
                    rc_ohm="100000", re_ohm="470", beta="150", vbe_v="0.7")
        html = self.client.post("/calculate", data=data).data.decode("utf-8")
        self.assertIn("saturation", html)
        self.assertIn("not a usable bias point", html)


if __name__ == "__main__":
    unittest.main()
