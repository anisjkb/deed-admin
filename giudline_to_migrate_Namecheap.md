Sure — here’s a clean “do this, not that” guide for **both Railway (now)** and **Namecheap VPS (future)**.

---

# ✅ A) Railway setup (current)

### 1) Start command (must)

Railway → **Service → Settings → Deploy → Start Command**

```bash
uvicorn src.backend.app:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"
```

Why: Railway sits in front as a proxy, so your app must trust forwarded HTTPS headers.

### 2) Healthcheck

Railway → **Settings → Deploy → Healthcheck Path**

```
/
```

### 3) Env variables (minimum)

Railway → **Variables**

* `DEBUG=false`
* `FRONTEND_URL=https://deed-admin-production.up.railway.app`
* `API_URL=https://deed-admin-production.up.railway.app`
* `COOKIE_SECURE=true`
* `SESSION_HTTPS_ONLY=true` (recommended)

### 4) Proxy middleware (optional)

You can keep it, but Railway already works fine with the uvicorn flags. If you keep it:

```py
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
```

---

# ✅ B) Namecheap VPS setup (future, production-safe)

## Recommended architecture

**Internet → Nginx (SSL) → Uvicorn on localhost**

### 1) Run app on localhost only (important)

Start Uvicorn like:

```bash
uvicorn src.backend.app:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips="127.0.0.1"
```

✅ This is the key difference from Railway: don’t use `*` on VPS.

### 2) Nginx config (required)

Example Nginx site:

```nginx
server {
  server_name admin.yourdomain.com;

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Host $host;
  }
}
```

### 3) HTTPS (Let’s Encrypt)

Use Certbot to enable SSL. After SSL, your site becomes:

```
https://admin.yourdomain.com
```

### 4) Env variables (VPS)

* `DEBUG=false`
* `FRONTEND_URL=https://admin.yourdomain.com`
* `API_URL=https://admin.yourdomain.com`
* `COOKIE_SECURE=true`
* `SESSION_HTTPS_ONLY=true`

### 5) ProxyHeadersMiddleware on VPS?

Optional. If you keep it, don’t use `*`. Use:

```py
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["127.0.0.1", "localhost"])
```

(Or skip it if you already use the uvicorn proxy flags.)

---

# ✅ Quick comparison (Railway vs VPS)

| Item         | Railway                     | VPS                                 |
| ------------ | --------------------------- | ----------------------------------- |
| Port         | `$PORT`                     | fixed like `8000`                   |
| Host binding | `0.0.0.0`                   | `127.0.0.1`                         |
| Proxy trust  | `--forwarded-allow-ips="*"` | `--forwarded-allow-ips="127.0.0.1"` |
| Front proxy  | Railway Edge                | Nginx                               |
| SSL          | automatic                   | Let’s Encrypt                       |

---

If you want, I can also give you a **copy-paste VPS checklist**: install Python, create venv, systemd service, Nginx, SSL, firewall (UFW).
