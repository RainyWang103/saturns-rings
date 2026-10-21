"""Exercise the real template with fictional planning facts, not live travel data."""
import importlib.util
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

FIXTURE = Path(__file__).parent / 'cases/travel-planner/render_delivery_fixture.py'
spec = importlib.util.spec_from_file_location('delivery_fixture', FIXTURE)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.ids, self.checks, self.links, self.resources, self.words = [], [], [], [], []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if 'data-check' in attrs:
            self.checks.append(attrs['data-check'])
        if attrs.get('href','').startswith('#'):
            self.links.append(attrs['href'][1:])
        if tag in ('script','img','iframe') and attrs.get('src'):
            self.resources.append(attrs['src'])
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.resources.append(attrs.get('href',''))

    def handle_data(self, data):
        self.words.append(data)


class DeliveryTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = fixture.render()
        cls.doc = Document(cls.html)
        cls.text = re.sub(r'\s+', '', ''.join(cls.doc.words))

    def assertVisibleFact(self, value):
        self.assertIn(re.sub(r'\s+', '', value), self.text)

    def test_all_planning_material_reaches_output(self):
        for day in fixture.DAYS:
            for key in ('city','hotel','stay','stay_note','logic','anchor','anchor_time','backup'):
                self.assertVisibleFact(day[key])
            for event in day['events']:
                for key in ('time','title','state','intro','execution','highlight','warning'):
                    self.assertVisibleFact(event[key])
            for transfer in day['transfers']:
                for value in transfer:
                    self.assertVisibleFact(value)
        self.assertVisibleFact('EUR 120–160（两人估算）')
        self.assertVisibleFact('未支付；含列车，不含出租与行李寄存')

    def test_navigation_symbols_and_checks_are_unambiguous(self):
        self.assertEqual(len(self.doc.ids),len(set(self.doc.ids)))
        self.assertEqual(len(self.doc.checks),len(set(self.doc.checks)))
        self.assertEqual(len(self.doc.checks),3)
        self.assertTrue(set(self.doc.links).issubset(self.doc.ids))
        self.assertTrue({'day1','day2','day3','anchors','budget','map-sources'}.issubset(self.doc.ids))

    def test_output_is_fictional_self_contained_and_filled(self):
        self.assertVisibleFact(fixture.INTRO)
        self.assertNotRegex(self.html,r'\{\{.*?\}\}')
        self.assertEqual(self.doc.resources,[])
        self.assertNotIn('@import',self.html)
        self.assertNotRegex(self.html,r'url\(\s*[\"\']?https?://')
        self.assertNotIn('tel:000',self.html)

    def test_unknown_tokens_fail_and_values_are_escaped(self):
        with self.assertRaises(ValueError):
            fixture.fill('{{missing}}',{})
        self.assertEqual(fixture.fill('{{x}}',{'x':'<b>"&'}),'&lt;b&gt;&quot;&amp;')

    def test_fixture_headings_counts_and_hard_connections(self):
        self.assertVisibleFact('河岸小院｜确认入住与行李')
        self.assertVisibleFact('雕塑步道｜按天气决定')
        self.assertEqual(self.html.count('1 项候选'),3)
        def clock(value):
            hour,minute=map(int,value.split(':'))
            return 60*hour+minute
        def upper(value):
            return int(value.split('–')[-1])
        def arrival(departure,transfer):
            return departure+upper(transfer[3])+upper(transfer[4])
        music=fixture.DAYS[1]
        departure=clock(re.search(r'(\d\d:\d\d)离餐',music['events'][1]['execution'])[1])
        self.assertLessEqual(arrival(departure,music['transfers'][1]),clock(music['transfers'][1][5]))
        last=fixture.DAYS[2]
        self.assertLessEqual(arrival(clock(last['events'][0]['time'].split('–')[0]),last['transfers'][0]),clock(last['transfers'][0][5]))
        self.assertLessEqual(arrival(clock(last['events'][1]['time'].split('–')[1]),last['transfers'][2]),clock(last['transfers'][2][5]))
        self.assertLessEqual(arrival(clock(last['transfers'][2][5]),last['transfers'][3]),clock(last['transfers'][3][5]))


if __name__ == '__main__':
    unittest.main()
