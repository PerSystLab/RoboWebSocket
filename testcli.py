#!/usr/bin/env python3

import asyncio
import json
import time
import websockets
import sys

# Use 'localhost' for local testing, 'raspberrypi' for remote connection
SERVER_ADDRESS = 'raspberrypi'
SERVER_PORT = 50051

class HandSimulatorClient:
    def __init__(self):
        self.is_running = False
        self.finger_values = [1500, 1500, 1500, 1500, 1500]
        self.message_count = 0
        self.ack_count = 0
        self.command_queue = asyncio.Queue()
        self.connection_retry_count = 0
        self.max_retries = 5
        self.retry_delay = 3  # seconds

    def set_finger(self, finger_idx, state):
        if state == "kapalı":
            self.finger_values[finger_idx] = 500
        elif state == "açık":
            self.finger_values[finger_idx] = 2500
        else:
            self.finger_values[finger_idx] = 1500

    def set_all_fingers(self, state):
        for i in range(5):
            self.set_finger(i, state)

    def show_status(self):
        print(f"Parmaklar: {self.finger_values}")
        print(f"Gönderilen: {self.message_count} mesaj, ACK: {self.ack_count}")

    def process_command(self, command):
        command = command.strip().lower()

        if command == 'q':
            self.is_running = False
            print("Çıkış...")
            return True  # Signal to exit
        elif command == 's':
            self.show_status()
        elif command == 'r':
            self.set_all_fingers("orta")
            print("Reset")
        elif command == 'a':
            self.set_all_fingers("açık")
            print("Açık")
        elif command == 'c':
            self.set_all_fingers("kapalı")
            print("Kapalı")
        elif command in '12345':
            finger_idx = int(command) - 1
            current = self.finger_values[finger_idx]
            if current == 500:
                new_val = 1500
            elif current == 1500:
                new_val = 2500
            else:
                new_val = 500
            self.finger_values[finger_idx] = new_val
            print(f"Parmak {command}: {new_val}")
        # Direct comma-separated input
        elif ',' in command:
            try:
                values = [int(v.strip()) for v in command.split(',')]
                if len(values) == 5:
                    # Validate values are in acceptable range
                    for i, val in enumerate(values):
                        if 500 <= val <= 2500:
                            self.finger_values[i] = val
                        else:
                            print(
                                f"Warning: Value for finger {i + 1} out of range (500-2500), using nearest valid value")
                            self.finger_values[i] = max(500, min(2500, val))
                    print(f"Parmaklar: {self.finger_values}")
                else:
                    print("Error: Need exactly 5 values (one for each finger)")
            except ValueError:
                print("Error: Invalid values, use numbers between 500-2500")
        return False  # Continue running

    async def data_sender_task(self):
        uri = f"ws://{SERVER_ADDRESS}:{SERVER_PORT}"
        start_time = time.time()

        while self.is_running and self.connection_retry_count < self.max_retries:
            try:
                print(f"Connecting to server: {SERVER_ADDRESS}:{SERVER_PORT}...")
                async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as websocket:
                    print(f"Connected to server: {SERVER_ADDRESS}:{SERVER_PORT}")
                    self.connection_retry_count = 0  # Reset retry count on successful connection

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

                            # Check for user commands
                            try:
                                cmd = await asyncio.wait_for(self.command_queue.get(), timeout=0.01)
                                should_exit = self.process_command(cmd)
                                if should_exit:
                                    break
                            except asyncio.TimeoutError:
                                pass  # No command available

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
                        print(f"Reconnection attempt {self.connection_retry_count}/{self.max_retries} in {self.retry_delay} seconds...")
                        await asyncio.sleep(self.retry_delay)
                    else:
                        print("Max reconnection attempts reached. Exiting.")
                        break
            except Exception as e:
                print(f"Connection error: {e}")
                self.connection_retry_count += 1
                if self.connection_retry_count < self.max_retries:
                    print(f"Reconnection attempt {self.connection_retry_count}/{self.max_retries} in {self.retry_delay} seconds...")
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
                    # Don't print any ACK messages
                except json.JSONDecodeError:
                    print("\nServer replied (non-JSON):", msg)
        except websockets.exceptions.ConnectionClosed:
            print("Server connection closed")

    async def command_input_task(self):
        print("Komutlar: 1-5(parmak), a(açık), c(kapalı), r(reset), s(durum), q(çıkış)")

        while self.is_running:
            try:
                command = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("Komut> ")
                )
                await self.command_queue.put(command)
            except (EOFError, KeyboardInterrupt):
                self.is_running = False
                break

    async def run(self):
        print("El Simülatörü ve İstemci başlıyor...")
        self.is_running = True

        # Start tasks
        input_task = asyncio.create_task(self.command_input_task())
        sender_task = asyncio.create_task(self.data_sender_task())

        # Wait for tasks to complete
        await asyncio.gather(input_task, sender_task)

        print("Uygulama kapandı")

async def main():
    simulator_client = HandSimulatorClient()
    await simulator_client.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
        sys.exit(0)