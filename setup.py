import os
import pathlib
from setuptools import setup, find_packages

DIR = pathlib.Path(__file__).resolve().parent
os.chdir(DIR)


requires = [
    "docutils", "pyyaml", "jinja2", "python-dateutil", "pygments",
    "pytz", "tzlocal", "happylogging", "beautifulsoup4", "feedgenerator"
]


entry_points = {
    'console_scripts': [
        'miyadaiku-start = miyadaiku.scripts.zichinsai:main',
        'miyadaiku-build = miyadaiku.scripts.muneage:main'
    ]
}

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def list_packages(root):
    yield root
    for dirpath, dirnames, filenames in os.walk(root):
        for d in dirnames:
            if not d.startswith('_'):
                path = os.path.join(dirpath, d).replace(os.path.sep, '.')
                yield path

setup(
    name="miyadaiku",
    version="0.0.3",
    author="Atsuo Ishimoto",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
    ],
    description='Miyadaiku - Flexible static site generator for Jinja2 artists',
    long_description=read('README.rst'),
    entry_points=entry_points,
    packages=list(list_packages('miyadaiku')),
    package_data={
        '': ['*.rst', '*.md', '*.html', '*.css', '*.js', '*.yml', '*.png', '*.jpg', '*.jpeg'],
    },
    install_requires=requires,
    include_package_data=True,
    zip_safe=False
)
