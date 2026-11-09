import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent
manifest=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
for relative,digest in manifest['sha256'].items():
    path=(root/relative).resolve()
    assert path.is_relative_to(root),relative
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,relative
print('Verified',len(manifest['sha256']),'publication files.')
