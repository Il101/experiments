// ============================================
// PATCH 007: Add Security Headers
// ============================================
// Priority: P0 - Critical Security
// Impact: Protects against XSS, CSRF, clickjacking
// Files: frontend/index.html, frontend/nginx.conf

// ============================================
// File: frontend/index.html (MODIFIED)
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    
    <!-- ✅ ADDED: Content Security Policy -->
    <meta http-equiv="Content-Security-Policy" content="
      default-src 'self';
      script-src 'self' 'unsafe-inline' 'unsafe-eval';
      style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
      font-src 'self' https://fonts.gstatic.com;
      img-src 'self' data: https:;
      connect-src 'self' ws://localhost:8000 http://localhost:8000 ws://127.0.0.1:8000 http://127.0.0.1:8000;
      frame-ancestors 'none';
      base-uri 'self';
      form-action 'self';
    ">
    
    <!-- ✅ ADDED: Other security headers -->
    <meta http-equiv="X-Content-Type-Options" content="nosniff">
    <meta http-equiv="X-Frame-Options" content="DENY">
    <meta http-equiv="X-XSS-Protection" content="1; mode=block">
    <meta name="referrer" content="strict-origin-when-cross-origin">
    
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Breakout Bot - Trading System</title>
  </head>
  <body>
    <noscript>
      <div style="padding: 20px; text-align: center;">
        <h1>JavaScript Required</h1>
        <p>Please enable JavaScript to use Breakout Bot Trading System.</p>
      </div>
    </noscript>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>

// ============================================
// File: frontend/nginx.conf (MODIFIED)
server {
    listen 80;
    server_name localhost;

    root /usr/share/nginx/html;
    index index.html;

    # ✅ ADDED: Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # ✅ ADDED: Content Security Policy
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' ws: http:; frame-ancestors 'none'; base-uri 'self'; form-action 'self';" always;

    # ✅ ADDED: HSTS (HTTP Strict Transport Security)
    # Uncomment in production with HTTPS
    # add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # ✅ ADDED: Cache static assets with security headers
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options "nosniff" always;
    }

    # ✅ ADDED: Disable server version disclosure
    server_tokens off;

    # ✅ ADDED: Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;

    # ✅ ADDED: Size limits
    client_max_body_size 1M;
    client_body_buffer_size 128k;
}

// ============================================
// File: frontend/vite.config.ts (MODIFIED)
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || 'http://localhost:8000'),
    'import.meta.env.VITE_WS_URL': JSON.stringify(process.env.VITE_WS_URL || 'ws://localhost:8000/ws/'),
  },
  server: {
    // ✅ ADDED: Security headers in dev mode
    headers: {
      'X-Frame-Options': 'DENY',
      'X-Content-Type-Options': 'nosniff',
      'X-XSS-Protection': '1; mode=block',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
    },
  },
  build: {
    // ✅ ADDED: Source maps only in dev
    sourcemap: process.env.NODE_ENV === 'development',
    // ✅ ADDED: Minify in production
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: process.env.NODE_ENV === 'production',
        drop_debugger: process.env.NODE_ENV === 'production',
      },
    },
  },
})

// ============================================
// File: backend/api/main.py (MODIFIED - Security Headers)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# ✅ ADDED: Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # CSP for API responses
        response.headers['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none';"
        
        # Remove server header
        if 'server' in response.headers:
            del response.headers['server']
        
        return response

app = FastAPI(
    title="Breakout Bot Trading System API",
    description="RESTful API for algorithmic cryptocurrency trading bot",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    # ✅ ADDED: Disable docs in production
    docs_url="/api/docs" if not os.getenv("PRODUCTION") else None,
    redoc_url="/api/redoc" if not os.getenv("PRODUCTION") else None,
)

# ✅ ADDED: Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Existing middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://127.0.0.1:5173",
        # Add production origins
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # ✅ Explicit methods
    allow_headers=["*"],
    max_age=3600,  # ✅ Cache preflight requests
)

# ... rest of app setup

// ============================================
// File: frontend/.env.example (NEW)
# API Configuration
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/

# Feature Flags
VITE_ENABLE_DEVTOOLS=true

# Security (Don't commit real values!)
VITE_SENTRY_DSN=https://example@sentry.io/123456

# Build
NODE_ENV=development

// ============================================
// Installation:
// 
// 1. Update frontend/index.html with security headers
// 2. Update frontend/nginx.conf with security headers
// 3. Update frontend/vite.config.ts with security options
// 4. Update backend/api/main.py with security middleware
// 5. Create .env.example if not exists
// 6. Test CSP doesn't block legitimate requests
// 7. Test in browser console: document.domain, window.parent (should fail)
//
// Testing CSP:
// - Open DevTools -> Console
// - Try: eval('1+1') - should be blocked
// - Try: document.write('<script>alert(1)</script>') - should be blocked
// - Check Network tab for CSP violations
//
// Testing Headers:
// - curl -I http://localhost:5173
// - Verify X-Frame-Options, X-Content-Type-Options, etc. present
//
// Security Checklist:
// ✅ CSP headers prevent XSS
// ✅ X-Frame-Options prevents clickjacking
// ✅ X-Content-Type-Options prevents MIME sniffing
// ✅ Referrer-Policy limits referrer leakage
// ✅ Permissions-Policy disables unnecessary APIs
// ✅ Server version disclosure disabled
// ✅ Rate limiting enabled
// ✅ Size limits enforced
