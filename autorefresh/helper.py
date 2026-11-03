#!/usr/bin/python3
"""One bounded qualification rebuild after the region driver's ready event."""
import argparse
import ctypes
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
from xml.parsers.expat import ExpatError

VERSION = '1.2.0'
STATE_DIR = Path('/Library/Application Support/RegionOnlySpoofRefresh')
STATE_PATH = STATE_DIR / 'state.json'
LOCK_PATH = STATE_DIR / 'refresh.lock'
NOTIFICATION = 'AppleLanguagePreferencesChangedNotification'
LABEL = 'com.local.regiononlyspoof.refresh'
EXTENSION = 'com.local.RegionOnlySpoof'
DRIVER_CLASS = b'com_local_RegionOnlySpoof'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def completed_marker(value):
    """Completion barrier, independent of the region value and write results."""
    if not isinstance(value, dict) or value.get('schema') != 1:
        return None
    keys = ('startTicks', 'regionBeforeTicks', 'regionAfterTicks',
            'originBeforeTicks', 'originAfterTicks', 'sampleTicks')
    ticks = [value.get(key) for key in keys]
    if not all(type(t) is int and t > 0 for t in ticks) or ticks != sorted(ticks):
        return None
    if any(value.get(key) not in (0, 1) for key in ('regionWriteOK', 'originWriteOK')):
        return None
    # Do not include original hardware properties or other registry fields.
    return {key: value[key] for key in ('schema',) + keys + ('regionWriteOK', 'originWriteOK')}


