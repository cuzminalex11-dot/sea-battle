from core.board import Board
from core.game import Game, BotPlayer

# Смотрим итоговое поле: "." пусто, "O" промах, "X" попадание
def show(board):
    for row in board.grid:
        print(" ".join(row))

wins = {0: 0, 1: 0}
for i in range(50):
    boards = [Board(), Board()]
    for b in boards:
        b.place_fleet_randomly()

    game = Game(BotPlayer("Bot-1"), BotPlayer("Bot-2"), boards[0], boards[1])
    winner = game.run()
    wins[game.players.index(winner)] += 1

print("Побед:", wins)   # должно быть примерно пополам, например 27:23
print("Ходов в последней партии:", game.shot_count)  # обычно 40–100
