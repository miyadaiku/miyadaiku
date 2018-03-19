import re
import shutil
import secrets
import os
import traceback
import posixpath
import atexit
import collections
import datetime
import pkg_resources
from pathlib import Path, PosixPath
import urllib.parse
import tempfile
import yaml
from jinja2 import Template
import jinja2.exceptions
import logging
import markupsafe
from bs4 import BeautifulSoup
from bs4.element import NavigableString
import pytz
from feedgenerator import Atom1Feed, Rss201rev2Feed, get_tag_uri

import miyadaiku
import miyadaiku.core
from . import YAML_ENCODING
from . import utils, rst, html, md, config, ipynb, hooks
from .hooks import run_hook, HOOKS
from .exception import MiyadaikuBuildError

logger = logging.getLogger(__name__)
LARGE_FILE_SIZE = 1024 * 1024

_tempfiles = []
pid = os.getpid()


@atexit.register
def deletefiles():
    if pid != os.getpid():
        return

    for f in _tempfiles:
        try:
            logger.debug(f'Removong {f}')
            os.unlink(f)
        except Exception as e:
            logger.exception(f'Failed to remove {f}')


class ContentNotFound(Exception):
    content = None

    def set_content(self, content):
        if not self.content:
            self.content = content
            self.args = (f'{self.content.srcfilename}: `{self.args[0]}` is not found',)


class _metadata(dict):
    def __getattr__(self, name):
        return self.get(name, None)


class _context(dict):
    def __init__(self, site, page_content, *, pageargs=None):
        self.site = site
        self.page_content = page_content
        self.__depends = set()
        self.__rebuildallways = False
        self.__pageargs = pageargs
        self.__html_cache = {}

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

    def set_rebuild(self):
        self.__rebuildallways = True

    def is_rebuild_always(self):
        return self.__rebuildallways

    def get_html_cache(self, content):
        f = self.__html_cache.get((content.dirname, content.name), (None, None))[0]
        if f:
            f.seek(0)
            return f.read()
        return f

    def get_header_cache(self, content):
        return self.__html_cache.get((content.dirname, content.name), (None, None))[1]

    def set_html_cache(self, content, html, headers):
        f = tempfile.SpooledTemporaryFile(mode='r+', max_size=LARGE_FILE_SIZE,
                                          encoding='utf32')
        f.write(html)
        self.__html_cache[(content.dirname, content.name)] = (f, headers)


class ContentArgProxy:
    def __init__(self, context, content):
        self.context, self.content = context, content

    def __getattr__(self, name):
        if not hasattr(self.content, name):
            prop = f'prop_get_{name}'
            f = getattr(self.content, prop, None)
            if f:
                return f(self.context)

        return getattr(self.content, name)

    _omit = object()

    def load(self, target, default=_omit):
        try:
            ret = self.content.get_content(target)
            return ContentArgProxy(self.context, ret)
        except ContentNotFound as e:
            e.set_content(self.content)
            raise

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
        self._body = self._bodyfilename = None

        assert (body is None) or (isinstance(body, str))
        if body is None:
            self._body = None
        elif len(body) < LARGE_FILE_SIZE:
            self._body = body
        else:
            fd, self._bodyfilename = tempfile.mkstemp()
            _tempfiles.append(self._bodyfilename)

            with os.fdopen(fd, mode='w', encoding='utf32') as f:
                f.write(body)

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
            return False

        if self.site.stat_depfile and stat.st_mtime > self.site.stat_depfile.st_mtime:
            return True

        return False

    def calc_path(self, path, dirname, name):
        dir = path.joinpath(*dirname)
        name = name.strip('/\\')
        dest = os.path.expanduser((dir / name))
        dest = os.path.normpath(dest)
        return dest

    def _check_fileupdate(self, outputpath, stat):
        filename = self.calc_path(outputpath, self.dirname, self.filename)
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
        ret = self.render_from_string(context, self, "filename_templ", filename_templ,
                                      kwargs=self.get_render_args(context))
        assert ret
        return ret

    @property
    def title(self):
        return self.get_metadata('title', None) or os.path.splitext(self.name)[0]

    @property
    def body(self):
        if self._body is not None:
            return self._body
        elif self._bodyfilename:
            return open(self._bodyfilename, mode='r', encoding='utf32').read()
        return None

    @property
    def filename(self):
        try:
            if self._filename:
                return self._filename

            self._filename = self.get_metadata('filename', None)
            if not self._filename:
                self._filename = self._to_filename()
            return self._filename
        except Exception:
            raise

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
            package = package + '!'

        path = self.metadata.get('srcpath', None)
        if path:
            path = os.path.relpath(path)
            return package + path

        return package + os.path.join(*self.dirname, self.name)

    @property
    def url(self):
        return self.get_url()

    def get_url(self, *args, **kwargs):
        site_url = self.get_metadata('site_url')
        path = self.metadata.get('canonical_url')
        if path:
            parsed = urllib.parse.urlsplit(path)
            if parsed.scheme or parsed.netloc:
                return path  # abs url

            if not parsed.path.startswith('/'):  # relative path?
                path = posixpath.join(*self.dirname, path)
        else:
            path = self.get_output_path(*args, **kwargs)
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
        return posixpath.join(*self.dirname, self.filename)

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

        target_url = target.get_url(*args, **kwargs)
        if abs_path or self.use_abs_path:
            return target_url + fragment

        target_parsed = urllib.parse.urlsplit(target_url)

        my_parsed = urllib.parse.urlsplit(self.get_url(*args, **kwargs))

        # return abs url if protocol or server differs
        if ((target_parsed.scheme != my_parsed.scheme) or
                (target_parsed.netloc != my_parsed.netloc)):
            return target_url + fragment

        my_dir = posixpath.dirname(my_parsed.path)
        if my_dir == target_parsed.path:
            ret_path = my_dir
        else:
            ret_path = posixpath.relpath(target_parsed.path, my_dir)

        if target_parsed.path.endswith('/') and (not ret_path.endswith('/')):
            ret_path = ret_path + '/'
        return ret_path + fragment

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

    def build(self, dir):
        return [], _context(self.site, self)

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

    def _amend_exception(self, e, context, page, filename, src):
        if not isinstance(e, MiyadaikuBuildError):
            return MiyadaikuBuildError(e, page, filename, src)
        return e

    def render_from_string(self, context, content, propname, text, kwargs):
        filename = f'{content.srcfilename}#{propname}'
        try:
            template = self.site.jinjaenv.from_string(text)
            template.filename = filename
            return template.render(**kwargs)
        except Exception as e:
            exc = self._amend_exception(e, context, content, filename, text)
            raise exc from e

    def render_from_template(self, context, content, filename, kwargs):
        try:
            template = self.site.jinjaenv.get_template(filename)
            template.filename = filename
            return template.render(**kwargs)
        except Exception as e:
            exc = self._amend_exception(e, context, content, filename, None)
            raise exc from e


