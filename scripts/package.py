"""Build an explicitly allowlisted source ZIP, never a copy of the workspace."""
from pathlib import Path
import argparse
import hashlib
from zipfile import ZipFile, ZIP_DEFLATED

ROOT_FILES = {'README.md', 'LICENSE', 'pyproject.toml', 'requirements.lock',
              'requirements-dev.lock', 'requirements-build.lock', 'install.sh', 'install.ps1', '.gitignore',
              'INSTALL_WITH_AI.md', 'PRODUCT.md', 'DESIGN.md'}


def build_archive(root: Path, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for file in sorted(root.rglob('*')):
            relative = file.relative_to(root)
            if file.is_symlink() or any(p.is_symlink() for p in file.parents if p != root):
                continue
            if not file.is_file() or any(p in {'.git','.venv','__pycache__','.superpowers','dist','build'} for p in relative.parts):
                continue
            allowed = str(relative) in ROOT_FILES
            allowed |= relative.parts[0] in {'src','scripts','tests'} and file.suffix in {'.py','.html'}
            allowed |= relative.parts[:2] == ('assets', 'branding') and file.suffix in {'.svg','.png','.md','.txt'}
            allowed |= relative.as_posix() in {'.impeccable/design.json', '.impeccable/surfaces/readme.md'}
            allowed |= relative.parts[0] == 'docs' and file.suffix in {'.md','.txt'}
            allowed |= relative.as_posix() == '.github/workflows/tests.yml'
            if allowed:
                archive.write(file, 'teams-facultad-mcp/' + relative.as_posix())
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('dist/teams-facultad-mcp-0.1.0.zip'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    file = build_archive(root, args.output.resolve())
    print(file)
    print('SHA256:', hashlib.sha256(file.read_bytes()).hexdigest())
