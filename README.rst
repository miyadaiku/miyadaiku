
Miyadaiku
=========================================================================

Miyadaiku is a flexible static site generator for Jinja2 artists.

- Contents are written in reStructuredText, Markdown, HTML, Jupyter Notebook and YAML.

- Jinja2 templates to create HTML pages.

- Jinja2 tags can be used in your contents too. Miyadaiku provides ReST/Markdown extensions to write Jinja2 in content files. 

- Hierarchical contents property. Each directory can have default property values for documents. These property values are also applied to contents of their sub-directories.

- Theme system to share templates, CSS, Javascript, Image or any other contents files.

- Themes are managed as Python package. You can install themes from PyPI with pip.

- Generate index pages and Atom/RSS feeds for Blog sites.


Documents
--------------------

https://miyadaiku.github.io

Requirements
------------------

Miydaiku requires Python 3.7 or later.


Installation
-----------------

Use pip to install miyadaiku.

.. code:: console

   $ pip3 install miyadaiku

Upgrading to Miyadaiku 1.0.0
----------------------------------------

Miyadaiku 1.0.0 has some incompatible changes.

To upgrade from older version of Miyadaiku, please read following notes.

1. Package name of external themes are changed.

   - miyadaiku.themes.bootstrap4 -> miyadaiku_theme_bootstrap4
   - miyadaiku.themes.jquery -> miyadaiku_theme_jquery
   - miyadaiku.themes.tether -> miyadaiku_theme_tether
   - miyadaiku.themes.fontawesome-> miyadaiku_theme_fontawesome
   - miyadaiku.themes.popper_js -> miyadaiku_theme_popper_js

2. Argument names of some method of Miydaiku objects are changed.

   - `value` argument of `path()`, `path_to()`, `link()`, `link_to()` methods are renamed to `group_value`.
   - `group_values` jinja variable is renamed to `group_value`.