class IOKitReadiness:
    """Public IOKit matching notification, including already-published services."""
    CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint32)

    def __init__(self, driver_class=DRIVER_CLASS):
        self.driver_class = driver_class
        self.io = ctypes.CDLL('/System/Library/Frameworks/IOKit.framework/IOKit')
        self.cf = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        ptr, u32, integer = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int
        def bind(lib, name, result, *args):
            fn = getattr(lib, name)
            fn.restype, fn.argtypes = result, list(args)
        bind(self.io, 'IOServiceMatching', ptr, ctypes.c_char_p)
        bind(self.io, 'IOServiceGetMatchingServices', integer, u32, ptr, ctypes.POINTER(u32))
        bind(self.io, 'IOServiceAddMatchingNotification', integer, ptr, ctypes.c_char_p,
             ptr, self.CALLBACK, ptr, ctypes.POINTER(u32))
        bind(self.io, 'IOIteratorNext', u32, u32)
        bind(self.io, 'IOObjectRelease', integer, u32)
        bind(self.io, 'IORegistryEntryGetParentEntry', integer, u32, ctypes.c_char_p, ctypes.POINTER(u32))
        bind(self.io, 'IORegistryEntryGetRegistryEntryID', integer, u32, ctypes.POINTER(ctypes.c_uint64))
        bind(self.io, 'IORegistryEntryCreateCFProperty', ptr, u32, ptr, ptr, u32)
        bind(self.io, 'IONotificationPortCreate', ptr, u32)
        bind(self.io, 'IONotificationPortDestroy', None, ptr)
        bind(self.io, 'IONotificationPortGetRunLoopSource', ptr, ptr)
        bind(self.cf, 'CFStringCreateWithCString', ptr, ptr, ctypes.c_char_p, u32)
        bind(self.cf, 'CFPropertyListCreateData', ptr, ptr, ptr, ctypes.c_long, ctypes.c_ulong, ptr)
        bind(self.cf, 'CFDataGetLength', ctypes.c_long, ptr)
        bind(self.cf, 'CFDataGetBytePtr', ptr, ptr)
        bind(self.cf, 'CFRelease', None, ptr)
        bind(self.cf, 'CFRunLoopGetCurrent', ptr)
        bind(self.cf, 'CFRunLoopAddSource', None, ptr, ptr, ptr)
        bind(self.cf, 'CFRunLoopRemoveSource', None, ptr, ptr, ptr)
        bind(self.cf, 'CFRunLoopRunInMode', integer, ptr, ctypes.c_double, ctypes.c_bool)
        bind(self.cf, 'CFRunLoopStop', None, ptr)
        self.mode = ctypes.c_void_p.in_dll(self.cf, 'kCFRunLoopDefaultMode').value

    def matching(self):
        value = self.io.IOServiceMatching(self.driver_class)
        if not value:
            raise RuntimeError('Cannot create driver match dictionary')
        return value  # Consumed by the matching API.

    def inspect(self, service):
        parent = ctypes.c_uint32()
        if self.io.IORegistryEntryGetParentEntry(service, b'IOService', ctypes.byref(parent)):
            return None
        key = prop = data = None
        try:
            key = self.cf.CFStringCreateWithCString(None, b'RegionOnlySpoofTiming', 0x08000100)
            if not key:
                raise RuntimeError('Cannot create completion property key')
            prop = self.io.IORegistryEntryCreateCFProperty(parent.value, key, None, 0)
            if not prop:
                return None
            data = self.cf.CFPropertyListCreateData(None, prop, 200, 0, None)
            if not data:
                return None
            length = self.cf.CFDataGetLength(data)
            if not 0 < length <= 65536:
                return None
            raw = ctypes.string_at(self.cf.CFDataGetBytePtr(data), length)
            marker = completed_marker(plistlib.loads(raw))
            if marker is None:
                return None
            entry_id = ctypes.c_uint64()
            if self.io.IORegistryEntryGetRegistryEntryID(service, ctypes.byref(entry_id)):
                return None
            return {'ready': True, 'serviceEntryID': entry_id.value, 'marker': marker}
        finally:
            for value in (data, prop, key):
                if value:
                    self.cf.CFRelease(value)
            self.io.IOObjectRelease(parent.value)

    def drain(self, iterator):
        found = None
        while True:
            service = self.io.IOIteratorNext(iterator)
            if not service:
                return found
            try:
                found = self.inspect(service) or found
            finally:
                self.io.IOObjectRelease(service)

    def snapshot(self):
        iterator = ctypes.c_uint32()
        rc = self.io.IOServiceGetMatchingServices(0, self.matching(), ctypes.byref(iterator))
        if rc:
            raise RuntimeError('Driver snapshot failed: ' + hex(rc & 0xffffffff))
        try:
            return self.drain(iterator.value) or {'ready': False}
        finally:
            if iterator.value:
                self.io.IOObjectRelease(iterator.value)

    def wait(self, seconds):
        port = self.io.IONotificationPortCreate(0)
        if not port:
            raise RuntimeError('Cannot create IOKit notification port')
        iterator, source, loop = ctypes.c_uint32(), None, None
        found, errors = [], []
        @self.CALLBACK
        def callback(refcon, current):
            try:
                ready = self.drain(current)
                if ready:
                    found.append(dict(ready, delivery='notification'))
            except Exception as exc:
                errors.append(str(exc))
            if found or errors:
                self.cf.CFRunLoopStop(loop)
        try:
            source = self.io.IONotificationPortGetRunLoopSource(port)
            if not source:
                raise RuntimeError('Cannot obtain IOKit run-loop source')
            loop = self.cf.CFRunLoopGetCurrent()
            self.cf.CFRunLoopAddSource(loop, source, self.mode)
            rc = self.io.IOServiceAddMatchingNotification(port, b'IOServiceFirstPublish',
                self.matching(), callback, None, ctypes.byref(iterator))
            if rc:
                raise RuntimeError('Cannot register driver notification: ' + hex(rc & 0xffffffff))
            # Register FIRST, then drain existing services. This also arms the
            # iterator, avoiding the check/subscribe race during early boot.
            existing = self.drain(iterator.value)
            if existing:
                return dict(existing, delivery='already_published')
            deadline = time.monotonic() + max(0, seconds)
            while not found and not errors and time.monotonic() < deadline:
                result = self.cf.CFRunLoopRunInMode(self.mode, deadline - time.monotonic(), False)
                if result == 1:  # kCFRunLoopRunFinished: source unexpectedly gone.
                    raise RuntimeError('IOKit notification run loop finished unexpectedly')
            if errors:
                raise RuntimeError('Driver readiness callback failed: ' + errors[0])
            return found[0] if found else {'ready': False, 'delivery': 'timeout'}
        finally:
            if source and loop:
                self.cf.CFRunLoopRemoveSource(loop, source, self.mode)
            if iterator.value:
                self.io.IOObjectRelease(iterator.value)
            self.io.IONotificationPortDestroy(port)


class System:
    def command(self, args):
        return subprocess.run(args, capture_output=True, timeout=8)

    def boot(self):
        p = self.command(['/usr/sbin/sysctl', '-n', 'kern.bootsessionuuid'])
        if p.returncode or not p.stdout.strip():
            raise RuntimeError('Cannot identify current boot; refusing to signal')
        return p.stdout.decode().strip()

    def wait_ready(self, seconds):
        return IOKitReadiness().wait(seconds)

    def ready_snapshot(self):
        return IOKitReadiness().snapshot()

    def region(self):
        try:
            p = self.command(['/usr/sbin/ioreg', '-a', '-r', '-d', '1', '-c', 'IOPlatformExpertDevice'])
            if p.returncode:
                return None
            entries = plistlib.loads(p.stdout)
        except (subprocess.TimeoutExpired, plistlib.InvalidFileException, ExpatError):
            # Early boot can stall IORegistry. Retry within the existing bounded
            # readiness window; never infer LL/A from a failed query.
            return None
        raw = entries[0].get('region-info', b'') if entries else b''
        return raw.rstrip(b'\0').decode('ascii', errors='replace') if isinstance(raw, bytes) else None

    def answers(self):
        try:
            raw = plistlib.loads(Path('/private/var/db/eligibilityd/eligibility.plist').read_bytes())
        except (OSError, plistlib.InvalidFileException, ExpatError):
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


