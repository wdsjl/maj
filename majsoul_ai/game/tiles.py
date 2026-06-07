"""麻将牌常量与 MJAI 牌面表示。"""

from __future__ import annotations

# 34 种牌 + 赤宝牌
ALL_TILES: list[str] = (
    [f"{n}m" for n in range(1, 10)]
    + [f"{n}p" for n in range(1, 10)]
    + [f"{n}s" for n in range(1, 10)]
    + ["E", "S", "W", "N", "P", "F", "C"]
)

AKA_DORA: list[str] = ["5mr", "5pr", "5sr"]

TILE_UNICODE: dict[str, str] = {
    "1m": "🀇", "2m": "🀈", "3m": "🀉", "4m": "🀊", "5m": "🀋",
    "6m": "🀌", "7m": "🀍", "8m": "🀎", "9m": "🀏",
    "1p": "🀙", "2p": "🀚", "3p": "🀛", "4p": "🀜", "5p": "🀝",
    "6p": "🀞", "7p": "🀟", "8p": "🀠", "9p": "🀡",
    "1s": "🀐", "2s": "🀑", "3s": "🀒", "4s": "🀓", "5s": "🀔",
    "6s": "🀕", "7s": "🀖", "8s": "🀗", "9s": "🀘",
    "E": "🀀", "S": "🀁", "W": "🀂", "N": "🀃",
    "P": "🀆", "F": "🀅", "C": "🀄",
    "5mr": "🀋", "5pr": "🀝", "5sr": "🀔",
}

TILE_NAMES_ZH: dict[str, str] = {
    "1m": "一萬", "2m": "二萬", "3m": "三萬", "4m": "四萬", "5m": "五萬",
    "6m": "六萬", "7m": "七萬", "8m": "八萬", "9m": "九萬",
    "1p": "一筒", "2p": "二筒", "3p": "三筒", "4p": "四筒", "5p": "五筒",
    "6p": "六筒", "7p": "七筒", "8p": "八筒", "9p": "九筒",
    "1s": "一索", "2s": "二索", "3s": "三索", "4s": "四索", "5s": "五索",
    "6s": "六索", "7s": "七索", "8s": "八索", "9s": "九索",
    "E": "东", "S": "南", "W": "西", "N": "北",
    "P": "白", "F": "发", "C": "中",
    "5mr": "赤五万", "5pr": "赤五筒", "5sr": "赤五索",
    "reach": "立直", "chi": "吃", "pon": "碰", "kan": "杠",
    "hora": "和", "ryukyoku": "流局", "none": "跳过",
}


def tile_display(tile: str) -> str:
    """返回牌的 Unicode + 中文名。"""
    u = TILE_UNICODE.get(tile, tile)
    name = TILE_NAMES_ZH.get(tile, tile)
    return f"{u}{name}"


def sort_tiles(tiles: list[str]) -> list[str]:
    order = {t: i for i, t in enumerate(ALL_TILES + AKA_DORA)}
    return sorted(tiles, key=lambda t: order.get(t, 999))
