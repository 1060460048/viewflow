import os
import queue
import threading
import time
import unittest

from django.db import connection
from django.test import skipUnlessDBFeature, TransactionTestCase

from viewflow import flow, lock
from viewflow.base import Flow, this
from viewflow.exceptions import FlowLockFailed


@unittest.skipUnless('DATABASE_URL' in os.environ, 'Lock test requires specific database config')
class Test(TransactionTestCase):
    class TestFlow(Flow):
        start = flow.Start().Next(this.end)
        end = flow.End()

    def setUp(self):
        self.finished = False
        self.locked = False
        self.process = Test.TestFlow.process_class.objects.create(flow_class=Test.TestFlow)
        self.exception_queue = queue.Queue()

    def run_with_lock(self, lock_impl):
        try:
            with lock_impl(Test.TestFlow, self.process.pk):
                while not self.finished:
                    time.sleep(0.001)
        except FlowLockFailed as e:
            self.exception_queue.put(e)
        finally:
            connection.close()

    def run_with_lock_and_release(self, lock_impl):
        try:
            with lock_impl(Test.TestFlow, self.process.pk):
                time.sleep(0.5)
        except FlowLockFailed as e:
            self.exception_queue.put(e)
        finally:
            connection.close()

    @skipUnlessDBFeature('has_select_for_update')
    def test_select_for_update_locks(self):
        thread1 = threading.Thread(target=self.run_with_lock, args=[lock.select_for_update_lock(Test.TestFlow, attempts=1)])
        thread2 = threading.Thread(target=self.run_with_lock, args=[lock.select_for_update_lock(Test.TestFlow, attempts=1)])

        thread1.start()
        thread2.start()

        try:
            self.exception_queue.get(True, 10)
        except queue.Empty:
            self.fail('No thread was blocked')
        finally:
            self.finished = True

        thread1.join()
        thread2.join()

    @skipUnlessDBFeature('has_select_for_update')
    def test_select_for_update_locks_released(self):
        thread1 = threading.Thread(
            target=self.run_with_lock_and_release,
            args=[lock.select_for_update_lock(Test.TestFlow, attempts=4)])
        thread2 = threading.Thread(
            target=self.run_with_lock_and_release,
            args=[lock.select_for_update_lock(Test.TestFlow, attempts=4)])

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        try:
            self.exception_queue.get(True, 1)
            self.fail('Thread was blocked')
        except queue.Empty:
            pass

    def test_cache_lock(self):
        thread1 = threading.Thread(target=self.run_with_lock, args=[lock.cache_lock(Test.TestFlow, attempts=1)])
        thread2 = threading.Thread(target=self.run_with_lock, args=[lock.cache_lock(Test.TestFlow, attempts=1)])

        thread1.start()
        thread2.start()

        try:
            self.exception_queue.get(True, 10)
        except queue.Empty:
            self.fail('No thread was blocked')
        finally:
            self.finished = True

        thread1.join()
        thread2.join()
