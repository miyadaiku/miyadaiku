from typing import List, Iterator, Dict, Tuple, Optional, DefaultDict, Any, Callable, Set, Union, TypedDict, NamedTuple
import os
import fnmatch
import pkg_resources
from pathlib import Path, PurePosixPath, PurePath

import yaml

import miyadaiku
from .config  import Config
from .loader import ContentFiles
from miyadaiku import ContentPath, ContentSrc
from . import content, rst, md






class Site:
    root: Path
    sitecondig: Dict[str, Any]
    config:Config
    files: ContentFiles
    ignores:Set[str]
    themes: List[str]
    
    @classmethod
    def load(cls, path:Path, props:Dict):
        site = cls(path)
        site.loadconfig(props)

    def __init__(self, path: Path):
        self.root = path

    def loadconfig(self, props:Dict):
        cfgfile = self.root / miyadaiku.CONFIG_FILE
        self.siteconfig = yaml.load(cfgfile.read_text(encoding=miyadaiku.YAML_ENCODING), Loader=yaml.FullLoader) or {}
        self.siteconfig.update(props)

        self.config = Config(self.sitecondig)
        self.stat_config = os.stat(cfgfile) if cfgfile.exists() else None

        self.themes = self.siteconfig.get('themes', [])
        self.ignores = set(self.siteconfig.get('ignores', []))


#    def load(self):
#            if f.metadata['type'] == 'config':
#                config.add(f.metadata)
