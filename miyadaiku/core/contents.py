import re
import shutil
import secrets
import os
import posixpath
import collections
import datetime
import pkg_resources
from pathlib import Path, PosixPath
import urllib.parse
import yaml
from jinja2 import Template
import jinja2.exceptions
import logging
import markupsafe
from bs4 import BeautifulSoup
from bs4.element import NavigableString
import pytz
from feedgenerator import Atom1Feed, Rss201rev2Feed, get_tag_uri

import miyadaiku.core
from . import utils, rst, html, md, config, ipynb
from . output import Output
from . import YAML_ENCODING

logger = logging.getLogger(__name__)


class _metadata(dict):
    def __getattr__(self, name):
        return self.get(name, None)


class _context(dict):
    def __init__(self, site, page_content, *, pageargs=None):
        self.site = site
        self.page_content = page_content
        self.__depends = set()
        self.__pageargs = pageargs

    def __getattr__(self, name):
        return self.get(name, None)

    def __setattr__(self, name, value):
        self[name] = value

    def set(self, **kwargs):
        self.update(kwargs)

    def add_depend(self, page):
        self.__depends.add(page)

    def get_depends(self):
        return (self.__depends, self.__pageargs)


class ContentArgProxy:
    def __init__(self, context, content):
        self.context, self.content = context, content
        self.context.add_depend(self.content)

    def __getattr__(self, name):
        try:
            if not hasattr(self.content, name):
                prop = f'prop_get_{name}'
                f = getattr(self.content, prop, None)
                if f:
                    return f(self.context)

            return getattr(self.content, name)
        except Exception as e:
            if miyadaiku.core.DEBUG:
                logging.exception(f'error detected in getattr({self}, name)')
            raise

    _omit = object()

    def load(self, target, default=_omit):
        ret = self.content.get_content(target)
        return ContentArgProxy(self.context, ret)

    def path(self, *args, **kwargs):
        return self.context.page_content.path_to(self, *args, **kwargs)

    def link(self, *args, **kwargs):
        return self.context.page_content.link_to(self.context, self, *args, **kwargs)

    def path_to(self, target, *args, **kwargs):
        target = self.load(target)
        return self.context.page_content.path_to(target, *args, **kwargs)

    def link_to(self, target, *args, **kwargs):
        target = self.load(target)
        return self.context.page_content.link_to(self.context, target, *args, **kwargs)

    @property
    def html(self):
        ret = self.__getattr__('html')
        return self._to_markupsafe(ret)

    @property
    def abstract(self):
        ret = self.__getattr__('abstract')
        return self._to_markupsafe(ret)

    def _to_markupsafe(self, s):
        if not hasattr(s, '__html__'):
            s = HTMLValue(s)
        return s

class ContentsArgProxy:
    def __init__(self, conext, content):
        self.context, self.content = (conext, content)

    def __getitem__(self, key):
        content = self.context.site.contents.get_content(key, self.content)
        return ContentArgProxy(self.context, content)

    def __getattr__(self, name):
        return getattr(self.context.site.contents, name)

    def get_content(self, *args, **kwargs):
        ret = self.context.site.contents.get_content(*args, **kwargs)
        return ContentArgProxy(self.context, ret)

    def get_contents(self, *args, **kwargs):
        ret = self.context.site.contents.get_contents(*args, **kwargs)
        return [ContentArgProxy(self.context, content) for content in ret]

    def group_items(self, *args, **kwargs):
        ret = self.context.site.contents.group_items(*args, **kwargs)
        ret = [(v, [ContentArgProxy(self.context, content)
                    for content in c]) for v, c in ret]
        return ret


class ConfigArgProxy:
    def __init__(self, context, content):
        self.context, self.content = (context, content)

    def __getitem__(self, key):
        return self.context.site.config.get(self.context.page_content.dirname, key)

    def __getattr__(self, name):
        return self.context.site.config.get(self.context.page_content.dirname, name)


