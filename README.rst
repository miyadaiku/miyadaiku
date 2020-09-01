
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


History
------------------

1.18.0
~~~~~~~~~~~~

- Add `bases` to the jinja variable.

- Add `ipynb_export_options` config for nbexport option. Default to
  ::

     {"TagRemovePreprocessor": {
         "remove_cell_tags": ["remove_cell"],
         "remove_all_outputs_tags": ["remove_output"],
         "remove_input_tags": ["remove_input"]
         },
     }



1.17.0
~~~~~~~~~~~~

- :jinja:``  tag can be used in Jupyter markdown cell.
- Generates sitemap

1.16.0
~~~~~~~~~~~~

- Removed div and a elements around headers.


1.15.0
~~~~~~~~~~~~

- Add ``context.get_url()``.

- Deprecate ``ContentPropxy.url`` property.


1.14.0
~~~~~~~~~~~~

- Add ``directories`` property to index and feed.

- Update samile contents created by miyadaiku-start command.

- Rebuild if YAML files in the project contents directory are updated.

- Escape :jinja:`` notation in markdown.


1.13.0
~~~~~~~~~~~~

- Support .txt file type.

- Wrong tzinfo was picked to apply default timezone.

- File name with extension '.j2' is treated as HTML.

- Ignore Yaml declarations which does not return dict.

- New property: updated.

1.12.0
~~~~~~~~~~~~

- Build title from abstract if ``title_fallback`` is ``title`` and header element not found in the content.

- Preserve newline in content.abstract.

- Add .anchor-link style for .ipynb file.

- YAML can be used in HTML content.

- Add setattr/getattr to jinja variables.

- Modified convention of anchor name generation.

- Add search option to link()/link_to().

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
