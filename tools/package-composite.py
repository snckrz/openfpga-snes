"""Package a Composite Blend build after checking its Quartus reports."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--results', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
config = json.loads((root / 'tools/composite-release.json').read_text())
spec = importlib.util.spec_from_file_location('pocketpublish_package', root / 'tools/vendor/pocketpublish_package.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
args.output.mkdir(parents=True, exist_ok=True)
sha = lambda data: hashlib.sha256(data).hexdigest()
table = bytes(int(f'{value:08b}'[::-1], 2) for value in range(256))
report = {}

for variant in config['variants']:
    folder = args.results / variant['folder']
    prefix = variant['report_prefix']
    log = (folder / 'build.log').read_text()
    if 'Quartus Prime Full Compilation was successful. 0 errors' not in log:
        raise RuntimeError(f"Compilation failed: {variant['name']}")
    if 'Critical Warning (127003)' in log:
        raise RuntimeError('Missing memory initialization file')
    if 'Fitter Status : Successful' not in (folder / (prefix + '.fit.summary')).read_text():
        raise RuntimeError('FPGA fitting failed')
    timing = (folder / (prefix + '.sta.summary')).read_text()
    entries = re.findall(r'Type\s+: (.+)\nSlack : ([-.0-9]+)\nTNS\s+: ([-.0-9]+)', timing)
    if not entries or any(float(slack) < 0 or float(tns) < 0 for _, slack, tns in entries):
        raise RuntimeError(f"Timing requirements not met: {variant['name']}")
    full = (folder / (prefix + '.sta.rpt')).read_text()
    if not re.search(r'; Unconstrained Clocks\s*;\s*0\s*;\s*0\s*;', full):
        raise RuntimeError('Unconstrained clocks require investigation')
    report[variant['name']] = {'minimum_reported_slack_ns': min(float(s) for _, s, _ in entries)}

with tempfile.TemporaryDirectory(prefix='pocket-composite-') as temp:
    stage = Path(temp) / 'stage'
    shutil.copytree(root / 'pkg/pocket', stage)
    helper.clean_up_files({'release': {'folders': {'stage_folder': str(stage)}}})
    core = stage / 'Cores' / config['core_id']
    metadata = json.loads((core / 'core.json').read_text())
    metadata['core']['metadata']['version'] = config['version']
    metadata['core']['metadata']['date_release'] = config['build_date']
    (core / 'core.json').write_text(json.dumps(metadata, indent=2) + '\n')
    for variant in config['variants']:
        original = args.results / variant['folder'] / variant['rbf']
        target = core / variant['rev']
        if original.stat().st_size < 1_000_000:
            raise RuntimeError('Unexpectedly small FPGA bitstream')
        helper.reverse_bitstream(str(original), str(target))
        if target.read_bytes().translate(table) != original.read_bytes():
            raise RuntimeError('Bit reversal failed')
    # Include the license and reviewed release documentation with every download.
    documentation = stage / 'Documentation' / config['core_id']
    for relative in ['LICENSE', 'README.md',
                     'docs/COMPOSITE_BUILD.md']:
        destination = documentation / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, destination)
    menu = json.loads((core / 'interact.json').read_text())['interact']['variables']
    ids = [item['id'] for item in menu if 'id' in item]
    if len(ids) != len(set(ids)):
        raise RuntimeError('Duplicate menu IDs')
    if not any(item.get('name') == 'Composite Blend' and item.get('address') == config['bridge_address'] for item in menu):
        raise RuntimeError('Missing Composite Blend menu')
    hashes = {}
    for path in stage.rglob('*'):
        if path.suffix == '.json':
            json.loads(path.read_text())
        if path.is_file():
            hashes[path.relative_to(stage).as_posix()] = sha(path.read_bytes())
    package = args.output / config['package']
    helper.create_zip_file(str(stage), str(package))
    with zipfile.ZipFile(package) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('ZIP integrity failed')
    manifest = {'base_commit': config['base_commit'], 'version': config['version'],
                'quartus_image': config['quartus_image'], 'timing': report,
                'package': package.name, 'package_sha256': sha(package.read_bytes()), 'sha256': hashes}
    (args.output / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (args.output / 'SHA256SUMS.txt').write_text(f"{manifest['package_sha256']}  {package.name}\n")
    print('Verified package:', package)
