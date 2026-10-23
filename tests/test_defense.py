"""Integrity contracts for the single-file, offline defense deliverable."""
from pathlib import Path
from html.parser import HTMLParser
from fontTools.ttLib import TTFont
import base64
import hashlib
import io
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Chapters(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections = []
        self.external_assets = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'section' and values.get('class', '').startswith('chapter'):
            self.sections.append(values)
        if tag in ('script', 'source', 'img', 'link'):
            for key in ('src', 'href'):
                uri = values.get(key)
                if uri and not uri.startswith('data:'):
                    self.external_assets.append(uri)


class DefenseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'deliverables/olist_visual_report.html').read_text()
        cls.snapshot = json.loads((ROOT / 'reports/analysis_snapshot.json').read_text())
        cls.parser = Chapters()
        cls.parser.feed(cls.html)

    def test_main_route_video_second_and_timing(self):
        main = [s for s in self.parser.sections if s.get('data-route') != 'supplement']
        self.assertEqual([s['id'] for s in main], [
            'p0', 'project-video', 'foundation', 'p1', 'p2', 'p3',
            'p5', 'p6', 'customer-cohort', 'p8', 'completion',
        ])
        self.assertEqual(sum(int(s['data-seconds']) for s in main), 535)
        self.assertEqual(len(self.parser.sections) - len(main), 2)

    def test_no_external_runtime_assets(self):
        self.assertEqual(self.parser.external_assets, [])
        self.assertNotRegex(self.html, r'__(?:DEFENSE|DATA|GEO|ECHARTS|FONT|VIDEO|POSTER)__')
        self.assertIn('Olist 巴西电商数据分析与可视化', self.html)
        self.assertNotIn('页面生成于 2026-10-15', self.html)

    def test_embedded_video_is_exact_current_approved_file(self):
        encoded = re.search(r'id="videoSource" src="data:video/mp4;base64,([^"]+)"', self.html)[1]
        actual = hashlib.sha256(base64.b64decode(encoded, validate=True)).hexdigest()
        expected = hashlib.sha256((ROOT / 'video/olist-vibe/final.mp4').read_bytes()).hexdigest()
        self.assertEqual(actual, expected)

    def test_cohort_weighting_and_missing_future(self):
        decoder = json.JSONDecoder()
        defense, _ = decoder.raw_decode(self.html.split(',DEFENSE=', 1)[1])
        self.assertEqual(defense['cohorts'], self.snapshot['cohorts'])
        m1 = [c for c in defense['cohorts'] if c['month'] == 1 and c['observed']]
        self.assertEqual(sum(c['customers'] for c in m1), 81263)
        self.assertEqual(sum(c['returning'] for c in m1), 389)
        self.assertEqual(defense['repeat']['pct'], self.snapshot['repeat']['pct'])
        self.assertTrue(any(not c['observed'] and c['pct'] is None for c in defense['cohorts']))

    def test_chinese_font(self):
        encoded = re.search(r'data:font/otf;base64,([^\']+)', self.html)[1]
        font = TTFont(io.BytesIO(base64.b64decode(encoded)))
        text = 'Olist 巴西电商数据分析与可视化答辩首购队列回访分母阈值重新播放问答证据'
        self.assertTrue(all(ord(c) in font.getBestCmap() for c in text))


if __name__ == '__main__':
    unittest.main()