class Content:
    _filename = None
    updated = False

    def __init__(self, site, dirname, name, metadata, body):
        self.site = site
        self.dirname = utils.dirname_to_tuple(dirname)
        self.name = name
        self.metadata = _metadata(metadata)
        self.body = body
        self._imports = None

        self.metadata['stat'] = None
        if 'package' not in metadata:
            path = self.metadata.get('srcpath', None)
            if path:
                try:
                    self.metadata['stat'] = os.stat(path)
                except IOError:
                    pass

    def check_update(self, output_path):
        if self.updated:
            return True

        stat = self.metadata.get('stat', None)
        if self._check_fileupdate(output_path, stat):
            return True

        if not stat:
            self.updated = False
            return False

        if self.site.stat_depfile and stat.st_mtime > self.site.stat_depfile.st_mtime:
            self.updated = True
            return True

        self.updated = False
        return False

    def _check_fileupdate(self, outputpath, stat):
        filename = Output.calc_path(outputpath, self.dirname, self.filename)
        try:
            filestat = os.stat(filename)
            if not stat:
                self.updated = False
                return False

            if filestat.st_mtime >= stat.st_mtime:
                self.updated = False
                return False

        except IOError:
            pass

        self.updated = True
        return True

    def __str__(self):
        return f'<{self.__class__.__module__}.{self.__class__.__name__} {self.srcfilename}>'
    _omit = object()

    def get_metadata(self, name, default=_omit):
        if name in self.metadata:
            return config.format_value(name, getattr(self.metadata, name))

        if default is self._omit:
            return self.site.config.get(self.dirname, name)
        else:
            return self.site.config.get(self.dirname, name, default)

    def is_same(self, other):
        return (self.dirname, self.name) == (other.dirname, other.name)

    def __getattr__(self, name):
        _omit = object()
        ret = self.get_metadata(name, default=_omit)
        if ret is _omit:
            raise AttributeError(f"Invalid attr name: {name}")
        return ret

    def _to_filename(self):
        filename_templ = self.filename_templ
        filename_templ = "{% autoescape false %}" + filename_templ + "{% endautoescape %}"

        context = _context(self.site, self)
        ret = self.site.render_from_string(self, "filename_templ", filename_templ,
                                           **self.get_render_args(context))
        assert ret
        return ret

    @property
    def title(self):
        return self.get_metadata('title', None) or os.path.splitext(self.name)[0]

    @property
    def filename(self):
        if self._filename:
            return self._filename

        self._filename = self.get_metadata('filename', None)
        if not self._filename:
            self._filename = self._to_filename()
        return self._filename

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
    def srcfilename(self):
        package = self.metadata.get('package', '')
        if package:
            package = package+'!'

        path = self.metadata.get('srcpath', None)
        if path:
            path = os.path.relpath(path)
            return package+path

        return package+os.path.join('/'.join(self.dirname), self.name)

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

    def prop_get_headers(self, context):
        return []

    def prop_get_abstract(self, context):
        return ""

    def prop_get_html(self, context):
        return ""

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

    def link_to(self, context, target, text=None, fragment=None, abs_path=False, attrs=None, *args, **kwargs):
        if isinstance(target, str):
            target = self.get_content(target)
        if not text:
            if fragment:
                text = target.get_headertext(context, fragment)
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

    def pre_build(self):
        pass

    def _getimports(self):
        if self._imports is None:
            self._imports = {}
            for name in self.get_metadata('imports'):
                template = self.site.jinjaenv.get_template(name)
                fname = name.split('!', 1)[-1]
                modulename = PosixPath(fname).stem
                self._imports[modulename] = template.module

        return self._imports

    def get_render_args(self, context):
        content = ContentArgProxy(context, self)
        if context.page_content is self:
            page = content
        else:
            page = ContentArgProxy(context, context.page_content)

        contents = ContentsArgProxy(context, self)
        config = ConfigArgProxy(context, self)
        kwargs = {'config': config, 'contents': contents,
                  'page': page, 'content': content, 'context': context}

        imports = self._getimports()
        imports.update(kwargs)
        return imports


class ConfigContent(Content):
    def get_outputs(self):
        return []

    def _check_fileupdate(self, output_path, stat):
        return False


class BinContent(Content):
    def __init__(self, site, dirname, name, metadata, body):
        super().__init__(site, dirname, name, metadata, body)

    def get_outputs(self):
        return [Output(self, self.filename)]

    def write(self, path):
        body = self.body
        if not body:
            package = self.metadata.get('package')
            if package:
                body = pkg_resources.resource_string(package, self.metadata['srcpath'])
                path.write_bytes(body)
            else:
                shutil.copyfile(str(self.metadata['srcpath']), str(path))
        else:
            path.write_bytes(body)

        context = _context(self.site, self)
        return context


class HTMLValue(markupsafe.Markup):
    pass


