from __future__ import absolute_import
import logging
import multiprocessing as mp
import signal
import Queue


logger = logging.getLogger(__name__)


def _master(function, iterable, processes, task_queue, result_queue, flatten):
    """ Controls the computation. Starts/stops the workers and assigns tasks """
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
        logger.error('caught KeyboardInterrupt, brutally slaughtering workers')
        result_queue.cancel_join_thread()
        task_queue.cancel_join_thread()
        [p.terminate() for p in workers]
    else:
        for _ in xrange(processes):
            task_queue.put(None)
        [p.join() for p in workers]

    result_queue.put(None)


def _worker(function, task_queue, result_queue, flatten):
    """ Worker process: gets tasks, applies the function and sends back results
        Stop with a `None` task.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    task = task_queue.get()
    while task is not None:
        for result in _process_task(function, task, flatten, False):
            result_queue.put(result)
        task = task_queue.get()


def _process_task(function, task, flatten, raise_exc):
    """ Actually processes a task, flattening the results if needed and logging or
        raising exceptions.
    """
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


def map(function, iterable, processes=0, flatten=False, raise_exc=True):
    """ Applies the given function to each element of the iterable in parallel.
        `None` values are not allowed in the iterable nor as return values, they will
        simply be discarded. Can be "safely" stopped with a keboard interrupt.
        :param function: the function used to transform the elements of the iterable
        :param processes: how many items to process in parallel. Use zero or a negative
        number to use all the available processors. No additional processes will be used
        if the value is 1.
        :param flatten: If the mapping function return an iterable flatten the resulting
        iterables into a single one.
        :param raise_exc: Only when `processes` equals 1, controls whether to propagate
        the exception raised by the mapping function to the called or simply to log
        them and carry on the computation. When `processes` is different than 1 this
        parameter is not used.
        :returns: iterable with the results. Order is not guaranteed to be preserved
    """
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
