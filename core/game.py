"""
game.py — игровой цикл: очередь ходов и определение победителя.

Game не знает, откуда приходят выстрелы: он общается с игроками
через единый интерфейс класса Player. Поэтому одна и та же игра
работает с человеком, ботом и сетевым соперником.
"""

import random

from .board import Board

# Стрелок, попавший в корабль, ходит снова (классическое правило).
# Если преподаватель требует «один выстрел на ход» — поменяйте на False.
SHOOT_AGAIN_ON_HIT = True


class Player:
    """Базовый класс игрока. Наследники обязаны реализовать два метода."""

    name = "Player"

    def get_shot(self) -> tuple[int, int]:
        """Вернуть (x, y) выстрела. Метод блокирующий: пока игрок
        не выбрал клетку, игра ждёт."""
        raise NotImplementedError

    def on_result(self, x: int, y: int, result: dict) -> None:
        """Сообщить игроку результат ЕГО выстрела."""
        raise NotImplementedError

    def on_enemy_shot(self, x: int, y: int, result: dict) -> None:
        """Сообщить игроку выстрел ПРОТИВНИКА по его полю."""
        raise NotImplementedError


class HumanPlayer(Player):
    """Игрок-человек: вводит координаты с клавиатуры."""

    def __init__(self, name: str):
        self.name = name
        self._last_result = None  # сюда игра складывает результат выстрела

    def get_shot(self) -> tuple[int, int]:
        while True:
            raw = input(f"{self.name}, ваш выстрел (два числа, x и y): ")
            parts = raw.split()
            if len(parts) != 2:
                print("Нужно два числа через пробел, например: 3 5")
                continue
            try:
                x, y = int(parts[0]), int(parts[1])
            except ValueError:
                print("Введите именно числа.")
                continue
            if 0 <= x <= 9 and 0 <= y <= 9:
                return x, y
            print("Координаты должны быть от 0 до 9.")

    def on_result(self, x: int, y: int, result: dict) -> None:
        outcome = result["outcome"]
        if outcome == "miss":
            print("Мимо!")
        elif outcome == "hit":
            print("Попадание! Ходите снова.")
        else:  # sunk
            print(f"Убил! Клетки корабля: {result['cells']}")

    def on_enemy_shot(self, x: int, y: int, result: dict) -> None:
        # Человеку важен только результат выстрела по ЕГО полю.
        outcome = result["outcome"]
        if outcome == "miss":
            print(f"Противник выстрелил в ({x}, {y}) — мимо.")
        elif outcome == "hit":
            print(f"Противник попал в ({x}, {y})!")
        else:
            print(f"Противник потопил корабль! Клетки: {result['cells']}")


class BotPlayer(Player):
    """
    Игрок-бот со стратегией «охотник-добиватель».

    Пока ничего не подбито — стреляет по случайной нестрелянной клетке.
    Как только есть попадание — целится в соседние клетки, чтобы
    добить раненый корабль.
    """

    def __init__(self, name: str = "Bot", rng: random.Random | None = None):
        self.name = name
        self.rng = rng if rng is not None else random
        self.size = 10

        # Карта выстрелов по полю противника: False — не стреляли,
        # True — стреляли.
        self.shots = [[False] * self.size for _ in range(self.size)]

        # Клетки, где было попадание, но корабль ещё не потоплен.
        # Бот добивает их в первую очередь.
        self.wounded: list[tuple[int, int]] = []

    def get_shot(self) -> tuple[int, int]:
        # 1. Режим добивания: ищем нестрелянного соседа раненой клетки.
        for wx, wy in self.wounded:
            for nx, ny in self._neighbors(wx, wy):
                if not self.shots[ny][nx]:
                    return nx, ny

        # 2. Обычный режим: случайная нестрелянная клетка.
        candidates = [
            (x, y)
            for y in range(self.size)
            for x in range(self.size)
            if not self.shots[y][x]
        ]
        return self.rng.choice(candidates)

    def on_result(self, x: int, y: int, result: dict) -> None:
        self.shots[y][x] = True  # сюда стреляли, второй раз не пойдём

        outcome = result["outcome"]
        if outcome == "hit":
            self.wounded.append((x, y))
        elif outcome == "sunk":
            for cx, cy in result["cells"]:
                if (cx, cy) in self.wounded:
                    self.wounded.remove((cx, cy))
                self.shots[cy][cx] = True
                # Помечаем соседей как «известно пустые» — не тратим на них ходы
                for nx, ny in self._neighbors(cx, cy):
                    self.shots[ny][nx] = True

    def on_enemy_shot(self, x: int, y: int, result: dict) -> None:
        pass  # боту не важно, куда стреляют в него

    def _neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        """Соседи по четырём сторонам (для добивания диагонали бесполезны:
        корабль не может стоять по диагонали от попадания)."""
        result = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                result.append((nx, ny))
        return result


