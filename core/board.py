"""
board.py — игровое поле 10x10 и правила размещения кораблей.

Поле хранит состояние каждой клетки:
  "." — пусто
  "S" — стоит корабль (видно только владельцу поля)
  "O" — промах (выстрел по пустой клетке)
  "X" — попадание (подбитая клетка корабля)
"""

import random
from .ship import Ship

# Размеры кораблей стандартного флота: один 4-палубный,
# два 3-палубных, три 2-палубных, четыре 1-палубных.
FLEET_SIZES = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]
HORIZONTAL = "horizontal"
VERTICAL = "vertical"

EMPTY = "."
SHIP = "S"
MISS = "O"
HIT = "X"


class Board:
    def __init__(self, size: int = 10):
        self.size = size
        # Сетка — список списков. Заполняем всё пустыми клетками.
        self.grid = [[EMPTY for _ in range(size)] for _ in range(size)]
        self.ships: list[Ship] = []

    # --- Размещение кораблей ---

    def can_place_ship(self, x: int, y: int, size: int,
                       orientation: str) -> bool:
        """
        Проверяет, можно ли поставить корабль с носом в (x, y),
        заданного размера и ориентации, не задевая чужие корабли.

        Правило «нельзя соприкасаться» включает и диагонали,
        поэтому проверяем клетку и всех её соседей вокруг.
        """
        # 1. Вычисляем все клетки будущего корабля.
        cells = self._ship_cells(x, y, size, orientation)
        if cells is None:
            return False  # корабль вылезает за границу поля

        # 2. Каждая клетка корабля и её соседи должны быть свободны.
        for cx, cy in cells:
            for nx, ny in self._neighbors(cx, cy):
                if self.grid[ny][nx] == SHIP:
                    return False
        return True

    def place_ship(self, x: int, y: int, size: int, orientation: str) -> bool:
        """Ставит корабль, если место свободно. Возвращает успех."""
        if not self.can_place_ship(x, y, size, orientation):
            return False
        cells = self._ship_cells(x, y, size, orientation)
        ship = Ship(cells)
        self.ships.append(ship)
        for cx, cy in cells:
            self.grid[cy][cx] = SHIP
        return True

    def is_fleet_complete(self) -> bool:
        """Все ли корабли расставлены. Считаем палубы: должно сойтись."""
        placed = sum(ship.size for ship in self.ships)
        return placed == sum(FLEET_SIZES)

    # --- Автогенерация расстановки ---

    def place_fleet_randomly(self, rng: random.Random | None = None) -> None:
        """
        Случайно расставляет весь флот из FLEET_SIZES.

        Гарантированно завершается с полностью расставленным флотом.
        Если за разумное число попыток не получилось (на 10x10 это
        практически исключено, но перестраховка не помешает) —
        поле сбрасывается и всё начинается заново.

        rng — необязательный генератор случайных чисел. Если передать
        свой, можно получить повторяемую расстановку: удобно для тестов.
        """
        if rng is None:
            rng = random  # по умолчанию — обычный генератор модуля random

        # Пробуем «забег» целиком, пока не получится.
        # На практике первый же забег почти всегда успешен.
        while True:
            self._reset_ships()
            all_placed = True

            # Ставим корабли от больших к маленьким.
            # Это важно: маленькие корабли ютятся в любых щелях,
            # а большие занимают много места — если начать с маленьких,
            # четырёхпалубнику в конце может не хватить места,
            # и придётся перекладывать всё заново.
            for size in sorted(FLEET_SIZES, reverse=True):
                placed = False
                attempts = 0

                while not placed:
                    attempts += 1
                    if attempts > 1000:
                        # Место кончилось — начинаем всю расстановку с нуля.
                        all_placed = False
                        break

                    orientation = rng.choice([HORIZONTAL, VERTICAL])
                    x = rng.randrange(self.size)
                    y = rng.randrange(self.size)

                    if self.place_ship(x, y, size, orientation):
                        placed = True

                if not all_placed:
                    break

            if all_placed:
                return  # флот расставлен полностью — выходим

    def _reset_ships(self) -> None:
        """Очищает поле и список кораблей перед новой расстановкой."""
        self.ships = []
        for row in range(self.size):
            for col in range(self.size):
                self.grid[row][col] = EMPTY

    # --- Выстрелы ---

    def receive_shot(self, x: int, y: int) -> dict:
        """
        Обрабатывает выстрел по полю. Возвращает словарь ровно в том
        формате, который уходит по сети в сообщении result:

          {"outcome": "miss" | "hit" | "sunk", "cells": [...],
           "game_over": bool}
        """
        if x < 0 or x >= self.size or y < 0 or y >= self.size:
            raise ValueError(f"Клетка ({x}, {y}) вне поля")

        cell = self.grid[y][x]

        # Сюда уже стреляли — тактически это промах, повторного
        # попадания нет. (Правило «нельзя стрелять дважды» проверяет
        # игра, а не доска: доска только честно отвечает.)
        if cell == MISS or cell == HIT:
            return {"outcome": "miss", "cells": [], "game_over": False}

        if cell == EMPTY:
            self.grid[y][x] = MISS
            return {"outcome": "miss", "cells": [], "game_over": False}

        # В клетке корабль — ищем, какой именно.
        self.grid[y][x] = HIT
        for ship in self.ships:
            if ship.register_hit(x, y):
                if ship.is_sunk:
                    # Корабль потоплен: сообщаем его клетки (для поля cells)
                    # и помечаем воду вокруг — туда стрелять бессмысленно.
                    self._mark_around_sunk(ship)
                    game_over = self._all_sunk()
                    return {"outcome": "sunk",
                            "cells": ship.get_cells(),
                            "game_over": game_over}
                return {"outcome": "hit", "cells": [], "game_over": False}

        # Сюда дойти не должно: клетка помечена как корабль,
        # значит, какой-то корабль обязан был ответить.
        raise RuntimeError("Несогласованное состояние: клетка корабля без корабля")

    # --- Вспомогательные методы (внутренняя кухня) ---

    def _ship_cells(self, x: int, y: int, size: int,
                    orientation: str) -> list[tuple[int, int]] | None:
        """Клетки корабля по точке, размеру и направлению.
        None — если корабль не помещается на поле."""
        cells = []
        for i in range(size):
            if orientation == "horizontal":
                cx, cy = x + i, y
            else:
                cx, cy = x, y + i
            if cx < 0 or cx >= self.size or cy < 0 or cy >= self.size:
                return None
            cells.append((cx, cy))
        return cells

    def _neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        """Все клетки вокруг (x, y), включая диагонали, плюс сама клетка."""
        result = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.size and 0 <= ny < self.size:
                    result.append((nx, ny))
        return result

    def _mark_around_sunk(self, ship: Ship) -> None:
        """Помечает пустые клетки вокруг потопленного корабля как промахи.
        Игроку это экономит ходы, а правилам не противоречит:
        там и так не могло быть корабля."""
        for cx, cy in ship.get_cells():
            for nx, ny in self._neighbors(cx, cy):
                if self.grid[ny][nx] == EMPTY:
                    self.grid[ny][nx] = MISS

    def _all_sunk(self) -> bool:
        """Потоплены ли все корабли на поле."""
        return all(ship.is_sunk for ship in self.ships)
