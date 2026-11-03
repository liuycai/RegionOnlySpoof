#!/usr/bin/python3
"""One bounded region-qualification refresh per boot; no policy overrides."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import plistlib
import re
import signal
import subprocess
import time

VERSION = '1.0.0'
STATE_DIR = Path('/Library/Application Support/RegionOnlySpoofRefresh')
STATE_PATH = STATE_DIR / 'state.json'
LOCK_PATH = STATE_DIR / 'refresh.lock'
NOTIFICATION = 'AppleLanguagePreferencesChangedNotification'
LABEL = 'com.local.regiononlyspoof.refresh'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class System:
    def command(self, args):
        return subprocess.run(args, capture_output=True, timeout=8)

    def boot(self):
        p = self.command(['/usr/sbin/sysctl', '-n', 'kern.bootsessionuuid'])
        if p.returncode or not p.stdout.strip():
            raise RuntimeError('Cannot identify current boot; refusing to signal')
        return p.stdout.decode().strip()

    def region(self):
        p = self.command(['/usr/sbin/ioreg', '-a', '-r', '-d', '1', '-c', 'IOPlatformExpertDevice'])
        if p.returncode:
            return None
        entries = plistlib.loads(p.stdout)
        raw = entries[0].get('region-info', b'') if entries else b''
        return raw.rstrip(b'\0').decode('ascii', errors='replace') if isinstance(raw, bytes) else None

    def answers(self):
        try:
            raw = plistlib.loads(Path('/private/var/db/eligibilityd/eligibility.plist').read_bytes())
        except (FileNotFoundError, plistlib.InvalidFileException):
            return {}
        return {k: raw.get('OS_ELIGIBILITY_DOMAIN_' + k) for k in
                ('GREYMATTER', 'FOUNDATION_MODELS', 'AMERICIUM')}

    def pid(self):
        p = self.command(['/bin/launchctl', 'print', 'system/com.apple.eligibilityd'])
        if p.returncode:
            raise RuntimeError('Cannot inspect eligibilityd service')
        match = re.search(rb'^\s*pid = (\d+)\s*$', p.stdout, re.MULTILINE)
        return int(match.group(1)) if match else None

    def verify_path(self, pid):
        p = self.command(['/bin/ps', '-p', str(pid), '-o', 'comm='])
        return p.returncode == 0 and p.stdout.strip() == b'/usr/libexec/eligibilityd'

    def terminate(self, pid):
        os.kill(pid, signal.SIGTERM)

    def notify(self):
        p = self.command(['/usr/bin/notifyutil', '-p', NOTIFICATION])
        if p.returncode:
            raise RuntimeError('Demand-start notification rejected: ' + p.stderr.decode(errors='replace').strip())

    def now(self):
        return time.monotonic()

    def sleep(self, seconds):
        time.sleep(seconds)


def qualified(answers):
    gm = answers.get('GREYMATTER') or {}
    return (gm.get('os_eligibility_answer_t') == 4 and
            gm.get('status', {}).get('OS_ELIGIBILITY_INPUT_DEVICE_REGION_CODE') == 3)


def region_status(answers):
    return (answers.get('GREYMATTER') or {}).get('status', {}).get('OS_ELIGIBILITY_INPUT_DEVICE_REGION_CODE')


def refresh(system, previous, checkpoint, wait_seconds=90, settle_seconds=20):
    boot = system.boot()
    if previous.get('bootSession') == boot and previous.get('attempted'):
        return dict(previous, lastInvocationUTC=utc(), lastInvocationOutcome='already_attempted_this_boot')
    result = {'schema': 1, 'helperVersion': VERSION, 'bootSession': boot,
              'startedUTC': utc(), 'attempted': False, 'signalAttempts': 0,
              'notificationPosts': 0}
    began = system.now()
    deadline = began + wait_seconds
    while True:
        current_region = system.region()
        answers = system.answers()
        if current_region == 'LL/A':
            if qualified(answers):
                return dict(result, outcome='already_eligible', afterEligibility=answers)
            if system.now() - began >= settle_seconds:
                if region_status(answers) == 2 or (not answers and system.pid() is None):
                    break
                if region_status(answers) is not None:
                    return dict(result, outcome='not_a_device_region_block', afterEligibility=answers)
        if system.now() >= deadline:
            return dict(result, outcome='preconditions_timeout', observedRegion=current_region,
                        afterEligibility=answers)
        system.sleep(1)

    # Recheck immediately before claiming the single per-boot attempt.
    if system.region() != 'LL/A':
        return dict(result, outcome='region_changed_no_action')
    answers = system.answers()
    if qualified(answers):
        return dict(result, outcome='already_eligible', afterEligibility=answers)
    if answers and region_status(answers) != 2:
        return dict(result, outcome='not_a_device_region_block', afterEligibility=answers)
    old_pid = system.pid()
    if old_pid and not system.verify_path(old_pid):
        return dict(result, outcome='process_identity_not_verified')
    if system.pid() != old_pid:
        return dict(result, outcome='process_changed_no_action')
    result.update(attempted=True, phase='action_started', beforePID=old_pid,
                  beforeEligibility=answers)
    # Persist BEFORE sending a signal, so a crash/relaunch cannot repeat it.
    checkpoint(result)
    try:
        if old_pid:
            result['signalAttempts'] = 1
            system.terminate(old_pid)
            exit_deadline = system.now() + 10
            while system.pid() == old_pid and system.now() < exit_deadline:
                system.sleep(0.5)
            if system.pid() == old_pid:
                return dict(result, phase='finished', outcome='old_process_did_not_exit',
                            finishedUTC=utc())
        if system.pid() is None:
            result['notificationPosts'] = 1
            system.notify()
        ready_deadline = system.now() + 30
        while True:
            new_pid = system.pid()
            after = system.answers()
            if new_pid and new_pid != old_pid and qualified(after):
                return dict(result, phase='finished', outcome='eligible_after_refresh',
                            afterPID=new_pid, afterEligibility=after, finishedUTC=utc())
            if system.now() >= ready_deadline:
                return dict(result, phase='finished', outcome='refresh_not_confirmed',
                            afterPID=new_pid, afterEligibility=after, finishedUTC=utc())
            system.sleep(0.5)
    except Exception as exc:
        return dict(result, phase='finished', outcome='action_failed', error=str(exc), finishedUTC=utc())


def save_state(value):
    temporary = STATE_DIR / ('state-' + str(os.getpid()) + '.tmp')
    with temporary.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    temporary.chmod(0o644)
    os.replace(temporary, STATE_PATH)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='read-only snapshot; never signal, notify or save state')
    args = parser.parse_args()
    system = System()
    if args.check:
        print(json.dumps({'helperVersion': VERSION, 'bootSession': system.boot(),
                          'region': system.region(), 'pid': system.pid(),
                          'eligibility': system.answers(), 'readOnly': True},
                         ensure_ascii=False, indent=2))
        return 0
    if os.geteuid() != 0:
        print('Administrator privileges required; no action taken.')
        return 1
    # Installer creates this root-owned, non-group/world-writable directory.
    st = STATE_DIR.stat()
    if st.st_uid != 0 or st.st_mode & 0o022:
        raise RuntimeError('Unsafe state directory ownership or mode')
    fd = os.open(str(LOCK_PATH), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'r+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Another refresh invocation is active; no action taken.')
            return 0
        # Invalid state fails closed rather than risking a repeated signal.
        previous = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
        result = refresh(system, previous, save_state)
        save_state(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0 if result.get('outcome') in ('already_eligible', 'eligible_after_refresh') or result.get('lastInvocationOutcome') == 'already_attempted_this_boot' else 2


if __name__ == '__main__':
    raise SystemExit(main())
