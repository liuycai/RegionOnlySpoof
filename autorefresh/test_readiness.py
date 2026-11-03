#!/usr/bin/python3
"""Completion validation and matching-notification delivery/cleanup tests."""
import ctypes
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('event_helper', Path(__file__).with_name('helper.py'))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def marker():
    return dict(schema=1, startTicks=1, regionBeforeTicks=2, regionAfterTicks=3,
                originBeforeTicks=4, originAfterTicks=5, sampleTicks=6,
                regionWriteOK=1, originWriteOK=1, originalRegion=b'CH/A')


class ReadinessCases(unittest.TestCase):
    def test_completed_marker_keeps_only_completion_fields(self):
        value = helper.completed_marker(marker())
        self.assertNotIn('originalRegion', value)
        self.assertEqual(value['sampleTicks'], 6)

    def test_missing_or_out_of_order_completion_is_rejected(self):
        for value in (None, {}, dict(marker(), sampleTicks=2), dict(marker(), originAfterTicks=0)):
            with self.subTest(value=value):
                self.assertIsNone(helper.completed_marker(value))

    def test_write_result_does_not_change_completion_barrier(self):
        self.assertIsNotNone(helper.completed_marker(dict(marker(), regionWriteOK=0)))

    def watcher(self, existing=False, callback_error=False, registration_error=False):
        watcher = object.__new__(helper.IOKitReadiness)
        watcher.mode = 30
        io = SimpleNamespace(
            IONotificationPortCreate=mock.Mock(return_value=10),
            IONotificationPortGetRunLoopSource=mock.Mock(return_value=20),
            IOObjectRelease=mock.Mock(), IONotificationPortDestroy=mock.Mock())
        cf = SimpleNamespace(CFRunLoopGetCurrent=mock.Mock(return_value=40),
            CFRunLoopAddSource=mock.Mock(), CFRunLoopRemoveSource=mock.Mock(),
            CFRunLoopStop=mock.Mock())
        callbacks = []
        def register(port, kind, matching, callback, refcon, output):
            self.assertEqual(kind, b'IOServiceFirstPublish')
            if registration_error:
                return 5
            ctypes.cast(output, ctypes.POINTER(ctypes.c_uint32)).contents.value = 50
            callbacks.append(callback)
            return 0
        io.IOServiceAddMatchingNotification = register
        def run(mode, seconds, once):
            callbacks[0](None, 50)
            return 2
        cf.CFRunLoopRunInMode = mock.Mock(side_effect=run)
        ready = {'ready': True, 'serviceEntryID': 7, 'marker': helper.completed_marker(marker())}
        watcher.io, watcher.cf = io, cf
        watcher.matching = mock.Mock(return_value=60)
        watcher.drain = mock.Mock(side_effect=[ready] if existing else
                                  [None, RuntimeError('bad event') if callback_error else ready])
        return watcher

    def test_existing_service_is_drained_after_subscribe_without_wait(self):
        watcher = self.watcher(existing=True)
        self.assertEqual(watcher.wait(5)['delivery'], 'already_published')
        watcher.cf.CFRunLoopRunInMode.assert_not_called()
        watcher.io.IOObjectRelease.assert_called_once_with(50)
        watcher.io.IONotificationPortDestroy.assert_called_once_with(10)

    def test_later_publish_callback_delivers_ready_and_releases_resources(self):
        watcher = self.watcher()
        self.assertEqual(watcher.wait(5)['delivery'], 'notification')
        watcher.cf.CFRunLoopStop.assert_called_once_with(40)
        self.assertEqual(watcher.drain.call_count, 2)
        watcher.cf.CFRunLoopRemoveSource.assert_called_once_with(40, 20, 30)
        watcher.io.IOObjectRelease.assert_called_once_with(50)
        watcher.io.IONotificationPortDestroy.assert_called_once_with(10)

    def test_callback_error_is_propagated_and_port_is_destroyed(self):
        watcher = self.watcher(callback_error=True)
        with self.assertRaisesRegex(RuntimeError, 'bad event'):
            watcher.wait(5)
        watcher.io.IONotificationPortDestroy.assert_called_once_with(10)

    def test_registration_error_destroys_port_without_signal_path(self):
        watcher = self.watcher(registration_error=True)
        with self.assertRaisesRegex(RuntimeError, 'Cannot register'):
            watcher.wait(5)
        watcher.io.IONotificationPortDestroy.assert_called_once_with(10)
        watcher.io.IOObjectRelease.assert_not_called()


if __name__ == '__main__':
    unittest.main()
