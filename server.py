import asyncio
import json
import time
import serial
import websockets

ROBOT_SERIAL_PORT = '/dev/ttyUSB0'  # adjust if needed (e.g., 'COM3' on Windows)
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
            ser = serial.Serial(ROBOT_SERIAL_PORT, ROBOT_BAUD_RATE, timeout=1)
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
                # Parse one frame
                try:
                    hand_data = json.loads(message)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"ok": False, "error": "invalid_json"}))
                    continue

                # Process (serial write, metrics)
                await self._process_data(hand_data)

                # ✅ Send ACK **for every message**
                ack = {
                    "ok": True,
                    "seq": self.message_count,
                    "ts_ms": int(time.time() * 1000),
                }
                await websocket.send(json.dumps(ack))

        except websockets.exceptions.ConnectionClosedOK:
            print("Client closed connection (OK).")
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed with error: {e}")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            if self.message_count > 0 and self.start_time is not None:
                total_time = time.time() - self.start_time
                avg_e2e_latency = self.total_e2e_latency / self.message_count
                throughput = self.message_count / total_time if total_time > 0 else 0.0
                print(
                    f"Total: {self.message_count} msgs | Duration: {total_time:.2f}s | "
                    f"Avg E2E: {avg_e2e_latency:.2f}ms | Throughput: {throughput:.1f} msg/s"
                )

    async def _process_data(self, hand_data):
        """
        Convert finger_values -> serial line for the robot, track E2E latency.
        """
        self.message_count += 1

        # Metrics
        now_ms = int(time.time() * 1000)
        sent_ts = int(hand_data.get("timestamp_ms", now_ms))
        e2e = max(0, now_ms - sent_ts)
        self.total_e2e_latency += e2e

        # Extract servo targets
        servo_values = hand_data.get("finger_values")
        if not isinstance(servo_values, list) or len(servo_values) != 5:
            # ignore malformed frames
            return

        # Write to robot over serial
        if self.robot_serial and self.robot_serial.is_open:
            line = ",".join(map(str, servo_values)) + "\n"
            try:
                self.robot_serial.write(line.encode("utf-8"))
                self.robot_serial.flush()
            except Exception as e:
                # Don't crash the server if serial hiccups
                print(f"Serial write error: {e}")

        # Throttle a little if you need to avoid overruns on Arduino
        await asyncio.sleep(0.01)  # 10ms


async def serve():
    controller = HandController()
    async with websockets.serve(controller.handle_client, "0.0.0.0", WEBSOCKET_PORT, ping_interval=20, ping_timeout=20):
        print(f"Server started - Port: {WEBSOCKET_PORT}")
        print("Waiting for clients...")
        try:
            await asyncio.Future()  # run forever
        except asyncio.CancelledError:
            pass
        finally:
            if controller.robot_serial and controller.robot_serial.is_open:
                controller.robot_serial.close()


if __name__ == '__main__':
    asyncio.run(serve())
