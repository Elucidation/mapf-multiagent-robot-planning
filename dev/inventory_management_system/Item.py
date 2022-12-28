from typing import NewType, List
import typing
from collections import Counter

ItemId = NewType('ItemId', int)
ItemCounter = typing.Counter[ItemId]

if __name__ == '__main__':
    x = ItemCounter(map(ItemId,[1, 2, 3, 2]))
    print(x)
