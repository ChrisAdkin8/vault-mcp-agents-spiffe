#!/usr/bin/env python3
"""Generate the Architecture Annotated diagram.

Replaces the previously committed binary that showed a SPIRE agent.
The actual architecture uses a Vault Agent sidecar that renders X.509
SVIDs to a shared Docker volume (certs-vol).
"""

from PIL import Image, ImageDraw, ImageFont
import math
import os

S = 3
W, H = 1500 * S, 850 * S
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
PURPLE = (160, 120, 210)
DARK_GREEN_BG = (40, 60, 40)
DARK_YELLOW_BG = (60, 55, 30)
DARK_PURPLE_BG = (50, 40, 65)
DARK_BLUE_BG = (35, 50, 85)
BLUE = (100, 160, 255)
DASHED_BORDER = (120, 120, 60)

# Fonts
try:
    font_title = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 20 * S)
    font_heading = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 14 * S)
    font_body = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12 * S)
    font_small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 10 * S)
    font_circle = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 12 * S)
    font_layer = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 10 * S)
except Exception:
    font_title = ImageFont.load_default()
    font_heading = font_body = font_small = font_circle = font_layer = font_title


def draw_rounded_rect(xy, fill, outline, radius=8, width=2):
    draw.rounded_rectangle(xy, radius=radius * S, fill=fill, outline=outline, width=width * S)


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


# ─── Layer labels (left gutter) ───
def draw_layer_label(y, num, line1, line2=""):
    draw_circle_number(40 * S, y, num)
    draw.text((56 * S, y - 14 * S), line1, fill=WHITE, font=font_layer)
    if line2:
        draw.text((56 * S, y + 2 * S), line2, fill=WHITE, font=font_layer)


# ═══════════════════════════════════════════════════════════════════════════
# Layer 1: Human Auth
# ═══════════════════════════════════════════════════════════════════════════
layer1_y = 50 * S
draw_layer_label(layer1_y + 25 * S, 1, "HUMAN", "AUTH")

# Human box
hum_x, hum_y = 600 * S, 30 * S
draw_rounded_rect((hum_x, hum_y, hum_x + 300 * S, hum_y + 50 * S), fill=(50, 50, 50), outline=GREY)
text_centered(hum_x + 150 * S, hum_y + 6 * S, "Human", font_heading, WHITE)
text_centered(hum_x + 150 * S, hum_y + 26 * S, "CLI login (username / password)", font_small, GREY)

# Vault box
vault_x, vault_y = 575 * S, 110 * S
draw_rounded_rect((vault_x, vault_y, vault_x + 350 * S, vault_y + 50 * S), fill=DARK_YELLOW_BG, outline=YELLOW)
text_centered(vault_x + 175 * S, vault_y + 6 * S, "Vault", font_heading, YELLOW)
text_centered(vault_x + 175 * S, vault_y + 26 * S, "userpass auth -> Session + role + token", font_small, GREY)

# Arrow: Human -> Vault
draw_arrow(hum_x + 150 * S, hum_y + 50 * S, vault_x + 175 * S, vault_y, color=YELLOW)

# ═══════════════════════════════════════════════════════════════════════════
# Layer 2: Agent Identity
# ═══════════════════════════════════════════════════════════════════════════
layer2_y = 195 * S
draw_layer_label(layer2_y + 15 * S, 2, "AGENT", "IDENTITY")

# data_agent
da_x, da_y = 350 * S, 190 * S
draw_rounded_rect((da_x, da_y, da_x + 250 * S, da_y + 50 * S), fill=DARK_PURPLE_BG, outline=PURPLE)
text_centered(da_x + 125 * S, da_y + 6 * S, "data_agent", font_heading, PURPLE)
text_centered(da_x + 125 * S, da_y + 26 * S, "LangChain AgentExecutor", font_small, GREY)

# compute_agent
ca_x, ca_y = 900 * S, 190 * S
draw_rounded_rect((ca_x, ca_y, ca_x + 270 * S, ca_y + 50 * S), fill=DARK_PURPLE_BG, outline=PURPLE)
text_centered(ca_x + 135 * S, ca_y + 6 * S, "compute_agent", font_heading, PURPLE)
text_centered(ca_x + 135 * S, ca_y + 26 * S, "LangChain AgentExecutor", font_small, GREY)

