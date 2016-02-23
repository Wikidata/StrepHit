from __future__ import absolute_import
import logging
import multiprocessing as mp
import signal
import Queue


logger = logging.getLogger(__name__)


def _master(function, iterable, processes, task_queue, result_queue, flatten):
    workers = [mp.Process(target=_worker,
                          args=(function, task_queue, result_queue, flatten))
               for _ in xrange(processes)]
    [p.start() for p in workers]

    try:
        for each in iterable:
            if each is None:
                logger.debug('received None task, ignoring it')
            else:
                task_queue.put(each)
    except KeyboardInterrupt:
        logger.error('KeyboardInterrupt, stopping workers')
        while True:
            try:
                task_queue.get_nowait()
            except Queue.Empty:
                break

    for _ in xrange(processes):
        task_queue.put(None)
    [p.join() for p in workers]

    result_queue.put(None)


def _worker(function, task_queue, result_queue, flatten):
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    task = task_queue.get()
    while task is not None:
        for result in _process_task(function, task, flatten, False):
            result_queue.put(result)
        task = task_queue.get()


def _process_task(function, task, flatten, raise_exc):
    try:
        result = function(task)
        if result is None:
            logger.debug('received None result from worker, ignoring it')
        elif flatten:
            for each in result:
                yield each
        else:
            yield result
    except KeyboardInterrupt:
        raise
    except:
        if raise_exc:
            raise
        else:
            logger.exception('caught exception in worker process')


def map(function, iterable, processes=0, flatten=False, raise_exc=None):
    if raise_exc is None:
        raise_exc = processes == 1

    if processes == 1:
        for task in iterable:
            if task is not None:
                for each in _process_task(function, task, flatten, raise_exc):
                    yield each
    else:
        if processes <= 0:
            processes = mp.cpu_count()

        task_queue = mp.Queue(50)
        result_queue = mp.Queue(50)

        master = mp.Process(target=_master,
                            args=(function, iterable, processes, task_queue,
                                  result_queue, flatten))
        master.start()

        result = result_queue.get()
        while result is not None:
            yield result
            result = result_queue.get()

        master.join()
