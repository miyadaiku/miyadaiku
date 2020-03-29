from typing import List, Type, Sequence, Tuple, Dict, Union, Optional
from miyadaiku import ContentPath, ContentSrc
from .loader import ContentFiles
from .site import Site
from .contents import Content


class ContentProxy:
    def __init__(self, site:Site, context:OutputContext, content:Content):
        self.site = site
        self.context = context
        self.content = content

    def __getattr__(self, name:str)->Any:
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





class OutputContext:
    contentpath: ContentPath
    _outputs: Dict[ContentPath, Union[None, bytes]]

    @classmethod
    def create(
        cls, site: Site, content: Content, files: ContentFiles
    ) -> List[OutputContext]:
        return [cls(site, content, files)]

    def __init__(self, site: Site, content: Content, files: ContentFiles) -> None:
        self.contentpath = content.src.contentpath
        self._outputs = {}

class BinaryOutput(OutputContext):
    pass

class ArticleOutput(OutputContext):
    def get_jinja_args(self, site:Site, context:OutputContext, content:Content)->Dict[str,Any]:

        page = ContextProxy(site, self,  site.files.get_content(self.contentpath))
        content = ContentProxy(site, self, content)
        
        contents = ContentsArgProxy(context, self)
        config = ConfigArgProxy(context, self)
        kwargs = {'config': config, 'contents': contents,
                  'page': page, 'content': content, 'context': context}

        imports = self._getimports()
        imports.update(kwargs)
        return imports


    def build(self, site: Site, path:ContentPath):
        self._outputs[path] = None
    
        content = site.files.get_content(self.contentpath)

        templatename = content .get_metadata(site, 'article_template')
        template = site.jinjaenv.get_template(templatename )
        template.filename = templatename

        output = template.render(**kwargs).encode("utf-8")
        self._outputs[path] = output

    def get_output(self, site: Site, path:ContentPath)->Union[None, bytes]:
        self.build(site, path)
        return self._outputs[path]

    def render_from_template(self, context, content, filename, kwargs):
        try:
            template = self.site.jinjaenv.get_template(filename)
            template.filename = filename
            return template.render(**kwargs)
        except Exception as e:
            exc = self._amend_exception(e, context, content, filename, None)
            raise exc from e

        
    


class IndexOutput(OutputContext):
    names: Tuple[str, ...]
    items: Sequence[ContentPath]
    cur_page: int
    num_pages: int


    @classmethod
    def create(
        cls, site: Site, content: Content, files: ContentFiles
    ) -> List[OutputContext]:
        filters = content.get_metadata(site, "filters", {}).copy()

        filters["type"] = {"article"}
        filters["draft"] = {False}

        groupby = content.get_metadata(site, "groupby", None)
        groups = files.group_items(site, groupby, filters=filters)

        n_per_page = int(content.get_metadata(site, "indexpage_max_articles", None))
        page_orphan = int(content.get_metadata(site, "indexpage_orphan", None))
        indexpage_max_num_pages = int(
            content.get_metadata(site, "indexpage_max_num_pages", 0)
        )

        ret: List[OutputContext] = []

        for names, group in groups:
            num = len(group)
            num_pages = ((num - 1) // n_per_page) + 1
            rest = num - (num_pages - 1) * n_per_page

            if rest <= page_orphan:
                if num_pages > 1:
                    num_pages -= 1

            if indexpage_max_num_pages:
                num_pages = min(num_pages, indexpage_max_num_pages)

            for page in range(0, num_pages):

                is_last = page == (num_pages - 1)

                f = page * n_per_page
                t = num if is_last else f + n_per_page
                articles = group[f:t]

                ret.append(cls(content, names, articles, page + 1, num_pages))

        return ret

    def __init__(
        self,
        content: Content,
        names: Tuple[str, ...],
        items: Sequence[Content],
        cur_page: int,
        num_pages: int,
    ) -> None:
        self.contentpath = content.src.contentpath
        self.names = names
        self.items = [c.src.contentpath for c in items]
        self.cur_page = cur_page
        self.num_pages = num_pages

BUILDERS = {
    "binary": BinaryOutput,
    "article": ArticleOutput,
    "index": IndexOutput,
}


def createBuilder(src: ContentSrc, files: ContentFiles) -> Optional[Type[OutputContext]]:
    builder = BUILDERS.get(src.metadata["type"], None)
    return builder
