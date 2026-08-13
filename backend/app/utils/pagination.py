from typing import Optional
from math import ceil


def paginate(page: int = 1, page_size: int = 20) -> tuple:
    """返回 (skip, limit)"""
    return (page - 1) * page_size, page_size


def calc_pages(total: int, page_size: int) -> int:
    return max(1, ceil(total / page_size))