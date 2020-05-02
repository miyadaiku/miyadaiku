from typing import Iterator, List, Any, Tuple
import os
import shutil
import glob
import distutils.dist
from distutils.core import Command
import pathlib

SETUP_FILE_EXTS = [
    "*.rst",
    "*.md",
    "*.html",
    "*.css",
    "*.js",
    "*.yml",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.otf",
    "*.eot",
    "*.svg",
    "*.ttf",
    "*.woff",
    "*.woff2",
]


def list_packages(packagedir: str, root: str) -> Iterator[str]:
    yield root

    dir = os.path.join(packagedir, root)
    for dirpath, dirnames, filenames in os.walk(dir):
        for d in dirnames:
            if not d.startswith("_"):
                path = os.path.join(dirpath, d)
                path = os.path.relpath(path, packagedir)
                yield path.replace(os.path.sep, ".")


def read_file(packagedir: str, fname: str) -> str:
    return open(os.path.join(packagedir, fname)).read()


distutils.dist.Distribution.exec_func = None  # type: ignore


class exec_func(Command):
    description = "Execute function"
    user_options: List[Any] = []
    boolean_options: List[Any] = []

    def initialize_options(self) -> None:
        pass

    def finalize_options(self) -> None:
        pass

    def run(self) -> None:
        if self.distribution.exec_func:  # type: ignore
            self.distribution.exec_func(self.distribution)  # type: ignore


distutils.dist.Distribution.copy_files = None  # type: ignore


class copy_files(Command):
    description = "Copy extra files"
    user_options: List[Any] = []
    boolean_options: List[Any] = []

    def initialize_options(self) -> None:
        pass

    def finalize_options(self) -> None:
        pass

    def run(self) -> None:
        if not self.distribution.copy_files:  # type: ignore
            return

        for srcdir, specs, destdir in self.distribution.copy_files:  # type: ignore
            if not destdir.is_dir():
                destdir.mkdir(parents=True, exist_ok=True)
            for spec in specs:
                srcfiles = glob.glob(os.path.join(srcdir, spec))
                for fname in srcfiles:
                    print(f"copy {fname} -> {destdir}")
                    shutil.copy(fname, destdir)


def copyfiles(files: List[Tuple[pathlib.Path, List[str], pathlib.Path]]) -> None:
    for srcdir, specs, destdir in files:
        if not destdir.is_dir():
            destdir.mkdir(parents=True, exist_ok=True)
        for spec in specs:
            srcfiles = glob.glob(os.path.join(srcdir, spec))
            for fname in srcfiles:
                print(f"copy {fname} -> {destdir}")
                shutil.copy(fname, destdir)
