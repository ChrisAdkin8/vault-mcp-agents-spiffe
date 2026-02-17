#!/usr/bin/env python3
"""Generate the SPIFFE SVID Acquisition Flow diagram.

Updated to reflect the actual architecture: Vault Agent sidecar with
AppRole auth renders SVIDs from Vault's PKI engine to a shared Docker
volume.  No SPIRE infrastructure is used.
"""

from PIL import Image, ImageDraw, ImageFont
import math
import os

# Scale factor for high resolution
S = 3

# Canvas
W, H = 1200 * S, 900 * S
BG = (30, 30, 30)
img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# Colours
CYAN = (0, 210, 210)
ORANGE = (255, 165, 0)
GREEN = (0, 200, 100)
YELLOW = (210, 200, 80)
WHITE = (240, 240, 240)
GREY = (160, 160, 160)
DARK_GREEN_BG = (40, 60, 40)
DARK_YELLOW_BG = (60, 55, 30)
DARK_BLUE_BG = (35, 45, 70)
DASHED_BORDER = (120, 120, 60)
PURPLE = (160, 120, 210)
DARK_PURPLE_BG = (50, 40, 65)

# Fonts (scaled)
try:
    font_title = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22 * S)
    font_subtitle = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13 * S)
    font_heading = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 14 * S)
    font_body = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12 * S)
    font_small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 10 * S)
    font_circle = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 12 * S)
except Exception:
    font_title = ImageFont.load_default()
    font_subtitle = font_heading = font_body = font_small = font_circle = font_title


def draw_rounded_rect(xy, fill, outline, radius=8, width=2):
    r = radius * S
    w = width * S
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=w)


def draw_circle_number(cx, cy, num, color=ORANGE):
    r = 11 * S
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    bbox = draw.textbbox((0, 0), str(num), font=font_circle)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((cx - tw / 2, cy - th / 2 - 1 * S), str(num), fill=(30, 30, 30), font=font_circle)


def draw_dashed_rect(xy, outline, dash_len=6, gap_len=4, width=1):
    dl = dash_len * S
    gl = gap_len * S
    w = width * S
    x0, y0, x1, y1 = xy
    for edge_start, edge_end, is_horiz in [
        ((x0, y0), (x1, y0), True), ((x0, y1), (x1, y1), True),
        ((x0, y0), (x0, y1), False), ((x1, y0), (x1, y1), False),
    ]:
        pos = 0
        length = abs((edge_end[0] - edge_start[0]) + (edge_end[1] - edge_start[1]))
        while pos < length:
            if is_horiz:
                sx, sy = edge_start[0] + pos, edge_start[1]
                ex, ey = min(edge_start[0] + pos + dl, edge_end[0]), edge_start[1]
            else:
                sx, sy = edge_start[0], edge_start[1] + pos
                ex, ey = edge_start[0], min(edge_start[1] + pos + dl, edge_end[1])
            draw.line([(sx, sy), (ex, ey)], fill=outline, width=w)
            pos += dl + gl