class ConfigContent(Content):
    def _check_fileupdate(self, output_path, stat):
        return False


class BinContent(Content):
    def __init__(self, site, dirname, name, metadata, body):
        super().__init__(site, dirname, name, metadata, body)

    def build(self, dir):
        outfilename = utils.prepare_output_path(dir, self.dirname, self.filename)
        context = self.write(outfilename)
        return [outfilename], context

    def write(self, path):
        body = self.body
        if body is None:
            package = self.metadata.get('package')
            if package:
                body = pkg_resources.resource_string(package, self.metadata['srcpath'])
                Path(path).write_bytes(body)
            else:
                shutil.copyfile(str(self.metadata['srcpath']), path)
        else:
            Path(path).write_bytes(body)

        context = _context(self.site, self)
        return context


class HTMLValue(markupsafe.Markup):
    pass


class HTMLContent(Content):
    has_jinja = True

    def __init__(self, site, dirname, name, metadata, body):
        super().__init__(site, dirname, name, metadata, body)

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
        context.add_depend(self)
        ret = context.get_html_cache(self)
        if ret is not None:
            return ret

        html = self.body or ''
        if self.has_jinja:
            html = self.render_from_string(context, self, "html", html,
                                           kwargs=self.get_render_args(context))

        headers, html = self._set_header_id(html)

        ret = context.set_html_cache(self, html, headers)
        return html

    def _get_headers(self, context):
        ret = context.get_header_cache(self)
        if ret is not None:
            return ret

        self._get_html(context)
        return context.get_header_cache(self)

    _in_get_headertext = False

    def get_headertext(self, context, fragment):
        if self._in_get_headertext:
            return 'dummy'

        self._in_get_headertext = True
        try:
            headers = self._get_headers(context)
            assert headers is not None
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

    def build(self, dir):
        outfilename = utils.prepare_output_path(dir, self.dirname, self.filename)
        context = self.write(outfilename)
        return [outfilename], context

    def write(self, path):
        context = _context(self.site, self)

        templatename = self.article_template
        body = self.render_from_template(
            context, self, templatename, kwargs=self.get_render_args(context))

        Path(path).write_bytes(body.encode('utf-8'))

        return context


