from typing import NewType
import typing

ItemId = NewType('ItemId', int)
ItemCounter = typing.Counter[ItemId]

# TODO: Load this from DB / This fails from wrong directory
def get_item_names():
    with open('inventory_management_system/item_names.txt', 'r') as f:
        item_names = [name.strip() for name in f.readlines()]
    return item_names

if __name__ == '__main__':
    x = ItemCounter(map(ItemId,[1, 2, 3, 2]))
    print(x)
    print(get_item_names())
