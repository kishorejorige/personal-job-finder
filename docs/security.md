# Security and Access Protection Guide

This document outlines the security architecture of the Personal Job Finder application and provides options for protecting private user data in production.

---

## 1. Implemented Security Controls

### Upload Security & Sandbox

The application processes resumes in-memory without persistent disk storage:
- **Allowed Extensions Check**: Rejects any file extension that is not exactly `pdf`, `docx`, or `txt`.
- **MIME Validation**: Validates file MIME types against `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, and `text/plain` to prevent uploading executable or malicious binaries disguised as documents.
- **Magic File Signatures**: Verifies binary headers (`%PDF` for PDFs and `PK\x03\x04` for DOCX) prior to loading/parsing.
- **Size Limitation**: Rejects files exceeding the configured limit (default: `2 MB`).
- **Filename Sanitization**: Sanitizes filename strings to alphanumeric characters, hyphens, and periods to block directory traversal attacks (`../../filename`).
- **No Local Writes**: Resumes are parsed in-memory and the text is saved to the SQLite database. No binary files are stored on the server's disk filesystem.

### CSV Formula Injection Protection

The CSV exporter sanitizes cells to protect against formula execution attacks:
- Any cell value beginning with `=`, `+`, `-`, or `@` is prefixed with an apostrophe `'`.
- This ensures Excel or Google Sheets interprets the value as raw text rather than executing it as a spreadsheet formula.

### Secure HTTP Headers (Nginx)

The production Nginx reverse proxy configuration enforces:
- `X-Frame-Options: DENY`: Blocks Clickjacking.
- `X-Content-Type-Options: nosniff`: Prevents MIME-type sniffing.
- `X-XSS-Protection: 1; mode=block`: Safeguards against Cross-Site Scripting.
- `Content-Security-Policy (CSP)`: Directs the browser to only fetch and execute approved scripts and resources.

---

## 2. Deploying Safely (Access Control Options)

Since this application is designed for personal use and does not contain a built-in authentication system, **it must never be exposed directly to the public internet** without access protection.

Choose one of the following deployment configurations:

### Option A: Private Local Network (Recommended)

Run the application entirely behind your local network or firewall. Access it using `http://localhost:4200` or the private IP address of the host machine (e.g., `http://192.168.1.100:4200`).

### Option B: Tailscale VPN (Highly Recommended for Remote Access)

1. Install Tailscale on the server hosting the app.
2. Install Tailscale on the client machines (laptop, phone) used to access the app.
3. Access the dashboard securely using the server's unique Tailscale private IP address (e.g., `http://100.x.y.z:4200`). This ensures all traffic is encrypted and only authenticated members of your tailnet can connect.

### Option C: Cloudflare Access / Tunnel

1. Set up a Cloudflare Tunnel on the deployment host.
2. Route the frontend domain (e.g., `jobfinder.yourdomain.com`) through the tunnel.
3. Configure a Cloudflare Access policy using standard identity providers (Google, GitHub, email OTP) to enforce authentication before granting HTTP traffic access to the Nginx server.

### Option D: Reverse Proxy Basic Authentication

If exposing via a public IP, configure HTTP Basic Authentication in Nginx to password-protect the entire application.

Generate a `.htpasswd` file on the server:
```bash
htpasswd -c /etc/nginx/.htpasswd username
```

Add these lines to `nginx.conf`:
```nginx
location / {
    auth_basic "Private Area";
    auth_basic_user_file /etc/nginx/.htpasswd;
    try_files $uri $uri/ /index.html;
}
```
