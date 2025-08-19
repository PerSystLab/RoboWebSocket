import asyncio
import json
import time
import serial
import websockets

GLOVE_SERIAL_PORT = '/tmp/glove_read'
GLOVE_BAUD_RATE = 115200
SERVER_ADDRESS = 'local,host'
SERVER_PORT = 50051


def parse_hand_data(line):
    try:
        parts = line.split(',')
        if len(parts) == 5:
            finger_values = list(map(int, parts))
            return finger_values
    except (ValueError, IndexError):
        pass
    return None


async def send_hand_data(websocket, serial_port):
    message_count = 0
    start_time = time.time()

    while True:
        try:
            line = serial_port.readline().decode('utf-8').strip()
            if not line:
                continue

            finger_values = parse_hand_data(line)
            if finger_values:
                message_count += 1

                # Rate hesapla
                elapsed = time.time() - start_time
                rate = message_count / elapsed if elapsed > 0 else 0

                if message_count % 50 == 0:
                    print(f"CLIENT #{message_count:04d} | {rate:.1f} msg/s | Parmaklar: {finger_values}")

                # Timestamp ekle
                timestamp_ms = int(time.time() * 1000)

                # Create JSON data
                hand_data = {
                    "finger_values": finger_values,
                    "timestamp_ms": timestamp_ms
                }

                # Send as JSON
                await websocket.send(json.dumps(hand_data))
            else:
                print(f"Geçersiz veri: {line}")

        except (UnicodeDecodeError, ValueError) as e:
            print(f"Parse hatası: {e}")
            continue
        except serial.SerialException as e:
            print(f"Serial hatası: {e}")
            break


async def main():
    print(f"Client başlatılıyor...")
    print(f"Eldiven portu: {GLOVE_SERIAL_PORT}")
    print(f"Server: {SERVER_ADDRESS}:{SERVER_PORT}")
    print("Server hazır olduğunda Enter'a basın:")
    input()

    try:
        glove_serial = serial.Serial(GLOVE_SERIAL_PORT, GLOVE_BAUD_RATE)
        print(f"Eldiven bağlandı: {GLOVE_SERIAL_PORT}")
    except serial.SerialException as e:
        print(f"Eldiven bağlantı hatası: {e}")
        return

    try:
        uri = f"ws://{SERVER_ADDRESS}:{SERVER_PORT}"
        start_time = time.time()

        async with websockets.connect(uri) as websocket:
            print("Server'a bağlandı")
            await send_hand_data(websocket, glove_serial)

            # Receive acknowledgment
            response = await websocket.recv()
            end_time = time.time()

            print(f"Tamamlandı. Süre: {end_time - start_time:.2f}s")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"WebSocket bağlantısı kapandı: {e}")
    except Exception as e:
        print(f"Hata: {e}")
    finally:
        if glove_serial.is_open:
            glove_serial.close()
            print("Serial port kapatıldı")


if __name__ == '__main__':
    asyncio.run(main())