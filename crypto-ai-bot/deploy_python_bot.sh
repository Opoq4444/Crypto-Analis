#!/bin/bash
# ╔══════════════════════════════════════════════════════╗
# ║  HedgeΣSignal Python Bot — Деплой на VPS            ║
# ╚══════════════════════════════════════════════════════╝
set -e
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}   HedgeΣSignal Python — Crypto Fund Bot  ${NC}"
echo -e "${CYAN}══════════════════════════════════════════${NC}"

# 1. Python 3.11+
echo -e "\n${CYAN}[1/6] Устанавливаю Python и зависимости...${NC}"
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git curl 2>/dev/null | tail -3
echo -e "  Python: $(python3 --version)"

# 2. Директория
echo -e "\n${CYAN}[2/6] Создаю директорию бота...${NC}"
BOT_DIR="/opt/hedgesignal-python"
mkdir -p $BOT_DIR
cp -r crypto-ai-bot/. $BOT_DIR/ 2>/dev/null || cp -r . $BOT_DIR/ 2>/dev/null || true

# 3. Виртуальная среда
echo -e "\n${CYAN}[3/6] Создаю виртуальную среду Python...${NC}"
cd $BOT_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "  Зависимости установлены ✅"

# 4. .env файл
echo -e "\n${CYAN}[4/6] Настройка конфигурации...${NC}"
if [ ! -f "$BOT_DIR/.env" ]; then
    echo -e "${YELLOW}  ⚠️ Создаю .env файл — ЗАПОЛНИТЕ API ключи!${NC}"
    cat > $BOT_DIR/.env << 'ENV'
TELEGRAM_BOT_TOKEN=8672583953:AAFpMmJXruX917bygJqKJtVqa6bqNWsHBiA
TELEGRAM_CHAT_ID=
GEMINI_API_KEY=
ETHERSCAN_API_KEY=
COINGLASS_API_KEY=
SYMBOLS=BTCUSDT,ETHUSDT,XRPUSDT,SOLUSDT
SIGNAL_INTERVAL=60
MIN_CONFIDENCE=0.65
RISK_PER_TRADE=1.0
TIMEFRAME=1h
LOOKBACK_CANDLES=200
DATABASE_URL=sqlite+aiosqlite:///data/signals.db
LOG_LEVEL=INFO
LOG_FILE=logs/hedgesignal.log
ENV
    echo -e "  .env создан: ${YELLOW}$BOT_DIR/.env${NC}"
else
    echo -e "  .env уже существует ✅"
fi

# 5. Systemd сервис
echo -e "\n${CYAN}[5/6] Настраиваю автозапуск...${NC}"
cat > /etc/systemd/system/hedgesignal-python.service << EOF
[Unit]
Description=HedgeSigSignal Python Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python main.py
Restart=always
RestartSec=15
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hedgesig-python
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hedgesignal-python
systemctl restart hedgesignal-python
sleep 4

# 6. Статус
echo -e "\n${CYAN}[6/6] Проверяю статус...${NC}"
if systemctl is-active --quiet hedgesignal-python; then
    echo -e "\n${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅  HedgeΣSignal Python ЗАПУЩЕН!        ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${CYAN}Команды управления:${NC}"
    echo -e "  Статус: ${GREEN}systemctl status hedgesignal-python${NC}"
    echo -e "  Логи:   ${GREEN}journalctl -u hedgesignal-python -f${NC}"
    echo -e "  Стоп:   ${YELLOW}systemctl stop hedgesignal-python${NC}"
    echo ""
    echo -e "  ${YELLOW}⚠️ Для полного функционала заполните API ключи:${NC}"
    echo -e "  ${GREEN}nano $BOT_DIR/.env${NC}"
    echo ""
    echo -e "  После изменения .env:"
    echo -e "  ${GREEN}systemctl restart hedgesignal-python${NC}"
    echo ""
    echo -e "  Telegram: ${GREEN}@ProfitMachineBot${NC} → /start"
else
    echo -e "\n${RED}❌ Ошибка запуска! Логи:${NC}"
    journalctl -u hedgesignal-python --no-pager -n 30
fi
