import re
import os
import posixpath
import collections
import pkg_resources
from pathlib import Path
import urllib.parse
import yaml
from jinja2 import Template
import logging
import markupsafe
from bs4 import BeautifulSoup
from bs4.element import NavigableString
import pytz
from feedgenerator import Atom1Feed, Rss201rev2Feed, get_tag_uri

from . import utils, rst, html, md, config
from . output import Output
from . import YAML_ENCODING

logger = logging.getLogger(__name__)


class _metadata(dict):
    def __getattr__(self, name):
        return self.get(name, None)


class ContentArgProxy:
    def __init__(self, site, page_content, content):
        self.site, self.page_content, self.content = site, page_content, content

    def __getattr__(self, name):
        prop = f'prop_get_{name}'
        f = getattr(self.content, prop, None)
        if f:
            return f(self.page_content)

        return getattr(self.content, name)

    def load(self, target):
        ret = self.content.get_content(target)
        return ContentArgProxy(self.site, self.page_content, ret)

    def path(self, *args, **kwargs):
        return self.page_content.path_to(self, *args, **kwargs)

    def link(self, *args, **kwargs):
        return self.page_content.link_to(self, *args, **kwargs)



class ContentsArgProxy:
    def __init__(self, site, page_content, content):
        self.site, self.page_content, self.content = (site, page_content, content)

    def __getitem__(self, key):
        content = self.site.contents.get_content(key, self.content)
        return ContentArgProxy(self.site, self.page_content, content)

    def __getattr__(self, name):
        return getattr(self.site.contents, name)

    def get_contents(self, *args, **kwargs):
        ret = self.site.contents.get_contents(*args, **kwargs)
        return [ContentArgProxy(self.site, self.page_content, content) for content in ret]

    def group_items(self, *args, **kwargs):
        ret = self.site.contents.group_items(*args, **kwargs)
        ret = [(v, [ContentArgProxy(self.site, self.page_content, content)
                    for content in c]) for v, c in ret]
        return ret


class ConfigArgProxy:
    def __init__(self, site, page_content, content):
        self.site, self.page_content, self.content = (site, page_content, content)

    def __getitem__(self, key):
        return self.site.config.get(self.page_content.dirname, key)

    def __getattr__(self, name):
        return self.site.config.get(self.page_content.dirname, name)


