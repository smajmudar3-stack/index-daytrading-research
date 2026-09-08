"""Make 04_live_system/ importable from a study. One place, one explanation.

The bundle split filed the live system and the research harnesses in separate
directories, but every module in both still imports its neighbours flat
(`import uw_client`, not `from live import uw_client`). So a study that reuses a
live engine has to put that directory on sys.path, and it has to say so out loud.

The version this replaces did say so, and was wrong:

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import uw_client as uw

from 05_studies/scripts/ that resolves to 05_studies/, which does not contain
uw_client. The insert looked deliberate, so nobody re-read it, and the script
died on its import line on every machine including the author's.

Usage — two lines, at the top of the study, before the live import:

    sys.path.insert(0, paths.STUDIES_DIR)   # so `import live_path` resolves
    import live_path; live_path.enable()    # so `import <live module>` resolves

`enable()` is a call rather than an import side effect on purpose: importing a
module should never rearrange the interpreter behind your back.
"""
import sys

from idt import paths


def enable():
    """Put 04_live_system/ at the front of sys.path. Idempotent; returns the dir."""
    if paths.LIVE_DIR not in sys.path:
        sys.path.insert(0, paths.LIVE_DIR)
    return paths.LIVE_DIR