def text_centered(x, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((x - tw / 2, y), text, fill=fill, font=font)


def draw_arrow(x0, y0, x1, y1, color=GREY, width=2, head_size=8):
    w = width * S
    hs = head_size * S
    draw.line([(x0, y0), (x1, y1)], fill=color, width=w)
    angle = math.atan2(y1 - y0, x1 - x0)
    lx = x1 - hs * math.cos(angle - 0.4)
    ly = y1 - hs * math.sin(angle - 0.4)
    rx = x1 - hs * math.cos(angle + 0.4)
    ry = y1 - hs * math.sin(angle + 0.4)
    draw.polygon([(x1, y1), (lx, ly), (rx, ry)], fill=color)


# ─── Title ───
text_centered(W // 2, 20 * S, "SPIFFE SVID Acquisition Flow", font_title, WHITE)
text_centered(W // 2, 50 * S, "vault-mcp-agents-spiffe  —  How MCP Server workloads obtain X.509 SVIDs", font_subtitle, GREY)

# ═══════════════════════════════════════════════════════════════════════════
# Row 1: vault-init Bootstrap
# ═══════════════════════════════════════════════════════════════════════════

# ─── vault-init box (top left) ───
tf_x, tf_y = 80 * S, 100 * S
draw_rounded_rect((tf_x, tf_y, tf_x + 260 * S, tf_y + 60 * S), fill=DARK_PURPLE_BG, outline=PURPLE)
text_centered(tf_x + 130 * S, tf_y + 8 * S, "vault-init", font_heading, PURPLE)
text_centered(tf_x + 130 * S, tf_y + 30 * S, "Bootstrap container", font_small, GREY)

# ─── Vault box (top right) ───
v_x, v_y = 680 * S, 100 * S
draw_rounded_rect((v_x, v_y, v_x + 350 * S, v_y + 60 * S), fill=DARK_YELLOW_BG, outline=YELLOW)
text_centered(v_x + 175 * S, v_y + 8 * S, "Vault Enterprise", font_heading, YELLOW)
text_centered(v_x + 175 * S, v_y + 30 * S, "PKI engine + AppRole auth", font_small, GREY)

# Step 1: vault-init -> Vault (configure PKI + AppRole)
draw_arrow(tf_x + 260 * S, tf_y + 30 * S, v_x, v_y + 30 * S, color=PURPLE)
draw_circle_number(tf_x + 290 * S, tf_y + 8 * S, 1)
draw.text((tf_x + 308 * S, tf_y + 1 * S), "Configure PKI engine,", font=font_small, fill=GREEN)
draw.text((tf_x + 308 * S, tf_y + 14 * S), "AppRole, and mcp-policy", font=font_small, fill=GREEN)

# ─── shared-creds volume (below Terraform) ───
sc_x, sc_y = 100 * S, 210 * S
draw_dashed_rect((sc_x, sc_y, sc_x + 220 * S, sc_y + 55 * S), outline=DASHED_BORDER)
draw.text((sc_x + 10 * S, sc_y + 5 * S), "shared-creds volume", fill=YELLOW, font=font_heading)
draw.text((sc_x + 10 * S, sc_y + 26 * S), "role_id  +  secret_id", fill=GREY, font=font_small)

# Step 2: vault-init -> shared-creds (write AppRole creds)
draw_arrow(tf_x + 130 * S, tf_y + 60 * S, sc_x + 110 * S, sc_y, color=PURPLE)
draw_circle_number(tf_x + 60 * S, tf_y + 72 * S, 2)
draw.text((tf_x + 78 * S, tf_y + 65 * S), "Write AppRole creds", font=font_small, fill=GREEN)

# ═══════════════════════════════════════════════════════════════════════════
# Row 2: Vault Agent
# ═══════════════════════════════════════════════════════════════════════════

# ─── Vault Agent box ───
va_x, va_y = 380 * S, 330 * S
draw_rounded_rect((va_x, va_y, va_x + 300 * S, va_y + 70 * S), fill=DARK_YELLOW_BG, outline=ORANGE)
text_centered(va_x + 150 * S, va_y + 8 * S, "Vault Agent", font_heading, ORANGE)
text_centered(va_x + 150 * S, va_y + 28 * S, "Sidecar container", font_small, GREY)
text_centered(va_x + 150 * S, va_y + 42 * S, "config/agent.hcl", font_small, GREY)

# Step 3: shared-creds -> Vault Agent (read AppRole creds)
draw_arrow(sc_x + 200 * S, sc_y + 40 * S, va_x, va_y + 20 * S, color=ORANGE)
draw_circle_number(sc_x + 180 * S, sc_y + 70 * S, 3)
draw.text((sc_x + 198 * S, sc_y + 63 * S), "Read role_id + secret_id", font=font_small, fill=GREEN)

# Step 4: Vault Agent -> Vault (authenticate via AppRole)
draw_arrow(va_x + 250 * S, va_y + 15 * S, v_x + 100 * S, v_y + 60 * S, color=ORANGE)
draw_circle_number(va_x + 310 * S, va_y - 20 * S, 4)
draw.text((va_x + 328 * S, va_y - 28 * S), "Authenticate via AppRole", font=font_small, fill=GREEN)
draw.text((va_x + 328 * S, va_y - 14 * S), "Receive Vault token", font=font_small, fill=GREY)

# ─── PKI Issue callout (right of Vault Agent) ───
pki_x, pki_y = 800 * S, 290 * S
draw_dashed_rect((pki_x, pki_y, pki_x + 280 * S, pki_y + 80 * S), outline=DASHED_BORDER)
draw.text((pki_x + 10 * S, pki_y + 5 * S), "PKI Issue Request:", fill=YELLOW, font=font_heading)
draw.text((pki_x + 10 * S, pki_y + 26 * S), "POST pki/issue/mcp-server", fill=CYAN, font=font_small)
draw.text((pki_x + 10 * S, pki_y + 40 * S), "common_name = mcp-server", fill=GREY, font=font_small)
draw.text((pki_x + 10 * S, pki_y + 54 * S), "uri_sans = spiffe://my-trust-", fill=GREY, font=font_small)
draw.text((pki_x + 10 * S, pki_y + 67 * S), "  domain/ns/default/sa/mcp", fill=GREY, font=font_small)

# Step 5: Vault Agent requests cert from PKI engine
draw_arrow(va_x + 300 * S, va_y + 50 * S, pki_x, pki_y + 40 * S, color=ORANGE)
draw_circle_number(va_x + 310 * S, va_y + 55 * S, 5)
draw.text((va_x + 328 * S, va_y + 48 * S), "Request X.509 SVID", font=font_small, fill=GREEN)

# ═══════════════════════════════════════════════════════════════════════════
# Row 3: certs-vol and X.509 SVID
# ═══════════════════════════════════════════════════════════════════════════

# ─── X.509 SVID box ───
svid_x, svid_y = 80 * S, 480 * S
draw_rounded_rect((svid_x, svid_y, svid_x + 280 * S, svid_y + 85 * S), fill=DARK_GREEN_BG, outline=CYAN)
draw.text((svid_x + 10 * S, svid_y + 8 * S), "X.509 SVID", fill=CYAN, font=font_heading)
draw.text((svid_x + 10 * S, svid_y + 28 * S), "SAN: spiffe://my-trust-domain/", fill=GREY, font=font_small)
draw.text((svid_x + 10 * S, svid_y + 42 * S), "       ns/default/sa/mcp", fill=GREY, font=font_small)
draw.text((svid_x + 10 * S, svid_y + 58 * S), "TTL: 1 hour (auto-rotated)", fill=GREY, font=font_small)

# ─── certs-vol volume (centre) ───
cv_x, cv_y = 450 * S, 490 * S
draw_dashed_rect((cv_x, cv_y, cv_x + 260 * S, cv_y + 70 * S), outline=DASHED_BORDER)
draw.text((cv_x + 10 * S, cv_y + 5 * S), "certs-vol (shared volume)", fill=YELLOW, font=font_heading)
draw.text((cv_x + 10 * S, cv_y + 26 * S), "/etc/mcp/certs/server.crt", fill=CYAN, font=font_small)
draw.text((cv_x + 10 * S, cv_y + 39 * S), "/etc/mcp/certs/server.key", fill=CYAN, font=font_small)
draw.text((cv_x + 10 * S, cv_y + 52 * S), "/etc/mcp/certs/ca.crt", fill=CYAN, font=font_small)

# Step 6: Vault Agent renders templates to certs-vol
draw_arrow(va_x + 150 * S, va_y + 70 * S, cv_x + 130 * S, cv_y, color=ORANGE)
draw_circle_number(va_x + 100 * S, va_y + 82 * S, 6)
draw.text((va_x + 118 * S, va_y + 75 * S), "Render templates to", font=font_small, fill=GREEN)
draw.text((va_x + 118 * S, va_y + 88 * S), "shared volume", font=font_small, fill=GREEN)

# ═══════════════════════════════════════════════════════════════════════════
# Row 4: MCP Servers read from certs-vol
# ═══════════════════════════════════════════════════════════════════════════

# ─── Data MCP Server ───
dm_x, dm_y = 120 * S, 660 * S
draw_rounded_rect((dm_x, dm_y, dm_x + 240 * S, dm_y + 60 * S), fill=DARK_GREEN_BG, outline=CYAN)
text_centered(dm_x + 120 * S, dm_y + 8 * S, "data-mcp-server", font_heading, CYAN)
text_centered(dm_x + 120 * S, dm_y + 30 * S, ":8001  (mTLS enabled)", font_small, GREY)

# ─── Compute MCP Server ───
cm_x, cm_y = 530 * S, 660 * S
draw_rounded_rect((cm_x, cm_y, cm_x + 260 * S, cm_y + 60 * S), fill=DARK_GREEN_BG, outline=CYAN)
text_centered(cm_x + 130 * S, cm_y + 8 * S, "compute-mcp-server", font_heading, CYAN)
text_centered(cm_x + 130 * S, cm_y + 30 * S, ":8002  (mTLS enabled)", font_small, GREY)

# Step 7: certs-vol -> Data MCP (read-only mount)
draw_arrow(cv_x + 60 * S, cv_y + 70 * S, dm_x + 150 * S, dm_y, color=CYAN)
draw_circle_number(cv_x - 30 * S, cv_y + 80 * S, 7)
draw.text((cv_x - 12 * S, cv_y + 73 * S), "Mount :ro", font=font_small, fill=GREEN)

# Step 7b: certs-vol -> Compute MCP (read-only mount)
draw_arrow(cv_x + 200 * S, cv_y + 70 * S, cm_x + 100 * S, cm_y, color=CYAN)

# ─── _tls_available() callout ───
tls_x, tls_y = 830 * S, 490 * S
draw_dashed_rect((tls_x, tls_y, tls_x + 260 * S, tls_y + 70 * S), outline=DASHED_BORDER)
draw.text((tls_x + 10 * S, tls_y + 5 * S), "http_transport.py:", fill=YELLOW, font=font_heading)
draw.text((tls_x + 10 * S, tls_y + 26 * S), "_tls_available() checks for", fill=GREY, font=font_small)
draw.text((tls_x + 10 * S, tls_y + 39 * S), "all 3 cert files at startup", fill=GREY, font=font_small)
draw.text((tls_x + 10 * S, tls_y + 52 * S), "If found -> mTLS  |  Else -> HTTP", fill=GREEN, font=font_small)

# ═══════════════════════════════════════════════════════════════════════════
# Bottom: Automatic rotation
# ═══════════════════════════════════════════════════════════════════════════
rot_x, rot_y = 350 * S, 790 * S
draw_circle_number(rot_x, rot_y + 10 * S, 8)
draw.text((rot_x + 18 * S, rot_y - 2 * S), "Automatic SVID Rotation", fill=GREEN, font=font_heading)
draw.text((rot_x + 18 * S, rot_y + 16 * S), "Vault Agent re-renders templates before cert expiry", fill=GREY, font=font_small)
draw.text((rot_x + 18 * S, rot_y + 30 * S), "MCP servers pick up new certs — no restart required", fill=GREY, font=font_small)
draw.text((rot_x + 18 * S, rot_y + 44 * S), "On Kubernetes: Vault Agent Injector automates the same flow", fill=GREY, font=font_small)

# Save
out = os.path.join(os.path.dirname(__file__), "spiffe-svid-acquisition.png")
img.save(out, dpi=(300, 300))
print(f"Saved {W}x{H} image to {out}")
