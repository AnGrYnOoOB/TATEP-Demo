import io
import socket
import delimited_protobuf

import protocol_pb2


LISTEN_IP = "100.127.42.140"
LISTEN_PORT = 2234

HEADER = b"TTP\1"

LAT = 50.28974
LON = 34.75593
ALT = 150.0


def build_status_packet():
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

    buf = io.BytesIO()
    buf.write(HEADER)
    delimited_protobuf.write(buf, msg)
    return buf.getvalue()


def parse_server_packet(data):
    if data[:4] != HEADER:
        print(f"Invalid header: {data!r}")
        return

    payload = io.BytesIO(data[4:])

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
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, LISTEN_PORT))

    print(f"TATEP client listening on {LISTEN_IP}:{LISTEN_PORT}")
    print(f"Own position: {LAT}, {LON}, alt={ALT}")

    while True:
        data, addr = sock.recvfrom(2048)

        print(f"\nReceived {len(data)} bytes from {addr}")
        parse_server_packet(data)

        packet = build_status_packet()
        sock.sendto(packet, addr)

        print(f"TX: ClientStatus to {addr}, bytes={len(packet)}")


if __name__ == "__main__":
    main()
