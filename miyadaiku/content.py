from typing import List, Iterator, Dict, Tuple, Optional, DefaultDict, Any, Callable, Set, Union, TypedDict

from miyadaiku import config, ContentPath



class Context:
    def __init__(self, config:config.Config, contents, path:ContentPath):
        self.config = config
        self.contents = contents
        self.path = path

    def build(self):
        content = self.getContent(path)
        builder = Builder.get(content)
        builder.build()



class Builder:
    pass



class Content:
    def __init__(self, context, path:ContentPath, metadata: Dict[str, Any]):
        self.path = path
        self.context = context
        self.metadata = metadata

    def __str__(self):
        return f'<{self.__class__.__name__} {self.srcfilename}>'

    _omit = object()

    def get_metadata(self, name:str, default=_omit):
        if name in self.metadata:
            return config.format_value(name, getattr(self.metadata, name))

        if default is self._omit:
            return self.site.config.get(self.dirname, name)
        else:
            return self.site.config.get(self.dirname, name, default)

    def is_same(self, other):
        other = self.get_content(other)
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
    def parents_dirs(self):
        ret = [()]
        for dirname in self.dirname:
            ret.append(ret[-1] + (dirname,))
        return ret

    @property
    def title(self):
        return self.get_metadata('title', None) or os.path.splitext(self.name)[0]

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
        # *args/**kwargsを削除してnpageを引数に追加
        # canonical_urlはnpage==1のときのみ
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

    def prop_get_header_anchors(self, context):
        return []

    def prop_get_fragments(self, context):
        return []

    def prop_get_abstract(self, context):
        return ""

    def prop_get_html(self, context):
        return ""

    def get_output_path(self, *args, **kwargs):
        return posixpath.join(*self.dirname, self.filename)

    def get_content(self, target):
        if isinstance(target, (Content, ContentArgProxy)):
            return target
        else:
            return self.site.contents.get_content(target, self)

    def path_to(self, target, fragment=None, abs_path=False, *args, **kwargs):
        target = self.get_content(target)
        fragment = f'#{markupsafe.escape(fragment)}' if fragment else ''

        target_url = target.get_url(*args, **kwargs)
        if abs_path or self.use_abs_path:
            return target_url + fragment

        target_parsed = urllib.parse.urlsplit(target_url)

        my_parsed = urllib.parse.urlsplit(self.get_url(*args, **kwargs))

        # return abs url if protocol or server differs
        if ((target_parsed.scheme != my_parsed.scheme)
                or (target_parsed.netloc != my_parsed.netloc)):
            return target_url + fragment

        my_dir = posixpath.dirname(my_parsed.path)
        if my_dir == target_parsed.path:
            ret_path = my_dir
        else:
            ret_path = posixpath.relpath(target_parsed.path, my_dir)

        if target_parsed.path.endswith('/') and (not ret_path.endswith('/')):
            ret_path = ret_path + '/'
        return ret_path + fragment

    def link_to(self, context, target, text=None, fragment=None,
                abs_path=False, attrs=None, plain=True, *args, **kwargs):
        target = self.get_content(target)

        if not text:
            if fragment:
                text = target.get_headertext(context, fragment)
                if text is None:
                    raise ValueError(f'Cannot find fragment: {fragment}')

                if plain:
                    soup = BeautifulSoup(text, 'html.parser')
                    text = markupsafe.escape(soup.text.strip())

            if not text:
                text = markupsafe.escape(target.title)

        else:
            text = markupsafe.escape(text or '')

        s_attrs = []
        if attrs:
            for k, v in attrs.items():
                s_attrs.append(f"{markupsafe.escape(k)}='{markupsafe.escape(v)}'")
        path = markupsafe.escape(self.path_to(target, fragment=fragment,
                                              abs_path=abs_path, *args, **kwargs))
        return markupsafe.Markup(f"<a href='{path}' { ' '.join(s_attrs) }>{text}</a>")


class BinContent:
    pass

class Article:
    pass

class Snippet:
    pass


class IndexPage:
    pass

class FeedPage:
    pass

class Config:
    pass

CONTENT_CLASSES = {
    'binary': BinContent,
    'snippet': Snippet,
    'article': Article,
    'index': IndexPage,
    'feed': FeedPage,
    'config': Config,
}

def get_content_cls(typename):
    return CONTENT_CLASSES[typename]
