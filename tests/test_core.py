import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from nutridraft.core import analyze, audit, render_brief, render_content

ROOT = Path(__file__).resolve().parents[1]


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'examples/label_demo.json').read_text())

    def invalid(self, mutate):
        mutate(self.data)
        with self.assertRaises(ValueError):
            analyze(self.data)

    def test_serving_calculation(self):
        r = analyze(self.data)
        self.assertEqual([x['per_serving'] for x in r['nutrients']], ['480', '3.6', '84'])
        self.assertFalse(r['publish_ready'])

    def test_different_basis(self):
        self.data['nutrients'][0]['basis_amount'] = 50
        self.assertEqual(analyze(self.data)['nutrients'][0]['per_100'], '3200')

    def test_liquids(self):
        self.data['serving_unit'] = 'ml'
        for row in self.data['nutrients']:
            row['basis_unit'] = 'ml'
        self.assertEqual(analyze(self.data)['serving_unit'], 'ml')

    def test_cross_mass_volume_rejected(self):
        self.invalid(lambda d: d['nutrients'][0].update(basis_unit='ml'))

    def test_zero_basis_rejected(self):
        self.invalid(lambda d: d['nutrients'][0].update(basis_amount=0))

    def test_negative_rejected(self):
        self.invalid(lambda d: d.update(serving_size=-2))

    def test_boolean_rejected(self):
        self.invalid(lambda d: d.update(serving_size=True))

    def test_nan_rejected(self):
        self.invalid(lambda d: d['nutrients'][0].update(amount=float('nan')))

    def test_inf_rejected(self):
        self.invalid(lambda d: d.update(serving_size=float('inf')))

    def test_duplicate_name(self):
        self.invalid(lambda d: d['nutrients'].append(copy.deepcopy(d['nutrients'][0])))

    def test_zero_nutrient(self):
        self.data['nutrients'][0]['amount'] = 0
        self.assertEqual(analyze(self.data)['nutrients'][0]['per_serving'], '0')

    def test_malformed_root(self):
        with self.assertRaises(ValueError):
            analyze([])

    def test_bad_nutrient_unit(self):
        self.invalid(lambda d: d['nutrients'][0].update(unit='kg'))

    def test_bad_url(self):
        self.invalid(lambda d: d['evidence'][0].update(url='javascript:alert(1)'))

    def test_credentials_url(self):
        self.invalid(lambda d: d['evidence'][0].update(url='https://secret:password@example.com/'))

    def test_duplicate_evidence(self):
        self.invalid(lambda d: d['evidence'].append(copy.deepcopy(d['evidence'][0])))

    def test_missing_evidence_warns(self):
        self.data['evidence'] = []
        self.assertIn('没有证据条目', analyze(self.data)['warnings'][-1])

    def test_risk_scan(self):
        findings = audit('百分百治愈，不用吃药，一周瘦十斤')
        self.assertEqual({x['code'] for x in findings}, {'medical', 'guarantee', 'restriction'})

    def test_evidence_claim_is_scanned(self):
        self.data['evidence'][0]['claim'] = '保证瘦'
        self.assertTrue(analyze(self.data)['findings'])

    def test_render_safe(self):
        self.data['topic'] = '<script>alert(1)</script>'
        r = analyze(self.data)
        self.assertNotIn('<script>', render_brief(r))
        self.assertIn('规则生成', render_content(r))
        self.assertIn('FDA-serving', render_brief(r))

    def test_cli_outputs_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'demo'
            command = [sys.executable, '-m', 'nutridraft', str(ROOT / 'examples/label_demo.json'), '--output', str(out)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(list(out.iterdir())), 3)
            self.assertEqual(json.loads((out / 'report.json').read_text())['project_status'], 'new_local_prototype')
            self.assertEqual(subprocess.run(command, cwd=ROOT, capture_output=True).returncode, 2)

    def test_cli_bad_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'bad.json'
            source.write_text('{"topic":"a","topic":"b"}')
            p = subprocess.run([sys.executable, '-m', 'nutridraft', str(source), '--output', str(Path(tmp)/'out')], cwd=ROOT, capture_output=True)
            self.assertEqual(p.returncode, 2)
            self.assertFalse((Path(tmp)/'out').exists())


if __name__ == '__main__':
    unittest.main()