class Content:
    def __init__(self, site, dirname, name, metadata, body):
        self.site = site
        self.dirname = utils.dirname_to_tuple(dirname)
        self.name = name
        self.metadata = _metadata(metadata)
        self.body = body

        self.metadata['stat'] = None
        path = self.metadata.get('srcpath', None)
        if path:
            try:
                self.metadata['stat'] = os.stat(path)
            except IOError:
                pass

    _omit = object()

    def get_metadata(self, name, default=_omit):
        if name in self.metadata:
            return config.format_value(name, getattr(self.metadata, name))

        if default is self._omit:
            return self.site.config.get(self.dirname, name)
        else:
            return self.site.config.get(self.dirname, name, default)

    def __getattr__(self, name):
        _omit = object()
        ret = self.get_metadata(name, default=_omit)
        if ret is _omit:
            raise AttributeError(f"Invalid attr name: {name}")
        return ret

    def _to_filename(self):
        filename_templ = self.filename_templ
        filename_templ = "{% autoescape false %}" + filename_templ + "{% endautoescape %}"
        template = self.site.jinjaenv.from_string(filename_templ)
        ret = self.site.render(template, **self.get_render_args(self))

        assert ret
        return ret

    @property
    def title(self):
        return self.get_metadata('title', None) or os.path.splitext(self.name)[0]

    @property
    def filename(self):
        filename = self.get_metadata('filename', None)
        if not filename:
            filename = self._to_filename()
        return filename

    @property
    def stem(self):
        stem = self.get_metadata('stem', None)
        if stem is not None:
            return stem
        name = self.name
        if not name:
            return ''
        d, name = posixpath.split(name)
        return posixpath.splitext(name)[0]

    @property
    def ext(self):
        ext = self.get_metadata('ext', None)
        if ext is not None:
            return ext
        name = self.name
        if not name:
            return ''
        d, name = posixpath.split(name)
        return posixpath.splitext(name)[1]

    @property
    def url(self):
        site_url = self.get_metadata('site_url')
        path = self.get_output_path()
        return urllib.parse.urljoin(site_url, path)

    @property
    def timezone_name(self):
        return self.get_metadata('timezone', '')

    @property
    def timezone(self):
        return pytz.timezone(self.timezone_name)

    @property
    def date(self):
        date = self.get_metadata('date', None)
        if not date:
            return
        tz = self.timezone
        return date.astimezone(tz)

    def get_output_path(self, *args, **kwargs):
        return f"{'/'.join(self.dirname)}/{self.filename}"

    def get_content(self, target):
        if isinstance(target, str):
            content = self.site.contents.get_content(target, self)
        else:
            return target
        return content

    def path_to(self, target, fragment=None, abs_path=False, *args, **kwargs):
        if isinstance(target, str):
            target = self.get_content(target)
        fragment = f'#{markupsafe.escape(fragment)}' if fragment else ''
        if abs_path or self.use_abs_path:
            return target.url + fragment
        else:
            here = f"/{'/'.join(self.dirname)}/"
            to = '/' + target.get_output_path(*args, **kwargs)
            return posixpath.relpath(to, here) + fragment

    def link_to(self, target, text=None, fragment=None, abs_path=False, attrs=None, *args, **kwargs):
        if isinstance(target, str):
            target = self.get_content(target)
        if not text:
            text = target.title

        text = markupsafe.escape(text or '')
        s_attrs = []
        if attrs:
            for k, v in attrs.items():
                s_attrs.append(f"{markupsafe.escape(k)}='{markupsafe.escape(v)}'")
        path = markupsafe.escape(self.path_to(target, fragment=fragment,
                                              abs_path=abs_path, *args, **kwargs))
        return markupsafe.Markup(f"<a href='{path}' { ' '.join(s_attrs) }>{text}</a>")

    def get_outputs(self):
        return []

    def get_render_args(self, page_content):
        content = ContentArgProxy(self.site, page_content, self)
        if page_content is self:
            page = content
        else:
            page = ContentArgProxy(self.site, page_content, page_content)

        contents = ContentsArgProxy(self.site, page_content, self)
        config = ConfigArgProxy(self.site, page_content, self)
        kwargs = {'config': config, 'contents': contents, 'page': page, 'content': content}
        return kwargs


class BinContent(Content):
    def __init__(self, site, dirname, name, metadata, body):
        super().__init__(site, dirname, name, metadata, body)

    def get_outputs(self):
        return [Output(dirname=self.dirname, name=self.name,
                       stat=self.stat,
                       body=self.body)]


class HTMLValue(markupsafe.Markup):
    pass


class HTMLContent(Content):
    @property
    def ext(self):
        ext = self.get_metadata('ext', None)
        if ext is not None:
            return ext
        return '.html'

    def _get_html(self, page_content):
        html = ""
        if self.body:
            template = self.site.jinjaenv.from_string(self.body)
            html = self.site.render(template, **self.get_render_args(page_content))
        return html

    def prop_get_abstract(self, page_content):
        html = self._get_html(page_content)
        soup = BeautifulSoup(html, 'html.parser')
        abstract_length = self.abstract_length

        if abstract_length == 0:
            return soup

        slen = 0
        gen = soup.recursiveChildGenerator()
        for c in gen:
            if isinstance(c, NavigableString):
                curlen = len(c.strip())
                slen += curlen
                if slen + curlen > abstract_length:
                    last_c = c
                    break
                slen += curlen
        else:
            return HTMLValue(soup)

        while c:
            while c.next_sibling:
                c.next_sibling.extract()
            c = c.parent

        last_c.string.replace_with(last_c[:abstract_length - curlen])
        return HTMLValue(soup)

    def prop_get_html(self, page_content):
        html = self._get_html(page_content)
        soup = BeautifulSoup(html, 'html.parser')
        n = 1
        headers = []
        for c in soup.recursiveChildGenerator():
            if re.match(r'h\d', c.name or ''):
                id = f'h_{"_".join(self.dirname)}_{self.name}_{n}'
                id = re.sub(r'[^a-zA-Z0-9_]', lambda m: f'_{ord(m[0]):02x}', id)
                n += 1
                a = soup.new_tag('a', id='a_' + id, **{'class': 'header_anchor'})
                c.insert_before(a)
                c['id'] = id
                headers.append((id, c.name, c.text))

        ret = HTMLValue(soup)
        ret.headers = headers
        return ret


