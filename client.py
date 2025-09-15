#!/usr/bin/env python3

import asyncio
import json
import time
import websockets
import sys
import serial

# Configuration
SERVER_ADDRESS = 'raspberrypi'
SERVER_PORT = 50051
SIMULATOR_PORT = 'COM3'
BAUD_RATE = 9600


class SerialHandClient:
    def __init__(self):
        self.is_running = False
        self.finger_values = [1500, 1500, 1500, 1500, 1500]
        self.message_count = 0
        self.ack_count = 0
        self.connection_retry_count = 0
        self.max_retries = 5
        self.retry_delay = 3
        self.serial_port = None

    async def initialize_serial(self):
        try:
            self.serial_port = serial.Serial(SIMULATOR_PORT, BAUD_RATE, timeout=1)
            print(f"Connected to simulator at {SIMULATOR_PORT}")
            return True
        except Exception as e:
            print(f"Serial error: {e}")
            return False

    async def serial_reader_task(self):
        if not self.serial_port:
            print("Serial port not initialized")
            return

        while self.is_running:
            try:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line:
                        print(f"Received raw data: {line}")

                        # Skip metadata lines
                        if line.startswith("max_list:") or line.startswith("min_list:"):
                            print("Skipping metadata line")
                            continue

                        parts = [p.strip() for p in line.split()]
                        if len(parts) == 5:
                            try:
                                new_values = list(map(int, parts))
                                # Validate values
                                for i, val in enumerate(new_values):
                                    if 500 <= val <= 2500:
                                        self.finger_values[i] = val
                                    else:
                                        print(f"Warning: Value for finger {i + 1} out of range")

                                print(f"Processed values: {self.finger_values}")
                            except ValueError:
                                print(f"Invalid data: {line}")
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"Serial read error: {e}")
                await asyncio.sleep(1)

    async def data_sender_task(self):
        uri = f"ws://{SERVER_ADDRESS}:{SERVER_PORT}"
        start_time = time.time()

        while self.is_running and self.connection_retry_count < self.max_retries:
            try:
                print(f"Connecting to server: {SERVER_ADDRESS}:{SERVER_PORT}...")
                async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as websocket:
                    print(f"Connected to server: {SERVER_ADDRESS}:{SERVER_PORT}")
                    self.connection_retry_count = 0  # Reset retry count

                    # Start the response listener
                    listener_task = asyncio.create_task(self.listen_responses(websocket))

                    while self.is_running:
                        try:
                            payload = {
                                "finger_values": self.finger_values,
                                "timestamp_ms": int(time.time() * 1000),
                            }
                            json_data = json.dumps(payload)
                            await websocket.send(json_data)
                            self.message_count += 1

                            # Only print status every 500 messages
                            if self.message_count % 500 == 0:
                                elapsed = time.time() - start_time
                                rate = self.message_count / elapsed if elapsed > 0 else 0.0
                                print(f"Status: {self.message_count} msgs | {rate:.1f} msg/s")

                            await asyncio.sleep(0.02)  # 50 Hz

                        except Exception as e:
                            print(f"Error in data sender: {e}")
                            break

                    listener_task.cancel()
                    try:
                        await listener_task
                    except asyncio.CancelledError:
                        pass

            except websockets.exceptions.ConnectionClosed as e:
                print(f"Connection closed: {e}")
                if self.is_running:
                    self.connection_retry_count += 1
                    if self.connection_retry_count < self.max_retries:
                        print(
                            f"Reconnection attempt {self.connection_retry_count}/{self.max_retries} in {self.retry_delay} seconds...")
                        await asyncio.sleep(self.retry_delay)
                    else:
                        print("Max reconnection attempts reached. Exiting.")
                        break
            except Exception as e:
                print(f"Connection error: {e}")
                self.connection_retry_count += 1
                if self.connection_retry_count < self.max_retries:
                    print(
                        f"Reconnection attempt {self.connection_retry_count}/{self.max_retries} in {self.retry_delay} seconds...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    print("Max reconnection attempts reached. Exiting.")
                    break

        self.is_running = False

    async def listen_responses(self, websocket):
        try:
            async for msg in websocket:
                try:
                    data = json.loads(msg)
                    self.ack_count += 1
                except json.JSONDecodeError:
                    print("\nServer replied (non-JSON):", msg)
        except websockets.exceptions.ConnectionClosed:
            print("Server connection closed")

    async def run(self):
        print(f"Serial Hand Client starting...")
        self.is_running = True

        # Initialize serial port
        if not await self.initialize_serial():
            print("Failed to initialize serial port. Exiting.")
            return

        # Start tasks
        serial_task = asyncio.create_task(self.serial_reader_task())
        sender_task = asyncio.create_task(self.data_sender_task())

        try:
            # Wait for tasks to complete
            await asyncio.gather(serial_task, sender_task)
        except asyncio.CancelledError:
            pass
        finally:
            # Clean up
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                print("Serial port closed")

        print("Application closed")


async def main():
    client = SerialHandClient()

    # Windows-compatible approach - no signal handlers
    await client.run()


async def shutdown(client):
    print("\nShutting down...")
    client.is_running = False


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
        sys.exit(0)