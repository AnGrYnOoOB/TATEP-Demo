import io
import socket
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

import delimited_protobuf
import protocol_pb2


HEADER = b"TTP\1"


class TatepUi:
    def __init__(self, root):
        self.root = root
        self.root.title("TATEP Demo Client")

        self.sock = None
        self.running = False
        self.thread = None

        self.listen_ip = tk.StringVar(value="100.127.42.140")
        self.listen_port = tk.StringVar(value="2234")
        self.lat = tk.StringVar(value="50.28974")
        self.lon = tk.StringVar(value="34.75593")
        self.alt = tk.StringVar(value="150.0")
        self.state = tk.StringVar(value="Engaging")

        self.build_ui()

    def build_ui(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        settings = ttk.LabelFrame(frame, text="TATEP settings", padding=10)
        settings.pack(fill="x")

        ttk.Label(settings, text="Listen IP").grid(row=0, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.listen_ip, width=18).grid(row=0, column=1)

        ttk.Label(settings, text="Port").grid(row=0, column=2, sticky="w")
        ttk.Entry(settings, textvariable=self.listen_port, width=8).grid(row=0, column=3)

        ttk.Label(settings, text="Latitude").grid(row=1, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.lat, width=18).grid(row=1, column=1)

        ttk.Label(settings, text="Longitude").grid(row=1, column=2, sticky="w")
        ttk.Entry(settings, textvariable=self.lon, width=18).grid(row=1, column=3)

        ttk.Label(settings, text="Altitude").grid(row=2, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.alt, width=18).grid(row=2, column=1)

        ttk.Label(settings, text="State").grid(row=2, column=2, sticky="w")
        ttk.Combobox(
            settings,
            textvariable=self.state,
            values=["NotReady", "Ready", "Engaging"],
            width=15,
            state="readonly",
        ).grid(row=2, column=3)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=8)

        self.start_btn = ttk.Button(buttons, text="Start", command=self.start)
        self.start_btn.pack(side="left")

        self.stop_btn = ttk.Button(buttons, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=8)

        logs = ttk.Frame(frame)
        logs.pack(fill="both", expand=True)

        left = ttk.LabelFrame(logs, text="TATEP Log", padding=5)
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))

        right = ttk.LabelFrame(logs, text="UDP Dump", padding=5)
        right.pack(side="left", fill="both", expand=True, padx=(5, 0))

        self.tatep_log = scrolledtext.ScrolledText(left, width=55, height=22)
        self.tatep_log.pack(fill="both", expand=True)

        self.udp_log = scrolledtext.ScrolledText(right, width=55, height=22)
        self.udp_log.pack(fill="both", expand=True)

    def log_tatep(self, text):
        self.root.after(0, self._append, self.tatep_log, text)

    def log_udp(self, text):
        self.root.after(0, self._append, self.udp_log, text)

    def _append(self, widget, text):
        ts = time.strftime("%H:%M:%S")
        widget.insert("end", f"{ts}  {text}\n")
        widget.see("end")

    def state_value(self):
        mapping = {
            "NotReady": protocol_pb2.NotReady,
            "Ready": protocol_pb2.Ready,
            "Engaging": protocol_pb2.Engaging,
        }
        return mapping[self.state.get()]

    def build_status_packet(self):
        msg = protocol_pb2.ClientMessage(
            status=protocol_pb2.ClientStatus(
                state=self.state_value(),
                position=protocol_pb2.WGS84(
                    latitude_deg=float(self.lat.get()),
                    longitude_deg=float(self.lon.get()),
                    altitude_msl_m=float(self.alt.get()),
                ),
            )
        )

        buf = io.BytesIO()
        buf.write(HEADER)
        delimited_protobuf.write(buf, msg)
        return buf.getvalue()

    def parse_server_packet(self, data):
        if data[:4] != HEADER:
            self.log_tatep(f"Invalid header: {data!r}")
            return

        payload = io.BytesIO(data[4:])

        while msg := delimited_protobuf.read(payload, protocol_pb2.ServerMessage):
            if msg.HasField("ping"):
                self.log_tatep("RX: Ping")
            elif msg.HasField("target_estimate"):
                t = msg.target_estimate
                self.log_tatep(
                    f"RX: TargetEstimate id={t.target_id} "
                    f"lat={t.position.latitude_deg:.6f} "
                    f"lon={t.position.longitude_deg:.6f} "
                    f"alt={t.position.altitude_msl_m:.1f}"
                )
            elif msg.HasField("interceptor_estimate"):
                i = msg.interceptor_estimate
                self.log_tatep(
                    f"RX: InterceptorEstimate id={i.target_id} "
                    f"lat={i.position.latitude_deg:.6f} "
                    f"lon={i.position.longitude_deg:.6f} "
                    f"alt={i.position.altitude_msl_m:.1f}"
                )
            elif msg.HasField("target_raw"):
                self.log_tatep("RX: TargetRaw")
            elif msg.HasField("target_interceptor"):
                self.log_tatep("RX: RawInterceptor")
            else:
                self.log_tatep("RX: Unknown message")

    def start(self):
        try:
            ip = self.listen_ip.get().strip()
            port = int(self.listen_port.get())
            float(self.lat.get())
            float(self.lon.get())
            float(self.alt.get())
        except Exception as e:
            messagebox.showerror("Invalid settings", str(e))
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((ip, port))
            self.sock.settimeout(0.5)
        except Exception as e:
            messagebox.showerror("Socket error", str(e))
            return

        self.running = True
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        self.log_tatep(f"Listening on {ip}:{port}")
        self.log_tatep(
            f"Own position: {self.lat.get()}, {self.lon.get()}, alt={self.alt.get()}, state={self.state.get()}"
        )

    def stop(self):
        self.running = False

        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.log_tatep("Stopped")

    def loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break

            self.log_udp(f"IN  {addr[0]}:{addr[1]} -> local, bytes={len(data)}, hex={data.hex()}")
            self.parse_server_packet(data)

            packet = self.build_status_packet()

            try:
                self.sock.sendto(packet, addr)
                self.log_udp(f"OUT local -> {addr[0]}:{addr[1]}, bytes={len(packet)}, hex={packet.hex()}")
                self.log_tatep(f"TX: ClientStatus to {addr[0]}:{addr[1]}, bytes={len(packet)}")
            except OSError as e:
                self.log_tatep(f"Send error: {e}")


def main():
    root = tk.Tk()
    root.geometry("1100x600")
    TatepUi(root)
    root.mainloop()


if __name__ == "__main__":
    main()
