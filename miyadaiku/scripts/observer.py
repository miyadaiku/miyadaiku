# type: ignore
import os

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from miyadaiku import CONFIG_FILE, CONTENTS_DIR, FILES_DIR, MODULES_DIR, TEMPLATES_DIR


class ContentDirHandler(FileSystemEventHandler):
    def __init__(self, ev):
        self._ev = ev

    def on_created(self, event):
        if event.is_directory:
            return
        self._ev.set()

    def on_modified(self, event):
        if event.is_directory:
            return
        self._ev.set()

    def on_deleted(self, event):
        if event.is_directory:
            return
        self._ev.set()


DIRS = [CONTENTS_DIR, FILES_DIR, MODULES_DIR, TEMPLATES_DIR]


class RootHandler(FileSystemEventHandler):
    def __init__(self, ev):
        self._ev = ev

    def on_created(self, event):
        if event.is_directory:
            if os.path.split(event.src_path)[1] in DIRS:
                OBSERVER.schedule(
                    ContentDirHandler(self._ev), event.src_path, recursive=True
                )
            return

        if os.path.split(event.src_path)[1] == CONFIG_FILE:
            self._ev.set()

    def on_modified(self, event):
        if os.path.split(event.src_path)[1] == CONFIG_FILE:
            self._ev.set()

    def on_deleted(self, event):
        if os.path.split(event.src_path)[1] == CONFIG_FILE:
            self._ev.set()


def create_observer(path, ev):
    global OBSERVER
    OBSERVER = Observer()
    for subdir in DIRS:
        d = path / subdir
        if d.is_dir():
            OBSERVER.schedule(ContentDirHandler(ev), str(d), recursive=True)

    OBSERVER.schedule(RootHandler(ev), str(path), recursive=False)
    return OBSERVER