class Snippet(HTMLContent):
    def get_outputs(self):
        return []


class Article(HTMLContent):
    def get_outputs(self):

        templatename = self.article_template
        template = self.site.jinjaenv.get_template(templatename)
        body = self.site.render(template, **self.get_render_args(self))

        return [Output(dirname=self.dirname, name=self.filename,
                       stat=self.stat,
                       body=body.encode('utf-8'))]


class IndexPage(Content):
    @property
    def ext(self):
        ext = self.get_metadata('ext', None)
        if ext is not None:
            return ext
        return '.html'

    def filename_to_page(self, values, npage):
        value = '_'.join(values)
        value = re.sub(r'[%/\\: \t]', lambda m: f'%{ord(m[0]):02x}', value)

        if getattr(self, 'groupby', None):
            if npage == 1:
                filename_templ = self.indexpage_group_filename_templ
            else:
                filename_templ = self.indexpage_group_filename_templ2
        else:
            if npage == 1:
                filename_templ = self.indexpage_filename_templ
            else:
                filename_templ = self.indexpage_filename_templ2

        filename_templ = "{% autoescape false %}" + filename_templ + "{% endautoescape %}"
        template = self.site.jinjaenv.from_string(filename_templ)
        ret = self.site.render(template,
                               value=value, cur_page=npage,
                               **self.get_render_args(self))

        return ret

    def get_output_path(self, values=(), npage=None, *args, **kwargs):
        if not npage:
            npage = 1
        filename = self.filename_to_page(values, npage)
        return f"{'/'.join(self.dirname)}/{filename}"

