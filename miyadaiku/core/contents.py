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

logger = logging.getLogger(__name__)

from . import utils, rst
from . output import Output
from . import YAML_ENCODING


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

        try:
            return getattr(self.content, name)
        except AttributeError:
            if name in self.content.metadata:
                return self.content.metadata[name]

        return self.site.config.get(self.content.dirname, name)

    def get_content(self, target):
        if isinstance(target, str):
            content = self.site.contents.get_content(target, self.content)
        elif isinstance(target, ContentArgProxy):
            content = target.content
        elif isinstance(target, Content):
            content = target
        else:
            raise ValueError(f'Cannot convert to path: {target}')
        return content

    def path_to(self, target):
        content = self.get_content(target)
        
        if self._use_abs_path:
            return content.url
        else:
            here = f"/{'/'.join(self.dirname)}/"
            to = f"/{'/'.join(content.dirname)}/{content.filename}"
            return posixpath.relpath(to, here)

    def link_to(self, target, text=None):
        content = self.get_content(target)
        if not text:
            text = content.title

        text = markupsafe.escape(text or '')
        return markupsafe.Markup(f"<a href='{self.path_to(target)}'>{text}</a>")


class ContentsArgProxy:
    def __init__(self, site, page_content, content):
        self.site, self.page_content, self.content = (site, page_content, content)

    def __getitem__(self, key):
        content = self.site.contents.get_content(key, self.content)
        return ContentArgProxy(self.site, self.page_content, content)

    def __getattr__(self, name):
        return getattr(self.site.contents, name)


class ConfigArgProxy:
    def __init__(self, site, page_content, content):
        self.site, self.page_content, self.content = (site, page_content, content)

    def __getitem__(self, key):
        return self.site.config.get(self.page_content.dirname, key)

    def __getattr__(self, name):
        return self.site.config.get(self.page_content.dirname, name)

class Content:
    _use_abs_path = False

    def __init__(self, site, dirname, name, metadata, body):
        self.site = site
        self.dirname = utils.dirname_to_tuple(dirname)
        self.name = name
        self.metadata = _metadata(metadata)
        self.body = body

        path = self.metadata.get('path', None)
        if path:
            try:
                self.metadata['stat'] = os.stat(path)
            except IOError:
                pass

    def _get_metadata(self, name):
        if name in self.metadata:
            return getattr(self.metadata, name)
        return self.site.config.get(self.dirname, name)

    def _to_filename(self, name):
        return name

    @property
    def title(self):
        return self.metadata.get('title') or os.path.splitext(self.name)[0]

    @property
    def filename(self):
        filename = self.metadata.get('filename')
        if not filename:
            filename = self._to_filename(self.name)
        return urllib.parse.quote(filename)

    @property
    def url(self):
        site_url = self._get_metadata('site_url')
        dir = '/'.join(self.dirname)
        ret = urllib.parse.urljoin(site_url, dir)
        return urllib.parse.urljoin(ret, self.filename)

    @property
    def timezone_name(self):
        return self.metadata.timezone or self.site.config.get(
            self.dirname, 'timezone')

    @property
    def timezone(self):
        return pytz.timezone(self.timezone_name)

    @property
    def date(self):
        date = self.metadata.date
        if not date:
            return 
        tz = self.timezone
        return date.astimezone(tz)

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
                stat=self.metadata.get('stat', None),
                body=self.body)]


class HTMLValue(markupsafe.Markup):
    pass


