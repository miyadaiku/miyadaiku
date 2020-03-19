from typing import List, Iterator, Dict, Tuple, Optional, DefaultDict, Any, Callable, Set, Union, TypedDict

import tzlocal # type: ignore

YAML_ENCODING = "utf-8"


CONFIG_FILE = 'config.yml'
MODULES_DIR = 'modules'
CONTENTS_DIR = 'contents'
FILES_DIR = 'files'
TEMPLATES_DIR = 'templates'
OUTPUTS_DIR = 'outputs'

DEFAULT_TIMEZONE = tzlocal.get_localzone().zone
DEFAULT_THEME = 'miyadaiku.themes.base'

IGNORE = [
    '.*',
    '*.o',
    '*.pyc',
    '*.egg-info',
    '*.bak',
    '*.swp',
    '*.~*',
    'dist',
    'build',

    'ehthumbs.db',
    'Thumbs.db',
]

METADATA_FILE_SUFFIX = '.props.yml'


PathTuple = Tuple[Tuple[str, ...], str]