#    def path_to_indexpage(self, values, npage, page_from=None, abs_path=False):
#        if not page_from:
#            page_from = self
#
#        to = self.get_output_path(values, npage)
#        if abs_path or page_from.use_abs_path:
#            site_url = self.site_url
#            return urllib.parse.urljoin(site_url, to)
#        else:
#            here = f"/{'/'.join(page_from.dirname)}/"
#            to = f"/{to}"
#            return posixpath.relpath(to, here)

    def _to_filename(self):
        return self.filename_to_page([''], 1)

    def get_outputs(self):
        n_per_page = int(self.indexpage_max_articles)
        page_orphan = int(self.indexpage_orphan)

        templatename1 = self.indexpage_template
        templatename2 = self.indexpage_template2
        outputs = []

        filters = getattr(self, 'filters', {})
        filters['type'] = {'article'}
        filters['draft'] = {False}

        groups = self.site.contents.group_items(
            getattr(self, 'groupby', None), filters=filters)

        for names, group in groups:
            num = len(group)
            num_pages = ((num - 1) // n_per_page) + 1
            rest = num - ((num_pages - 1) * n_per_page)
            if rest <= page_orphan:
                if num_pages > 1:
                    num_pages -= 1

            if self.indexpage_max_num_pages:
                num_pages = min(num_pages, self.indexpage_max_num_pages)

            templatename = templatename1
            for page in range(0, num_pages):
                is_last = (page == (num_pages - 1))

                f = page * n_per_page
                t = num if is_last else f + n_per_page

                articles = [ContentArgProxy(self.site, self, article)
                            for article in group[f:t]]

                template = self.site.jinjaenv.get_template(templatename)
                args = self.get_render_args(self)

                body = self.site.render(template,
                                        group_names=names, cur_page=page + 1, is_last=is_last,
                                        num_pages=num_pages, articles=articles,
                                        **args)

                filename = self.filename_to_page(names, page + 1)
                output = Output(dirname=self.dirname, name=filename,
                                stat=self.stat,
                                body=body.encode('utf-8'))
                outputs.append(output)

                if templatename2:
                    templatename = templatename2

        return outputs


class FeedPage(Content):
    use_abs_path = True

    @property
    def ext(self):
        feedtype = self.feedtype
        if feedtype == 'atom':
            return '.xml'
        elif feedtype == 'rss':
            return '.rdf'
        else:
            raise ValueError(f"Invarid feed type: {feedtype}")

    def get_outputs(self):

        feedtype = self.feedtype
        if feedtype == 'atom':
            cls = Atom1Feed
        elif feedtype == 'rss':
            cls = Rss201rev2Feed
        else:
            raise ValueError(f"Invarid feed type: {feedtype}")

        feed = cls(
            title=self.site_title,
            link=self.site_url,
            feed_url=self.url,
            description='')

        filters = getattr(self, 'filters', {})
        filters['type'] = {'article'}
        filters['draft'] = {False}
        contents = [c for c in self.site.contents.get_contents(
            filters=filters)]

        num_articles = int(self.feed_num_articles)
        for c in contents[:num_articles]:
            link = c.url
            description = c.prop_get_abstract(self)

            feed.add_item(
                title=c.title,
                link=link,
                unique_id=get_tag_uri(link, c.date),
                description=description,
                pubdate=c.date,
            )

        body = feed.writeString('utf-8').encode('utf-8')
        return [Output(dirname=self.dirname, name=self.filename,
                       stat=self.stat,
                       body=body)]


class Contents:
    def __init__(self):
        self._contents = {}

    def add(self, content):
        key = (content.dirname, content.name)
        if key not in self._contents:
            self._contents[key] = content

    def get_content(self, key, base=None):
        dirname, filename = utils.abs_path(key, base.dirname if base else ())
        return self._contents[(dirname, filename)]

    def get_contents(self, subdirs=None, base=None, filters=None):
        contents = [c for c in self._contents.values()]

        if filters:
            def f(content):
                for k, v in filters.items():
                    if not hasattr(content, k):
                        return False
                    prop = getattr(content, k)
                    if isinstance(prop, str):
                        if prop not in v:
                            return False
                    elif isinstance(prop, collections.abc.Collection):
                        for e in prop:
                            if e in v:
                                break
                        else:
                            return False
                    else:
                        if prop not in v:
                            return False
                return True

            contents = [c for c in self._contents.values() if f(c)]

        if subdirs:
            cur = base.dirname if base else None
            subdirs = [utils.abs_dir(d, cur) for d in subdirs]
            contents = filter(lambda c: any(c.dirname[:len(d)] == d for d in subdirs), contents)

        recs = []
        for c in contents:
            d = c.date
            if d:
                ts = d.timestamp()
            else:
                ts = 0
            recs.append((ts, c))

        recs.sort(reverse=True, key=lambda r: (r[0], r[1].title))
        return [c for (ts, c) in recs]

    def group_items(self, group, subdirs=None, base=None, filters=None):
        if not group:
            return [(('',), list(self.get_contents(subdirs, base, filters)))]

        d = collections.defaultdict(list)
        for c in self.get_contents(subdirs, base, filters):
            g = getattr(c, group, None)

            if g:
                if isinstance(g, str):
                    d[(g,)].append(c)
                elif isinstance(g, collections.abc.Collection):
                    for e in g:
                        d[(e,)].append(c)
                else:
                    d[(g,)].append(c)

        return sorted(d.items())

    @property
    def categories(self):
        contents = self.get_contents(filters={'type': {'article'}})
        categories = (getattr(c, 'category', None) for c in contents)
        return sorted(set(c for c in categories if c))

    @property
    def tags(self):
        tags = set()
        for c in self.get_contents(filters={'type': {'article'}}):
            t = getattr(c, 'tags', None)
            if t:
                tags.update(t)
        return sorted(tags)


def load_config(site, dirname, filename, metadata, body):
    site.config.add(dirname, metadata)


CONTENT_CLASSES = {
    'binary': BinContent,
    'snippet': Snippet,
    'article': Article,
    'index': IndexPage,
    'feed': FeedPage,
    'config': load_config,
}


def content_class(type):
    return CONTENT_CLASSES[type]


class bin_loader:
    def from_file(site, path, dirname, filename):
        body = path.read_bytes()
        metadata = {'srcpath': path, 'type': 'binary'}

        return content_class(metadata['type'])(site, dirname, filename, metadata, body)

    def from_byte(site, dirname, filename, bin):
        metadata = {'type': 'binary'}
        return content_class(metadata['type'])(site, dirname, filename, metadata, bin)


class rst_loader:
    def from_file(site, path, dirname, filename):
        metadata, body = rst.load(path)
        metadata['srcpath'] = path
        return content_class(metadata['type'])(site, dirname, filename, metadata, body)

    def from_byte(site, dirname, filename, bin):
        src = bin.decode('utf-8')
        metadata, body = rst.load_string(src)
        return content_class(metadata['type'])(site, dirname, filename, metadata, body)


class yaml_loader:
    def from_file(site, path, dirname, filename):
        text = path.read_text(encoding=YAML_ENCODING)
        metadata = yaml.load(text)
        if not metadata:
            metadata = {}
        metadata['srcpath'] = path
        return content_class(metadata['type'])(site, dirname, filename, metadata, body=text)

    def from_byte(site, dirname, filename, bin):
        text = bin.decode(YAML_ENCODING)
        metadata = yaml.load(text)
        if not metadata:
            metadata = {}
        return content_class(metadata['type'])(site, dirname, filename, metadata, text)


class html_loader:
    def from_file(site, path, dirname, filename):
        metadata, body = html.load(path)
        metadata['srcpath'] = path
        return content_class(metadata['type'])(site, dirname, filename, metadata, body)

    def from_byte(site, dirname, filename, bin):
        src = bin.decode('utf-8')
        metadata, body = html.load_string(src)
        return content_class(metadata['type'])(site, dirname, filename, metadata, body)


class md_loader:
    def from_file(site, path, dirname, filename):
        metadata, body = md.load(path)
        metadata['srcpath'] = path
        return content_class(metadata['type'])(site, dirname, filename, metadata, body)

    def from_byte(site, dirname, filename, bin):
        src = bin.decode('utf-8')
        metadata, body = md.load_string(src)
        return content_class(metadata['type'])(site, dirname, filename, metadata, body)


LOADERS = {
    ".rst": rst_loader,
    ".yml": yaml_loader,
    ".yaml": yaml_loader,
    ".html": html_loader,
    ".md": md_loader,
}


def getContentLoader(ext):
    return LOADERS.get(ext, bin_loader)


def load_directory(site, path, loader=None):
    logger.info(f"Loading {path}")
    path = path.expanduser().resolve()
    if not path.is_dir():
        logger.debug(f'directory: {str(path)} is not a valid directory.')
        return

    for p in utils.walk(path):
        name = os.path.relpath(p, path)
        dirname, filename = os.path.split(name)
        if site.config.is_ignored(filename):
            continue

        _loader = loader
        if not _loader:
            _loader = getContentLoader(p.suffix)
        content = _loader.from_file(site, p, dirname, filename)

        if content:
            site.contents.add(content)

    return


def get_content_from_package(site, package, srcpath, destname=None, loader=None):
    s = pkg_resources.resource_string(package, srcpath)

    if destname is None:
        destname = srcpath

    destdir, filename = posixpath.split(destname)
    ext = os.path.splitext(filename)[1]

    _loader = loader
    if not _loader:
        _loader = getContentLoader(ext)

    return _loader.from_byte(site, destdir, filename, s)


def load_package(site, package, path, loader=None):
    logger.info(f"Loading {package}/{path}")
    if not path.endswith('/'):
        path = path + '/'

    for filename in utils.walk_package(package, path):
        name = filename[len(path):]

        content = get_content_from_package(site, package, filename, name, loader)
        if content is not None:
            site.contents.add(content)

    return
