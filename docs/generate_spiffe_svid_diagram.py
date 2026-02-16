#!/usr/bin/env python3
"""Generate the SPIFFE SVID Acquisition Flow diagram."""

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
DASHED_BORDER = (120, 120, 60)

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
    # Top edge
    x = x0
    while x < x1:
        draw.line([(x, y0), (min(x + dl, x1), y0)], fill=outline, width=w)
        x += dl + gl
    # Bottom edge
    x = x0
    while x < x1:
        draw.line([(x, y1), (min(x + dl, x1), y1)], fill=outline, width=w)
        x += dl + gl
    # Left edge
    y = y0
    while y < y1:
        draw.line([(x0, y), (x0, min(y + dl, y1))], fill=outline, width=w)
        y += dl + gl
    # Right edge
    y = y0
    while y < y1:
        draw.line([(x1, y), (x1, min(y + dl, y1))], fill=outline, width=w)
        y += dl + gl


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


# Helper: scale coordinates
def s(*vals):
    return tuple(v * S for v in vals)


# ─── Title ───
text_centered(W // 2, 20 * S, "SPIFFE SVID Acquisition Flow", font_title, WHITE)
text_centered(W // 2, 50 * S, "vault-mcp-agents-spiffe  -  How MCP Server workloads obtain X.509 SVIDs", font_subtitle, GREY)

# ─── MCP Server box (top left) ───
mcp_x, mcp_y = 80 * S, 100 * S
draw_rounded_rect((mcp_x, mcp_y, mcp_x + 180 * S, mcp_y + 55 * S), fill=DARK_GREEN_BG, outline=CYAN)
text_centered(mcp_x + 90 * S, mcp_y + 8 * S, "MCP Server", font_heading, CYAN)
text_centered(mcp_x + 90 * S, mcp_y + 30 * S, "data / compute workload", font_small, GREY)

# ─── SPIRE Agent box (top right) ───
sa_x, sa_y = 880 * S, 100 * S
draw_rounded_rect((sa_x, sa_y, sa_x + 180 * S, sa_y + 55 * S), fill=DARK_GREEN_BG, outline=CYAN)
text_centered(sa_x + 90 * S, sa_y + 8 * S, "SPIRE Agent", font_heading, CYAN)
text_centered(sa_x + 90 * S, sa_y + 30 * S, "Node-level daemon", font_small, GREY)

# ─── Arrow: MCP Server -> SPIRE Agent (step 1) ───
draw_arrow(mcp_x + 180 * S, mcp_y + 27 * S, sa_x, sa_y + 27 * S, color=GREY)
# Step 1 circle - positioned above the arrow line
text_centered(W // 2, 88 * S, "Connect via Workload API", font_small, GREEN)
draw_circle_number(W // 2 - 110 * S, 96 * S, 1)
text_centered(W // 2, 100 * S, "unix:///run/spire/agent/agent.sock", font_small, GREY)

# ─── Workload Attestation box (dashed, right side) ───
wa_x, wa_y = 870 * S, 175 * S
draw_dashed_rect((wa_x, wa_y, wa_x + 230 * S, wa_y + 70 * S), outline=DASHED_BORDER)
draw.text((wa_x + 10 * S, wa_y + 5 * S), "Workload Attestation", fill=YELLOW, font=font_heading)
draw.text((wa_x + 10 * S, wa_y + 24 * S), "SPIRE Agent verifies caller:", fill=GREY, font=font_small)
draw.text((wa_x + 10 * S, wa_y + 37 * S), "Docker labels / k8s selectors", fill=GREY, font=font_small)
draw.text((wa_x + 10 * S, wa_y + 50 * S), "Process UID/GID, binary hash", fill=GREY, font=font_small)

# Step 2 circle - left of the attestation box
draw_circle_number(wa_x - 20 * S, wa_y + 15 * S, 2)
draw.text((wa_x - 115 * S, wa_y + 6 * S), "Attest workload", font=font_small, fill=GREEN)

# Step 3 - Request SVID (below attestation box)
draw_circle_number(wa_x + 115 * S, wa_y + 85 * S, 3, color=ORANGE)
draw.text((wa_x + 132 * S, wa_y + 78 * S), "Request SVID", font=font_small, fill=GREEN)

# ─── SPIRE Server box (centre) ───
ss_x, ss_y = 460 * S, 310 * S
draw_rounded_rect((ss_x, ss_y, ss_x + 220 * S, ss_y + 60 * S), fill=DARK_YELLOW_BG, outline=YELLOW)
text_centered(ss_x + 110 * S, ss_y + 8 * S, "SPIRE Server", font_heading, YELLOW)
text_centered(ss_x + 110 * S, ss_y + 28 * S, "Central trust authority", font_small, GREY)
text_centered(ss_x + 110 * S, ss_y + 42 * S, "Signs X.509 certs to matching", font_small, GREY)

# Arrow: SPIRE Agent -> SPIRE Server
draw_arrow(sa_x + 40 * S, sa_y + 55 * S, ss_x + 160 * S, ss_y, color=GREY)

# ─── Registration Entry box (dashed, right) ───
re_x, re_y = 820 * S, 310 * S
draw_dashed_rect((re_x, re_y, re_x + 230 * S, re_y + 65 * S), outline=DASHED_BORDER)
draw.text((re_x + 10 * S, re_y + 5 * S), "Registration Entry", fill=YELLOW, font=font_heading)
draw.text((re_x + 10 * S, re_y + 24 * S), "SPIFFE ID:", fill=GREY, font=font_small)
draw.text((re_x + 10 * S, re_y + 37 * S), "spiffe://vault-mcp-demo/", fill=CYAN, font=font_small)
draw.text((re_x + 10 * S, re_y + 50 * S), "agent/data_agent", fill=CYAN, font=font_small)

# Step 4 - Validate registration entry
draw_arrow(ss_x + 220 * S, ss_y + 30 * S, re_x, re_y + 30 * S, color=GREY)
draw_circle_number(ss_x + 235 * S, ss_y - 5 * S, 4)
draw.text((ss_x + 250 * S, ss_y - 12 * S), "Validate registration", font=font_small, fill=GREEN)
draw.text((ss_x + 250 * S, ss_y + 1 * S), "entry", font=font_small, fill=GREEN)

# ─── X.509 SVID box (left) ───
svid_x, svid_y = 60 * S, 400 * S
draw_rounded_rect((svid_x, svid_y, svid_x + 250 * S, svid_y + 75 * S), fill=DARK_GREEN_BG, outline=CYAN)
draw.text((svid_x + 10 * S, svid_y + 8 * S), "X.509 SVID", fill=CYAN, font=font_heading)
draw.text((svid_x + 10 * S, svid_y + 27 * S), "SAN: spiffe://vault-mcp-demo/", fill=GREY, font=font_small)
draw.text((svid_x + 10 * S, svid_y + 40 * S), "       agent/data_agent", fill=GREY, font=font_small)
draw.text((svid_x + 10 * S, svid_y + 55 * S), "Private key  +  Trust bundle", fill=GREY, font=font_small)

# Step 5 - SVID issued (arrow from SPIRE Server to X.509 SVID)
draw_arrow(ss_x + 30 * S, ss_y + 60 * S, svid_x + 200 * S, svid_y, color=GREY)
draw_circle_number(ss_x - 100 * S, ss_y + 55 * S, 5)
draw.text((ss_x - 85 * S, ss_y + 48 * S), "SVID issued", font=font_small, fill=GREEN)

# ─── Vault Enterprise box (centre bottom) ───
ve_x, ve_y = 400 * S, 560 * S
draw_rounded_rect((ve_x, ve_y, ve_x + 260 * S, ve_y + 65 * S), fill=DARK_YELLOW_BG, outline=YELLOW)
text_centered(ve_x + 130 * S, ve_y + 8 * S, "Vault Enterprise", font_heading, YELLOW)
text_centered(ve_x + 130 * S, ve_y + 28 * S, "SPIFFE auth method", font_small, GREY)
text_centered(ve_x + 130 * S, ve_y + 42 * S, "Cert chain validation + role matching", font_small, GREY)

# Step 6 - Login with cert + key (arrow from X.509 SVID to Vault)
draw_arrow(svid_x + 125 * S, svid_y + 75 * S, ve_x + 80 * S, ve_y, color=GREY)
draw_circle_number(svid_x + 30 * S, svid_y + 100 * S, 6)
draw.text((svid_x + 47 * S, svid_y + 93 * S), "Login with cert + key", font=font_small, fill=GREEN)

# ─── Vault Validates box (dashed, right) ───
vv_x, vv_y = 800 * S, 550 * S
draw_dashed_rect((vv_x, vv_y, vv_x + 280 * S, vv_y + 80 * S), outline=DASHED_BORDER)
draw.text((vv_x + 10 * S, vv_y + 5 * S), "Vault Validates:", fill=YELLOW, font=font_heading)
draw.text((vv_x + 10 * S, vv_y + 24 * S), "1. Cert chain against SPIRE CA", fill=GREY, font=font_small)
draw.text((vv_x + 10 * S, vv_y + 39 * S), "2. SPIFFE ID from SAN extension", fill=GREY, font=font_small)
draw.text((vv_x + 10 * S, vv_y + 54 * S), "3. Match role -> issue token + policies", fill=GREY, font=font_small)

# Arrow: Vault -> Vault Validates
draw_arrow(ve_x + 260 * S, ve_y + 30 * S, vv_x, vv_y + 30 * S, color=GREY)

# ─── WorkloadSession box (bottom centre) ───
ws_x, ws_y = 380 * S, 720 * S
draw_rounded_rect((ws_x, ws_y, ws_x + 340 * S, ws_y + 60 * S), fill=DARK_YELLOW_BG, outline=ORANGE)
text_centered(ws_x + 170 * S, ws_y + 8 * S, "WorkloadSession", font_heading, ORANGE)
text_centered(ws_x + 170 * S, ws_y + 28 * S, "spiffe_id + vault_token + policies", font_small, GREY)
text_centered(ws_x + 170 * S, ws_y + 42 * S, "token_ttl=3600s  |  policies=[operator-policy]", font_small, GREY)

# Step 7 - Session created (arrow from Vault to WorkloadSession)
draw_arrow(ve_x + 130 * S, ve_y + 65 * S, ws_x + 170 * S, ws_y, color=GREY)
draw_circle_number(ve_x + 145 * S, ve_y + 82 * S, 7)
draw.text((ve_x + 162 * S, ve_y + 75 * S), "Session created", font=font_small, fill=GREEN)
draw.text((ve_x + 162 * S, ve_y + 88 * S), "Ready for GCP requests", font=font_small, fill=GREY)

# ─── Automatic SVID Rotation (bottom) ───
rot_x, rot_y = 420 * S, 810 * S
draw_circle_number(rot_x, rot_y + 10 * S, 8)
draw.text((rot_x + 18 * S, rot_y - 2 * S), "Automatic SVID Rotation", fill=GREEN, font=font_heading)
draw.text((rot_x + 18 * S, rot_y + 16 * S), "On token expiry, re-fetch from step 1", fill=GREY, font=font_small)
draw.text((rot_x + 18 * S, rot_y + 30 * S), "No restarts, hot SVID rotation", fill=GREY, font=font_small)

# Save
out = os.path.join(os.path.dirname(__file__), "spiffe-svid-acquisition.png")
img.save(out, dpi=(300, 300))
print(f"Saved {W}x{H} image to {out}")