class RemotePlayer(Player):
    """
    Каркас сетевого игрока — заполняет ваш друг в network/.

    Идея: этот класс — единственное место, где встречаются сеть и игра.
    Game общается с ним так же, как с ботом или человеком, а RemotePlayer
    внутри себя переводит вызовы в сообщения протокола.
    """

    def __init__(self, name: str, sock, protocol_module):
        """
        sock — сетевое соединение (socket.socket),
        protocol_module — модуль protocol.py с send_message/receive_message.
        """
        self.name = name
        self.sock = sock
        self.protocol = protocol_module

    def get_shot(self) -> tuple[int, int]:
        # Ход этого игрока приходит по сети: ждём сообщение shot.
        msg = self.protocol.receive_message(self.sock)
        if msg is None:
            raise ConnectionError("Противник отключился")
        if msg["action"] == self.protocol.MSG_SHOT:
            return msg["x"], msg["y"]
        raise ValueError(f"Неожиданное сообщение: {msg}")

    def on_result(self, x: int, y: int, result: dict) -> None:
        # Результат выстрела ПРОТИВНИКА по нашему полю уходит в сеть.
        self.protocol.send_message(self.sock, {
            "action": self.protocol.MSG_RESULT,
            "x": x,
            "y": y,
            **result,  # outcome, cells, game_over — как договорились в протоколе
        })

    def on_enemy_shot(self, x: int, y: int, result: dict) -> None:
        # В сетевой игре у каждого свой Game: игрок не «наблюдает»
        # за чужим выстрелом, а сам его получает. Поэтому этот метод
        # для удалённого игрока не используется.
        pass


class Game:
    """Матч между двумя игроками."""

    def __init__(self, player1: Player, player2: Player,
                 board1: Board, board2: Board):
        # Флот обоих должен быть расставлен заранее.
        if not board1.is_fleet_complete() or not board2.is_fleet_complete():
            raise ValueError("Флот должен быть расставлен до начала игры")

        self.players = [player1, player2]
        self.boards = [board1, board2]  # поле каждого игрока
        self.current = 0        # индекс игрока, чей сейчас ход
        self.finished = False
        self.winner: Player | None = None
        self.shot_count = 0     # статистика — пригодится для отчёта

    def _opponent_index(self) -> int:
        return 1 - self.current

    def run(self) -> Player:
        """Основной цикл. Возвращает победителя."""
        while not self.finished:
            self._play_turn()
        return self.winner

    def _play_turn(self) -> None:
        shooter = self.players[self.current]
        enemy_board = self.boards[self._opponent_index()]

        # 1. Стреляющий игрок называет клетку.
        x, y = shooter.get_shot()
        self.shot_count += 1

        # 2. Поле противника обрабатывает выстрел.
        result = enemy_board.receive_shot(x, y)

        # 3. Все узнают, что произошло.
        shooter.on_result(x, y, result)
        self.players[self._opponent_index()].on_enemy_shot(x, y, result)

        # 4. Проверяем конец игры.
        if result["game_over"]:
            self.finished = True
            self.winner = shooter
            return

        # 5. Переход хода: после промаха ходит противник,
        #    после попадания — ходит снова стрелявший.
        if result["outcome"] == "miss" or not SHOOT_AGAIN_ON_HIT:
            self.current = self._opponent_index()
