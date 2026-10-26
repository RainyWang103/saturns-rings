#!/usr/bin/env python3
"""Offline, guarded literal patches for an existing itinerary; never writes the input.

Checks structure and preserves existing CSS, scripts, IDs and checkbox keys.
This is not a sanitizer, fact checker, visual test or authorization mechanism.
"""
import argparse
from collections import Counter
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


# Strict, explicitly closed template subset; optional-end-tag legacy HTML uses
# the normal delivery workflow instead of being silently repaired by this tool.
VOID_TAGS = frozenset(('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                       'link', 'meta', 'param', 'source', 'track', 'wbr'))


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.ids, self.checks, self.links, self.styles = [], [], [], []
        self.errors = []
        self.tags = Counter()
        self.stack = []
        self.blocks = {'style': [], 'script': []}
        self.active = None
        self.feed(source)
        self.close()
        if self.active:
            self.errors.append('unclosed style/script')
        if self.stack:
            self.errors.append('unclosed element')
        if any(self.tags[tag] != 1 for tag in ('html', 'head', 'body')):
            self.errors.append('expected one html/head/body shell')
        for kind, values in (('id', self.ids), ('data-check', self.checks)):
            if any(not value or re.search(r'\s', value) for value in values):
                self.errors.append(f'empty or whitespace in {kind}')
            if any(count > 1 for count in Counter(values).values()):
                self.errors.append(f'duplicate {kind}')
        for target in self.links:
            if target not in self.ids:
                self.errors.append('unresolved fragment link')
        if re.search(r'\{\{[^{}]*\}\}', source):
            self.errors.append('unfilled template token')

    def handle_starttag(self, tag, attributes):
        self.tags[tag] += 1
        if tag not in VOID_TAGS:
            self.stack.append(tag)
        attrs = dict(attributes)
        if len(attrs) != len(attributes):
            self.errors.append('duplicate attribute')
        for name, value in attributes:
            if name.startswith('on') or name in ('srcdoc', 'srcset'):
                self.errors.append('active or external attribute')
            if name in ('href', 'src', 'xlink:href', 'action', 'formaction'):
                value = value or ''
                if any(ord(c) <= 32 or ord(c) == 127 for c in value):
                    self.errors.append('whitespace/control in URL')
                try:
                    scheme = urlsplit(value).scheme.lower()
                except ValueError:
                    self.errors.append('invalid URL')
                    continue
                if scheme not in ('', 'https', 'http', 'tel', 'mailto'):
                    self.errors.append('unsupported URL scheme')
                if value.startswith('#'):
                    self.links.append(unquote(value[1:]))
        if 'style' in attrs:
            self.styles.append(attrs['style'])
        if 'id' in attrs:
            self.ids.append(attrs['id'] or '')
        if 'data-check' in attrs:
            self.checks.append(attrs['data-check'] or '')
            if tag != 'input' or (attrs.get('type') or '').lower() != 'checkbox':
                self.errors.append('data-check requires a checkbox input')
        if tag in ('iframe', 'object', 'embed', 'base', 'form', 'template',
                   'textarea', 'xmp', 'plaintext', 'noscript', 'noembed',
                   'noframes', 'frameset', 'frame'):
            self.errors.append('unsupported active element')
        if tag == 'meta' and (attrs.get('http-equiv') or '').lower() == 'refresh':
            self.errors.append('redirect metadata')
        if tag == 'link' or (tag in ('script', 'img', 'audio', 'video', 'source', 'input') and 'src' in attrs):
            self.errors.append('external resource element')
        if tag in self.blocks:
            self.blocks[tag].append({'attrs': attributes, 'text': ''})
            self.active = tag

    def handle_startendtag(self, tag, attributes):
        foreign = tag in ('svg', 'math') or any(t in ('svg', 'math') for t in self.stack)
        if tag not in VOID_TAGS and not foreign:
            self.errors.append('self-closing non-void HTML element')
        self.handle_starttag(tag, attributes)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append('mismatched closing element')
        else:
            self.stack.pop()
        if tag == self.active:
            self.active = None

    def handle_data(self, data):
        if self.active:
            self.blocks[self.active][-1]['text'] += data


def patch_html(source_bytes, edits, expected_sha256):
    """Apply non-overlapping unique replacements against one exact source version."""
    if sha256(source_bytes).hexdigest() != expected_sha256:
        raise ValueError('source version changed; reread and review the affected scope')
    source = source_bytes.decode('utf-8')
    before = Document(source)
    if before.errors:
        raise ValueError('baseline failed structural checks: ' + ', '.join(sorted(set(before.errors))))
    if not isinstance(edits, list) or not edits:
        raise ValueError('patch must be a nonempty array')
    spans = []
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {'old', 'new'}:
            raise ValueError('each patch needs exactly old and new')
        old, new = edit['old'], edit['new']
        if not isinstance(old, str) or not isinstance(new, str) or not old or old == new:
            raise ValueError('patch values must be strings and make a change')
        start = source.find(old)
        if start < 0 or source.find(old, start + 1) >= 0:
            raise ValueError('old text must match exactly once; include surrounding context')
        spans.append((start, start + len(old), new))
    spans.sort()
    if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
        raise ValueError('overlapping patches; combine into one reviewed replacement')
    result = source
    for start, end, new in reversed(spans):
        result = result[:start] + new + result[end:]
    after = Document(result)
    errors = list(after.errors)
    if before.blocks != after.blocks or before.styles != after.styles:
        errors.append('CSS/script changed (including trip storage key)')
    for kind, original, changed in (('IDs', before.ids, after.ids),
                                    ('checkbox keys', before.checks, after.checks)):
        original_set = set(original)
        if [value for value in changed if value in original_set] != original:
            errors.append(f'existing {kind} removed, renamed or reordered')
    if errors:
        raise ValueError('updated document failed checks: ' + ', '.join(sorted(set(errors))))
    return result.encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--patch', required=True, type=Path, help='JSON array of literal old/new replacements')
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path, help='new local candidate file, must not exist')
    args = parser.parse_args()
    try:
        # Read only; do not follow a write path to an existing file or symlink.
        data = args.input.read_bytes()
        edits = json.loads(args.patch.read_text(encoding='utf-8'))
        updated = patch_html(data, edits, args.expected_sha256)
        with args.output.open('xb') as stream:
            stream.write(updated)
    except (ValueError, OSError) as exc:
        print(f'Update rejected: {exc}', file=sys.stderr)
        return 1
    print(json.dumps({'sha256': sha256(updated).hexdigest(), 'bytes': len(updated),
                      'patches': len(edits), 'structural_checks': 'passed',
                      'facts_and_visuals': 'not_checked'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
