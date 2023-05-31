"""Zips two lists using a key"""
from typing import List, Tuple, Callable, Any


# don't know how to specify type hints for this
# def keyzip(left: List[Any], right: List[Any], getter: Callable[Any, Any]) -> List(Tuple):
def keyzip(left, right, getter):
    lkeys = [(getter(x), idx) for idx, x in enumerate(left)]
    lkeys.sort()
    rkeys = [(getter(x), idx) for idx, x in enumerate(right)]
    rkeys.sort()
    result = []
    idx_l = 0
    idx_r = 0

    while idx_l < len(left) or idx_r < len(right):
        if idx_r >= len(right) or \
                (idx_l < len(left) and lkeys[idx_l][0] < rkeys[idx_r][0]):
            result.append((lkeys[idx_l][1], left[lkeys[idx_l][1]], None))
            idx_l += 1
        elif idx_l >= len(left) or \
                (idx_r < len(right) and rkeys[idx_r][0] < lkeys[idx_l][0]):
            result.append((rkeys[idx_r][1], None, right[rkeys[idx_r][1]]))
            idx_r += 1
        else:
            idx_lr = (lkeys[idx_l][1] + rkeys[idx_r][1]) * 0.5
            result.append((idx_lr, left[lkeys[idx_l][1]], right[rkeys[idx_r][1]]))
            idx_l += 1
            idx_r += 1
    result.sort(key=lambda x: x[0])
    result = [(r[1], r[2]) for r in result]
    return result
