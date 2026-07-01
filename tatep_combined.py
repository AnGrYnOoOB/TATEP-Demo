"""Простий TATEP-клієнт для обміну статусами по UDP.

Скрипт приймає повідомлення від сервера по UDP, розбирає вхідні
protobuf-пакети та відповідає пакетом статусу.
"""

import io
import socket
import delimited_protobuf

import protocol_pb2


# Адреса та порт, на яких слухає UDP-сокет.
LISTEN_IP = "100.127.42.140"
LISTEN_PORT = 2234

# Заголовок пакета для визначення початку protobuf-повідомлення.
HEADER = b"TTP\1"

# Поточні координати клієнта, які відправляються в статусі.
LAT = 50.28974
LON = 34.75593
ALT = 150.0


def build_status_packet():
    """Створити пакет ClientMessage зі станом та позицією клієнта."""
    msg = protocol_pb2.ClientMessage(
        status=protocol_pb2.ClientStatus(
            state=protocol_pb2.Engaging,
            position=protocol_pb2.WGS84(
                latitude_deg=LAT,
                longitude_deg=LON,
                altitude_msl_m=ALT,
            ),
        )
    )

    # Послідовно серіалізувати заголовок і protobuf-повідомлення.
    buf = io.BytesIO()
    buf.write(HEADER)
    delimited_protobuf.write(buf, msg)
    return buf.getvalue()


def parse_server_packet(data):
    """Розібрати вхідний ServerMessage та вивести його вміст."""
    if data[:4] != HEADER:
        print(f"Невірний заголовок: {data!r}")
        return

    payload = io.BytesIO(data[4:])

    # У пакеті може міститися один або кілька protobuf-повідомлень.
    while msg := delimited_protobuf.read(payload, protocol_pb2.ServerMessage):
        if msg.HasField("ping"):
            print("RX: Ping")
        elif msg.HasField("target_estimate"):
            print("RX: TargetEstimate")
            print(msg.target_estimate)
        elif msg.HasField("interceptor_estimate"):
            print("RX: InterceptorEstimate")
            print(msg.interceptor_estimate)
        elif msg.HasField("target_raw"):
            print("RX: TargetRaw")
            print(msg.target_raw)
        elif msg.HasField("target_interceptor"):
            print("RX: RawInterceptor")
            print(msg.target_interceptor)
        else:
            print("RX: Unknown")
            print(msg)


def main():
    """Запустити UDP-приймач і відповідати серверу на кожен пакет."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, LISTEN_PORT))

    print(f"TATEP клієнт слухає на {LISTEN_IP}:{LISTEN_PORT}")
    print(f"Власна позиція: {LAT}, {LON}, alt={ALT}")

    while True:
        data, addr = sock.recvfrom(2048)

        print(f"\nОтримано {len(data)} байт від {addr}")
        parse_server_packet(data)

        packet = build_status_packet()
        sock.sendto(packet, addr)

        print(f"TX: ClientStatus до {addr}, байт={len(packet)}")


if __name__ == "__main__":
    main()
