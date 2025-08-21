import asyncio
import json
import time
import sys
import contextlib
import websockets

SERVER_ADDRESS = 'raspberrypi'  # or IP/hostname
SERVER_PORT = 50051

# --- Async, non-blocking line reader (does NOT block event loop) ---
async def readline():
    # Use a background thread to avoid blocking asyncio loop
    line = await asyncio.to_thread(sys.stdin.readline)
    if not line:
        # EOF (Ctrl+D)
        return None
    return line.rstrip("\n")

async def send_hand_data(websocket):
    """
    Read user input lines asynchronously and send to server.
    Type 'q' to quit.
    """
    message_count = 0
    start_time = time.time()

    while True:
        try:
            print("Enter 5 comma-separated finger values (0-1023), or 'q' to quit: ", end="", flush=True)
            line = await readline()
            if line is None:
                # stdin closed
                break

            line = line.strip()
            if line.lower() == 'q':
                break

            parts = [p.strip() for p in line.split(',')]
            if len(parts) != 5:
                print("\nInvalid input. Please enter 5 values.")
                continue

            finger_values = list(map(int, parts))
            if not all(0 <= v <= 1023 for v in finger_values):
                print("\nAll values must be between 0 and 1023.")
                continue

            message_count += 1
            elapsed = time.time() - start_time
            rate = message_count / elapsed if elapsed > 0 else 0.0

            if message_count % 50 == 0:
                print(f"\nCLIENT #{message_count:04d} | {rate:.1f} msg/s | Fingers: {finger_values}")

            payload = {
                "finger_values": finger_values,
                "timestamp_ms": int(time.time() * 1000),
            }
            await websocket.send(json.dumps(payload))

        except ValueError:
            print("\nInvalid input. Please enter integers.")
        except (EOFError, KeyboardInterrupt):
            break

async def listen_responses(websocket):
    """
    Concurrently read server acknowledgments (keeps WS pump alive too).
    """
    try:
        async for msg in websocket:
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                print("\nServer replied (non-JSON):", msg)
                continue

            print(f"\nServer ACK: {data}")
    except websockets.exceptions.ConnectionClosed:
        # normal or error closure
        pass

async def main():
    print(f"Client starting...")
    print(f"Server: {SERVER_ADDRESS}:{SERVER_PORT}")
    uri = f"ws://{SERVER_ADDRESS}:{SERVER_PORT}"

    # Reasonable keepalive; pings are handled by the library as long as the loop isn't blocked
    try:
        async with websockets.connect(
            uri,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
            max_queue=None,   # don't artificially backpressure
        ) as websocket:
            print("Connected to server")

            sender = asyncio.create_task(send_hand_data(websocket))
            listener = asyncio.create_task(listen_responses(websocket))

            await sender
            # After user quits sending, cancel listener and close
            listener.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await listener

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(main())