# Arrows: Vault -> agents
draw_arrow(vault_x + 100 * S, vault_y + 50 * S, da_x + 125 * S, da_y, color=YELLOW)
draw_arrow(vault_x + 250 * S, vault_y + 50 * S, ca_x + 135 * S, ca_y, color=YELLOW)

# Transport labels
text_centered(da_x + 125 * S, da_y + 54 * S, "stdio / HTTP", font_small, GREY)
text_centered(ca_x + 135 * S, ca_y + 54 * S, "stdio / HTTP", font_small, GREY)

# ═══════════════════════════════════════════════════════════════════════════
# Layer 5: Workload Identity (Vault Agent + certs-vol)
# ═══════════════════════════════════════════════════════════════════════════
layer5_y = 290 * S
draw_layer_label(layer5_y + 15 * S, 5, "WORKLOAD", "IDENTITY")

# Vault Agent box
vagent_x, vagent_y = 560 * S, 280 * S
draw_rounded_rect((vagent_x, vagent_y, vagent_x + 380 * S, vagent_y + 50 * S), fill=DARK_YELLOW_BG, outline=ORANGE)
text_centered(vagent_x + 190 * S, vagent_y + 6 * S, "Vault Agent (sidecar)", font_heading, ORANGE)
text_centered(vagent_x + 190 * S, vagent_y + 26 * S, "AppRole auth -> PKI issue -> render SVIDs to certs-vol", font_small, GREY)

# certs-vol
cv_x, cv_y = 620 * S, 355 * S
draw_dashed_rect((cv_x, cv_y, cv_x + 260 * S, cv_y + 45 * S), outline=DASHED_BORDER)
text_centered(cv_x + 130 * S, cv_y + 5 * S, "certs-vol", font_heading, YELLOW)
text_centered(cv_x + 130 * S, cv_y + 24 * S, "/etc/mcp/certs/ (read-only mount)", font_small, GREY)

# Arrow: Vault Agent -> certs-vol
draw_arrow(vagent_x + 190 * S, vagent_y + 50 * S, cv_x + 130 * S, cv_y, color=ORANGE)

# "X.509 SVID" labels on the arrows from certs-vol to MCP servers
text_centered(da_x + 40 * S, cv_y + 55 * S, "X.509 SVID", font_small, CYAN)
text_centered(ca_x + 170 * S, cv_y + 55 * S, "X.509 SVID", font_small, CYAN)

# ═══════════════════════════════════════════════════════════════════════════
# Layer 4: Tool Access Control (MCP Servers)
# ═══════════════════════════════════════════════════════════════════════════
layer4_y = 430 * S
draw_layer_label(layer4_y + 15 * S, 4, "TOOL ACCESS", "CONTROL")

# Data MCP Server
dms_x, dms_y = 280 * S, 425 * S
draw_rounded_rect((dms_x, dms_y, dms_x + 280 * S, dms_y + 50 * S), fill=DARK_GREEN_BG, outline=CYAN)
text_centered(dms_x + 140 * S, dms_y + 6 * S, "Data MCP Server", font_heading, CYAN)
text_centered(dms_x + 140 * S, dms_y + 26 * S, "GCS + BigQuery tools", font_small, GREY)

# Compute MCP Server
cms_x, cms_y = 940 * S, 425 * S
draw_rounded_rect((cms_x, cms_y, cms_x + 280 * S, cms_y + 50 * S), fill=DARK_GREEN_BG, outline=CYAN)
text_centered(cms_x + 140 * S, cms_y + 6 * S, "Compute MCP Server", font_heading, CYAN)
text_centered(cms_x + 140 * S, cms_y + 26 * S, "GCE instance tools", font_small, GREY)