class IndexPage(HTMLContent):
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
        kwargs = dict(value=value, cur_page=npage)
        kwargs.update(self.get_render_args(context))
        return self.render_from_string(context, self, "indexpage_group_filename", filename_templ,
                                       kwargs=kwargs)

    def get_output_path(self, values=(), npage=None, *args, **kwargs):
        if not npage:
            npage = 1
        filename = self.filename_to_page(values, npage)
        return posixpath.join(*self.dirname, filename)

    def _to_filename(self):
        return self.filename_to_page([''], 1)

    def build(self, dir):
        context = _context(self.site, self)
        outfilenames = []

        filters = getattr(self, 'filters', {}).copy()
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
                outfilename = utils.prepare_output_path(dir, self.dirname, filename)

                self.write(outfilename, context, group_values=names, cur_page=page + 1,
                           is_last=is_last, num_pages=num_pages, articles=articles)
                outfilenames.append(outfilename)

        return outfilenames, context

    def write(self, path, context, group_values, cur_page, is_last,
              num_pages, articles):
        if cur_page == 1:
            templatename = self.indexpage_template
        elif self.indexpage_template2:
            templatename = self.indexpage_template2
        else:
            templatename = self.indexpage_template

        template = self.site.jinjaenv.get_template(templatename)
        articles = [ContentArgProxy(context, article)
                    for article in articles]
        kwargs = dict(group_values=group_values, cur_page=cur_page,
                      is_last=is_last, num_pages=num_pages, articles=articles)
        kwargs.update(self.get_render_args(context))
        body = self.render_from_template(context, self, template,
                                         kwargs=kwargs)

        Path(path).write_bytes(body.encode('utf-8'))
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

    def build(self, dir):
        outfilename = utils.prepare_output_path(dir, self.dirname, self.filename)
        context = self.write(outfilename)
        return [outfilename], context

    def write(self, path):

        num_articles = int(self.feed_num_articles)

        filters = getattr(self, 'filters', {}).copy()
        filters['type'] = {'article'}
        filters['draft'] = {False}
        contents = [c for c in self.site.contents.get_contents(
            filters=filters)][:num_articles]

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
        Path(path).write_bytes(body.encode('utf-8'))
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
        try:
            return self._contents[(dirname, filename)]
        except KeyError:
            raise ContentNotFound(key) from None

    def get_contents(self, subdirs=None, base=None, filters=None):
        contents = [c for c in self._contents.values()]

        if not filters:
            filters = {}

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

    def _update_metadata(self, base, add):
        keys = list(add.keys() - base.keys())
        for k in keys:
            base[k] = add[k]

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
        self._update_metadata(metadata, _metadata)
        return body

    def _get_body_from_package(self, site, package, srcpath, destpath, metadata):
        src = pkg_resources.resource_string(package, srcpath).decode('utf-8')
        _metadata, body = rst.load_string(src, metadata)
        self._update_metadata(metadata, _metadata)
        return body


class YamlLoader(FileLoader):
    def _load(self, src, metadata):
        _metadata = yaml.load(src) or {}
        self._update_metadata(metadata, _metadata)

    def _get_body_from_file(self, site, srcpath, destpath, metadata):
        src = srcpath.read_text(encoding=YAML_ENCODING)
        self._load(src, metadata)

    def _get_body_from_package(self, site, package, srcpath, destpath, metadata):
        src = pkg_resources.resource_string(package, srcpath).decode('utf-8')
        self._load(src, metadata)


class HtmlLoader(FileLoader):
    def _get_body_from_file(self, site, srcpath, destpath, metadata):
        _metadata, body = html.load(srcpath)
        self._update_metadata(metadata, _metadata)
        return body

    def _get_body_from_package(self, site, package, srcpath, destpath, metadata):
        src = pkg_resources.resource_string(package, srcpath).decode('utf-8')
        _metadata, body = html.load_string(src)
        self._update_metadata(metadata, _metadata)
        return body


class MdLoader(FileLoader):
    def _get_body_from_file(self, site, srcpath, destpath, metadata):
        _metadata, body = md.load(srcpath)
        self._update_metadata(metadata, _metadata)
        return body

    def _get_body_from_package(self, site, package, srcpath, destpath, metadata):
        src = pkg_resources.resource_string(package, srcpath).decode('utf-8')
        _metadata, body = md.load_string(src)
        self._update_metadata(metadata, _metadata)
        return body


class IpynbLoader(FileLoader):
    def _build_content(self, site, package, srcpath, dirname, filename, metadata, body):
        content = super()._build_content(site, package, srcpath, dirname, filename,
                                         metadata, body)
        content.has_jinja = False
        return content

    def _get_body_from_file(self, site, srcpath, destpath, metadata):
        _metadata, body = ipynb.load(srcpath)
        self._update_metadata(metadata, _metadata)
        return body

    def _get_body_from_package(self, site, package, srcpath, destpath, metadata):
        src = pkg_resources.resource_string(package, srcpath).decode('utf-8')
        _metadata, body = ipynb.load_string(src)
        self._update_metadata(metadata, _metadata)
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

            run_hook(HOOKS.pre_load, site, p, None)
            _loader = loader
            if not _loader:
                _loader = getContentLoader(p.suffix)

            content = _loader.from_file(site, p, name)
            if content:
                site.contents.add(content)

            run_hook(HOOKS.post_load, site, p, None, content)

        except Exception as e:
            logger.exception(f'Error loading {p}')
            raise
    return


def load_package(site, package, path, loader=None):
    logger.info(f"Loading {package}/{path}")
    if not path.endswith('/'):
        path = path + '/'

    for filename in utils.walk_package(package, path):
        run_hook(HOOKS.pre_load, site, filename, package)

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
        run_hook(HOOKS.post_load, site, filename, package, content)

    return
