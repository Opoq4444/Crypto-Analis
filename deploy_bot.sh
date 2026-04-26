#!/bin/bash
# ╔══════════════════════════════════════════════╗
# ║  HedgeΣSignal — Telegram Bot Deploy         ║
# ║  Запускать: bash deploy_bot.sh               ║
# ╚══════════════════════════════════════════════╝
set -e
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${CYAN}🤖 Разворачиваю Telegram бота...${NC}"

# 1. Node.js
echo -e "${CYAN}[1/5] Проверяю Node.js...${NC}"
if ! command -v node &>/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
echo -e "  Node: $(node -v)"

# 2. Копируем бота
echo -e "${CYAN}[2/5] Устанавливаю бота...${NC}"
mkdir -p /opt/hedgesignal-bot
cp tg_bot/bot.js     /opt/hedgesignal-bot/
cp tg_bot/package.json /opt/hedgesignal-bot/

# 3. Systemd сервис
echo -e "${CYAN}[3/5] Настраиваю автозапуск...${NC}"
cp tg_bot/hedgesigbot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable hedgesigbot

# 4. Запуск
echo -e "${CYAN}[4/5] Запускаю бота...${NC}"
systemctl restart hedgesigbot
sleep 3

# 5. Статус
echo -e "${CYAN}[5/5] Проверяю статус...${NC}"
if systemctl is-active --quiet hedgesigbot; then
  echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  ✅  Telegram бот ЗАПУЩЕН!               ║${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  ${CYAN}Бот работает как системный сервис${NC}"
  echo -e "  ${CYAN}Перезапускается автоматически при сбоях${NC}"
  echo ""
  echo -e "  Статус: ${GREEN}systemctl status hedgesigbot${NC}"
  echo -e "  Логи:   ${GREEN}journalctl -u hedgesigbot -f${NC}"
  echo -e "  Стоп:   ${YELLOW}systemctl stop hedgesigbot${NC}"
  echo ""
  echo -e "  ${GREEN}Найдите бота в Telegram и нажмите /start${NC}"
else
  echo -e "  ❌ Ошибка запуска. Логи:"
  journalctl -u hedgesigbot --no-pager -n 20
fi
