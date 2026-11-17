import re
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

    def test_mohm_units_are_converted(self):
        data = dict(mode="fixed", vcc_v="12", rb_ohm="1", rb_ohm_unit="mohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm", beta="100", vbe_v="0.70")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("9.514 V", html)
        self.assertIn("1.13 mA", html)

    def test_mohm_option_present_on_every_resistor_unit_select(self):
        html = self.client.get("/").data.decode("utf-8")
        self.assertEqual(html.count('value="mohm"'), 5)

    def test_selected_unit_is_retained_after_post(self):
        data = dict(mode="fixed", vcc_v="12", rb_ohm="1", rb_ohm_unit="mohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm", beta="100", vbe_v="0.70")
        html = self.client.post("/calculate", data=data).data.decode("utf-8")
        self.assertIn('value="mohm" selected', html)

    def test_unknown_unit_falls_back_to_ohm(self):
        data = dict(mode="fixed", vcc_v="12", rb_ohm="1000000", rb_ohm_unit="gohm",
                    rc_ohm="2200", beta="100", vbe_v="0.70")
        response = self.client.post("/calculate", data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("1.13 mA", response.data.decode("utf-8"))

    def test_bias_mode_is_three_radios(self):
        html = self.client.get("/").data.decode("utf-8")
        self.assertEqual(html.count('name="mode"'), 3)
        for value in ("divider", "fixed", "emitter"):
            self.assertIn(f'id="mode_{value}"', html)
            self.assertIn(f'value="{value}"', html)

    def test_divider_mode_hides_rb_field(self):
        html = self.client.get("/").data.decode("utf-8")
        self.assertRegex(html, r'data-field="rb_ohm"[^>]*hidden')

    def test_fixed_mode_hides_divider_and_re_fields(self):
        data = dict(mode="fixed", vcc_v="12", rb_ohm="1", rb_ohm_unit="mohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm", beta="100", vbe_v="0.70")
        html = self.client.post("/calculate", data=data).data.decode("utf-8")
        self.assertRegex(html, r'data-field="r1_ohm"[^>]*hidden')
        self.assertRegex(html, r'data-field="r2_ohm"[^>]*hidden')
        self.assertRegex(html, r'data-field="re_ohm"[^>]*hidden')
        self.assertNotRegex(html, r'data-field="rb_ohm"[^>]*hidden')

    def test_every_label_for_matches_an_element_id(self):
        html = self.client.get("/").data.decode("utf-8")
        for_ids = set(re.findall(r'<label for="([^"]+)"', html))
        ids = set(re.findall(r'id="([^"]+)"', html))
        self.assertTrue(for_ids)
        self.assertLessEqual(for_ids, ids)

    def test_svg_has_data_slots_for_every_parameter(self):
        html = self.client.get("/").data.decode("utf-8")
        for slot in ("vcc", "r1", "r2", "rb", "rc", "re", "beta", "vbe"):
            self.assertIn(f'data-slot="{slot}"', html)

    def test_svg_shows_submitted_values_with_units(self):
        data = dict(mode="fixed", vcc_v="12", rb_ohm="1", rb_ohm_unit="mohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm", beta="100", vbe_v="0.70")
        html = self.client.post("/calculate", data=data).data.decode("utf-8")
        self.assertIn("= 1 MΩ", html)
        self.assertIn("= 2.2 kΩ", html)
        self.assertIn("= 12 V", html)

    def test_circuit_labels_use_dash_for_empty_values(self):
        from app import circuit_labels
        labels = circuit_labels({}, {"r1_ohm": "kohm"})
        self.assertEqual(labels["r1"], "= —")
        self.assertEqual(labels["vcc"], "= —")

    def test_svg_labels_are_separated_from_the_symbol(self):
        data = dict(mode="fixed", vcc_v="12", rb_ohm="1", rb_ohm_unit="mohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm", beta="100", vbe_v="0.70")
        html = self.client.post("/calculate", data=data).data.decode("utf-8")
        for expected in ("&#160;= 12 V", "&#160;= 1 MΩ", "&#160;= 2.2 kΩ"):
            self.assertIn(expected, html)

    def test_fixed_mode_hides_divider_components_in_svg(self):
        data = dict(mode="fixed", vcc_v="12", rb_ohm="1", rb_ohm_unit="mohm",
                    rc_ohm="2.2", rc_ohm_unit="kohm", beta="100", vbe_v="0.70")
        html = self.client.post("/calculate", data=data).data.decode("utf-8")
        self.assertRegex(html, r'data-component="r1"[^>]*is-hidden')
        self.assertRegex(html, r'data-component="r2"[^>]*is-hidden')
        self.assertNotRegex(html, r'data-component="rb"[^>]*is-hidden')

    def test_divider_mode_shows_r1_and_r2_components_in_svg(self):
        html = self.client.get("/").data.decode("utf-8")
        for component in ("r1", "r2"):
            self.assertNotRegex(html, rf'data-component="{component}"[^>]*is-hidden')
        self.assertRegex(html, r'data-component="rb"[^>]*is-hidden')

    def test_stylesheet_uses_dark_theme_tokens(self):
        import pathlib
        css = pathlib.Path("static/style.css").read_text(encoding="utf-8")
        for token in ("--bg: #0B0D10", "--panel: #14171C", "--ink: #E8EAF0", "--accent: #F5B301"):
            self.assertIn(token, css)
        self.assertIn(".is-hidden", css)


if __name__ == "__main__":
    unittest.main()
