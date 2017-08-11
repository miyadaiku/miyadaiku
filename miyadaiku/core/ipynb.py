from nbconvert.exporters import HTMLExporter
import nbformat


def _export(json):
    config = {'TemplateExporter': {'template_file': 'basic.tpl'}}
    html, _ = HTMLExporter(config).from_notebook_node(json)

    metadata = {'type': 'article'}
    metadata.update(json.get('metadata', {}).get('miyadaiku', {}))

    return metadata, '<div>' + html + '</div>'


def load(path):
    json = nbformat.read(str(path), nbformat.current_nbformat)
    return _export(json)


def load_string(s):
    json = nbformat.reads(s, nbformat.current_nbformat)
    return _export(json)
