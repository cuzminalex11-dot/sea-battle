import random
from core.board import Board, SHIP, FLEET_SIZES

board = Board()

# Успешное размещение
print(board.place_ship(0, 0, 4, "horizontal"))  # True — четырёхпалубник в начале поля

# Попытка поставить вплотную — должна быть запрещена
print(board.place_ship(0, 1, 1, "horizontal"))  # False — касается по вертикали

# Выстрелы
print(board.receive_shot(0, 0))  # hit
print(board.receive_shot(5, 5))  # miss
print(board.receive_shot(0, 0))  # miss — повторный выстрел

# Добиваем корабль
print(board.receive_shot(1, 0))  # hit
print(board.receive_shot(2, 0))  # hit
print(board.receive_shot(3, 0))  # sunk, cells = [[0,0],[1,0],[2,0],[3,0]], game_over = True

# Обычная случайная расстановка
board.place_fleet_randomly()

# Считаем клетки с кораблями — их должно быть ровно 20 (сумма FLEET_SIZES)
ship_cells = sum(row.count(SHIP) for row in board.grid)
print("Клеток под корабли:", ship_cells)          # 20
print("Кораблей на поле:", len(board.ships))      # 10

# Повторяемость: с фиксированным зерном расстановки всегда одинаковы
b1 = Board()
b1.place_fleet_randomly(random.Random(42))
b2 = Board()
b2.place_fleet_randomly(random.Random(42))
print("Одинаковы с одним зерном:", b1.grid == b2.grid)  # True

# Стресс-тест: 1000 случайных расстановок, все должны быть полными
ok = 0
for i in range(1000):
    b = Board()
    b.place_fleet_randomly()
    if b.is_fleet_complete():
        ok += 1
print(f"Успешных расстановок: {ok}/1000")  # 1000/1000

for row in board.grid:
    print(" ".join(row))