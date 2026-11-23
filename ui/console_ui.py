"""
console_ui.py — меню, расстановка кораблей и запуск партий.
"""

import random

from core.board import Board, FLEET_SIZES, HORIZONTAL, VERTICAL
from core.game import Game, HumanPlayer, BotPlayer
from ui.renderer import render_pair, render_single, LETTERS


def parse_cell(raw: str) -> tuple[int, int] | None:
    """«Б5» -> (1, 5). Возвращает None, если ввод не разобрать."""
    raw = raw.strip().upper().replace(" ", "")
    if len(raw) >= 2 and raw[0] in LETTERS and raw[1:].isdigit():
        x, y = LETTERS.index(raw[0]), int(raw[1:])
    else:
        return None
    if 0 <= x < 10 and 0 <= y < 10:
        return x, y
    return None


def read_shot() -> tuple[int, int]:
    """Функция ввода, которую интерфейс передаёт HumanPlayer."""
    while True:
        raw = input("Ваш выстрел: ")
        cell = parse_cell(raw)
        if cell is not None:
            return cell
        print("Не понял. Формат: буква столбца и номер строки, например Б5")


def place_remaining_randomly(board: Board, sizes: list[int]) -> None:
    """
    Расставляет перечисленные корабли случайно, но гарантированно:
    для каждого корабля собираем ВСЕ допустимые позиции и выбираем
    одну из них случайно. Отказа быть не может в принципе —
    если позиции существуют, мы их увидим.
    """
    for size in sizes:
        options = []
        for y in range(board.size):
            for x in range(board.size):
                for orientation in (HORIZONTAL, VERTICAL):
                    if board.can_place_ship(x, y, size, orientation):
                        options.append((x, y, orientation))
        x, y, orientation = random.choice(options)
        board.place_ship(x, y, size, orientation)


def setup_manual(board: Board) -> None:
    """Ручная расстановка: для каждого корабля спрашиваем клетку и направление."""
    pending = sorted(FLEET_SIZES, reverse=True)

    while pending:
        render_single(board, title="Ваша расстановка")
        counts: dict[int, int] = {}
        for size in pending:
            counts[size] = counts.get(size, 0) + 1
        description = ", ".join(
            f"{size}-палубных — {count}"
            for size, count in sorted(counts.items(), reverse=True)
        )
        raw = input(
            f"Осталось: {description}.\n"
            "Клетка и направление (например «Б5 в»), "
            "«а» — расставить остаток случайно: "
        ).strip()

        if raw.lower() == "а":
            place_remaining_randomly(board, pending)
            return

        parts = raw.replace(",", " ").split()
        if len(parts) != 2:
            print("Нужно: клетка и направление, например «Б5 в»")
            continue

        cell = parse_cell(parts[0])
        if cell is None:
            print("Не понял клетку. Пример: Б5")
            continue

        ori = parts[1].lower()
        if ori in ("г", "h"):
            orientation = HORIZONTAL
        elif ori in ("в", "v"):
            orientation = VERTICAL
        else:
            print("Направление: «г» (горизонтально) или «в» (вертикально)")
            continue

        x, y = cell
        if board.place_ship(x, y, pending[0], orientation):
            pending.pop(0)
        else:
            print("Здесь корабль не встаёт: граница поля или соседний корабль.")


def play_vs_bot() -> None:
    my_board = Board()
    bot_board = Board()
    bot_board.place_fleet_randomly()

    print("Как расставить флот? 1 — вручную, 2 — случайно")
    if input("> ").strip() == "1":
        setup_manual(my_board)
    else:
        my_board.place_fleet_randomly()

    human = HumanPlayer(
        "Вы",
        read_shot=read_shot,
        draw=lambda: render_pair(my_board, bot_board),
    )
    bot = BotPlayer("Бот")

    game = Game(human, bot, my_board, bot_board)
    winner = game.run()

    render_pair(my_board, bot_board)
    if winner is human:
        print("Победили вы!")
    else:
        print("Бот выиграл. В следующий раз повезёт.")
    print(f"Выстрелов: вы — {game.shots[0]}, бот — {game.shots[1]}")


def main() -> None:
    while True:
        print()
        print("=== Морской бой ===")
        print("1 — Играть против бота")
        print("2 — Сетевая игра (в разработке)")
        print("0 — Выход")
        choice = input("> ").strip()

        if choice == "1":
            play_vs_bot()
        elif choice == "2":
            print("Этот режим появится, когда друг достроит network/.")
        elif choice == "0":
            break
        else:
            print("Выберите 1, 2 или 0.")


if __name__ == "__main__":
    main()
