# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell
#
# See the included LICENSE.txt file for licensing details.

# Import System Modules
import time
import unittest
try:
    from queue import Queue
except ImportError:
    from Queue import Queue

# Import Custom Modules
from rocket import threadpool, worker

# Constants

# Define Tests
class ThreadPoolTest(unittest.TestCase):
    def setUp(self):
        self.min_threads = 10
        self.max_threads = 20
        self.active_queue = Queue()
        self.monitor_queue = Queue()
        w = worker.Worker
        self.tp = threadpool.ThreadPool(w,
                                        dict(),
                                        self.active_queue,
                                        self.monitor_queue,
                                        self.min_threads,
                                        self.max_threads)

    def aliveConnections(self):
        return reduce(lambda x, y: x+y,
                      [1 if x.isAlive() else 0 for x in self.tp.threads],
                      0)

    def testThreadPoolStart(self):

        self.assertEqual(self.aliveConnections(), 0)

        self.tp.start()

        self.assertEqual(self.aliveConnections(), self.min_threads)

    def testThreadPoolStop(self):

        self.assertEqual(self.aliveConnections(), 0)

        self.tp.start()

        self.assertEqual(self.aliveConnections(), self.min_threads)

        self.tp.stop()

        self.assertEqual(len(self.tp.threads), 0)

    def testThreadPoolShrink(self):

        self.assertEqual(self.aliveConnections(), 0)

        self.tp.start()

        self.assertEqual(self.aliveConnections(), self.min_threads)

        self.tp.shrink(1)

        # Give the other threads some time to process the death threat
        time.sleep(0.5)

        self.assertEqual(self.aliveConnections(), self.min_threads - 1)

    def testThreadPoolGrow(self):

        self.assertEqual(self.aliveConnections(), 0)

        self.tp.start()

        self.assertEqual(self.aliveConnections(), self.min_threads)

        self.tp.grow(1)

        self.assertEqual(self.aliveConnections(), self.min_threads + 1)


    def testThreadPoolDeadThreadCleanup(self):

        self.assertEqual(self.aliveConnections(), 0)

        self.tp.start()

        self.assertEqual(self.aliveConnections(), self.min_threads)

        self.tp.shrink(1)

        # Give the other threads some time to process the death threat
        time.sleep(0.5)

        self.assertEqual(self.aliveConnections(), self.min_threads - 1)
        self.assertEqual(len(self.tp.threads), self.min_threads)

        self.tp.bring_out_your_dead()

        self.assertEqual(len(self.tp.threads), self.min_threads - 1)

    def testThreadPoolDynamicResizeDown(self):

        self.assertEqual(self.aliveConnections(), 0)

        self.tp.start()

        self.assertEqual(self.aliveConnections(), self.min_threads)

        self.tp.grow(1)

        self.assertEqual(self.aliveConnections(), self.min_threads + 1)
        self.assertEqual(len(self.tp.threads), self.min_threads + 1)

        self.tp.dynamic_resize()

        # Give the other threads some time to process the death threat
        time.sleep(0.5)

        self.tp.bring_out_your_dead()

        self.assertEqual(self.aliveConnections(), self.min_threads)
        self.assertEqual(len(self.tp.threads), self.min_threads)

    def testThreadPoolDynamicResizeUp(self):

        self.assertEqual(self.aliveConnections(), 0)

        for x in range(self.max_threads * 3):
            self.active_queue.put(None)

        self.tp.alive = True

        self.tp.dynamic_resize()

        self.assert_(self.min_threads < len(self.tp.threads) < self.max_threads + 1)

    def tearDown(self):
        try:
            self.tp.stop()
        except:
            pass

        del self.tp

if __name__ == '__main__':
    unittest.main()
