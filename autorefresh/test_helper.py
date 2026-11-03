#!/usr/bin/python3
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('refresh_helper', Path(__file__).with_name('helper.py'))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def answers(eligible=False, region=2):
    return {'GREYMATTER': {'os_eligibility_answer_t': 4 if eligible else 2,
                           'status': {'OS_ELIGIBILITY_INPUT_DEVICE_REGION_CODE': region}}}


class Fake:
    def __init__(self, region='LL/A', eligible=False, pid=10, reject=False, complete=True):
        self.region_value = region
        self.eligible = eligible
        self.current_pid = pid
        self.reject = reject
        self.complete = complete
        self.clock = 0
        self.signals = []
        self.notifications = 0
        self.saved = []
        self.device_region = 3 if eligible else 2
        self.extension_load_time = 0
        self.wait_calls = 0

    def boot(self): return 'boot-A'
    def region(self): raise AssertionError('Region reads must not gate refresh')
    def wait_ready(self, seconds):
        self.wait_calls += 1
        if self.extension_load_time > self.clock + seconds:
            self.clock += seconds
            return {'ready': False, 'delivery': 'timeout'}
        self.clock = max(self.clock, self.extension_load_time)
        return dict(self.ready_snapshot(), delivery='notification')
    def ready_snapshot(self):
        return {'ready': self.clock >= self.extension_load_time, 'serviceEntryID': 7}
    def answers(self): return answers(self.eligible, self.device_region)
    def pid(self): return self.current_pid
    def verify_path(self, pid): return True
    def now(self): return self.clock
    def sleep(self, seconds): self.clock += seconds
    def checkpoint(self, value): self.saved.append(copy.deepcopy(value))
    def terminate(self, pid):
        assert self.saved[-1]['attempted'], 'Attempt must be persisted BEFORE signal'
        self.signals.append(pid)
        if self.reject: raise PermissionError('denied')
        self.current_pid = None
    def notify(self):
        self.notifications += 1
        self.current_pid = 20
        if self.complete:
            self.eligible = True
            self.device_region = 3


class Cases(unittest.TestCase):
    def run_fake(self, system, previous=None):
        return helper.refresh(system, previous or {}, system.checkpoint,
                              wait_seconds=4)

    def test_already_eligible_still_refreshes_once(self):
        s = Fake(eligible=True)
        self.assertEqual(self.run_fake(s)['outcome'], 'eligible_after_refresh')
        self.assertEqual(s.signals, [10])
        self.assertEqual(s.notifications, 1)

    def test_one_signal_then_notification(self):
        s = Fake()
        result = self.run_fake(s)
        self.assertEqual(result['outcome'], 'eligible_after_refresh')
        self.assertEqual(s.signals, [10])
        self.assertEqual(s.notifications, 1)
        self.assertEqual(s.clock, 0)
        self.assertEqual(result['fixedSettleSeconds'], 0)
        self.assertEqual(result['timings']['readyToActionSeconds'], 0)

    def test_attempt_is_not_repeated_this_boot(self):
        s = Fake()
        result = self.run_fake(s)
        self.run_fake(s, result)
        self.assertEqual(s.signals, [10])
        self.assertEqual(s.notifications, 1)

    def test_original_region_still_refreshes(self):
        s = Fake(region='CH/A')
        self.assertEqual(self.run_fake(s)['outcome'], 'eligible_after_refresh')
        self.assertEqual(s.signals, [10])

    def test_extension_never_loaded_does_not_signal(self):
        s = Fake()
        s.extension_load_time = 100
        self.assertEqual(self.run_fake(s)['outcome'], 'driver_not_ready_timeout')
        self.assertEqual(s.signals, [])
        self.assertEqual(s.notifications, 0)

    def test_ready_event_triggers_immediately_without_settling_delay(self):
        s = Fake()
        s.extension_load_time = 2
        self.assertEqual(self.run_fake(s)['outcome'], 'eligible_after_refresh')
        self.assertEqual(s.clock, 2)

    def test_no_process_only_posts_notification(self):
        s = Fake(pid=None)
        self.assertEqual(self.run_fake(s)['outcome'], 'eligible_after_refresh')
        self.assertEqual(s.signals, [])
        self.assertEqual(s.notifications, 1)

    def test_rejected_signal_is_not_retried(self):
        s = Fake(reject=True)
        result = self.run_fake(s)
        self.assertEqual(result['outcome'], 'action_failed')
        self.run_fake(s, result)
        self.assertEqual(s.signals, [10])
        self.assertEqual(s.notifications, 0)

    def test_other_restriction_still_refreshes(self):
        s = Fake()
        s.device_region = 3
        self.assertEqual(self.run_fake(s)['outcome'], 'eligible_after_refresh')
        self.assertEqual(s.signals, [10])

    def test_verification_timeout_is_bounded(self):
        s = Fake(complete=False)
        result = self.run_fake(s)
        self.assertEqual(result['outcome'], 'refreshed_but_not_eligible')
        self.assertTrue(result['relaunchConfirmed'])
        self.assertFalse(result['greymatterEligible'])
        self.assertLessEqual(s.clock, 32)
        self.assertEqual(s.signals, [10])

    def test_ready_wait_error_is_recorded_without_signal(self):
        s = Fake()
        s.wait_ready = mock.Mock(side_effect=RuntimeError('notification unavailable'))
        result = self.run_fake(s)
        self.assertEqual(result['outcome'], 'precondition_failed')
        self.assertEqual(s.signals, [])
        self.assertEqual(s.saved[0]['phase'], 'waiting_for_driver_ready')
        self.assertFalse(s.saved[0]['attempted'])

    def test_previous_boot_does_not_suppress_current_refresh(self):
        s = Fake()
        self.assertEqual(self.run_fake(s, {'bootSession': 'boot-old', 'attempted': True})['outcome'], 'eligible_after_refresh')
        self.assertEqual(s.signals, [10])

    def test_driver_instance_changes_before_action_no_signal(self):
        s = Fake()
        original = s.wait_ready
        def wait(seconds):
            result = original(seconds)
            s.ready_snapshot = lambda: {'ready': True, 'serviceEntryID': 8}
            return result
        s.wait_ready = wait
        self.assertEqual(self.run_fake(s)['outcome'], 'driver_changed_no_action')
        self.assertEqual(s.signals, [])

    def test_unverified_process_never_signalled(self):
        s = Fake()
        s.verify_path = lambda pid: False
        self.assertEqual(self.run_fake(s)['outcome'], 'process_identity_not_verified')
        self.assertEqual(s.signals, [])

    def test_no_relaunch_is_not_reported_as_success(self):
        s = Fake()
        s.notify = lambda: None
        result = self.run_fake(s)
        self.assertEqual(result['outcome'], 'refresh_not_confirmed')
        self.assertFalse(result['relaunchConfirmed'])

    def test_upgrade_same_boot_skips_even_readiness_wait(self):
        s = Fake()
        result = self.run_fake(s, {'bootSession': 'boot-A', 'attempted': True, 'helperVersion': '1.1.0'})
        self.assertEqual(result['lastInvocationHelperVersion'], helper.VERSION)
        self.assertEqual(s.wait_calls, 0)
        self.assertEqual(s.signals, [])


if __name__ == '__main__':
    unittest.main()
