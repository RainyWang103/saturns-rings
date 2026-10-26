"""Keep offline replay telemetry truthful and bounded to its supplied materials."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).parent/'cases/travel-planner/replay_materials.py'


class ReplayMaterialsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.materials = self.root/'materials'
        self.materials.mkdir()
        (self.materials/'rule.md').write_text('按目标日期核实。', encoding='utf-8')
        self.session = self.root/'session'
        self.session.mkdir()
        self.input = self.root/'input.md'
        self.input.write_text('虚构旅行任务', encoding='utf-8')
        (self.session/'config.json').write_text(json.dumps({'variant_root':str(self.materials),'input':str(self.input)}))

    def call(self, *args):
        return subprocess.run([sys.executable,str(SCRIPT),str(self.session),*args],capture_output=True,text=True)

    def test_read_counts_bytes_and_finish_hashes_output(self):
        self.assertEqual(self.call('start').returncode,0)
        self.assertEqual(self.call('read','@input','rule.md').returncode,0)
        (self.session/'output.md').write_text('草案',encoding='utf-8')
        self.assertEqual(self.call('finish','output.md').returncode,0)
        events=[json.loads(line) for line in (self.session/'events.jsonl').read_text().splitlines()]
        self.assertEqual([e['action'] for e in events],['start','read','read','finish'])
        self.assertEqual(events[1]['bytes'],len(self.input.read_bytes()))
        self.assertEqual(events[2]['bytes'],len((self.materials/'rule.md').read_bytes()))
        self.assertGreaterEqual(events[-1]['monotonic'],events[0]['monotonic'])
        self.assertEqual(len(events[-1]['sha256']),64)
        self.assertNotIn('model_time',events[-1])

    def test_restart_and_path_escape_are_rejected(self):
        self.assertEqual(self.call('start').returncode,0)
        self.assertNotEqual(self.call('start').returncode,0)
        self.assertNotEqual(self.call('read','../input.md').returncode,0)
        self.assertNotEqual(self.call('finish','../input.md').returncode,0)
        (self.materials/'escape.md').symlink_to(self.input)
        self.assertNotEqual(self.call('read','escape.md').returncode,0)

    def test_missing_start_produces_no_fake_read_or_finish(self):
        self.assertNotEqual(self.call('read','rule.md').returncode,0)
        self.assertNotEqual(self.call('finish','output.md').returncode,0)
        self.assertFalse((self.session/'events.jsonl').exists())


class ResearchFixtureTests(unittest.TestCase):
    script = Path(__file__).parent/'cases/travel-planner/replay_research.py'

    def call(self, session, key):
        return subprocess.run([sys.executable,str(self.script),'--session',str(session),'--query',key],capture_output=True,text=True)

    def test_faults_and_session_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = Path(tmp)/'first'
            first = self.call(session,'hotel-b')
            self.assertEqual(first.returncode,75)
            self.assertEqual(json.loads(first.stdout)['status'],'transient_error')
            self.assertEqual(json.loads(self.call(session,'hotel-b').stdout)['status'],'ok')
            self.assertEqual(self.call(session,'gallery').returncode,77)
            self.assertEqual(json.loads(self.call(session,'festival').stdout)['status'],'unpublished')
            self.assertEqual(self.call(Path(tmp)/'second','hotel-b').returncode,75)

    def test_parallel_requests_do_not_lose_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd=[sys.executable,str(self.script),'--session',tmp,'--query','hotel-b']
            ps=[subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(2)]
            for p in ps:
                p.communicate(timeout=10)
            self.assertEqual(sorted(p.returncode for p in ps),[0,75])
            counts=json.loads((Path(tmp)/'research-counts.json').read_text())
            self.assertEqual(counts['hotel-b'],2)
            events=[json.loads(line) for line in (Path(tmp)/'research-events.jsonl').read_text().splitlines()]
            self.assertEqual([e['attempt'] for e in events],[1,2])


if __name__ == '__main__':
    unittest.main()
