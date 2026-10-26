"""Prepare fictional full and partial-update HTML for the same browser checks."""
import argparse
from hashlib import sha256
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fixture = runpy.run_path(str(Path(__file__).with_name('render_delivery_fixture.py')))
    updater = runpy.run_path(str(ROOT / 'shared/travel-planner/scripts/update_html.py'))
    original = fixture['render']().encode('utf-8')
    old = fixture['DAYS'][1]['logic']
    new = old + ' 如遇降雨，取消户外散步；音乐会与午后休息保持。'
    updated = updater['patch_html'](original, [{'old': old, 'new': new}], sha256(original).hexdigest())
    args.output.mkdir(parents=True, exist_ok=True)
    for name, data in [('original.html', original), ('updated.html', updated)]:
        with (args.output / name).open('xb') as stream:
            stream.write(data)
    print('Rendered fictional original and updated itineraries.')


if __name__ == '__main__':
    main()
