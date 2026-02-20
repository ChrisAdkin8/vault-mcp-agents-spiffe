#!/usr/bin/env python3
"""Generate the Credential Exposure Without SPIFFE diagram."""

from PIL import Image, ImageDraw, ImageFont
import math
import os

S = 3
W, H = 1200 * S, 900 * S
BG = (30, 30, 30)
img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# Colours
CYAN = (0, 210, 230)
RED = (220, 80, 80)
RED_BG = (180, 60, 60)
GREEN = (80, 210, 170)
BLUE = (100, 160, 255)
ORANGE = (255, 165, 0)
YELLOW = (230, 210, 70)
WHITE = (240, 240, 240)
GREY = (160, 160, 160)
DARK_BG = (45, 45, 45)

# Fonts
try:
    font_title = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 20 * S)
    font_heading = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 16 * S)
    font_body = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12 * S)
    font_small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 10 * S)
    font_label = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 11 * S)
except Exception:
    font_title = ImageFont.load_default()
    font_heading = font_body = font_small = font_label = font_title


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
        # Draw dashed line
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
    # Arrowhead
    angle = math.atan2(y1 - y0, x1 - x0)
    lx = x1 - hs * math.cos(angle - 0.4)
    ly = y1 - hs * math.sin(angle - 0.4)
    rx = x1 - hs * math.cos(angle + 0.4)
    ry = y1 - hs * math.sin(angle + 0.4)
    draw.polygon([(x1, y1), (lx, ly), (rx, ry)], fill=color)


# ─── Outer border (Docker network) ───
border_x0, border_y0 = 40 * S, 30 * S
border_x1, border_y1 = 1160 * S, 870 * S
draw.rounded_rectangle(
    (border_x0, border_y0, border_x1, border_y1),
    radius=12 * S, fill=DARK_BG, outline=(80, 80, 80), width=2 * S
)
text_centered(W // 2, 40 * S, "Docker bridge network (mcp-net)", font_small, GREY)

# ─── Title area ───
text_centered(W // 2, 65 * S, "Credential Exposure Without SPIFFE", font_title, WHITE)
text_centered(W // 2, 92 * S, "X-Identity-Context header", font_label, YELLOW)
text_centered(W // 2, 108 * S, "human's Vault token in plaintext HTTP", font_small, ORANGE)

# ─── agent-cli box (top left) ───
ac_x, ac_y = 100 * S, 140 * S
draw_rounded_rect((ac_x, ac_y, ac_x + 250 * S, ac_y + 60 * S), fill=(0, 140, 160), outline=CYAN)
text_centered(ac_x + 125 * S, ac_y + 10 * S, "agent-cli", font_heading, WHITE)
text_centered(ac_x + 125 * S, ac_y + 34 * S, "(LangChain)", font_body, (220, 220, 220))

# ─── data-mcp-server box (top right) ───
ds_x, ds_y = 750 * S, 140 * S
draw_rounded_rect((ds_x, ds_y, ds_x + 300 * S, ds_y + 60 * S), fill=(0, 140, 160), outline=CYAN)
text_centered(ds_x + 150 * S, ds_y + 10 * S, "data-mcp-server", font_heading, WHITE)
text_centered(ds_x + 150 * S, ds_y + 34 * S, ":8001", font_body, (220, 220, 220))

# ─── Arrow: agent-cli -> data-mcp-server ───
draw_arrow(ac_x + 250 * S, ac_y + 30 * S, ds_x, ds_y + 30 * S, color=ORANGE, width=2)

# ─── Dashed arrow: intercepts token (down from midpoint of top arrow) ───
intercept_x = 500 * S
draw_arrow(intercept_x, ac_y + 60 * S + 15 * S, intercept_x, 300 * S, color=RED, width=2, dashed=True)
text_centered(intercept_x + 80 * S, 225 * S, "intercepts token", font_small, RED)
text_centered(intercept_x + 80 * S, 240 * S, "from network traffic", font_small, RED)

# ─── Compromised container box (centre) ───
cc_x, cc_y = 300 * S, 310 * S
draw_rounded_rect((cc_x, cc_y, cc_x + 350 * S, cc_y + 70 * S), fill=RED_BG, outline=RED)
text_centered(cc_x + 175 * S, cc_y + 12 * S, "Compromised container", font_heading, WHITE)
text_centered(cc_x + 175 * S, cc_y + 40 * S, "on same Docker network", font_body, (220, 200, 200))

# ─── Arrow: Compromised -> Vault (replays stolen token) ───
vault_x, vault_y = 380 * S, 570 * S
draw_arrow(cc_x + 130 * S, cc_y + 70 * S, vault_x + 80 * S, vault_y, color=RED, width=2)
draw.text((180 * S, 440 * S), "replays stolen", font=font_small, fill=ORANGE)
draw.text((180 * S, 455 * S), "token directly", font=font_small, fill=ORANGE)
draw.text((180 * S, 470 * S), "to Vault", font=font_small, fill=ORANGE)

# ─── Arrow: data-mcp-server -> Vault (legitimate request) ───
draw_arrow(ds_x + 150 * S, ds_y + 60 * S + 10 * S, vault_x + 250 * S, vault_y, color=CYAN, width=2)
draw.text((820 * S, 390 * S), "legitimate", font=font_small, fill=CYAN)
draw.text((820 * S, 405 * S), "request with", font=font_small, fill=CYAN)
draw.text((820 * S, 420 * S), "same token", font=font_small, fill=CYAN)

# ─── Vault box ───
draw_rounded_rect((vault_x, vault_y, vault_x + 350 * S, vault_y + 70 * S), fill=(30, 140, 110), outline=GREEN)
text_centered(vault_x + 175 * S, vault_y + 12 * S, "Vault", font_heading, WHITE)
text_centered(vault_x + 175 * S, vault_y + 38 * S, "(OSS)", font_body, (220, 220, 220))

# ─── "Vault sees identical tokens" callout ───
callout_x = 800 * S
draw.text((callout_x, vault_y + 5 * S), "Vault sees identical tokens", font=font_heading, fill=ORANGE)
draw.text((callout_x, vault_y + 30 * S), "No workload identity to verify", font=font_small, fill=GREY)
draw.text((callout_x, vault_y + 46 * S), "Cannot distinguish attacker", font=font_small, fill=GREY)
draw.text((callout_x, vault_y + 62 * S), "from legitimate MCP server", font=font_small, fill=GREY)

# ─── Arrow: Vault -> GCP APIs ───
gcp_x, gcp_y = 410 * S, 730 * S
draw_arrow(vault_x + 175 * S, vault_y + 70 * S, gcp_x + 140 * S, gcp_y, color=GREEN, width=2)

# ─── GCP APIs box ───
draw_rounded_rect((gcp_x, gcp_y, gcp_x + 280 * S, gcp_y + 60 * S), fill=(60, 100, 180), outline=BLUE)
text_centered(gcp_x + 140 * S, gcp_y + 15 * S, "GCP APIs", font_heading, WHITE)

# ─── Bottom text ───
text_centered(W // 2, 830 * S, "Attacker mints OAuth2 access tokens using the stolen human credential", font_label, ORANGE)

# Save
out = os.path.join(os.path.dirname(__file__), "credential-exposure-without-spiffe.png")
img.save(out, dpi=(300, 300))
print(f"Saved {W}x{H} image to {out}")
