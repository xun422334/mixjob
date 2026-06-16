# 阿里云轻量应用服务器部署指南

## 一、购买服务器

1. 打开 [阿里云轻量应用服务器](https://swas.console.aliyun.com/)
2. 选择配置：
   - **地域**：选离你最近的（杭州/上海/北京）
   - **镜像**：Ubuntu 22.04
   - **套餐**：2核1G（~40元/月），够用了
3. 购买后在控制台设置 **root 密码**
4. 在防火墙规则中开放端口：**22**（SSH）、**80**（HTTP）、**443**（HTTPS）、**8000**（后端）

## 二、登录服务器

```bash
ssh root@<你的服务器公网IP>
```

## 三、安装 Docker

```bash
curl -fsSL https://get.docker.com | bash
```

## 四、拉取项目并构建

```bash
git clone https://github.com/xun422334/mixjob.git /opt/mixjob
cd /opt/mixjob
```

修改 Dockerfile 添加 Playwright 支持：

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装 Playwright 依赖 + Xvfb（虚拟显示器）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    xvfb \
    libnss3 \
    libnspr4 \
    libatk1.0-0t64 \
    libatk-bridge2.0-0t64 \
    libcups2t64 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2t64 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install firefox

COPY backend/ .

EXPOSE 8000

CMD ["python", "-c", "import os, uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))"]
```

构建镜像：

```bash
docker build -t mixjob .
```

## 五、启动服务

```bash
# 创建数据持久化目录
mkdir -p /opt/mixjob/data /opt/mixjob/browser_states

# 启动容器
docker run -d \
  --name mixjob \
  --restart always \
  -p 8000:8000 \
  -v /opt/mixjob/data:/app/data \
  -v /opt/mixjob/browser_states:/app/browser_states \
  -e DEEPSEEK_API_KEY=sk-589243dffe2843df8c743c5a10515e41 \
  mixjob
```

验证：

```bash
curl http://localhost:8000/api/health
# 应返回 {"status":"ok"}
```

## 六、更新前端 API 地址

修改 [frontend/src/api/index.ts](../frontend/src/api/index.ts) 第1行：

```typescript
const BASE = import.meta.env.DEV ? '/api' : 'http://<你的服务器IP>:8000/api'
```

然后重新构建部署到 Vercel：

```bash
cd frontend && npm run build
# 把 dist/ 部署到 Vercel
```

## 七、配置域名（可选）

如果想用 `api.mixjob.cn` 指向后端：

1. 在阿里云 DNS 添加 A 记录：`api.mixjob.cn` → 服务器 IP
2. 在服务器上安装 Nginx 反向代理：

```bash
apt install -y nginx
```

添加配置 `/etc/nginx/sites-available/mixjob`：

```nginx
server {
    listen 80;
    server_name api.mixjob.cn;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/mixjob /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

3. 前端 API 地址改为 `https://api.mixjob.cn/api`

## 八、Playwright 登录流程在服务器上的工作方式

服务器上用 `xvfb-run` 启动虚拟显示器，Playwright 才能打开浏览器：

修改 [backend/app/routes/auth.py](../backend/app/routes/auth.py) 的 `login_source` 函数，`subprocess.Popen` 那行改为：

```python
subprocess.Popen(
    ["xvfb-run", "-a", python_cmd, script, source],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
```

这样即使用户在云端，点击"一键登录"也能在服务器上打开无头浏览器完成自动抓取。

## 九、后续更新

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
  -v /opt/mixjob/browser_states:/app/browser_states \
  -e DEEPSEEK_API_KEY=sk-589243dffe2843df8c743c5a10515e41 \
  mixjob
```

或者写一个 `docker-compose.yml` 简化：

```yaml
version: "3"
services:
  mixjob:
    build: .
    restart: always
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./browser_states:/app/browser_states
    environment:
      - DEEPSEEK_API_KEY=sk-589243dffe2843df8c743c5a10515e41
```

之后更新只需：

```bash
git pull && docker compose up -d --build
```
