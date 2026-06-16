#!/bin/bash
set -e

# ============================================================
# I Ching Oracle VPS 一键安装脚本
# 包含：Hysteria2（代理）+ I Ching Oracle（应用部署）
# 适用系统：Ubuntu 22.04 / 24.04 / 26.04
# ============================================================

IP=$(curl -s ifconfig.me)
echo "========================================"
echo "VPS IP: $IP"
echo "开始安装..."
echo "========================================"

# -------- 1. 系统更新 + 基础工具 --------
apt update && apt upgrade -y
apt install -y curl wget git ufw python3 python3-pip python3-venv nginx certbot python3-certbot-nginx

# -------- 2. 防火墙 --------
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 4443/udp
ufw --force enable

# -------- 3. Hysteria2 安装 --------
bash <(curl -fsSL https://get.hy2.sh/)
if [ $? -ne 0 ]; then
    echo "Hysteria2 官方脚本失败，尝试备选..."
    # 备选：直接下载
    wget -O /tmp/hysteria2.tar.gz https://github.com/apernet/hysteria/releases/latest/download/hysteria-linux-amd64.tar.gz
    tar -xzf /tmp/hysteria2.tar.gz -C /usr/local/bin/
    chmod +x /usr/local/bin/hysteria
fi

# -------- 4. 生成 Hysteria2 配置 --------
# 生成随机密码
PASSWORD=$(openssl rand -base64 16 | tr -d '=')

mkdir -p /etc/hysteria
cat > /etc/hysteria/config.yaml << 'EOF'
listen: :4443
auth:
  type: password
  password: __PASSWORD__
tls:
  type: self
  cert: /etc/hysteria/server.crt
  key: /etc/hysteria/server.key
masquerade:
  type: proxy
  proxy:
    url: https://www.apple.com
    rewriteHost: true
bandwidth:
  up: 100 mbps
  down: 100 mbps
EOF

sed -i "s/__PASSWORD__/$PASSWORD/" /etc/hysteria/config.yaml

# 生成自签证书
openssl req -x509 -nodes -days 36500 -newkey rsa:2048 \
  -keyout /etc/hysteria/server.key \
  -out /etc/hysteria/server.crt \
  -subj "/CN=$IP"

# 启动 Hysteria2
systemctl enable hysteria-server
systemctl start hysteria-server

# -------- 5. 部署 I Ching Oracle --------
cd /root
git clone https://github.com/zhangyi-pd/iching-oracle.git
cd iching-oracle

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install uvicorn[standard]

# 创建系统服务
cat > /etc/systemd/system/iching.service << 'EOF'
[Unit]
Description=I Ching Oracle API
After=network.target

[Service]
User=root
WorkingDirectory=/root/iching-oracle
ExecStart=/root/iching-oracle/venv/bin/uvicorn api.divination:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
Environment=DEEPSEEK_API_KEY=
Environment=GUMROAD_SECRET=

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable iching
systemctl start iching

# -------- 6. Nginx 反向代理 --------
# 先用 IP 部署，等域名买好后随时切
cat > /etc/nginx/sites-available/iching << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /root/iching-oracle/;
    }
}
EOF

ln -sf /etc/nginx/sites-available/iching /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# -------- 7. 保存信息到文件 --------
cat > /root/vps_info.txt << 'EOF'
========================================
I Ching Oracle 部署完成！
========================================

你的 VPS 信息已保存，请勿泄露。

EOF

echo "========================================" >> /root/vps_info.txt
echo "Hysteria2 连接信息：" >> /root/vps_info.txt
echo "  服务器: $IP" >> /root/vps_info.txt
echo "  端口: 4443" >> /root/vps_info.txt
echo "  密码: $PASSWORD" >> /root/vps_info.txt
echo "  协议: hysteria2" >> /root/vps_info.txt
echo "" >> /root/vps_info.txt
echo "I Ching Oracle 访问地址：" >> /root/vps_info.txt
echo "  http://$IP" >> /root/vps_info.txt
echo "" >> /root/vps_info.txt
echo "DeepSeek API Key 配置：" >> /root/vps_info.txt
echo "  编辑 /etc/systemd/system/iching.service" >> /root/vps_info.txt
echo "  找到 Environment=DEEPSEEK_API_KEY= 填上你的 Key" >> /root/vps_info.txt
echo "  然后 systemctl daemon-reload && systemctl restart iching" >> /root/vps_info.txt
echo "========================================" >> /root/vps_info.txt

echo ""
echo "========================================"
echo "✅ 安装完成！"
echo "========================================"
echo ""
echo "Hysteria2 连接信息："
echo "  服务器: $IP"
echo "  端口: 4443"
echo "  密码: $PASSWORD"
echo "  协议: hysteria2"
echo "  客户端下载: https://github.com/apernet/hysteria/releases"
echo ""
echo "I Ching Oracle 访问地址："
echo "  http://$IP"
echo ""
echo "⚠️  注意：DeepSeek API Key 尚未配置"
echo "   执行：systemctl edit iching.service"
echo "   或在 /etc/systemd/system/iching.service 中设置 DEEPSEEK_API_KEY"
echo "   然后运行: systemctl daemon-reload && systemctl restart iching"
echo "========================================"
echo "信息已保存到 /root/vps_info.txt"