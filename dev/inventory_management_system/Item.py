from typing import NewType, List
import typing
from collections import Counter

ItemId = NewType('ItemId', int)
ItemCounter = typing.Counter[ItemId]

def make_counter_of_items(item_list: List[int]) -> ItemCounter:
    return Counter([ItemId(item) for item in item_list])