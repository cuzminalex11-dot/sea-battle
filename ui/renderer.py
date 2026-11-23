"""
renderer.py — отрисовка полей в консоли.

Поле противника рисуется с «туманом войны»: не подбитые корабли
выглядят как пустые клетки. (Символы при желании можно заменить
на красивые (■, ~, ×) — они собраны в одном словаре.)
"""

from core.board import Board, EMPTY, SHIP, MISS, HIT

# Столбцы обозначаются буквами: А, Б, В ... К
LETTERS = "АБВГДЕЖЗИК"

SYMBOLS = {EMPTY: ".", SHIP: "S", MISS: "O", HIT: "X"}


def _rows(board: Board, hide_ships: bool) -> list[str]:
    """Собирает строки поля: 10 строк по 10 символов через пробел."""
    result = []
    for y in range(board.size):
        cells = []
        for x in range(board.size):
            cell = board.grid[y][x]
            if hide_ships and cell == SHIP:
                cell = EMPTY
            cells.append(SYMBOLS[cell])
        result.append(" ".join(cells))
    return result


def render_single(board: Board, title: str = "Поле") -> None:
    """Рисует одно поле — используется при расстановке."""
    print(title)
    print("    " + " ".join(LETTERS))
    for y, row in enumerate(_rows(board, hide_ships=False)):
        print(f"{y:>2}  " + row)


def render_pair(my_board: Board, enemy_board: Board) -> None:
    """Рисует оба поля рядом: своё — с кораблями, чужое — без."""
    my_rows = _rows(my_board, hide_ships=False)
    enemy_rows = _rows(enemy_board, hide_ships=True)

    gap = "      "
    print("Моё поле" + " " * 17 + "Противник")
    print("    " + " ".join(LETTERS) + gap + "    " + " ".join(LETTERS))
    for y in range(my_board.size):
        print(f"{y:>2}  " + my_rows[y] + gap + f"{y:>2}  " + enemy_rows[y])
