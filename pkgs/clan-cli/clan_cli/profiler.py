import cProfile
import io
import logging
import os
import pstats
import re
import weakref
from collections.abc import Callable
from typing import Any

# Ensure you have a logger set up for logging exceptions
log = logging.getLogger(__name__)
explanation = """
cProfile Output Columns Explanation:

- ncalls: The number of calls to the function. This includes both direct and indirect (recursive) calls.

- tottime: The total time spent in the given function alone, excluding time spent in calls to sub-functions. 
  This measures the function's own overhead and execution time.

- percall (first instance): Represents the average time spent in the function per call, calculated as tottime divided by ncalls.
  This value excludes time spent in sub-function calls, focusing on the function's own processing time.

- cumtime: The cumulative time spent in this function and all the sub-functions it calls (both directly and indirectly). 
  This includes all execution time within the function, from the start of its invocation to its return, 
  including all calls to other functions and the time those calls take.

- percall (second instance): Represents the average time per call, including time spent in this function and in all sub-function calls.
  It is calculated as cumtime divided by ncalls, providing an average over all calls that includes all nested function calls.
"""


def print_profile(profiler: cProfile.Profile, sortkey: pstats.SortKey) -> None:
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.sort_stats(sortkey)
    ps.print_stats(12)

    # Process the output to trim file paths
    output_lines = s.getvalue().split("\n")
    for line in output_lines:
        try:
            parts = re.split(r"\s+", line)[
                1:
            ]  # Split on the first space to separate the time from the path
            fqpath = parts[-1]
            fpath, line_num = fqpath.split(":")
            if os.path.sep in fpath:  # Check if this looks like it includes a path
                fpath = trim_path_to_three_levels(fpath)
                prefix = f"{parts[0]:>7}"
                prefix += f"{parts[1]:>9}"
                prefix += f"{parts[2]:>9}"
                prefix += f"{parts[3]:>9}"
                prefix += f"{parts[4]:>9}"
                new_line = f"{prefix:}   {fpath}:{line_num}"
            else:
                new_line = line
        except (ValueError, IndexError):
            new_line = line  # If there's no path, leave the line as is
        print(new_line)


# TODO: Add an RLock for every profiler, currently not thread safe
class ProfilerStore:
    profilers: dict[str, cProfile.Profile]

    def __init__(self) -> None:
        self.profilers = {}
        self._exit_callback = weakref.finalize(self, self.on_exit)

    def __getitem__(self, func: Callable) -> cProfile.Profile:
        key = f"{func.__module__}:{func.__name__}"
        if key not in self.profilers:
            self.profilers[key] = cProfile.Profile()
        return self.profilers[key]

    def on_exit(self) -> None:
        for key, profiler in self.profilers.items():
            print("=" * 7 + key + "=" * 7)
            print_profile(profiler, pstats.SortKey.TIME)
            print_profile(profiler, pstats.SortKey.CUMULATIVE)

        if len(self.profilers) > 0:
            print(explanation)


def trim_path_to_three_levels(path: str) -> str:
    parts = path.split(os.path.sep)
    if len(parts) > 4:
        return os.path.sep.join(parts[-4:])
    return path


PROFS = ProfilerStore()


def profile(func: Callable) -> Callable:
    """
    A decorator that profiles the decorated function, printing out the profiling
    results with paths trimmed to three directories deep.
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        global PROFS
        profiler = PROFS[func]

        try:
            profiler.enable()
            res = func(*args, **kwargs)
            profiler.disable()
        except Exception:
            profiler.disable()
            raise
        return res

    if os.getenv("PERF", "0") == "1":
        return wrapper
    return func
