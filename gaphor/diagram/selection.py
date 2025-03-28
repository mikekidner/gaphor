from collections.abc import Iterable

from gaphas.item import Item
from gaphas.selection import Selection as _Selection


class Selection(_Selection):
    def __init__(self):
        super().__init__()
        self._dropzone_item: Item | None = None
        self._grayed_out_items: set[Item] = set()

    def clear(self):
        self._dropzone_item = None
        self._grayed_out_items.clear()
        super().clear()

    @property
    def dropzone_item(self) -> Item | None:
        return self._dropzone_item

    @dropzone_item.setter
    def dropzone_item(self, item: Item | None) -> None:
        if item is not self._dropzone_item:
            self._dropzone_item = item

    @property
    def grayed_out_items(self) -> set[Item]:
        return self._grayed_out_items

    @grayed_out_items.setter
    def grayed_out_items(self, items: Iterable[Item]) -> None:
        self._grayed_out_items = set(items)
