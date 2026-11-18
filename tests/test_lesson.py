"""Real local trusted adapters; script-free HTML parsed without a browser."""
import copy
from html.parser import HTMLParser
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from timeedge import compare, lesson

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / 'examples' / 'compare'


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.attributes = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)


@unittest.skipUnless(os.name == 'posix' and shutil.which('node'), 'Real adapters require POSIX and Node; skip is not pass.')
class LessonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = tempfile.TemporaryDirectory()
        cls.bundle = Path(cls.shared.name) / 'bundle'
        cls.report = compare.run(EX / 'suite.json', EX / 'python_adapter.py', EX / 'node_adapter.js', cls.bundle, True, 2)

    @classmethod
    def tearDownClass(cls):
        cls.shared.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.output = self.path / 'lesson.html'

    def test_real_build_verify_and_full_case_coverage(self):
        with patch.object(compare, 'execute', side_effect=AssertionError('must not execute')):
            a = lesson.build(self.bundle, self.output)
            self.assertEqual(a, lesson.verify(self.bundle, self.output))
        parser = Tags()
        parser.feed(self.output.read_text())
        self.assertEqual(parser.tags.count('details'), 7)
        self.assertNotIn('script', parser.tags)
        self.assertNotIn('a', parser.tags)
        self.assertNotIn('img', parser.tags)
        for case in self.report['cases']:
            self.assertIn(case['case_id'], self.output.read_text())
        if os.name == 'posix':
            self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)

    def test_html_tamper(self):
        lesson.build(self.bundle, self.output)
        original = self.output.read_bytes()
        for extra in (b'<script>alert(1)</script>', b'<img src="https://example.invalid">', b'2027'):
            self.output.write_bytes(original + extra)
            with self.assertRaises(ValueError):
                lesson.verify(self.bundle, self.output)

    def test_bundle_tamper_no_output(self):
        bundle = self.path / 'bundle'
        shutil.copytree(self.bundle, bundle)
        for name in compare.FILES:
            target = bundle / name
            original = target.read_bytes()
            target.write_bytes(original + b' ')
            with self.assertRaises(ValueError):
                lesson.build(bundle, self.output)
            self.assertFalse(self.output.exists())
            target.write_bytes(original)

    def test_untrusted_text_and_runtime_status(self):
        report = copy.deepcopy(self.report)
        payload = '</pre><script>alert(1)</script><img src="https://example.invalid">![x](https://example.invalid)'
        report['cases'][0]['semantics']['note'] = payload
        report['cases'][0]['sides']['node'].update(execution_status='launch_error', assertion='execution_error', observation=None, adapter_runtime=None)
        report['cases'][0]['field_differences'] = None
        data = lesson.render(report).decode()
        parser = Tags()
        parser.feed(data)
        self.assertNotIn('script', parser.tags)
        self.assertNotIn('img', parser.tags)
        self.assertFalse(any(k in ('href', 'src') or k.startswith('on') for k, _ in parser.attributes))
        self.assertIn('No successful response recorded', data)
        self.assertIn('execution_error', data)
        self.assertIn('null means comparison unavailable', data)
        self.assertIn('default-src', data)

    def test_existing_directory_and_file_preserved(self):
        self.output.write_bytes(b'keep')
        with self.assertRaises(OSError):
            lesson.build(self.bundle, self.output)
        self.assertEqual(self.output.read_bytes(), b'keep')
        with self.assertRaises(OSError):
            lesson.build(self.bundle, self.path)

    def test_symlink_and_fifo_rejected(self):
        target = self.path / 'missing'
        self.output.symlink_to(target)
        with self.assertRaises(OSError):
            lesson.build(self.bundle, self.output)
        self.assertFalse(target.exists())
        with self.assertRaises(ValueError):
            lesson.verify(self.bundle, self.output)
        self.output.unlink()
        os.mkfifo(self.output)
        with self.assertRaises(ValueError):
            lesson.verify(self.bundle, self.output)

    def test_limits_before_creation(self):
        with patch.object(lesson, 'LIMIT', 1):
            with self.assertRaises(ValueError):
                lesson.build(self.bundle, self.output)
        self.assertFalse(self.output.exists())

    def test_cli_and_conflict(self):
        args = [sys.executable, '-m', 'timeedge.lesson', 'build', str(self.bundle), str(self.output)]
        first = subprocess.run(args, cwd=ROOT, capture_output=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = subprocess.run(args, cwd=ROOT, capture_output=True)
        self.assertEqual(second.returncode, 2)
        args[3] = 'verify'
        verified = subprocess.run(args, cwd=ROOT, capture_output=True)
        self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_unknown_version_rejected(self):
        bundle = self.path / 'bundle'
        shutil.copytree(self.bundle, bundle)
        receipt = compare.parse((bundle / 'receipt.json').read_bytes(), compare.OUT_LIMIT)
        receipt['version'] = 'future'
        (bundle / 'receipt.json').write_bytes(compare.canonical(receipt))
        with self.assertRaises(ValueError):
            lesson.build(bundle, self.output)
        self.assertFalse(self.output.exists())

    def test_concurrent_cli_one_creator(self):
        args = [sys.executable, '-m', 'timeedge.lesson', 'build', str(self.bundle), str(self.output)]
        children = [subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(3)]
        for child in children:
            child.communicate(timeout=20)
        self.assertEqual(sorted(child.returncode for child in children), [0, 2, 2])
        lesson.verify(self.bundle, self.output)

    def test_partial_write_retained_and_not_valid(self):
        real_fdopen = os.fdopen

        class Broken:
            def __init__(self, fd, mode):
                self.file = real_fdopen(fd, mode)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.file.close()
            def write(self, data):
                self.file.write(data[:30])
                raise OSError('synthetic write failure')

        with patch.object(lesson.os, 'fdopen', side_effect=lambda fd, mode: Broken(fd, mode) if mode == 'wb' else real_fdopen(fd, mode)):
            with self.assertRaises(OSError):
                lesson.build(self.bundle, self.output)
        self.assertEqual(self.output.stat().st_size, 30)
        with self.assertRaises(ValueError):
            lesson.verify(self.bundle, self.output)
        with self.assertRaises(OSError):
            lesson.build(self.bundle, self.output)
