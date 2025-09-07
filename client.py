import asyncio
import json
import time
import serial
import websockets

SERVER_ADDRESS = 'raspberrypi'
SERVER_PORT = 50051
SIMULATOR_PORT = '/tmp/glove_write'
BAUD_RATE = 9600

async def send_simulator_data(websocket):
    try:
        ser = serial.Serial(SIMULATOR_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to simulator at {SIMULATOR_PORT}")
    except Exception as e:
        print(f"Serial error: {e}")
        return

    message_count = 0
    start_time = time.time()

    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            if not line:
                await asyncio.sleep(0.01)
                continue

            parts = [p.strip() for p in line.split(',')]
            if len(parts) != 5:
                continue

            finger_values = list(map(int, parts))
            message_count += 1
            elapsed = time.time() - start_time
            rate = message_count / elapsed if elapsed > 0 else 0.0

            if message_count % 50 == 0:
                print(f"CLIENT #{message_count:04d} | {rate:.1f} msg/s | Fingers: {finger_values}")

            payload = {
                "finger_values": finger_values,
                "timestamp_ms": int(time.time() * 1000),
            }
            await websocket.send(json.dumps(payload))

        except Exception as e:
            print(f"Error: {e}")
            break

    ser.close()

async def listen_responses(websocket):
    try:
        async for msg in websocket:
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                print("\nServer replied (non-JSON):", msg)
                continue
            print(f"\nServer ACK: {data}")
    except websockets.exceptions.ConnectionClosed:
        pass

async def main():
    print(f"Client starting...")
    print(f"Server: {SERVER_ADDRESS}:{SERVER_PORT}")
    uri = f"ws://{SERVER_ADDRESS}:{SERVER_PORT}"

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to server")
            sender = asyncio.create_task(send_simulator_data(websocket))
            listener = asyncio.create_task(listen_responses(websocket))
            await sender
            listener.cancel()
            await listener
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(main())