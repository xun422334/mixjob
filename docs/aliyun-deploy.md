# 阿里云轻量应用服务器部署指南

## 一、购买服务器

1. 打开 [阿里云轻量应用服务器](https://swas.console.aliyun.com/)
2. 选择配置：
   - **地域**：选离你最近的（杭州/上海/北京）
   - **镜像**：Ubuntu 24.04
   - **套餐**：2核2G（~68元/月），1G 内存跑 Firefox 可能不够
3. 购买后在控制台设置 **root 密码**
4. 防火墙规则开放端口：**22**、**80**、**443**、**8000**

## 二、登录服务器 & 安装 Docker

```bash
ssh root@<服务器IP>

# 安装 Docker
curl -fsSL https://get.docker.com | bash
```

## 三、拉取项目

```bash
git clone https://github.com/xun422334/mixjob.git /opt/mixjob
cd /opt/mixjob
```

项目已有 Dockerfile，无需修改。

## 四、启动服务

```bash
# 构建并启动
docker build -t mixjob .
docker run -d \
  --name mixjob \
  --restart always \
  -p 8000:8000 \
  -v /opt/mixjob/data:/app/data \
  mixjob
```

验证：

```bash
curl http://localhost:8000/api/health
# 返回 {"status":"ok"}
```

## 五、更新前端 API 地址

修改 [frontend/src/api/index.ts](../frontend/src/api/index.ts) 第1行，将 Render 地址改为阿里云地址：

```typescript
const BASE = import.meta.env.DEV ? '/api' : 'http://<服务器IP>:8000/api'
```

如果在后面配置了域名，则改为：

```typescript
const BASE = import.meta.env.DEV ? '/api' : 'https://api.mixjob.cn/api'
```

修改后重新部署前端到 Vercel（push 到 GitHub 即可自动部署）。

## 六、配置域名 + HTTPS（推荐）

在阿里云 DNS 添加 A 记录：`api.mixjob.cn` → 服务器 IP

然后在服务器上配置 Nginx + 免费 HTTPS：

```bash
apt install -y nginx certbot python3-certbot-nginx

# Nginx 反向代理配置
cat > /etc/nginx/sites-available/mixjob << 'NGINX'
server {
    listen 80;
    server_name api.mixjob.cn;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
NGINX

ln -s /etc/nginx/sites-available/mixjob /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 申请免费 SSL 证书
certbot --nginx -d api.mixjob.cn --non-interactive --agree-tos -m your@email.com
```

## 七、后续更新

每次更新代码后：

```bash
cd /opt/mixjob
git pull
docker build -t mixjob .
docker stop mixjob && docker rm mixjob
docker run -d \
  --name mixjob \
  --restart always \
  -p 8000:8000 \
  -v /opt/mixjob/data:/app/data \
  mixjob
```

或者用 docker compose（更方便）：

```yaml
# docker-compose.yml（项目已包含）
services:
  mixjob:
    build: .
    restart: always
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
```

之后更新只需：

```bash
git pull && docker compose up -d --build
```

## 八、登录招聘网站

阿里云服务器有 2GB 内存，足以运行 Playwright Firefox。用户在 `mixjob.cn` 点击"一键登录"后：

1. 服务器后台启动 Playwright Firefox
2. 浏览器窗口打开招聘网站登录页
3. 用户完成登录后，cookie 自动保存到服务器的 `browser_states/` 目录
4. 后续抓取自动使用已保存的登录状态

无需额外配置 Xvfb，Docker 容器内 Playwright 的 headless 模式直接可用。
