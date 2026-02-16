#!/usr/bin/env python3
"""Generate the 'Why SPIFFE?' timeline diagram.

Mirrors the style of credential-threat-timeline.png:
  Top panel (red):   Without SPIFFE — unlimited impersonation window
  Bottom panel (green): With SPIFFE — cryptographic workload identity
"""

from PIL import Image, ImageDraw, ImageFont
import math
import os

# ── Scale & canvas ──────────────────────────────────────────────────────────
S = 3
W, H = 1200 * S, 950 * S
BG = (30, 30, 30)
img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# ── Colour palette ──────────────────────────────────────────────────────────
RED = (220, 80, 80)
RED_GLOW = (180, 50, 50)
RED_DIM = (120, 50, 50)
GREEN = (80, 210, 130)
GREEN_GLOW = (50, 160, 90)
GREEN_DIM = (40, 100, 60)
ORANGE = (255, 165, 0)
YELLOW = (230, 210, 70)
CYAN = (0, 210, 230)
WHITE = (240, 240, 240)
GREY = (160, 160, 160)
DARK_PANEL = (22, 22, 22)
MID_GREY = (55, 55, 55)
SHIELD_GREEN = (60, 180, 120)

# ── Fonts ───────────────────────────────────────────────────────────────────
try:
    font_title = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf", 18 * S
    )
    font_heading = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf", 14 * S
    )
    font_body = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Arial.ttf", 12 * S
    )
    font_small = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Arial.ttf", 10 * S
    )
    font_small_bold = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf", 10 * S
    )
    font_icon = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22 * S
    )
    font_vs = ImageFont.truetype(
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf", 14 * S
    )
except Exception:
    font_title = ImageFont.load_default()
    font_heading = font_body = font_small = font_small_bold = font_icon = font_vs = font_title


