"""
protocol.py — общий «язык общения» между двумя игроками по сети.

Файл общий для обеих частей проекта (игровая логика + сеть),
поэтому менять его можно только по договорённости с партнёром.
"""

import json
import socket

# --- Технические настройки ---

# Максимальный размер одного сообщения (байт). Длина его на много меньше,
# защита от повреждённых данных или случайного мусора в сети.
MAX_MESSAGE_SIZE = 4096

# Сколько байт занимает запись длины сообщения. Используем 4 байта
# (это число от 0 до ~4 млрд, хватает с запасом).
LENGTH_PREFIX_SIZE = 4

# Кодировка текста — должна совпадать у обоих игроков.
ENCODING = "utf-8"


# --- Типы сообщений (действия) ---

# Это «словарь имён». Вместо голых строк типа "shot" в коде пишут
# MSG_SHOT — так опечатка превратится в ошибку при запуске,
# а не в тихий баг на 3 часа отладки.

MSG_HELLO = "hello"           # приветствие при подключении
MSG_WELCOME = "welcome"       # ответ сервера: подключение принято
MSG_FLEET_READY = "fleet_ready"  # «я закончил расстановку кораблей»
MSG_SHOT = "shot"             # выстрел по координатам
MSG_RESULT = "result"         # ответ на выстрел: что получилось
MSG_FLEET = "fleet"           # передача итоговой информации о кораблях
MSG_GAME_OVER = "game_over"   # партия окончена
MSG_ERROR = "error"           # что-то пошло не так


# --- Формат сообщений  ---
#
# hello:      {"action": "hello", "name": "Имя игрока"}
# welcome:    {"action": "welcome", "your_turn_first": true/false}
# fleet_ready: {"action": "fleet_ready"}
# shot:       {"action": "shot", "x": 3, "y": 5}
# result:     {"action": "result", "outcome": "miss" | "hit" | "sunk",
#              "cells": [[3,5],[3,6], "game_over": false}
# fleet:      {"action": "fleet", "ships": [[0,0,0], ...]}  (клетки кораблей)
# game_over:  {"action": "game_over", "winner": "Имя победителя"}
# error:      {"action": "error", "message": "текст ошибки"}


# --- Функции отправки и получения ---

def send_message(sock: socket.socket, data: dict) -> None:
    """
    Отправляет словарь (сообщение) через сокет.

    Сначала отправляет 4 байта с длиной сообщения, потом само сообщение.
    Это позволяет принимающей стороне точно знать, сколько байтов читать.
    """
    # Превращаем словарь в строку JSON, затем в байты.
    raw = json.dumps(data, ensure_ascii=False).encode(ENCODING)

    # Проверяем, что сообщение не слишком длинное.
    if len(raw) > MAX_MESSAGE_SIZE:
        raise ValueError(f"Сообщение слишком длинное: {len(raw)} байт")

    # Упаковываем длину в 4 байта (big-endian — старший байт первым,
    # это общепринятый сетевой порядок байтов).
    length_prefix = len(raw).to_bytes(LENGTH_PREFIX_SIZE, byteorder="big")

    # Отправляем сначала длину, потом само сообщение.
    sock.sendall(length_prefix + raw)


def receive_message(sock: socket.socket) -> dict:
    """
    Получает одно сообщение из сокета и возвращает его как словарь.

    Блокируется (ждёт), пока сообщение не придёт полностью.
    Если соединение закрыто — возвращает None.
    """
    # 1. Читаем длину сообщения (ровно 4 байта).
    length_bytes = _recv_exact(sock, LENGTH_PREFIX_SIZE)
    if length_bytes is None:
        return None  # соединение закрыто

    length = int.from_bytes(length_bytes, byteorder="big")

    # Защита: длина не может быть больше разумного максимума.
    if length > MAX_MESSAGE_SIZE:
        raise ValueError(f"Подозрительная длина сообщения: {length}")

    # 2. Читаем само сообщение ровно такой длины.
    raw = _recv_exact(sock, length)
    if raw is None:
        return None

    # 3. Распаковываем JSON обратно в словарь.
    return json.loads(raw.decode(ENCODING))


def _recv_exact(sock: socket.socket, count: int) -> bytes | None:
    """
    Читает из сокета ровно count байтов.

    Нужна, потому что recv() может вернуть меньше байтов, чем мы
    попросили — TCP сам решает, сколько данных отдаст за раз.
    Мы собираем данные, пока не наберём ровно нужное количество.
    """
    parts = []          # сюда складываем кусочки
    received = 0        # сколько байтов уже получили

    while received < count:
        chunk = sock.recv(count - received)
        if not chunk:
            # Пустой ответ = соединение закрыто.
            return None
        parts.append(chunk)
        received += len(chunk)

    return b"".join(parts)
