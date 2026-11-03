#!/usr/bin/python3
"""Install/remove only the local once-per-boot refresh helper."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
LABEL = 'com.local.regiononlyspoof.refresh'
PLIST = Path('/Library/LaunchDaemons/' + LABEL + '.plist')
HELPER = Path('/Library/PrivilegedHelperTools/' + LABEL + '.py')
STATE_DIR = Path('/Library/Application Support/RegionOnlySpoofRefresh')
LOG = Path('/Library/Logs/RegionOnlySpoofRefresh.log')
# Only these exact previously prepared helpers are eligible for an upgrade.
PREVIOUS_HELPER_SHA256 = {
    '53ab75c8f4a6e591ad3fe87f5c17d3e82423552d3dd7e1e34206172ff799ffed',
    '73ec73f7192d26fa4bdb54396b7ebb002ab2c63723c5ce1b90f393eb33fff235',
    '251d9d6e62570f7ac084cb996384a0e39357b4c3b0d443973a546e7b14a5380b',
}


def command(args):
    return subprocess.run(args, capture_output=True, text=True, timeout=15)


def service():
    p = command(['/bin/launchctl', 'print', 'system/' + LABEL])
    if p.returncode:
        if 'could not find service' in (p.stdout + p.stderr).lower():
            return None
        raise RuntimeError('Cannot inspect helper registration: ' + p.stderr.strip())
    return p.stdout


def package():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    files = {}
    for name in ('helper.py', LABEL + '.plist'):
        p = ROOT / name
        if p.is_symlink():
            raise RuntimeError('Source must not be a symlink: ' + name)
        data = p.read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest[name]:
            raise RuntimeError('Package checksum mismatch: ' + name)
        files[name] = data
    config = plistlib.loads(files[LABEL + '.plist'])
    expected_args = ['/usr/bin/python3', '-I', str(HELPER)]
    if (config.get('Label') != LABEL or config.get('ProgramArguments') != expected_args
            or config.get('RunAtLoad') is not True or config.get('KeepAlive') is not False
            or 'StartInterval' in config or 'StartCalendarInterval' in config):
        raise RuntimeError('Unexpected launch configuration')
    return files


def check_managed(path, data):
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or not path.is_file():
        raise RuntimeError('Unexpected destination type: ' + str(path))
    st = path.stat()
    existing = path.read_bytes()
    known_previous = path == HELPER and hashlib.sha256(existing).hexdigest() in PREVIOUS_HELPER_SHA256
    if st.st_uid != 0 or st.st_mode & 0o022 or (existing != data and not known_previous):
        raise RuntimeError('Existing file is not this managed package; refusing to overwrite: ' + str(path))


def write_root_file(path, data, mode):
    fd, temporary = tempfile.mkstemp(prefix='.' + LABEL + '-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchown(stream.fileno(), 0, 0)
            os.fchmod(stream.fileno(), mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def status():
    registration = service()
    state = json.loads((STATE_DIR / 'state.json').read_text()) if (STATE_DIR / 'state.json').exists() else None
    fields = {}
    if registration:
        for key in ('state', 'runs', 'pid', 'last exit code'):
            match = re.search(r'^\s*' + re.escape(key) + r' = (.*)$', registration, re.MULTILINE)
            if match:
                fields[key] = match.group(1)
    version_match = re.search(rb"^VERSION = '([0-9.]+)'$", HELPER.read_bytes(), re.MULTILINE) if HELPER.exists() else None
    result = {'installedFiles': {'helper': HELPER.exists(), 'plist': PLIST.exists()},
              'installedHelperVersion': version_match.group(1).decode() if version_match else None,
              'registered': registration is not None, 'job': fields,
              'lastRun': state, 'log': str(LOG)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


def install():
    files = package()
    check_managed(HELPER, files['helper.py'])
    check_managed(PLIST, files[LABEL + '.plist'])
    registration = service()
    upgrading = HELPER.exists() and HELPER.read_bytes() != files['helper.py']
    if STATE_DIR.exists() or STATE_DIR.is_symlink():
        if STATE_DIR.is_symlink() or not STATE_DIR.is_dir():
            raise RuntimeError('Unsafe state directory')
        st = STATE_DIR.stat()
        if st.st_uid != 0 or st.st_mode & 0o022:
            raise RuntimeError('State directory must be owned by root and not writable by others')
    else:
        STATE_DIR.mkdir(mode=0o755)
    os.chown(STATE_DIR, 0, 0)
    if LOG.exists() or LOG.is_symlink():
        if LOG.is_symlink() or not LOG.is_file() or LOG.stat().st_uid != 0 or LOG.stat().st_mode & 0o022:
            raise RuntimeError('Unsafe log file')
    else:
        fd = os.open(str(LOG), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        os.fchown(fd, 0, 0)
        os.close(fd)
    if registration is not None and upgrading:
        p = command(['/bin/launchctl', 'bootout', 'system/' + LABEL])
        if p.returncode:
            raise RuntimeError('Cannot unload old helper; files retained: ' + p.stderr.strip())
        registration = None
    write_root_file(HELPER, files['helper.py'], 0o755)
    write_root_file(PLIST, files[LABEL + '.plist'], 0o644)
    if registration is None:
        p = command(['/bin/launchctl', 'bootstrap', 'system', str(PLIST)])
        if p.returncode:
            raise RuntimeError('Files installed, but bootstrap failed: ' + p.stderr.strip())
    print('Installed once-per-boot task. No reboot or security-policy change performed.')
    status()


def uninstall():
    files = package()
    check_managed(HELPER, files['helper.py'])
    check_managed(PLIST, files[LABEL + '.plist'])
    if service() is not None:
        p = command(['/bin/launchctl', 'bootout', 'system/' + LABEL])
        if p.returncode:
            raise RuntimeError('Cannot unload helper; files retained: ' + p.stderr.strip())
    for path in (PLIST, HELPER):
        if path.exists():
            path.unlink()
    print('Automatic task removed. Existing region extension, logs and state retained.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('install', 'uninstall', 'status'))
    args = parser.parse_args()
    if args.action != 'status' and os.geteuid() != 0:
        raise SystemExit('Administrator privileges required; no files changed.')
    if args.action == 'install':
        install()
    elif args.action == 'uninstall':
        uninstall()
    else:
        status()


if __name__ == '__main__':
    main()
