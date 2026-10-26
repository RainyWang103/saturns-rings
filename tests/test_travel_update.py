"""Local HTML updates: content retention, version races and hostile fragments."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_travel_delivery import fixture, Document

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'shared/travel-planner/scripts/update_html.py'
spec = importlib.util.spec_from_file_location('travel_update', SCRIPT)
update = importlib.util.module_from_spec(spec)
# Import the packaged script without generating artifacts inside skill sources.
previous_bytecode = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    spec.loader.exec_module(update)
finally:
    sys.dont_write_bytecode = previous_bytecode


class UpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = fixture.render().encode('utf-8')
        cls.digest = sha256(cls.source).hexdigest()
        cls.old = fixture.DAYS[1]['logic']
        cls.new = '今天下雨：取消户外散步，保留音乐会、午后休息及已确认住宿。'

    def patch(self, old=None, new=None, source=None):
        return update.patch_html(self.source if source is None else source,
                                 [{'old': self.old if old is None else old,
                                   'new': self.new if new is None else new}], self.digest)

    def test_local_change_retains_every_unaffected_byte(self):
        result = self.patch()
        self.assertEqual(result, self.source.replace(self.old.encode(), self.new.encode(), 1))
        before, after = Document(self.source.decode()), Document(result.decode())
        self.assertEqual(before.ids, after.ids)
        self.assertEqual(before.checks, after.checks)
        for day in fixture.DAYS:
            for event in day['events']:
                for key in ('intro', 'execution', 'highlight', 'warning'):
                    self.assertIn(event[key], result.decode())

    def test_batched_edits_use_original_version_not_previous_replacement(self):
        second = fixture.DAYS[2]['logic']
        result = update.patch_html(self.source, [
            {'old': self.old, 'new': second}, {'old': second, 'new': self.new}], self.digest)
        expected = self.source.decode().replace(second, self.new).replace(self.old, second)
        self.assertEqual(result.decode(), expected)

    def test_stale_source_rejected(self):
        with self.assertRaisesRegex(ValueError, 'version changed'):
            self.patch(source=self.source + b'\n')

    def test_missing_ambiguous_or_overlapping_edits_rejected(self):
        for old in ('not present', '<p>'):
            with self.subTest(old=old), self.assertRaisesRegex(ValueError, 'exactly once'):
                self.patch(old=old)
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            update.patch_html(self.source, [{'old': self.old, 'new': self.new},
                                           {'old': self.old[:12], 'new': 'changed'}], self.digest)

    def test_invalid_patch_schema_rejected(self):
        for edits in ([], {}, [1], [{'old': '', 'new': 'x'}],
                      [{'old': self.old, 'new': 1}], [{'old': self.old, 'new': self.old}],
                      [{'old': self.old, 'new': 'x', 'command': 'write elsewhere'}]):
            with self.subTest(edits=edits), self.assertRaises(ValueError):
                update.patch_html(self.source, edits, self.digest)

    def test_scripts_css_and_existing_storage_keys_cannot_change(self):
        for old, new in [('fictional-delivery-fixture', 'another-trip'),
                         ('--accent:#94453c', '--accent:#123456'),
                         ('data-check="concert"', 'data-check="new-concert"'),
                         ('id="day2"', 'id="new-day2"')]:
            with self.subTest(old=old), self.assertRaises(ValueError):
                self.patch(old, new)

    def test_injection_duplicates_broken_links_and_tokens_rejected(self):
        for fragment in ('<script>alert(1)</script>', '<p style="display:none">x</p>', '<p onclick="alert(1)">x</p>',
                         '<a href="javascript:alert(1)">x</a>',
                         '<a href="java&#x09;script:alert(1)">x</a>',
                         '<iframe srcdoc="x"></iframe>', '<img src="https://example.org/x">',
                         '<base href="https://example.org/">', '<form action="/send"></form>',
                         '<svg><use href="data:text/html,x"/></svg>',
                         '<p id="day1">duplicate</p>', '<a href="#absent">x</a>',
                         '<p title="a" title="b">x</p>', '{{missing}}'):
            with self.subTest(fragment=fragment), self.assertRaises(ValueError):
                self.patch(new=fragment)

    def test_escaped_source_text_and_real_links_work(self):
        result = self.patch(new='&lt;script&gt;仅作为文字&lt;/script&gt; <a href="https://example.org/?a=1&amp;b=2">来源</a>')
        self.assertIn(b'&lt;script&gt;', result)

    def test_incompatible_baseline_not_silently_migrated(self):
        baseline = self.source.replace(b'id="day2"', b'id="day1"')
        with self.assertRaisesRegex(ValueError, 'baseline'):
            update.patch_html(baseline, [{'old': self.old, 'new': self.new}], sha256(baseline).hexdigest())

    def test_overlapping_occurrences_are_not_a_unique_match(self):
        source = self.source.replace(self.old.encode(), b'aaaa')
        with self.assertRaisesRegex(ValueError, 'exactly once'):
            update.patch_html(source, [{'old': 'aaa', 'new': 'x'}], sha256(source).hexdigest())

    def test_existing_check_keys_cannot_be_swapped(self):
        keys = Document(self.source.decode()).checks
        edits = [{'old': f'data-check="{keys[0]}"', 'new': f'data-check="{keys[1]}"'},
                 {'old': f'data-check="{keys[1]}"', 'new': f'data-check="{keys[0]}"'}]
        with self.assertRaises(ValueError):
            update.patch_html(self.source, edits, self.digest)

    def test_checkbox_cannot_become_a_text_input(self):
        source = self.source.decode()
        import re
        original = re.search(r'<input[^>]*data-check="concert"[^>]*>', source)[0]
        with self.assertRaises(ValueError):
            self.patch(original, original.replace('type="checkbox"', 'type="text"'))

    def test_incomplete_or_misnested_markup_is_rejected(self):
        for old, new in [('</body>', ''), ('</html>', ''),
                         ('<section class="day" id="day2">', '<div class="day" id="day2">')]:
            with self.subTest(old=old), self.assertRaises(ValueError):
                self.patch(old, new)

    def test_existing_navigation_ids_cannot_be_swapped(self):
        with self.assertRaises(ValueError):
            update.patch_html(self.source, [
                {'old': 'id="day1"', 'new': 'id="day2"'},
                {'old': 'id="day2"', 'new': 'id="day1"'}], self.digest)

    def test_self_closing_nonvoid_html_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'self-closing'):
            self.patch(new='<div/>')

    def test_inert_or_raw_text_wrappers_cannot_hide_the_itinerary(self):
        for tag in ('template', 'textarea', 'xmp', 'plaintext', 'noscript'):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                update.patch_html(self.source, [
                    {'old': '<main>', 'new': f'<{tag}><main>'},
                    {'old': '</main>', 'new': f'</main></{tag}>'}], self.digest)

    def test_new_checkbox_can_be_added_without_resetting_existing_keys(self):
        result = self.patch('</main>', '<label><input type="checkbox" data-check="new-task">新增核对</label></main>')
        self.assertEqual(Document(result.decode()).checks, Document(self.source.decode()).checks + ['new-task'])

    def test_unicode_and_crlf_bytes_are_preserved(self):
        source = b'\xef\xbb\xbf' + self.source.replace(b'\n', b'\r\n')
        result = update.patch_html(source, [{'old': self.old, 'new': '改为休息 ☕ Café'}], sha256(source).hexdigest())
        self.assertEqual(result, source.replace(self.old.encode(), '改为休息 ☕ Café'.encode()))

    def test_plain_text_is_not_accepted_as_html(self):
        source = b'plain text'
        with self.assertRaisesRegex(ValueError, 'html/head/body'):
            update.patch_html(source, [{'old': 'plain', 'new': 'changed'}], sha256(source).hexdigest())

    def test_cli_writes_new_candidate_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, patches, output = root/'source.html', root/'edits.json', root/'candidate.html'
            source.write_bytes(self.source)
            patches.write_text(json.dumps([{'old': self.old, 'new': self.new}]), encoding='utf-8')
            cmd = [sys.executable, str(SCRIPT), '--input', str(source), '--patch', str(patches),
                   '--expected-sha256', self.digest, '--output', str(output)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['facts_and_visuals'], 'not_checked')
            self.assertEqual(source.read_bytes(), self.source)
            candidate = output.read_bytes()
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual(output.read_bytes(), candidate)
            cmd[-1] = str(source)
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual(source.read_bytes(), self.source)
            link = root/'link.html'
            link.symlink_to(source)
            cmd[-1] = str(link)
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual(source.read_bytes(), self.source)

    def test_concurrent_writers_cannot_overwrite_each_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, patches, output = root/'source.html', root/'edits.json', root/'candidate.html'
            source.write_bytes(self.source)
            patches.write_text(json.dumps([{'old': self.old, 'new': self.new}]), encoding='utf-8')
            cmd = [sys.executable, str(SCRIPT), '--input', str(source), '--patch', str(patches),
                   '--expected-sha256', self.digest, '--output', str(output)]
            processes = [subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
            for process in processes:
                process.communicate(timeout=10)
            self.assertEqual(sorted(p.returncode for p in processes), [0, 1])
            self.assertEqual(output.read_bytes(), self.patch())
            self.assertEqual(source.read_bytes(), self.source)

    def test_cli_failure_creates_no_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, patches, output = root/'source.html', root/'edits.json', root/'candidate.html'
            source.write_bytes(self.source)
            patches.write_text('[]')
            result = subprocess.run([sys.executable, str(SCRIPT), '--input', str(source),
                                     '--patch', str(patches), '--expected-sha256', self.digest,
                                     '--output', str(output)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            self.assertEqual(source.read_bytes(), self.source)


if __name__ == '__main__':
    unittest.main()