class HTMLContent(Content):
    def _to_filename(self, name):
        n, e = os.path.splitext(name)
        return f'{n}.html'

    def _get_html(self, page_content):
        html = ""
        if self.body:
            template = self.site.jinjaenv.from_string(self.body)
            html = template.render(
                **self.get_render_args(page_content)
            )
        return html
    
    def prop_get_abstract(self, page_content):
        html = self._get_html(page_content)
        soup = BeautifulSoup(html, 'html.parser')
        article_abstract_length = self._get_metadata('article_abstract_length')
        
        slen = 0
        gen = soup.recursiveChildGenerator()
        for c in gen:
            if isinstance(c, NavigableString):
                curlen = len(c.strip())
                slen += len(c.strip())
                if slen + curlen > article_abstract_length:
                    last_c = c
                    break
                slen += curlen
        else:
            return HTMLValue(soup)
                        
        while c:
            while c.next_sibling:
                c.next_sibling.extract()
            c = c.parent
        
        last_c.string.replace_with(last_c[:article_abstract_length-curlen])
        return HTMLValue(soup)
    
    def prop_get_html(self, page_content):
        html = self._get_html(page_content)
        soup = BeautifulSoup(html, 'html.parser')
        n = 1
        headers = []
        for c in soup.recursiveChildGenerator():
            if re.match(r'h\d', c.name or ''):
                id = f'h_{"_".join(self.dirname)}_{self.name}_{n}'
                n += 1
                a = soup.new_tag('a', id=id)
                c.insert_before(a)
                headers.append((id, c.name, c.text))

        ret = HTMLValue(soup)
        ret.headers = headers
        return ret


class Snippet(HTMLContent):
    def get_outputs(self):
        return []


class Article(HTMLContent):
    def get_outputs(self):

        templatename = self._get_metadata('article_template')
        template = self.site.jinjaenv.get_template(templatename)
        body = template.render(
            **self.get_render_args(self))

        return [Output(dirname=self.dirname, name=self.filename,
                       stat=self.metadata.get('stat', None),
                       body=body.encode('utf-8'))]


class IndexPage(Content):
    def filename_to_page(self, values, npage):
        value = '_'.join(values)
        stem, ext = os.path.splitext(self.name)

        if self.metadata.groupby:
            if npage == 1:
                filename_templ = self._get_metadata('indexpage_group_filename_templ')
            else:
                filename_templ = self._get_metadata('indexpage_group_filename_templ2')
        else:
            if npage == 1:
                filename_templ = self._get_metadata('indexpage_filename_templ')
            else:
                filename_templ = self._get_metadata('indexpage_filename_templ2')

        kwargs = self.get_render_args(self)
        ret = filename_templ.format(
            groupby=self.metadata.groupby, value=value, cur_page=npage, stem=stem, ext=ext, **kwargs)
            
        return urllib.parse.quote(ret)
    
    def path_from_page(self, page_from, value, npage):
        filename = urllib.parse.quote(self.filename_to_page(value, npage))
        to = f"/{'/'.join(self.dirname)}/{filename}"

        if page_from._use_abs_path:
            site_url = self._get_metadata('site_url')
            return urllib.parse.urljoin(site_url, to)
        else:
            here = f"/{'/'.join(page_from.dirname)}/"
            return posixpath.relpath(to, here)
        
    def _to_filename(self, name):
        return self.filename_to_page([''], 1)

    def get_outputs(self):
        n_per_page = int(self._get_metadata('indexpage_max_articles'))
        page_orphan = int(self._get_metadata('indexpage_orphan'))

        templatename1 = self._get_metadata('indexpage_template')
        templatename2 = self._get_metadata('indexpage_template2')
        outputs = []
        groups = self.site.contents.group_items(self.metadata.groupby)

        for names, group in groups:
            num = len(group)
            num_pages = ((num-1) // n_per_page) + 1
            rest = num - ((num_pages-1) * n_per_page)
            if rest <= page_orphan:
                if num_pages > 1:
                    num_pages -= 1

            templatename = templatename1
            for page in range(0, num_pages):
                is_last = (page == (num_pages-1))

                f = page * n_per_page
                t = num if is_last else f + n_per_page

                articles = [ContentArgProxy(self.site, self, article)
                    for article in group[f:t]]

                template = self.site.jinjaenv.get_template(templatename)
                args = self.get_render_args(self)

                body = template.render(
                    group_names=names, cur_page=page+1, is_last=is_last,
                    num_pages=num_pages, articles=articles,
                    **args)
                
                filename = self.filename_to_page(names, page+1)
                output = Output(dirname=self.dirname, name=filename,
                                stat=self.metadata.get('stat', None),
                                body=body.encode('utf-8'))
                outputs.append(output)

                if templatename2:
                    templatename = templatename2

        return outputs


class FeedPage(Content):
    _use_abs_path = True

    def _to_filename(self, name):
        n, e = os.path.splitext(name)

        feedtype = self.metadata.feedtype
        if feedtype == 'atom':
            ext = 'xml'
        elif feedtype == 'rss':
            ext = 'rdf'
        else:
            raise ValueError(f"Invarid feed type: {feedtype}")

        return f'{n}.{ext}'

    def get_outputs(self):

        feedtype = self.metadata.feedtype
        if feedtype == 'atom':
            cls = Atom1Feed
        elif feedtype == 'rss':
            cls = Rss201rev2Feed
        else:
            raise ValueError(f"Invarid feed type: {feedtype}")

        feed = cls(
            title=self._get_metadata('site_title'),
            link=self._get_metadata('site_url'),
            feed_url=self.url,
            description='')

        contents = [c for c in self.site.contents.get_contents() if c.date]

        num_articles = int(self._get_metadata('rss_num_articles'))
        for c in contents[:num_articles]:
            title = c.title
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
                       stat=self.metadata.get('stat', None),
                       body=body)]


