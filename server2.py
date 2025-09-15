import asyncio
import json
import time
import serial
import websockets

ROBOT_SERIAL_PORT = '/dev/ttyUSB0'
ROBOT_BAUD_RATE = 9600
WEBSOCKET_PORT = 50051

class HandController:
    def __init__(self):
        self.message_count = 0
        self.total_e2e_latency = 0.0
        self.start_time = None
        self.robot_serial = self._initialize_serial()

    def _initialize_serial(self):
        try:
            ser = serial.Serial(ROBOT_SERIAL_PORT, ROBOT_BAUD_RATE, timeout=0)
            print(f"Serial opened: {ROBOT_SERIAL_PORT} @ {ROBOT_BAUD_RATE}")
            return ser
        except Exception as e:
            print(f"Serial error: {e}")
            return None

    async def handle_client(self, websocket):
        print("Client connected.")
        self.start_time = time.time()
        try:
            async for message in websocket:
                # Parse message
                try:
                    data = json.loads(message)
                    print(f"Received: {data}")  # Debug log
                except Exception as e:
                    print(f"JSON parse error: {e}")
                    data = {"raw": message}

                # Process timestamp and count message
                timestamp_ms = data.get("timestamp_ms")
                if isinstance(timestamp_ms, (int, float)):
                    now_ms = int(time.time() * 1000)
                    self.message_count += 1
                    self.total_e2e_latency += max(0, now_ms - timestamp_ms)

                # Process finger values if present
                finger_values = data.get("finger_values")
                if isinstance(finger_values, list) and len(finger_values) == 5:
                    if self.robot_serial:
                        try:
                            line = ",".join(map(str, finger_values)) + "\n"
                            self.robot_serial.write(line.encode("utf-8"))
                            self.robot_serial.flush()
                        except Exception as e:
                            print(f"Serial write error: {e}")

                # Send acknowledgment
                ack = {
                    "ok": True,
                    "seq": self.message_count,
                    "ts_ms": int(time.time() * 1000)
                }
                await websocket.send(json.dumps(ack))

                # Give event loop a chance to process other tasks
                await asyncio.sleep(0)

        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed with error: {e}")
        finally:
            dur = time.time() - (self.start_time or time.time())
            avg = (self.total_e2e_latency / self.message_count) if self.message_count else 0.0
            print(f"Total: {self.message_count} msgs | Duration: {dur:.2f}s | Avg E2E: {avg:.2f}ms")
            print("Client disconnected.")

async def main():
    ctrl = HandController()
    server = await websockets.serve(
        ctrl.handle_client,
        host="0.0.0.0",
        port=WEBSOCKET_PORT,
        ping_interval=30,
        ping_timeout=30
    )
    print(f"Server started - Port: {WEBSOCKET_PORT}")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
