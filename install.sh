#!/bin/bash

echo "----------------------------------------------------"
echo "🤖 Встановлення Stable Node Monitor Bot"
echo "   by SashaDrop"
echo "----------------------------------------------------"
sleep 1

# 1. Встановлення Python та pip
echo "📦 Встановлення бібліотек..."
sudo apt update
sudo apt install python3-pip -y
pip3 install pyTelegramBotAPI requests

# 2. Створення папки
mkdir -p $HOME/node_bot
cd $HOME/node_bot

# 3. Завантаження коду бота
wget -O bot.py https://raw.githubusercontent.com/Sashabnk/Stable-node-monitor/main/bot.py

if [ ! -f bot.py ]; then
    echo "❌ Помилка: файл bot.py не знайдено! (Залийте його на сервер)"
    exit 1
fi

# 4. Налаштування
echo ""
echo "📝 Налаштування:"
read -p "Введи API Token від @BotFather: " TOKEN

echo "{\"token\": \"$TOKEN\", \"owner_id\": 0}" > config.json

# 5. Створення сервісу Systemd
SERVICE_FILE=/etc/systemd/system/nodebot.service

sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Stable Node Monitor Bot
After=network.target

[Service]
User=$USER
WorkingDirectory=$HOME/node_bot
ExecStart=/usr/bin/python3 $HOME/node_bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 6. Запуск
sudo systemctl daemon-reload
sudo systemctl enable nodebot
sudo systemctl start nodebot

echo ""
echo "✅ Бот успішно запущений!"
echo "Напиши /start своєму боту в Telegram."