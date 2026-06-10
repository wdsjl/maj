"""将游戏快照格式化为可读的牌面监视文本。"""

from __future__ import annotations

from majsoul_ai.game.snapshot import GameSnapshot, MeldGroup
from majsoul_ai.game.tiles import TILE_UNICODE, tile_display


def format_tile_short(tile: str | None) -> str:
    if not tile:
        return "?"
    u = TILE_UNICODE.get(tile, "")
    return f"{u}{tile}"


def format_tile_list(tiles: list[str], sep: str = " ") -> str:
    if not tiles:
        return "（无）"
    return sep.join(format_tile_short(t) for t in tiles)


def format_meld(meld: MeldGroup) -> str:
    tiles = format_tile_list(meld.tiles, "")
    type_zh = {"chi": "吃", "pon": "碰", "daiminkan": "大明杠", "ankan": "暗杠", "kakan": "加杠"}
    return f"{type_zh.get(meld.meld_type, meld.meld_type)} [{tiles}]"


def format_snapshot(snap: GameSnapshot, template_count: int = 0, template_total: int = 37) -> str:
    """生成牌面监视面板的完整文本。"""
    lines: list[str] = []

    turn = "轮到你出牌" if snap.is_my_turn else "等待"
    lines.append(f"【状态】{'对局中' if snap.in_kyoku else '未开局'} | {turn}")
    lines.append(
        f"【置信】手牌 {snap.hand_confidence:.0%} | 牌河 {snap.river_confidence:.0%}"
    )

    if template_total > 0:
        lines.append(f"【模板库】{template_count}/{template_total} 已采集")

    if snap.dora or snap.dora_indicators:
        dora_str = format_tile_list(snap.dora_indicators or ([snap.dora] if snap.dora else []))
        lines.append(f"【宝牌】{dora_str}")

    hand_str = format_tile_list(snap.hand)
    lines.append(f"【手牌】{len(snap.hand)}张: {hand_str}")

    lines.append("【牌河】")
    seat_names = {0: "自家 P0", 1: "下家 P1", 2: "对家 P2", 3: "上家 P3"}
    has_river = False
    for pid in range(4):
        tiles = snap.rivers.get(pid, [])
        if tiles:
            has_river = True
            arrow = " → ".join(format_tile_short(t) for t in tiles)
            lines.append(f"  {seat_names.get(pid, f'P{pid}')} ({len(tiles)}): {arrow}")
    if not has_river:
        lines.append("  （无）")

    meld_lines = []
    for pid in range(4):
        for m in snap.melds.get(pid, []):
            meld_lines.append(f"  {seat_names.get(pid, f'P{pid}')}: {format_meld(m)}")
    lines.append("【副露】")
    lines.extend(meld_lines if meld_lines else ["  （无）"])

    return "\n".join(lines)


def format_hand_slots(
    slots: list[tuple[str | None, float, int]],
) -> list[str]:
    """格式化手牌槽位识别结果，供采集界面显示。"""
    result = []
    for tile, conf, idx in slots:
        if tile:
            result.append(f"[{idx}] {format_tile_short(tile)} {conf:.0%}")
        else:
            result.append(f"[{idx}] ? {conf:.0%}" if conf > 0 else f"[{idx}] —")
    return result