class Contents:
    def __init__(self):
        self._contents = {}

    def add(self, content):
        key = (content.dirname, content.name)
        if key not in self._contents:
            self._contents[key] = content

    def get_content(self, key, base=None):
        dirname, filename = utils.abs_path(key, base.dirname if base else '/')
        return self._contents[(dirname, filename)]

    def get_contents(self, types=None):
        if not types:
            contents = [c for c in self._contents.values()]
        else:
            contents = [c for c in self._contents.values() if c.metadata.type in types]
        
        recs = []
        for c in contents:
            d = c.date
            if d:
                ts = d.timestamp()
            else:
                ts = 0
            recs.append((ts, c))

        recs.sort(reverse=True, key=lambda r:(r[0], r[1].title))
        return [c for (ts, c) in recs]

    def group_items(self, group):
        if not group:
            return [(('',), list(self.get_contents({'article'})))]

        d = collections.defaultdict(list)
        for c in self.get_contents({'article'}):
            if hasattr(c.metadata, group):
                g = getattr(c.metadata, group)
            else:
                g = getattr(c, group)

            if g:
                if isinstance(g, str):
                    d[(g,)].append(c)
                else:
                    for e in g:
                        d[(e,)].append(c)

        return sorted(d.items())

    @property
    def categories(self):
        contents = self.get_contents({'article'})
        categories = (c.metadata.category for c in contents if c.metadata.category)
        return sorted(set(categories))

    @property
    def tags(self):
        tags = set()
        for c in self.get_contents({'article'}):
            t = c.metadata.tags
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
        metadata = {'path': path, 'type': 'binary'}

        return content_class(metadata['type'])(site, dirname, filename, metadata, body)

    def from_byte(site, dirname, filename, bin):
        metadata = {'type': 'binary'}
        return content_class(metadata['type'])(site, dirname, filename, metadata, bin)


class rst_loader:
    def from_file(site, path, dirname, filename):
        metadata, body = rst.load(path)
        metadata['path'] = path
        return content_class(metadata['type'])(site, dirname, filename, metadata, body)


class yaml_loader:
    def from_file(site, path, dirname, filename):
        text = path.read_text(encoding=YAML_ENCODING)
        metadata = yaml.load(text)
        if not metadata:
            metadata = {}
        metadata['path'] = path
        return content_class(metadata['type'])(site, dirname, filename, metadata, body=None)

    def from_byte(site, dirname, filename, bin):
        text = bin.decode(YAML_ENCODING)
        metadata = yaml.load(text)
        if not metadata:
            metadata = {}
        return content_class(metadata['type'])(site, dirname, filename, metadata, bin)


LOADERS = {
    ".rst": rst_loader,
    ".yml": yaml_loader,
    ".yaml": yaml_loader,
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

    destdir, filename  = posixpath.split(destname)
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
        s = pkg_resources.resource_string(package, filename)
        name = filename[len(path):]

        content = get_content_from_package(site, package, filename, name, loader)
        if content is not None:
            site.contents.add(content)

    return