# Arrows: certs-vol -> MCP servers
draw_arrow(cv_x + 40 * S, cv_y + 45 * S, dms_x + 200 * S, dms_y, color=CYAN)
draw_arrow(cv_x + 220 * S, cv_y + 45 * S, cms_x + 80 * S, cms_y, color=CYAN)

# Policy Engine callout (left of Data MCP)
pe_x, pe_y = 150 * S, 490 * S
draw_dashed_rect((pe_x, pe_y, pe_x + 200 * S, pe_y + 40 * S), outline=DASHED_BORDER)
text_centered(pe_x + 100 * S, pe_y + 5 * S, "Policy Engine", font_heading, YELLOW)
text_centered(pe_x + 100 * S, pe_y + 22 * S, "capabilities.yaml", font_small, GREY)

# Tools filtered callout (right of Compute MCP)
tf_x, tf_y = 1150 * S, 490 * S
draw_dashed_rect((tf_x, tf_y, tf_x + 230 * S, tf_y + 40 * S), outline=DASHED_BORDER)
text_centered(tf_x + 115 * S, tf_y + 5 * S, "Tools filtered by", font_heading, YELLOW)
text_centered(tf_x + 115 * S, tf_y + 22 * S, "(role, agent_id)", font_small, GREY)

# ═══════════════════════════════════════════════════════════════════════════
# Layer 3: GCP Credential Issuance
# ═══════════════════════════════════════════════════════════════════════════
layer3_y = 570 * S
draw_layer_label(layer3_y + 15 * S, 3, "GCP CREDENTIAL", "ISSUANCE")

# Vault GCP Secrets Engine
gcp_vault_x, gcp_vault_y = 500 * S, 565 * S
draw_rounded_rect(
    (gcp_vault_x, gcp_vault_y, gcp_vault_x + 500 * S, gcp_vault_y + 50 * S),
    fill=DARK_YELLOW_BG, outline=YELLOW,
)
text_centered(gcp_vault_x + 250 * S, gcp_vault_y + 6 * S, "Vault GCP Secrets Engine", font_heading, YELLOW)
text_centered(gcp_vault_x + 250 * S, gcp_vault_y + 26 * S, "OAuth2 access tokens — max lease 5 min", font_small, GREY)

# TTL callout
ttl_x, ttl_y = 1060 * S, 565 * S
draw_dashed_rect((ttl_x, ttl_y, ttl_x + 190 * S, ttl_y + 50 * S), outline=(0, 160, 80))
draw.text((ttl_x + 10 * S, ttl_y + 5 * S), "TTL ceiling: 300s", fill=GREEN, font=font_heading)
draw.text((ttl_x + 10 * S, ttl_y + 26 * S), "enforced by Vault", fill=GREY, font=font_small)

# Arrows: MCP servers -> GCP Secrets Engine
draw_arrow(dms_x + 140 * S, dms_y + 50 * S, gcp_vault_x + 100 * S, gcp_vault_y, color=YELLOW)
draw_arrow(cms_x + 140 * S, cms_y + 50 * S, gcp_vault_x + 400 * S, gcp_vault_y, color=YELLOW)

# ═══════════════════════════════════════════════════════════════════════════
# GCP APIs
# ═══════════════════════════════════════════════════════════════════════════
gcp_x, gcp_y = 550 * S, 680 * S
draw_rounded_rect(
    (gcp_x, gcp_y, gcp_x + 400 * S, gcp_y + 55 * S),
    fill=DARK_BLUE_BG, outline=BLUE,
)
text_centered(gcp_x + 200 * S, gcp_y + 6 * S, "GCP APIs", font_heading, BLUE)
text_centered(gcp_x + 200 * S, gcp_y + 26 * S, "Cloud Storage — BigQuery — Compute Engine", font_small, GREY)

# Arrow: GCP Secrets Engine -> GCP APIs
draw_arrow(gcp_vault_x + 250 * S, gcp_vault_y + 50 * S, gcp_x + 200 * S, gcp_y, color=GREEN)

# Save
out = os.path.join(os.path.dirname(__file__), "architecture-annotated.png")
img.save(out, dpi=(300, 300))
print(f"Saved {W}x{H} image to {out}")
