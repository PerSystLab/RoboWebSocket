#!/usr/bin/env python3

import time
import threading
import serial

class SimpleHandSimulator:
    def __init__(self):
        self.serial_port = None
        self.is_running = False
        self.finger_values = [1500, 1500, 1500, 1500, 1500]
        self.message_count = 0
        
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
        print(f"Gönderilen: {self.message_count} mesaj")
    
    def process_command(self, command):
        command = command.strip().lower()
        
        if command == 'q':
            self.is_running = False
            print("Çıkış...")
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
    
    def data_sender_thread(self):
        while self.is_running:
            if self.serial_port:
                try:
                    data = ",".join(map(str, self.finger_values)) + "\n"
                    self.serial_port.write(data.encode('utf-8'))
                    self.serial_port.flush()
                    self.message_count += 1
                except Exception as e:
                    print(f"Hata: {e}")
                    break
            time.sleep(0.02)  # 50 Hz
    
    def run(self):
        print("Simülatör başlıyor...")
        
        try:
            self.serial_port = serial.Serial('COM4', 9600, timeout=1)
            print("Port açıldı")
        except Exception as e:
            print(f"Port hatası: {e}")
            return
        
        self.is_running = True
        
        # Veri göndericiyi başlat
        thread = threading.Thread(target=self.data_sender_thread, daemon=True)
        thread.start()
        
        print("Komutlar: 1-5(parmak), a(açık), c(kapalı), r(reset), s(durum), q(çıkış)")
        
        # Komut döngüsü
        while self.is_running:
            try:
                command = input("Komut> ")
                self.process_command(command)
            except (EOFError, KeyboardInterrupt):
                break
        
        self.is_running = False
        if self.serial_port:
            self.serial_port.close()
        print("Simülatör kapandı")

if __name__ == "__main__":
    simulator = SimpleHandSimulator()
    simulator.run()