class HTMLContent(Content):
    def __init__(self, site, dirname, name, metadata, body):
        super().__init__(site, dirname, name, metadata, body)

        self._html_cache = {}
        self._header_cache = {}

    @property
    def ext(self):
        ext = self.get_metadata('ext', None)
        if ext is not None:
            return ext
        return '.html'

    def _set_header_id(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        n = 1
        headers = []
        id = None
        for c in soup.recursiveChildGenerator():
            if c.name and ('header_target' in (c.get('class', '') or [])):
                id = c.get('id', None)

            elif re.match(r'h\d', c.name or ''):
                if not id:
                    id = f'h_{"_".join(self.dirname)}_{self.name}_{n}'
                    id = re.sub(r'[^a-zA-Z0-9_]', lambda m: f'_{ord(m[0]):02x}', id)

                    n += 1
                    a = soup.new_tag('div', id=id, **{'class': 'header_target'})
                    c.insert_before(a)

                headers.append((id, c.name, c.text))
                id = None

        return headers, str(soup)

    def _get_html(self, context):
        ret = self._html_cache.get(context.page_content, None)
        if ret:
            return ret

        html = self.site.render_from_string(self, "html", self.body or '',
                                           **self.get_render_args(context))

        headers, html = self._set_header_id(html)

        self._html_cache[context.page_content] = html
        self._header_cache[context.page_content] = headers
        return html

    def _get_headers(self, context):
        ret = self._header_cache.get(context.page_content)
        if ret is not None:
            return ret

        self._get_html(context)
        return self._header_cache.get(context.page_content)

    _in_get_headertext = False

    def get_headertext(self, context, fragment):
        if self._in_get_headertext:
            return 'dummy'

        self._in_get_headertext = True
        try:
            headers = self._get_headers(context)
            for id, elem, text in headers:
                if id == fragment:
                    return text
        finally:
            self._in_get_headertext = False
        return None

    def prop_get_headers(self, context):
        headers = self._get_headers(context)
        return headers

    def prop_get_abstract(self, context, abstract_length=None):
        html = self._get_html(context)
        soup = BeautifulSoup(html, 'html.parser')

        for elem in soup(["head", "style", "script", "title"]):
            elem.extract()

        if abstract_length is None:
            abstract_length = self.abstract_length

        if abstract_length == 0:
            return HTMLValue(soup)

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

    def prop_get_html(self, context):
        html = self._get_html(context)
        ret = HTMLValue(html)
        return ret


class Snippet(HTMLContent):
    def get_outputs(self):
        return []

    def check_update(self, output_path):
        if self.updated:
            return True

        stat = self.metadata.get('stat', None)
        if self.site.stat_depfile and stat.st_mtime > self.site.stat_depfile.st_mtime:
            self.updated = True
            return True

        self.updated = False
        return False


class Article(HTMLContent):
    def pre_build(self):
        if self.generate_metadata_file:
            self._generate_metadata_file()

    def _generate_metadata_file(self):
        srcpath = self.metadata.get('srcpath', None)
        if srcpath is None:
            return

        if 'date' not in self.metadata:
            if self.date:
                return

            tz = self.timezone
            date = datetime.datetime.now().astimezone(tz).replace(microsecond=0)

            yaml = f'''
date: {date.isoformat(timespec='seconds')}
'''

            dir, fname = os.path.split(srcpath)
            metafilename = Path(metadata_file_name(dir, fname))
            metafilename.write_text(yaml, 'utf-8')

            self.metadata['date'] = date

    def get_outputs(self):
        return [Output(self, self.filename)]

    def write(self, path):
        templatename = self.article_template
        template = self.site.jinjaenv.get_template(templatename)
        context = _context(self.site, self)
#        body = self.site.render(self, template, **self.get_render_args(context))

        body = self.site.render_from_template(self, template, **self.get_render_args(context))

        path.write_bytes(body.encode('utf-8'))

        return context


class IndexPage(Content):
    @property
    def ext(self):
        ext = self.get_metadata('ext', None)
        if ext is not None:
            return ext
        return '.html'

    def filename_to_page(self, values, npage):
        value = '_'.join(values)
        value = re.sub(r'[@/\\: \t]', lambda m: f'@{ord(m[0]):02x}', value)

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

        context = _context(self.site, self)
        return self.site.render_from_string(self, "indexpage_group_filename", filename_templ,
                                     value=value, cur_page=npage,
                                     **self.get_render_args(context))


    def get_output_path(self, values=(), npage=None, *args, **kwargs):
        if not npage:
            npage = 1
        filename = self.filename_to_page(values, npage)
        return f"{'/'.join(self.dirname)}/{filename}"

    def _to_filename(self):
        return self.filename_to_page([''], 1)

    def get_outputs(self):
        ret = []

        filters = getattr(self, 'filters', {})
        filters['type'] = {'article'}
        filters['draft'] = {False}

        groups = self.site.contents.group_items(
            getattr(self, 'groupby', None), filters=filters)

        n_per_page = int(self.indexpage_max_articles)
        page_orphan = int(self.indexpage_orphan)
        for names, group in groups:
            num = len(group)
            num_pages = ((num - 1) // n_per_page) + 1
            rest = num - ((num_pages - 1) * n_per_page)

            if rest <= page_orphan:
                if num_pages > 1:
                    num_pages -= 1

            if self.indexpage_max_num_pages:
                num_pages = min(num_pages, self.indexpage_max_num_pages)

            for page in range(0, num_pages):

                is_last = (page == (num_pages - 1))

                f = page * n_per_page
                t = num if is_last else f + n_per_page
                articles = group[f:t]

                filename = self.filename_to_page(names, page + 1)
                output = Output(self, filename, group_values=names, cur_page=page + 1,
                                is_last=is_last, num_pages=num_pages, articles=articles)
                ret.append(output)

        return ret

    def write(self, path, group_values, cur_page, is_last,
              num_pages, articles):
        if cur_page == 1:
            templatename = self.indexpage_template
        elif self.indexpage_template2:
            templatename = self.indexpage_template2
        else:
            templatename = self.indexpage_template

        template = self.site.jinjaenv.get_template(templatename)

        context = _context(self.site, self, pageargs=(cur_page - 1,))
        articles = [ContentArgProxy(context, article)
                    for article in articles]

        args = self.get_render_args(context)

#        body = self.site.render(self, template,
#                                group_values=group_values, cur_page=cur_page, is_last=is_last,
#                                num_pages=num_pages, articles=articles,
#                               **args)

        body = self.site.render_from_template(self, template,
                                group_values=group_values, cur_page=cur_page, is_last=is_last,
                                num_pages=num_pages, articles=articles,
                                **args)

        path.write_bytes(body.encode('utf-8'))
        return context


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

        filters = getattr(self, 'filters', {})
        filters['type'] = {'article'}
        filters['draft'] = {False}
        contents = [c for c in self.site.contents.get_contents(
            filters=filters)]

        num_articles = int(self.feed_num_articles)

        return [Output(self, self.filename, contents=contents[:num_articles])]

    def write(self, path, contents):
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

        context = _context(self.site, self)
        for c in contents:
            link = c.url
            description = c.prop_get_abstract(context, self.abstract_length)

            feed.add_item(
                title=str(c.title),
                link=link,
                unique_id=get_tag_uri(link, c.date),
                description=str(description),
                pubdate=c.date,
            )

        body = feed.writeString('utf-8')
        path.write_bytes(body.encode('utf-8'))
        return context


class Contents:
    def __init__(self):
        self._contents = {}

    def get_contents_keys(self):
        return self._contents.keys()

    def items(self):
        return self._contents.items()

    def add(self, content):
        key = (content.dirname, content.name)
        if key not in self._contents:
            self._contents[key] = content

    def has_content(self, key, base=None):
        dirname, filename = utils.abs_path(key, base.dirname if base else None)
        return ((dirname, filename) in self._contents)

    def get_content(self, key, base=None):
        dirname, filename = utils.abs_path(key, base.dirname if base else None)
        return self._contents[(dirname, filename)]

    def get_contents(self, subdirs=None, base=None, filters=None):
        contents = [c for c in self._contents.values()]

        if filters:
            filters = filters.copy()
            if 'draft' not in filters:
                filters['draft'] = {False}
            if 'type' not in filters:
                filters['type'] = {'article'}

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
            return [((), list(self.get_contents(subdirs, base, filters)))]

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
    return ConfigContent(site, dirname, filename, metadata, body)


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


class FileLoader:
    def _build_content(self, site, package, srcpath, dirname, filename, metadata, body):
        return content_class(metadata['type'])(site, dirname, filename, metadata, body)

    def from_file(self, site, srcpath, destpath):
        metadata = {
            'srcpath': srcpath,
            'destpath': destpath,
        }
        metadatafile = metadata_file_name(*os.path.split(srcpath))
        if os.path.exists(metadatafile):
            text = open(metadatafile, encoding=YAML_ENCODING).read()
            metadata.update(yaml.load(text) or {})

        body = self._get_body_from_file(site, srcpath, destpath, metadata)
        dirname, name = os.path.split(destpath)
        return self._build_content(site, None, srcpath, dirname, name, metadata, body)

    def from_package(self, site, package, srcpath, destpath):
        metadata = {
            'package': package,
            'srcpath': srcpath,
            'destpath': destpath,
        }
        metadatafile = metadata_file_name(*posixpath.split(srcpath))
        if pkg_resources.resource_exists(package, metadatafile):
            m = pkg_resources.resource_string(package, metadatafile)
            if m:
                metadata = yaml.load(m.decode(YAML_ENCODING)) or {}

        body = self._get_body_from_package(site, package, srcpath, destpath, metadata)

        dirname, name = os.path.split(destpath)
        return self._build_content(site, package, srcpath, dirname, name, metadata, body)


class BinaryLoader(FileLoader):
    def _get_body_from_file(self, site, srcpath, destpath, metadata):
        metadata.update({'type': 'binary'})

    def _get_body_from_package(self, site, package, srcpath, destpath, metadata):
        metadata.update({'type': 'binary'})


class RstLoader(FileLoader):
    def _get_body_from_file(self, site, srcpath, destpath, metadata):
        _metadata, body = rst.load(srcpath, metadata)
        metadata.update(_metadata)
        return body

    def _get_body_from_package(self, site, package, srcpath, destpath, metadata):
        src = pkg_resources.resource_string(package, srcpath).decode('utf-8')
        _metadata, body = rst.load_string(src, metadata)
        metadata.update(_metadata)
        return body


class YamlLoader(FileLoader):
    def _load(self, src, metadata):
        _metadata = yaml.load(src) or {}
        metadata.update(_metadata)

    def _get_body_from_file(self, site, srcpath, destpath, metadata):
        src = srcpath.read_text(encoding=YAML_ENCODING)
        self._load(src, metadata)

    def _get_body_from_package(self, site, package, srcpath, destpath, metadata):
        src = pkg_resources.resource_string(package, srcpath).decode('utf-8')
        self._load(src, metadata)


class HtmlLoader(FileLoader):
    def _get_body_from_file(self, site, srcpath, destpath, metadata):
        _metadata, body = html.load(srcpath)
        metadata.update(_metadata)
        return body

    def _get_body_from_package(self, site, package, srcpath, destpath, metadata):
        src = pkg_resources.resource_string(package, srcpath).decode('utf-8')
        _metadata, body = html.load_string(src)
        metadata.update(_metadata)
        return body


class MdLoader(FileLoader):
    def _get_body_from_file(self, site, srcpath, destpath, metadata):
        _metadata, body = md.load(srcpath)
        metadata.update(_metadata)
        return body

    def _get_body_from_package(self, site, package, srcpath, destpath, metadata):
        src = pkg_resources.resource_string(package, srcpath).decode('utf-8')
        _metadata, body = md.load_string(src)
        return body


class IpynbLoader(FileLoader):
    def _get_body_from_file(self, site, srcpath, destpath, metadata):
        _metadata, body = ipynb.load(srcpath)
        metadata.update(_metadata)
        return body

    def _get_body_from_package(self, site, package, srcpath, destpath, metadata):
        src = pkg_resources.resource_string(package, srcpath).decode('utf-8')
        _metadata, body = ipynb.load_string(src)
        metadata.update(_metadata)
        return body


LOADERS = {
    ".rst": RstLoader(),
    ".yml": YamlLoader(),
    ".yaml": YamlLoader(),
    ".html": HtmlLoader(),
    ".md": MdLoader(),
    ".ipynb": IpynbLoader(),
}


bin_loader = BinaryLoader()


def getContentLoader(ext):
    return LOADERS.get(ext, bin_loader)


METADATA_FILE_SUFFIX = '.props.yml'


def metadata_file_name(dirname, fname):
    return posixpath.join(dirname, f'{fname}{METADATA_FILE_SUFFIX}')


def load_directory(site, path, loader=None):
    logger.info(f"Loading {path}")
    path = path.expanduser().resolve()
    if not path.is_dir():
        logger.debug(f'directory: {str(path)} is not a valid directory.')
        return

    for p in utils.walk(path):
        try:
            name = os.path.relpath(p, path)
            dirname, filename = os.path.split(name)
            if site.config.is_ignored(filename):
                continue
            if filename.lower().endswith(METADATA_FILE_SUFFIX):
                continue

            _loader = loader
            if not _loader:
                _loader = getContentLoader(p.suffix)

            content = _loader.from_file(site, p, name)
            if content:
                site.contents.add(content)
        except Exception as e:
            logger.exception(f'Error loading {p}')
            raise
    return


def load_package(site, package, path, loader=None):
    logger.info(f"Loading {package}/{path}")
    if not path.endswith('/'):
        path = path + '/'

    for filename in utils.walk_package(package, path):
        name = filename[len(path):]
        if name.lower().endswith(METADATA_FILE_SUFFIX):
            continue

        _loader = loader
        if not _loader:
            ext = os.path.splitext(filename)[1]
            _loader = getContentLoader(ext)

        content = _loader.from_package(site, package, filename, name)
        if content:
            site.contents.add(content)

    return
