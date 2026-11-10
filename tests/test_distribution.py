from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import zipfile


def load_packager():
    spec = spec_from_file_location('packager', Path('scripts/package.py'))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_archive_excludes_profiles_configs_and_symlinks(tmp_path):
    root = tmp_path / 'source'
    (root / 'src' / 'teams_facultad_mcp').mkdir(parents=True)
    (root / 'src' / 'teams_facultad_mcp' / '__init__.py').write_text('')
    (root / 'README.md').write_text('hello')
    (root / 'profiles').mkdir()
    (root / 'profiles' / 'Cookies').write_text('SECRET')
    (root / 'mcp-config.json').write_text('PRIVATE')
    (root / 'src' / 'teams_facultad_mcp' / 'leak.py').symlink_to(root / 'profiles' / 'Cookies')
    output = tmp_path / 'out.zip'
    load_packager().build_archive(root, output)
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert names == ['teams-facultad-mcp/README.md', 'teams-facultad-mcp/src/teams_facultad_mcp/__init__.py']
        assert all(b'SECRET' not in archive.read(name) for name in names)


def test_install_scripts_are_present_and_no_automatic_privilege_escalation():
    for name in ['install.sh','install.ps1','scripts/install.py']:
        text = Path(name).read_text()
        assert 'sudo ' not in text
    assert 'requirements.lock' in Path('scripts/install.py').read_text()