def refresh(system, previous, checkpoint, wait_seconds=90):
    boot = system.boot()
    if previous.get('bootSession') == boot and previous.get('attempted'):
        return dict(previous, lastInvocationUTC=utc(), lastInvocationHelperVersion=VERSION,
                    lastInvocationOutcome='already_attempted_this_boot')
    result = {'schema': 1, 'helperVersion': VERSION, 'bootSession': boot,
              'startedUTC': utc(), 'attempted': False, 'signalAttempts': 0,
              'notificationPosts': 0, 'policy': 'once_after_driver_ready_event',
              'regionValueRequired': False, 'fixedSettleSeconds': 0, 'timings': {}}
    began = system.now()
    def finish(outcome, **values):
        result['timings']['totalSeconds'] = round(system.now() - began, 6)
        return dict(result, phase='finished', outcome=outcome, finishedUTC=utc(), **values)
    checkpoint(dict(result, phase='waiting_for_driver_ready', outcome='in_progress'))
    try:
        waiting = system.now()
        ready = system.wait_ready(wait_seconds)
        result['timings']['readyWaitSeconds'] = round(system.now() - waiting, 6)
        if not ready.get('ready'):
            return finish('driver_not_ready_timeout', readiness=ready)
        ready_at = system.now()
        result.update(driverReadyUTC=utc(), readiness=ready)
        # The volatile completion marker is written before registerService().
        # Recheck the same registry instance; never gate on a region string.
        fresh = system.ready_snapshot()
        if not fresh.get('ready') or fresh.get('serviceEntryID') != ready.get('serviceEntryID'):
            return finish('driver_changed_no_action')
        answers = system.answers()
        old_pid = system.pid()
        if old_pid and not system.verify_path(old_pid):
            return finish('process_identity_not_verified')
        if system.pid() != old_pid:
            return finish('process_changed_no_action')
        result.update(attempted=True, phase='action_started', actionStartedUTC=utc(),
                      beforePID=old_pid, beforeEligibility=answers)
        # Persist BEFORE signaling; a crash or upgrade cannot repeat this boot.
        checkpoint(result)
        result['timings']['readyToActionSeconds'] = round(system.now() - ready_at, 6)
        if old_pid:
            result['signalAttempts'] = 1
            system.terminate(old_pid)
            result['signalAcceptedUTC'] = utc()
            exit_began = system.now()
            exit_deadline = system.now() + 10
            while system.pid() == old_pid and system.now() < exit_deadline:
                system.sleep(0.5)
            if system.pid() == old_pid:
                return finish('old_process_did_not_exit')
            result['timings']['oldProcessExitSeconds'] = round(system.now() - exit_began, 6)
        if system.pid() is None:
            result['notificationPosts'] = 1
            system.notify()
            result['notificationPostedUTC'] = utc()
        verification_began = system.now()
        ready_deadline = system.now() + 30
        while True:
            new_pid = system.pid()
            after = system.answers()
            if new_pid and new_pid != old_pid and qualified(after):
                result['timings']['qualificationWaitSeconds'] = round(system.now() - verification_began, 6)
                return finish('eligible_after_refresh',
                            relaunchConfirmed=True, greymatterEligible=True,
                            afterPID=new_pid, afterEligibility=after)
            if system.now() >= ready_deadline:
                relaunched = bool(new_pid and new_pid != old_pid)
                result['timings']['qualificationWaitSeconds'] = round(system.now() - verification_began, 6)
                return finish('refreshed_but_not_eligible' if relaunched else 'refresh_not_confirmed',
                            relaunchConfirmed=relaunched, greymatterEligible=qualified(after),
                            afterPID=new_pid, afterEligibility=after)
            system.sleep(0.5)
    except Exception as exc:
        return finish('action_failed' if result['attempted'] else 'precondition_failed', error=str(exc))


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
    parser.add_argument('--wait-ready', type=float, metavar='SECONDS',
                        help='read-only ready-event probe, bounded to 0..90 seconds')
    args = parser.parse_args()
    system = System()
    if args.wait_ready is not None:
        if not 0 <= args.wait_ready <= 90:
            parser.error('--wait-ready must be between 0 and 90 seconds')
        began = system.now()
        ready = system.wait_ready(args.wait_ready)
        print(json.dumps({'helperVersion': VERSION, 'readOnly': True,
                          'readiness': ready, 'elapsedSeconds': round(system.now() - began, 6)}, indent=2))
        return 0 if ready.get('ready') else 2
    if args.check:
        print(json.dumps({'helperVersion': VERSION, 'bootSession': system.boot(),
                          'driverReadiness': system.ready_snapshot(),
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
        return 0 if result.get('outcome') in ('eligible_after_refresh', 'refreshed_but_not_eligible') or result.get('lastInvocationOutcome') == 'already_attempted_this_boot' else 2


if __name__ == '__main__':
    raise SystemExit(main())
