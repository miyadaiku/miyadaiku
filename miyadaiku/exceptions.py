from __future__ import annotations

from typing import Optional, TYPE_CHECKING


if TYPE_CHECKING:
    import miyadaiku.contents


class ContentNotFound(Exception):
    content: Optional[miyadaiku.contents.Content] = None

    def set_content(self, content: miyadaiku.contents.Content) -> None:
        if not self.content:
            self.content = content
            self.args = (
                f"{self.content.src.contentpath}: `{self.args[0]}` is not found",
            )


class ConfigNotFoundError(Exception):
    pass