# ── Helpers ─────────────────────────────────────────────────────────────────
def text_centered(x, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((x - tw // 2, y), text, fill=fill, font=font)


def rounded_rect(xy, fill, outline, radius=10, width=2):
    draw.rounded_rectangle(
        xy, radius=radius * S, fill=fill, outline=outline, width=width * S
    )


def draw_arrow_right(x0, y, x1, color, width=3):
    """Horizontal arrow with filled head."""
    w = width * S
    hs = 10 * S
    draw.line([(x0, y), (x1 - hs, y)], fill=color, width=w)
    draw.polygon(
        [(x1, y), (x1 - hs, y - hs // 2), (x1 - hs, y + hs // 2)], fill=color
    )


def draw_cross(cx, cy, size, color):
    """Draw an X mark."""
    s = size * S
    w = 3 * S
    draw.line([(cx - s, cy - s), (cx + s, cy + s)], fill=color, width=w)
    draw.line([(cx - s, cy + s), (cx + s, cy - s)], fill=color, width=w)


def draw_check(cx, cy, size, color):
    """Draw a checkmark."""
    s = size * S
    w = 3 * S
    draw.line([(cx - s, cy), (cx - s // 3, cy + s)], fill=color, width=w)
    draw.line([(cx - s // 3, cy + s), (cx + s, cy - s + 2 * S)], fill=color, width=w)


def draw_shield(cx, cy, size, color):
    """Draw a simple shield icon."""
    s = size * S
    points = [
        (cx, cy - s),
        (cx + s, cy - s // 2),
        (cx + s, cy + s // 3),
        (cx, cy + s),
        (cx - s, cy + s // 3),
        (cx - s, cy - s // 2),
    ]
    draw.polygon(points, fill=None, outline=color, width=2 * S)


def draw_lock(cx, cy, size, color):
    """Draw a simple padlock icon."""
    s = size * S
    # Body
    bx0, by0 = cx - s, cy
    bx1, by1 = cx + s, cy + int(s * 1.3)
    draw.rounded_rectangle((bx0, by0, bx1, by1), radius=3 * S, fill=color)
    # Shackle
    r = int(s * 0.65)
    draw.arc(
        (cx - r, cy - int(s * 0.9), cx + r, cy + int(s * 0.2)),
        start=180,
        end=0,
        fill=color,
        width=3 * S,
    )


# ═══════════════════════════════════════════════════════════════════════════
# TOP PANEL — Without SPIFFE
# ═══════════════════════════════════════════════════════════════════════════
panel_pad = 30 * S
p1_x0, p1_y0 = panel_pad, panel_pad
p1_x1, p1_y1 = W - panel_pad, 420 * S
rounded_rect((p1_x0, p1_y0, p1_x1, p1_y1), fill=DARK_PANEL, outline=RED_DIM, radius=12, width=2)

# Title
text_centered(W // 2, p1_y0 + 14 * S, "WITHOUT SPIFFE: THE IMPERSONATION TIMELINE", font_title, RED)
text_centered(
    W // 2,
    p1_y0 + 42 * S,
    "Any container on the Docker network can steal and replay Vault tokens",
    font_small,
    GREY,
)

# Red attack bar
bar_y = p1_y0 + 80 * S
bar_x0 = 120 * S
bar_x1 = W - 120 * S
bar_h = 44 * S  # taller to fit text + arrows
draw.rounded_rectangle(
    (bar_x0, bar_y, bar_x1, bar_y + bar_h),
    radius=6 * S,
    fill=RED_GLOW,
    outline=RED,
    width=2 * S,
)
text_centered(
    W // 2, bar_y + 4 * S, "ATTACKER CAN IMPERSONATE MCP SERVER INDEFINITELY", font_small_bold, WHITE
)

# Arrow indicators on bar — below the text
for ax in range(bar_x0 + 60 * S, bar_x1 - 20 * S, 80 * S):
    draw_arrow_right(ax, bar_y + 30 * S, ax + 40 * S, RED, width=2)

# ── Timeline events (without SPIFFE) ──
events_y = bar_y + bar_h + 25 * S
event_positions = [
    (160 * S, "Minute 0", "Agent sends HTTP", "request with Vault", "token in header"),
    (380 * S, "Minute 1", "Rogue container", "sniffs token from", "Docker bridge"),
    (600 * S, "Minute 5", "Attacker replays", "token to Vault as", "the MCP server"),
    (820 * S, "Day 1+", "Attacker mints", "GCP credentials", "at will"),
    (1020 * S, "Day ???", "Still working —", "no identity check", "to revoke"),
]

for ex, label, l1, l2, l3 in event_positions:
    # Dot
    draw.ellipse(
        (ex - 6 * S, events_y - 6 * S, ex + 6 * S, events_y + 6 * S), fill=RED
    )
    # Vertical tick
    draw.line(
        [(ex, events_y + 6 * S), (ex, events_y + 20 * S)], fill=GREY, width=1 * S
    )
    # Label
    text_centered(ex, events_y + 22 * S, label, font_heading, ORANGE)
    text_centered(ex, events_y + 42 * S, l1, font_small, WHITE)
    text_centered(ex, events_y + 56 * S, l2, font_small, WHITE)
    text_centered(ex, events_y + 70 * S, l3, font_small, WHITE)

# Bottom callout — red
callout_y = p1_y1 - 48 * S
draw.rounded_rectangle(
    (80 * S, callout_y, W - 80 * S, callout_y + 32 * S),
    radius=6 * S,
    fill=(50, 20, 20),
    outline=RED_DIM,
    width=1 * S,
)
draw_cross(110 * S, callout_y + 16 * S, 7, RED)
draw.text(
    (135 * S, callout_y + 5 * S),
    "Unlimited impersonation window. ",
    font=font_heading,
    fill=RED,
)
draw.text(
    (530 * S, callout_y + 7 * S),
    "Vault cannot distinguish the attacker from the real workload.",
    font=font_body,
    fill=GREY,
)

# ═══════════════════════════════════════════════════════════════════════════
# VS divider
# ═══════════════════════════════════════════════════════════════════════════
vs_y = p1_y1 + 15 * S
rounded_rect(
    (W // 2 - 30 * S, vs_y, W // 2 + 30 * S, vs_y + 30 * S),
    fill=MID_GREY,
    outline=GREY,
    radius=6,
    width=1,
)
text_centered(W // 2, vs_y + 5 * S, "VS", font_vs, WHITE)

# ═══════════════════════════════════════════════════════════════════════════
# BOTTOM PANEL — With SPIFFE
# ═══════════════════════════════════════════════════════════════════════════
p2_y0 = vs_y + 50 * S
p2_y1 = H - panel_pad
rounded_rect(
    (panel_pad, p2_y0, W - panel_pad, p2_y1),
    fill=DARK_PANEL,
    outline=GREEN_DIM,
    radius=12,
    width=2,
)

# Title
draw_shield(130 * S, p2_y0 + 26 * S, 12, SHIELD_GREEN)
text_centered(
    W // 2, p2_y0 + 14 * S, "WITH SPIFFE: THE ZERO-TRUST TIMELINE", font_title, GREEN
)
text_centered(
    W // 2,
    p2_y0 + 42 * S,
    "Every workload gets an X.509 SVID — mTLS encrypts and authenticates all traffic",
    font_small,
    GREY,
)

# Green defence bar (short — 1 hour max)
bar2_y = p2_y0 + 80 * S
bar2_x0 = 120 * S
bar2_x1_cert = 520 * S  # 1-hour cert window
bar2_x1_full = W - 120 * S

# Short green bar (cert lifetime)
bar2_h = 44 * S  # taller to fit text + arrows
draw.rounded_rectangle(
    (bar2_x0, bar2_y, bar2_x1_cert, bar2_y + bar2_h),
    radius=6 * S,
    fill=GREEN_GLOW,
    outline=GREEN,
    width=2 * S,
)
text_centered(
    (bar2_x0 + bar2_x1_cert) // 2,
    bar2_y + 4 * S,
    "1 hr SVID (auto-rotated)",
    font_small_bold,
    WHITE,
)

# Grey bar (attacker locked out)
draw.rounded_rectangle(
    (bar2_x1_cert + 10 * S, bar2_y, bar2_x1_full, bar2_y + bar2_h),
    radius=6 * S,
    fill=MID_GREY,
    outline=GREY,
    width=1 * S,
)
text_centered(
    (bar2_x1_cert + 10 * S + bar2_x1_full) // 2,
    bar2_y + 4 * S,
    "Attacker never gains access",
    font_small_bold,
    GREY,
)

# Arrow indicators on green bar — below the text
for ax in range(bar2_x0 + 60 * S, bar2_x1_cert - 20 * S, 80 * S):
    draw_arrow_right(ax, bar2_y + 30 * S, ax + 40 * S, GREEN, width=2)

# ── Timeline events (with SPIFFE) ──
events2_y = bar2_y + bar2_h + 25 * S
events2 = [
    (160 * S, "Boot", "Vault Agent gets", "SVID via AppRole;", "mTLS enabled"),
    (380 * S, "Minute 1", "Attacker sniffs", "traffic — sees only", "encrypted TLS"),
    (600 * S, "Minute 2", "Attacker tries to", "connect — rejected,", "no valid SVID"),
    (820 * S, "Minute 30", "Vault Agent auto-", "rotates SVID;", "zero downtime"),
    (1020 * S, "Always", "SPIFFE ID maps to", "policy — only allowed", "tools exposed"),
]

for ex, label, l1, l2, l3 in events2:
    draw.ellipse(
        (ex - 6 * S, events2_y - 6 * S, ex + 6 * S, events2_y + 6 * S), fill=GREEN
    )
    draw.line(
        [(ex, events2_y + 6 * S), (ex, events2_y + 20 * S)], fill=GREY, width=1 * S
    )
    text_centered(ex, events2_y + 22 * S, label, font_heading, CYAN)
    text_centered(ex, events2_y + 42 * S, l1, font_small, WHITE)
    text_centered(ex, events2_y + 56 * S, l2, font_small, WHITE)
    text_centered(ex, events2_y + 70 * S, l3, font_small, WHITE)

# ── Three defence pillars ──
pillars_y = events2_y + 105 * S
pillar_data = [
    (250 * S, "mTLS on the wire", "Traffic encrypted; sniffing", "yields nothing usable"),
    (600 * S, "Cryptographic identity", "Rogue containers can't", "obtain a valid SVID"),
    (950 * S, "Policy-bound SPIFFE IDs", "Each SPIFFE ID maps to a", "scoped tool allowlist"),
]

for px, title, d1, d2 in pillar_data:
    bx0 = px - 130 * S
    bx1 = px + 130 * S
    by0 = pillars_y
    by1 = pillars_y + 68 * S
    rounded_rect((bx0, by0, bx1, by1), fill=(25, 50, 35), outline=GREEN_DIM, radius=8, width=1)
    draw_lock(px - 100 * S, by0 + 16 * S, 8, GREEN)
    text_centered(px + 10 * S, by0 + 8 * S, title, font_heading, GREEN)
    text_centered(px + 10 * S, by0 + 30 * S, d1, font_small, WHITE)
    text_centered(px + 10 * S, by0 + 44 * S, d2, font_small, WHITE)

# Bottom callout — green
callout2_y = p2_y1 - 48 * S
draw.rounded_rectangle(
    (80 * S, callout2_y, W - 80 * S, callout2_y + 32 * S),
    radius=6 * S,
    fill=(15, 40, 25),
    outline=GREEN_DIM,
    width=1 * S,
)
draw_check(110 * S, callout2_y + 16 * S, 7, GREEN)
draw.text(
    (135 * S, callout2_y + 5 * S),
    "Zero-trust workload identity. ",
    font=font_heading,
    fill=GREEN,
)
draw.text(
    (480 * S, callout2_y + 7 * S),
    "No valid SVID = no connection. Stolen certs expire in 1 hour.",
    font=font_body,
    fill=GREY,
)

# ═══════════════════════════════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════════════════════════════
out = os.path.join(os.path.dirname(__file__), "why-spiffe-timeline.png")
img.save(out, dpi=(300, 300))
print(f"Saved {W}x{H} image to {out}")
