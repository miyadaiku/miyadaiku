from typing import List, Type, Sequence, Tuple
from miyadaiku import ContentPath, ContentSrc
from .loader import ContentFiles
from .site import Site
from .contents import Content


class OutputContext:
    @classmethod
    def create(
        cls, site: Site, content: Content, files: ContentFiles
    ) -> List[OutputContext]:
        return [cls(site, content, files)]

    def __init__(self, site: Site, content: Content, files: ContentFiles) -> None:
        self.contentpath = content.src.contentpath


class IndexOutputContext(OutputContext):
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


BUILDERS = {
    "index": IndexOutputContext,
}


def createBuilder(src: ContentSrc, files: ContentFiles) -> Type[OutputContext]:
    builder = BUILDERS.get(src.metadata["type"], OutputContext)
    return builder
