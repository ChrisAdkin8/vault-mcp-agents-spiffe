#!/usr/bin/env python3
"""Generate the SPIFFE SVID Lifecycle for MCP Servers diagram."""

from PIL import Image, ImageDraw, ImageFont
import math
import os

S = 3
W, H = 1400 * S, 1700 * S
BG = (20, 20, 25)
img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# Colours
CYAN = (0, 210, 230)
GREEN = (80, 210, 170)
BLUE = (100, 160, 255)
ORANGE = (255, 180, 40)
YELLOW = (230, 210, 70)
MAGENTA = (210, 100, 220)
RED = (220, 80, 80)
WHITE = (240, 240, 240)
GREY = (160, 160, 160)
DARK_BG = (38, 38, 45)
DARK_CYAN_BG = (15, 70, 80)
DARK_GREEN_BG = (15, 70, 55)
DARK_BLUE_BG = (25, 50, 100)
DARK_YELLOW_BG = (70, 65, 15)
DARK_MAGENTA_BG = (70, 30, 75)
DARK_ORANGE_BG = (80, 55, 10)
DARK_RED_BG = (80, 30, 30)

# Fonts
try:
    font_title = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22 * S)
    font_heading = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15 * S)
    font_body = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12 * S)
    font_small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 10 * S)
    font_label = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 11 * S)
    font_code = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 10 * S)
except Exception:
    font_title = ImageFont.load_default()
    font_heading = font_body = font_small = font_label = font_code = font_title


