#!/usr/bin/env python3
"""Generate the Secret Zero Problem diagram."""

from PIL import Image, ImageDraw, ImageFont
import math
import os

S = 3
W, H = 1200 * S, 700 * S
BG = (30, 30, 30)
img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# Colours
CYAN = (0, 210, 230)
RED = (220, 80, 80)
RED_BG = (140, 50, 50)
GREEN = (80, 210, 170)
ORANGE = (255, 165, 0)
YELLOW = (230, 210, 70)
WHITE = (240, 240, 240)
GREY = (160, 160, 160)
DIM_GREY = (120, 120, 120)

# Fonts
try:
    font_title = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22 * S)
    font_heading = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 16 * S)
    font_body = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13 * S)
    font_small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 11 * S)
    font_question = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 50 * S)
    font_q_heading = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 18 * S)
    font_bottom = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 13 * S)
except Exception:
    font_title = ImageFont.load_default()
    font_heading = font_body = font_small = font_question = font_q_heading = font_bottom = font_title


def text_centered(x, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((x - tw / 2, y), text, fill=fill, font=font)


def draw_rounded_rect(xy, fill, outline, radius=10, width=2):
    draw.rounded_rectangle(xy, radius=radius * S, fill=fill, outline=outline, width=width * S)


def draw_arrow(x0, y0, x1, y1, color=GREY, width=2, head_size=10):
    w = width * S
    hs = head_size * S
    draw.line([(x0, y0), (x1, y1)], fill=color, width=w)
    angle = math.atan2(y1 - y0, x1 - x0)
    lx = x1 - hs * math.cos(angle - 0.4)
    ly = y1 - hs * math.sin(angle - 0.4)
    rx = x1 - hs * math.cos(angle + 0.4)
    ry = y1 - hs * math.sin(angle + 0.4)
    draw.polygon([(x1, y1), (lx, ly), (rx, ry)], fill=color)


def draw_dashed_line_v(x, y0, y1, color, width=1):
    """Draw a vertical dashed line."""
    w = width * S
    dash = 8 * S
    gap = 6 * S
    y = y0
    while y < y1:
        ey = min(y + dash, y1)
        draw.line([(x, y), (x, ey)], fill=color, width=w)
        y += dash + gap


# ─── Title ───
text_centered(W // 2, 25 * S, "The Secret Zero Problem", font_title, WHITE)

# ─── Workload box (top left) ───
wl_x, wl_y = 80 * S, 80 * S
draw_rounded_rect((wl_x, wl_y, wl_x + 300 * S, wl_y + 65 * S), fill=(0, 140, 160), outline=CYAN)
text_centered(wl_x + 150 * S, wl_y + 10 * S, "Workload", font_heading, WHITE)
text_centered(wl_x + 150 * S, wl_y + 36 * S, "(container)", font_body, (220, 220, 220))

# ─── Vault box (top right) ───
v_x, v_y = 820 * S, 80 * S
draw_rounded_rect((v_x, v_y, v_x + 300 * S, v_y + 65 * S), fill=(30, 140, 110), outline=GREEN)
text_centered(v_x + 150 * S, v_y + 10 * S, "Vault", font_heading, WHITE)
text_centered(v_x + 150 * S, v_y + 36 * S, "(secrets manager)", font_body, (220, 220, 220))

# ─── Arrow: Workload -> Vault ───
draw_arrow(wl_x + 300 * S, wl_y + 30 * S, v_x, v_y + 30 * S, color=ORANGE, width=2)
text_centered(W // 2, wl_y + 5 * S, "must authenticate to access secrets", font_small, ORANGE)

# ─── Red return box (indicating circular dependency) ───
ret_y_top = wl_y + 65 * S + 15 * S
ret_y_bot = ret_y_top + 100 * S
# Draw the L-shaped red arrow: from Vault area down and left back to Workload
# Right vertical
draw.line([(v_x, ret_y_top - 15 * S), (v_x, ret_y_bot)], fill=RED, width=2 * S)
# Bottom horizontal
draw.line([(wl_x + 10 * S, ret_y_bot), (v_x, ret_y_bot)], fill=RED, width=2 * S)
# Left vertical going up with arrowhead
draw_arrow(wl_x + 10 * S, ret_y_bot, wl_x + 10 * S, wl_y + 65 * S + 5 * S, color=RED, width=2)
text_centered(W // 2, ret_y_bot + 12 * S, "but authentication requires a credential", font_small, ORANGE)

# ─── Question mark ───
qm_y = ret_y_bot + 50 * S
text_centered(W // 2, qm_y, "?", font_question, YELLOW)

# ─── "Where does Secret Zero live?" ───
wh_y = qm_y + 70 * S
text_centered(W // 2, wh_y, "Where does Secret Zero live?", font_q_heading, ORANGE)

# ─── Four option boxes ───
box_w = 230 * S
box_h = 60 * S
box_y = wh_y + 50 * S
gap = 30 * S
total_w = 4 * box_w + 3 * gap
start_x = (W - total_w) // 2

options = [
    ("Hardcoded", "in source code", "leaked via", "git push"),
    ("Environment", "variable", "visible via", "docker inspect"),
    ("Config file", "on disk", "readable by", "any process"),
    ("Baked into", "container image", "extractable", "via docker pull"),
]

for i, (title, subtitle, risk1, risk2) in enumerate(options):
    bx = start_x + i * (box_w + gap)
    draw_rounded_rect((bx, box_y, bx + box_w, box_y + box_h), fill=RED_BG, outline=RED, radius=8)
    text_centered(bx + box_w // 2, box_y + 12 * S, title, font_heading, WHITE)
    text_centered(bx + box_w // 2, box_y + 36 * S, subtitle, font_body, (220, 200, 200))

    # Dashed line above each box
    draw_dashed_line_v(bx + box_w // 2, box_y - 30 * S, box_y, GREY)

    # Risk text below
    text_centered(bx + box_w // 2, box_y + box_h + 12 * S, risk1, font_small, ORANGE)
    text_centered(bx + box_w // 2, box_y + box_h + 28 * S, risk2, font_small, ORANGE)

# ─── Bottom summary ───
summary_y = box_y + box_h + 65 * S
text_centered(W // 2, summary_y, "Every approach requires a static, long-lived secret", font_bottom, WHITE)
text_centered(W // 2, summary_y + 22 * S, "that can be intercepted, extracted, or stolen", font_bottom, WHITE)

# ─── Final note ───
text_centered(W // 2, summary_y + 60 * S,
              "The circular dependency has no solution without an external trust anchor",
              font_small, DIM_GREY)

# Save
out = os.path.join(os.path.dirname(__file__), "secret-zero-problem.png")
img.save(out, dpi=(300, 300))
print(f"Saved {W}x{H} image to {out}")
