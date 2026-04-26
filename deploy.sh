#!/bin/bash
# ╔══════════════════════════════════════════╗
# ║  Crypto Intel AI — установка на VPS     ║
# ║  Запускать: bash deploy.sh               ║
# ╚══════════════════════════════════════════╝
set -e
GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${CYAN}🚀 Разворачиваю Crypto Intel AI...${NC}"

# 1. Обновление и установка nginx
echo -e "${CYAN}[1/4] Устанавливаю nginx...${NC}"
apt-get update -qq
apt-get install -y nginx curl 2>/dev/null | grep -E "installed|upgraded" || true

# 2. Копируем приложение
echo -e "${CYAN}[2/4] Копирую приложение...${NC}"
mkdir -p /var/www/cryptointel
cp GlobalInsightEngine/app/src/main/assets/index.html /var/www/cryptointel/index.html
chmod -R 755 /var/www/cryptointel

# 3. Настраиваем nginx
echo -e "${CYAN}[3/4] Настраиваю nginx...${NC}"
cat > /etc/nginx/sites-available/cryptointel << 'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /var/www/cryptointel;
    index index.html;
    charset utf-8;

    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header X-Frame-Options "SAMEORIGIN";
        add_header X-Content-Type-Options "nosniff";
    }

    gzip on;
    gzip_types text/html text/css application/javascript text/plain;
    gzip_min_length 1000;
}
NGINX

ln -sf /etc/nginx/sites-available/cryptointel /etc/nginx/sites-enabled/cryptointel
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl restart nginx

# 4. Готово!
IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}╔════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Crypto Intel AI запущен!        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════╝${NC}"
echo -e "${CYAN}Откройте в браузере:${NC}"
echo -e "${GREEN}  http://${IP}${NC}"
echo ""
echo -e "${CYAN}Для запуска на телефоне:${NC}"
echo -e "  1. Откройте Chrome → введите: ${GREEN}http://${IP}${NC}"
echo -e "  2. Меню ⋮ → 'Добавить на главный экран'"
echo -e "  3. Готово — работает как приложение!"
