# type: ignore

from . import ipynbhead
def load_package(site):
    site.add_jinja_global("ipynb", ipynbhead)