def text_centered(x, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((x - tw / 2, y), text, fill=fill, font=font)


def draw_rounded_rect(xy, fill, outline, radius=10, width=2):
    draw.rounded_rectangle(xy, radius=radius * S, fill=fill, outline=outline, width=width * S)


def draw_arrow(x0, y0, x1, y1, color=GREY, width=2, head_size=10, dashed=False):
    w = width * S
    hs = head_size * S
    if dashed:
        dx = x1 - x0
        dy = y1 - y0
        length = math.sqrt(dx * dx + dy * dy)
        dash_len = 12 * S
        gap_len = 8 * S
        nx, ny = dx / length, dy / length
        pos = 0
        while pos < length:
            sx = x0 + nx * pos
            sy = y0 + ny * pos
            end = min(pos + dash_len, length)
            ex = x0 + nx * end
            ey = y0 + ny * end
            draw.line([(sx, sy), (ex, ey)], fill=color, width=w)
            pos += dash_len + gap_len
    else:
        draw.line([(x0, y0), (x1, y1)], fill=color, width=w)
    angle = math.atan2(y1 - y0, x1 - x0)
    lx = x1 - hs * math.cos(angle - 0.4)
    ly = y1 - hs * math.sin(angle - 0.4)
    rx = x1 - hs * math.cos(angle + 0.4)
    ry = y1 - hs * math.sin(angle + 0.4)
    draw.polygon([(x1, y1), (lx, ly), (rx, ry)], fill=color)


def draw_circle_number(x, y, num, color=ORANGE, size=14):
    r = size * S
    draw.ellipse((x - r, y - r, x + r, y + r), fill=color)
    text_centered(x, y - 8 * S, str(num), font_heading, (20, 20, 20))


# ─── Title ───
text_centered(W // 2, 30 * S, "SPIFFE SVID Lifecycle for MCP Servers", font_title, WHITE)
text_centered(W // 2, 60 * S, "PKI setup → AppRole auth → SVID rendering → mTLS between services", font_body, GREY)

# ═══════════════════════════════════════════════════════════════
# PHASE 1: PKI & APPROLE SETUP (vault-init)
# ═══════════════════════════════════════════════════════════════
phase1_y = 110 * S
draw.rounded_rectangle(
    (40 * S, phase1_y, 1360 * S, phase1_y + 310 * S),
    radius=12 * S, fill=DARK_BG, outline=(60, 60, 70), width=2 * S
)
draw_circle_number(80 * S, phase1_y + 25 * S, 1)
draw.text((100 * S, phase1_y + 12 * S), "PKI & APPROLE BOOTSTRAP", font=font_heading, fill=ORANGE)
draw.text((100 * S, phase1_y + 36 * S), "vault-init container configures Vault and exports AppRole credentials", font=font_small, fill=GREY)

# vault-init box
vi_x, vi_y = 100 * S, phase1_y + 70 * S
draw_rounded_rect((vi_x, vi_y, vi_x + 240 * S, vi_y + 70 * S), fill=DARK_MAGENTA_BG, outline=MAGENTA)
text_centered(vi_x + 120 * S, vi_y + 10 * S, "vault-init", font_heading, WHITE)
text_centered(vi_x + 120 * S, vi_y + 35 * S, "vault_init.sh", font_code, MAGENTA)
text_centered(vi_x + 120 * S, vi_y + 50 * S, "(one-shot container)", font=font_small, fill=GREY)

# Vault PKI box
vpki_x, vpki_y = 530 * S, phase1_y + 70 * S
draw_rounded_rect((vpki_x, vpki_y, vpki_x + 360 * S, vpki_y + 70 * S), fill=DARK_GREEN_BG, outline=GREEN)
text_centered(vpki_x + 180 * S, vpki_y + 10 * S, "Vault PKI Engine", font_heading, WHITE)
text_centered(vpki_x + 180 * S, vpki_y + 35 * S, "pki/ mount", font_code, GREEN)
text_centered(vpki_x + 180 * S, vpki_y + 50 * S, "Internal root CA (RSA 4096)", font=font_small, fill=GREY)

# Arrow vault-init -> Vault PKI
draw_arrow(vi_x + 240 * S, vi_y + 35 * S, vpki_x, vpki_y + 35 * S, color=MAGENTA, width=2)

# PKI config details
pkd_x, pkd_y = 530 * S, phase1_y + 160 * S
draw_rounded_rect((pkd_x, pkd_y, pkd_x + 360 * S, pkd_y + 95 * S), fill=(30, 30, 35), outline=(80, 80, 90), width=1)
draw.text((pkd_x + 10 * S, pkd_y + 5 * S), "mcp-server PKI role:", font=font_label, fill=YELLOW)
draw.text((pkd_x + 10 * S, pkd_y + 25 * S), "TTL: 3600s (1 hour)", font=font_code, fill=WHITE)
draw.text((pkd_x + 10 * S, pkd_y + 42 * S), "Key: RSA 2048", font=font_code, fill=WHITE)
draw.text((pkd_x + 10 * S, pkd_y + 59 * S), "Allowed URI SANs:", font=font_code, fill=GREEN)
draw.text((pkd_x + 10 * S, pkd_y + 76 * S), "spiffe://my-trust-domain/ns/default/sa/mcp", font=font_code, fill=CYAN)

draw_arrow(vpki_x + 180 * S, vpki_y + 70 * S, pkd_x + 180 * S, pkd_y, color=(80, 80, 90), width=1, dashed=True)

# AppRole + shared volume
ar_x, ar_y = 100 * S, phase1_y + 170 * S
draw_rounded_rect((ar_x, ar_y, ar_x + 240 * S, ar_y + 85 * S), fill=(30, 30, 35), outline=YELLOW, width=1)
draw.text((ar_x + 10 * S, ar_y + 5 * S), "AppRole credentials:", font=font_label, fill=YELLOW)
draw.text((ar_x + 10 * S, ar_y + 28 * S), "mcp-role", font=font_code, fill=WHITE)
draw.text((ar_x + 130 * S, ar_y + 28 * S), "(mcp-policy)", font=font_small, fill=GREY)
draw.text((ar_x + 10 * S, ar_y + 48 * S), "/creds/role_id", font=font_code, fill=ORANGE)
draw.text((ar_x + 10 * S, ar_y + 65 * S), "/creds/secret_id", font=font_code, fill=ORANGE)

# Shared volume icon
sv_x, sv_y = 100 * S, phase1_y + 275 * S
draw_rounded_rect((sv_x, sv_y, sv_x + 240 * S, sv_y + 30 * S), fill=DARK_ORANGE_BG, outline=ORANGE, width=1)
text_centered(sv_x + 120 * S, sv_y + 5 * S, "shared-creds volume", font_label, ORANGE)

draw_arrow(ar_x + 120 * S, ar_y + 85 * S, sv_x + 120 * S, sv_y, color=ORANGE, width=2)

# mcp-policy details
mp_x, mp_y = 980 * S, phase1_y + 70 * S
draw_rounded_rect((mp_x, mp_y, mp_x + 330 * S, mp_y + 75 * S), fill=(30, 30, 35), outline=(80, 80, 90), width=1)
draw.text((mp_x + 10 * S, mp_y + 5 * S), "mcp-policy:", font=font_label, fill=YELLOW)
draw.text((mp_x + 10 * S, mp_y + 28 * S), "path \"pki/issue/mcp-server\"", font=font_code, fill=GREEN)
draw.text((mp_x + 10 * S, mp_y + 48 * S), "  capabilities = [\"create\",\"update\"]", font=font_code, fill=WHITE)

draw_arrow(vpki_x + 360 * S, vpki_y + 35 * S, mp_x, mp_y + 35 * S, color=(80, 80, 90), width=1, dashed=True)

# ═══════════════════════════════════════════════════════════════
# PHASE 2: VAULT AGENT AUTHENTICATION & SVID RENDERING
# ═══════════════════════════════════════════════════════════════
phase2_y = 460 * S
draw.rounded_rectangle(
    (40 * S, phase2_y, 1360 * S, phase2_y + 340 * S),
    radius=12 * S, fill=DARK_BG, outline=(60, 60, 70), width=2 * S
)
draw_circle_number(80 * S, phase2_y + 25 * S, 2)
draw.text((100 * S, phase2_y + 12 * S), "VAULT AGENT SVID RENDERING", font=font_heading, fill=ORANGE)
draw.text((100 * S, phase2_y + 36 * S), "Sidecar authenticates via AppRole, requests PKI certs, renders to shared volume", font=font_small, fill=GREY)

# Vault Agent box
va_x, va_y = 100 * S, phase2_y + 70 * S
draw_rounded_rect((va_x, va_y, va_x + 280 * S, va_y + 80 * S), fill=DARK_CYAN_BG, outline=CYAN)
text_centered(va_x + 140 * S, va_y + 10 * S, "Vault Agent", font_heading, WHITE)
text_centered(va_x + 140 * S, va_y + 35 * S, "agent.hcl", font_code, CYAN)
text_centered(va_x + 140 * S, va_y + 55 * S, "(long-running sidecar)", font=font_small, fill=GREY)

# shared-creds input
svi_x, svi_y = 100 * S, phase2_y + 170 * S
draw_rounded_rect((svi_x, svi_y, svi_x + 280 * S, svi_y + 30 * S), fill=DARK_ORANGE_BG, outline=ORANGE, width=1)
text_centered(svi_x + 140 * S, svi_y + 5 * S, "reads shared-creds volume", font_label, ORANGE)

draw_arrow(svi_x + 140 * S, svi_y, va_x + 140 * S, va_y + 80 * S, color=ORANGE, width=2)

# Vault Server
vs_x, vs_y = 530 * S, phase2_y + 70 * S
draw_rounded_rect((vs_x, vs_y, vs_x + 300 * S, vs_y + 80 * S), fill=DARK_GREEN_BG, outline=GREEN)
text_centered(vs_x + 150 * S, vs_y + 10 * S, "Vault Server", font_heading, WHITE)
text_centered(vs_x + 150 * S, vs_y + 35 * S, "auth/approle/login", font_code, GREEN)
text_centered(vs_x + 150 * S, vs_y + 55 * S, "pki/issue/mcp-server", font_code, GREEN)

# Arrow: Agent -> Vault (AppRole login)
draw_arrow(va_x + 280 * S, va_y + 25 * S, vs_x, vs_y + 25 * S, color=CYAN, width=2)
draw.text((va_x + 290 * S, va_y + 5 * S), "1. AppRole login", font=font_small, fill=YELLOW)
draw.text((va_x + 290 * S, va_y + 20 * S), "(role_id + secret_id)", font=font_small, fill=GREY)

# Arrow: Agent -> Vault (PKI issue)
draw_arrow(va_x + 280 * S, va_y + 55 * S, vs_x, vs_y + 55 * S, color=CYAN, width=2)
draw.text((va_x + 290 * S, va_y + 48 * S), "2. Issue certificate", font=font_small, fill=YELLOW)
draw.text((va_x + 290 * S, va_y + 63 * S), "(SPIFFE URI SAN)", font=font_small, fill=GREY)

# PKI request details
prd_x, prd_y = 530 * S, phase2_y + 170 * S
draw_rounded_rect((prd_x, prd_y, prd_x + 420 * S, prd_y + 70 * S), fill=(30, 30, 35), outline=CYAN, width=1)
draw.text((prd_x + 10 * S, prd_y + 5 * S), "PKI issue request:", font=font_label, fill=CYAN)
draw.text((prd_x + 10 * S, prd_y + 28 * S), "common_name = \"mcp-server\"", font=font_code, fill=WHITE)
draw.text((prd_x + 10 * S, prd_y + 48 * S), "uri_sans = \"spiffe://my-trust-domain/ns/default/sa/mcp\"", font=font_code, fill=GREEN)

draw_arrow(vs_x + 150 * S, vs_y + 80 * S, prd_x + 150 * S, prd_y, color=GREEN, width=1, dashed=True)

# Certificate files output (certs-vol)
cv_x, cv_y = 980 * S, phase2_y + 70 * S
draw_rounded_rect((cv_x, cv_y, cv_x + 330 * S, cv_y + 140 * S), fill=(30, 30, 35), outline=GREEN, width=1)
draw.text((cv_x + 10 * S, cv_y + 5 * S), "certs-vol (/etc/mcp/certs/):", font=font_label, fill=GREEN)
draw.text((cv_x + 10 * S, cv_y + 32 * S), "server.crt", font=font_code, fill=WHITE)
draw.text((cv_x + 140 * S, cv_y + 32 * S), "X.509 certificate", font=font_small, fill=GREY)
draw.text((cv_x + 10 * S, cv_y + 52 * S), "server.key", font=font_code, fill=WHITE)
draw.text((cv_x + 140 * S, cv_y + 52 * S), "RSA private key", font=font_small, fill=GREY)
draw.text((cv_x + 10 * S, cv_y + 72 * S), "ca.crt", font=font_code, fill=WHITE)
draw.text((cv_x + 140 * S, cv_y + 72 * S), "Root CA certificate", font=font_small, fill=GREY)
draw.text((cv_x + 10 * S, cv_y + 100 * S), "SPIFFE URI SAN embedded in server.crt:", font=font_small, fill=GREY)
draw.text((cv_x + 10 * S, cv_y + 115 * S), "spiffe://my-trust-domain/ns/default/sa/mcp", font=font_code, fill=CYAN)

# Arrow: Vault Agent -> certs-vol
draw_arrow(vs_x + 300 * S, vs_y + 40 * S, cv_x, cv_y + 40 * S, color=GREEN, width=2)
draw.text((vs_x + 310 * S, vs_y + 20 * S), "3. Renders templates", font=font_small, fill=YELLOW)
draw.text((vs_x + 310 * S, vs_y + 35 * S), "to cert volume", font=font_small, fill=GREY)

# Renewal note
rn_x, rn_y = 980 * S, phase2_y + 240 * S
draw_rounded_rect((rn_x, rn_y, rn_x + 330 * S, rn_y + 75 * S), fill=(35, 35, 50), outline=YELLOW, width=1)
draw.text((rn_x + 10 * S, rn_y + 5 * S), "Auto-renewal:", font=font_label, fill=YELLOW)
draw.text((rn_x + 10 * S, rn_y + 28 * S), "Vault Agent re-renders", font=font_small, fill=GREY)
draw.text((rn_x + 10 * S, rn_y + 43 * S), "templates before cert expiry.", font=font_small, fill=GREY)
draw.text((rn_x + 10 * S, rn_y + 58 * S), "Cert files updated on disk.", font=font_small, fill=GREEN)

# ═══════════════════════════════════════════════════════════════
# PHASE 3: MCP SERVER mTLS STARTUP
# ═══════════════════════════════════════════════════════════════
phase3_y = 840 * S
draw.rounded_rectangle(
    (40 * S, phase3_y, 1360 * S, phase3_y + 260 * S),
    radius=12 * S, fill=DARK_BG, outline=(60, 60, 70), width=2 * S
)
draw_circle_number(80 * S, phase3_y + 25 * S, 3)
draw.text((100 * S, phase3_y + 12 * S), "MCP SERVER mTLS STARTUP", font=font_heading, fill=ORANGE)
draw.text((100 * S, phase3_y + 36 * S), "MCP servers load SVIDs from cert volume and start with mutual TLS", font=font_small, fill=GREY)

# _tls_available check
tls_x, tls_y = 100 * S, phase3_y + 70 * S
draw_rounded_rect((tls_x, tls_y, tls_x + 300 * S, tls_y + 70 * S), fill=DARK_CYAN_BG, outline=CYAN)
text_centered(tls_x + 150 * S, tls_y + 10 * S, "http_transport.py", font_heading, WHITE)
text_centered(tls_x + 150 * S, tls_y + 35 * S, "_tls_available()", font_code, CYAN)
text_centered(tls_x + 150 * S, tls_y + 52 * S, "checks cert files exist", font=font_small, fill=GREY)

# SSL Context
ssl_x, ssl_y = 530 * S, phase3_y + 70 * S
draw_rounded_rect((ssl_x, ssl_y, ssl_x + 380 * S, ssl_y + 120 * S), fill=(30, 30, 35), outline=GREEN, width=1)
draw.text((ssl_x + 10 * S, ssl_y + 5 * S), "SSL Context (PROTOCOL_TLS_SERVER):", font=font_label, fill=GREEN)
draw.text((ssl_x + 10 * S, ssl_y + 30 * S), "load_cert_chain(server.crt, server.key)", font=font_code, fill=WHITE)
draw.text((ssl_x + 10 * S, ssl_y + 50 * S), "load_verify_locations(ca.crt)", font=font_code, fill=WHITE)
draw.text((ssl_x + 10 * S, ssl_y + 70 * S), "verify_mode = ssl.CERT_REQUIRED", font=font_code, fill=YELLOW)
draw.text((ssl_x + 10 * S, ssl_y + 92 * S), "Clients MUST present valid certificate", font=font_small, fill=GREY)

draw_arrow(tls_x + 300 * S, tls_y + 35 * S, ssl_x, ssl_y + 35 * S, color=CYAN, width=2)

# MCP Server instances
ms1_x, ms1_y = 530 * S, phase3_y + 210 * S
draw_rounded_rect((ms1_x, ms1_y, ms1_x + 180 * S, ms1_y + 35 * S), fill=DARK_BLUE_BG, outline=BLUE, width=1)
text_centered(ms1_x + 90 * S, ms1_y + 8 * S, "data-mcp :8001", font_label, WHITE)

ms2_x, ms2_y = 730 * S, phase3_y + 210 * S
draw_rounded_rect((ms2_x, ms2_y, ms2_x + 180 * S, ms2_y + 35 * S), fill=DARK_BLUE_BG, outline=BLUE, width=1)
text_centered(ms2_x + 90 * S, ms2_y + 8 * S, "compute-mcp :8002", font_label, WHITE)

draw_arrow(ssl_x + 100 * S, ssl_y + 120 * S, ms1_x + 90 * S, ms1_y, color=BLUE, width=1)
draw_arrow(ssl_x + 280 * S, ssl_y + 120 * S, ms2_x + 90 * S, ms2_y, color=BLUE, width=1)

# certs-vol input
cvi_x, cvi_y = 1020 * S, phase3_y + 70 * S
draw_rounded_rect((cvi_x, cvi_y, cvi_x + 300 * S, cvi_y + 60 * S), fill=DARK_GREEN_BG, outline=GREEN, width=1)
draw.text((cvi_x + 10 * S, cvi_y + 5 * S), "certs-vol (read-only):", font=font_label, fill=GREEN)
draw.text((cvi_x + 10 * S, cvi_y + 28 * S), "/etc/mcp/certs/server.crt", font=font_code, fill=WHITE)
draw.text((cvi_x + 10 * S, cvi_y + 45 * S), "/etc/mcp/certs/server.key, ca.crt", font=font_code, fill=WHITE)

draw_arrow(cvi_x, cvi_y + 30 * S, ssl_x + 380 * S, ssl_y + 30 * S, color=GREEN, width=2)

# ═══════════════════════════════════════════════════════════════
# PHASE 4: mTLS HANDSHAKE & IDENTITY VERIFICATION
# ═══════════════════════════════════════════════════════════════
phase4_y = 1140 * S
draw.rounded_rectangle(
    (40 * S, phase4_y, 1360 * S, phase4_y + 290 * S),
    radius=12 * S, fill=DARK_BG, outline=(60, 60, 70), width=2 * S
)
draw_circle_number(80 * S, phase4_y + 25 * S, 4)
draw.text((100 * S, phase4_y + 12 * S), "mTLS HANDSHAKE & WORKLOAD IDENTITY", font=font_heading, fill=ORANGE)
draw.text((100 * S, phase4_y + 36 * S), "Agent CLI connects to MCP servers over mutual TLS — rogue containers are rejected", font=font_small, fill=GREY)

# Agent CLI box
ac_x, ac_y = 100 * S, phase4_y + 75 * S
draw_rounded_rect((ac_x, ac_y, ac_x + 250 * S, ac_y + 70 * S), fill=DARK_CYAN_BG, outline=CYAN)
text_centered(ac_x + 125 * S, ac_y + 10 * S, "agent-cli", font_heading, WHITE)
text_centered(ac_x + 125 * S, ac_y + 35 * S, "streamable_http_client", font_code, CYAN)
text_centered(ac_x + 125 * S, ac_y + 52 * S, "mounts certs-vol", font=font_small, fill=GREY)

# MCP servers (mTLS enabled)
mcp1_x, mcp1_y = 530 * S, phase4_y + 70 * S
draw_rounded_rect((mcp1_x, mcp1_y, mcp1_x + 250 * S, mcp1_y + 80 * S), fill=DARK_BLUE_BG, outline=BLUE)
text_centered(mcp1_x + 125 * S, mcp1_y + 10 * S, "data-mcp-server", font_heading, WHITE)
text_centered(mcp1_x + 125 * S, mcp1_y + 35 * S, ":8001 (mTLS)", font_code, BLUE)
text_centered(mcp1_x + 125 * S, mcp1_y + 55 * S, "CERT_REQUIRED", font_code, YELLOW)

mcp2_x, mcp2_y = 530 * S, phase4_y + 165 * S
draw_rounded_rect((mcp2_x, mcp2_y, mcp2_x + 250 * S, mcp2_y + 80 * S), fill=DARK_BLUE_BG, outline=BLUE)
text_centered(mcp2_x + 125 * S, mcp2_y + 10 * S, "compute-mcp-server", font_heading, WHITE)
text_centered(mcp2_x + 125 * S, mcp2_y + 35 * S, ":8002 (mTLS)", font_code, BLUE)
text_centered(mcp2_x + 125 * S, mcp2_y + 55 * S, "CERT_REQUIRED", font_code, YELLOW)

# mTLS arrows
draw_arrow(ac_x + 250 * S, ac_y + 25 * S, mcp1_x, mcp1_y + 25 * S, color=GREEN, width=3)
draw_arrow(ac_x + 250 * S, ac_y + 50 * S, mcp2_x, mcp2_y + 25 * S, color=GREEN, width=3)

# mTLS lock icon (text)
draw.text((ac_x + 260 * S, ac_y + 5 * S), "mTLS", font=font_heading, fill=GREEN)
draw.text((ac_x + 260 * S, ac_y + 25 * S), "encrypted +", font=font_small, fill=GREEN)
draw.text((ac_x + 260 * S, ac_y + 40 * S), "mutually authenticated", font=font_small, fill=GREEN)

# Rogue container (blocked)
rc_x, rc_y = 900 * S, phase4_y + 75 * S
draw_rounded_rect((rc_x, rc_y, rc_x + 370 * S, rc_y + 80 * S), fill=DARK_RED_BG, outline=RED)
text_centered(rc_x + 185 * S, rc_y + 10 * S, "Rogue Container", font_heading, WHITE)
text_centered(rc_x + 185 * S, rc_y + 35 * S, "No AppRole creds = no SVID", font_code, RED)
text_centered(rc_x + 185 * S, rc_y + 55 * S, "mTLS rejects connection", font=font_small, fill=RED)

# Blocked arrow
draw_arrow(rc_x, rc_y + 40 * S, mcp1_x + 250 * S, mcp1_y + 40 * S, color=RED, width=2, dashed=True)
draw.text((mcp1_x + 260 * S, mcp1_y + 20 * S), "REJECTED", font=font_heading, fill=RED)

# SPIFFE identity verification
spf_x, spf_y = 900 * S, phase4_y + 180 * S
draw_rounded_rect((spf_x, spf_y, spf_x + 370 * S, spf_y + 85 * S), fill=(30, 30, 35), outline=CYAN, width=1)
draw.text((spf_x + 10 * S, spf_y + 5 * S), "SPIFFE ID \u2192 Policy mapping:", font=font_label, fill=CYAN)
draw.text((spf_x + 10 * S, spf_y + 28 * S), "spiffe://...agent/data_agent", font=font_code, fill=GREEN)
draw.text((spf_x + 10 * S, spf_y + 48 * S), "\u2192 agent_id: data_agent", font=font_code, fill=WHITE)
draw.text((spf_x + 10 * S, spf_y + 65 * S), "\u2192 resolve(role, agent_id) \u2192 tools", font=font_code, fill=ORANGE)

# ═══════════════════════════════════════════════════════════════
# PHASE 5: SECURITY PROPERTIES (bottom)
# ═══════════════════════════════════════════════════════════════
phase5_y = 1470 * S
draw.rounded_rectangle(
    (40 * S, phase5_y, 1360 * S, phase5_y + 200 * S),
    radius=12 * S, fill=DARK_BG, outline=(60, 60, 70), width=2 * S
)
draw_circle_number(80 * S, phase5_y + 25 * S, 5)
draw.text((100 * S, phase5_y + 12 * S), "SECURITY PROPERTIES", font=font_heading, fill=ORANGE)

# Properties in two columns
props_left = [
    ("Encrypted traffic", "mTLS on all agent \u2194 MCP communication", GREEN),
    ("Cryptographic identity", "No SVID = no connection (CERT_REQUIRED)", CYAN),
    ("Auto-rotation", "Vault Agent renews certs before expiry", YELLOW),
]
props_right = [
    ("No static secrets", "No long-lived keys in container images", GREEN),
    ("Policy-bound identity", "SPIFFE ID \u2192 scoped tool allowlist", CYAN),
    ("Defence in depth", "mTLS + Vault policies + app policy engine", YELLOW),
]

for i, (title, desc, color) in enumerate(props_left):
    py = phase5_y + 50 * S + i * 50 * S
    draw_rounded_rect((100 * S, py, 680 * S, py + 40 * S), fill=(30, 30, 35), outline=color, width=1)
    draw.text((115 * S, py + 4 * S), title, font=font_label, fill=color)
    draw.text((115 * S, py + 22 * S), desc, font=font_small, fill=GREY)

for i, (title, desc, color) in enumerate(props_right):
    py = phase5_y + 50 * S + i * 50 * S
    draw_rounded_rect((720 * S, py, 1300 * S, py + 40 * S), fill=(30, 30, 35), outline=color, width=1)
    draw.text((735 * S, py + 4 * S), title, font=font_label, fill=color)
    draw.text((735 * S, py + 22 * S), desc, font=font_small, fill=GREY)

# Save
out = os.path.join(os.path.dirname(__file__), "spiffe-svid-lifecycle.png")
img.save(out, dpi=(300, 300))
print(f"Saved {W}x{H} image to {out}")
