import itertools
import multiprocessing
import typing
from multiprocessing import Queue, Process, cpu_count

import threaded_log


def _process_queue(log_queue: Queue, element_queue: Queue, action: callable, args) -> None:
    threaded_log.configure_process_logger(log_queue)
    while True:
        element = element_queue.get()
        if element is None:  # check for sentinel value and break when it appears
            break

        if args is not None and len(args) > 0:
            action(element, args)
        else:
            action(element)


# since we can not be sure that each run will take a similar amount of time (due to larger/more tex files) we are not
# splitting the list of paper directories and passing each part to a thread as that may result in one thread having a
# way larger workload, and thus increasing the total time.
# Additionally, using this approach benefits us in I/O-heavy workloads (which this program spends most of its time on).
# Because of that we use a queue to assign new papers to a thread when they are done with their current one. We use
# as many threads as CPU cores as testing showed that although more threads may speed up I/O loads while not having
# a huge benefit (or even reduce performance) for CPU-heavy tasks, more threads do not scale for this application.
def run(queue_elements: typing.Collection, queue_action: callable, *args) -> None:
    queue = Queue()  # speed benefit compared to JoinableQueue
    for queue_element in queue_elements:
        queue.put(queue_element)

    cores = cpu_count()
    for _ in range(cores):
        queue.put(None)  # sentinel value to notify a process that the queue is finished

    log_queue = Queue()
    logging_thread = threaded_log.start_logging_thread(log_queue)
    processes = []
    for _ in range(cores):
        p = Process(target=_process_queue, args=(log_queue, queue, queue_action, args), daemon=True)
        p.start()  # kill all child processes when the main process is killed
        processes.append(p)

    for p in processes:
        p.join()

    log_queue.put(None)
    logging_thread.join()


def _filter_return_values(return_values: list) -> list:
    results = []
    for return_value in return_values:
        if return_value is not None:
            results.append(return_value)

    return results


def run_with_results(queue_elements: typing.Collection, queue_action: callable, *args) -> list:
    log_queue = Queue()
    logging_thread = threaded_log.start_logging_thread(log_queue)

    cores = cpu_count()
    with multiprocessing.Pool(processes=cores) as pool:
        if args is not None and len(args) > 0:
            # use zip() to pass the argument for the queue action and additional arguments, we need to repeat the args
            # so zip() does not use the elements of the tuple instead of the whole tuple.
            # default chunk size is divmod(len(iterable), len(self._pool) * 4) -> 767 on 6 cores and 18400 iterable length.
            # that leads to processes taking way longer than other ones and hurting the overall runtime. instead, we
            # select a way smaller chunk size as context switching and pre-processing of the data are way faster than
            # the task itself. We arbitrarily select cores * 4 as our chunk size.
            return_values = pool.starmap(queue_action, zip(queue_elements, itertools.repeat(args)), chunksize=cores * 4)
        else:
            return_values = pool.map(queue_action, queue_elements, chunksize=cores * 4)

        # queue action might return None so we filter any Nones. we also need to handle the results before leaving the
        # context as they will be removed when leaving the context
        results = _filter_return_values(return_values)

    log_queue.put(None)
    logging_thread.join()
    return results
