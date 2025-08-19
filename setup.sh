#!/bin/bash
echo "Sistem güncelleniyor..."
sudo apt update
sudo apt upgrade -y

echo "Python ve pip kontrol ediliyor..."
sudo apt install -y python3 python3-pip python3-venv

echo "Sistem kütüphaneleri kuruluyor..."
sudo apt install -y build-essential python3-dev

echo "Virtual environment oluşturuluyor..."
python3 -m venv venv
source venv/bin/activate

echo "Python kütüphaneleri kuruluyor..."
pip install pyserial websockets

echo "USB port izinleri ayarlanıyor..."
sudo usermod -a -G dialout $USER
sudo usermod -a -G tty $USER