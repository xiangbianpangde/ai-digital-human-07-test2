"""Readonly guards and camera math checks; never renders a clip or creates a take."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

from PIL import Image, ImageChops

PATH = Path(__file__).with_name('render_one_shot.py')
spec = importlib.util.spec_from_file_location('one_shot', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class SingleShotChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = json.loads(m.CONTRACT.read_text())

    def denied(self, change):
        c = copy.deepcopy(self.c)
        change(c)
        with self.assertRaises(ValueError):
            m.validate(c)

    def test_approved_contract(self):
        m.validate(self.c)

    def test_wrong_listing_rejected(self):
        self.denied(lambda c: c.update(listing_id='other-house'))

    def test_wrong_point_rejected(self):
        self.denied(lambda c: c['source'].update(pano_index=24))

    def test_no_native_exception_rejected(self):
        self.denied(lambda c: c['approval'].update(native_view_exception=False))

    def test_wrong_duration_rejected(self):
        self.denied(lambda c: c['shot'].update(duration_sec=30))

    def test_cross_point_or_translation_rejected(self):
        self.denied(lambda c: c['shot'].update(spatial_translation=True))

    def test_voice_or_cta_rejected(self):
        self.denied(lambda c: c['shot'].update(voice='any-new-voice'))
        self.denied(lambda c: c['shot'].update(cta='contact-agent'))

    def test_paid_or_external_generation_rejected(self):
        self.denied(lambda c: c['shot'].update(new_paid_cost=1))
        self.denied(lambda c: c['shot'].update(external_media_request=True))
        self.denied(lambda c: c['shot'].update(synthetic_room_pixels=True))

    def test_metric_claims_or_next_shot_rejected(self):
        self.denied(lambda c: c['shot'].update(clearance_0_5m_verified=True))
        self.denied(lambda c: c['shot'].update(physical_height_verified=True))
        self.denied(lambda c: c['approval'].update(next_shot_authorized=True))

    def test_wrong_output_or_guard_rejected(self):
        self.denied(lambda c: c.update(output_parent='03_实现/old-fixed-output'))
        self.denied(lambda c: c['guards'].update(no_overwrite=False))

    def test_absolute_yaw_endpoints_monotonic_symmetric(self):
        values = [m.yaw_for(i) for i in range(180)]
        self.assertAlmostEqual(values[0], -8)
        self.assertAlmostEqual(values[-1], 8)
        self.assertTrue(all(a < b for a, b in zip(values, values[1:])))
        self.assertTrue(all(abs(a + b) < 1e-12 for a, b in zip(values, reversed(values))))
        self.assertLess(max((b-a)*30 for a, b in zip(values, values[1:])), 4.3)

    def test_camera_coefficients_match_ray_equations(self):
        for angle in (-8, 0, 8):
            a, b, c, d, e, f, g, h = m.coefficients(angle)
            for x, y in ((0, 0), (719, 1279), (359.5, 639.5), (195, 560)):
                expected = m.ray_to_source(x, y, angle, 720, 1280, 2048, 50, self.c['shot']['v_fov_deg'])
                got = ((a*x + b*y + c)/(g*x + h*y + 1), (d*x + e*y + f)/(g*x + h*y + 1))
                self.assertAlmostEqual(got[0], expected[0], places=8)
                self.assertAlmostEqual(got[1], expected[1], places=8)

    def test_zero_yaw_identity_preserves_pixels(self):
        image = Image.new('RGB', (32, 32))
        image.putdata([((x*17)%256, (y*19)%256, (x+y)*3) for y in range(32) for x in range(32)])
        coeff = m.coefficients(0, 32, 32, 32, 90, 90)
        projected = image.transform((32, 32), Image.Transform.PERSPECTIVE, coeff, Image.Resampling.BICUBIC)
        self.assertIsNone(ImageChops.difference(image, projected).getbbox())

    def test_readonly_preflight_and_all180_source_bounds(self):
        before = list((m.ROOT / m.OUT_PARENT).glob('*')) if (m.ROOT / m.OUT_PARENT).exists() else []
        receipt = m.preflight(self.c)
        after = list((m.ROOT / m.OUT_PARENT).glob('*')) if (m.ROOT / m.OUT_PARENT).exists() else []
        self.assertEqual(before, after)
        self.assertTrue(receipt['all180_frame_rays_inside_real_face'])
        self.assertFalse((m.ROOT / m.OUT_PARENT / m.ATTEMPT).exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
