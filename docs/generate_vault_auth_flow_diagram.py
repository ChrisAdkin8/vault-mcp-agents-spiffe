#!/usr/bin/env python3
"""Generate the Vault Authentication Flow for GCP Credentials diagram."""

from PIL import Image, ImageDraw, ImageFont
import math
import os

S = 3
W, H = 1400 * S, 1600 * S
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
text_centered(W // 2, 30 * S, "Vault Authentication Flow for GCP Credentials", font_title, WHITE)
text_centered(W // 2, 60 * S, "End-to-end: Human login → Policy resolution → GCP token issuance", font_body, GREY)

# ═══════════════════════════════════════════════════════════════
# PHASE 1: HUMAN LOGIN
# ═══════════════════════════════════════════════════════════════
phase1_y = 110 * S
draw.rounded_rectangle(
    (40 * S, phase1_y, 1360 * S, phase1_y + 250 * S),
    radius=12 * S, fill=DARK_BG, outline=(60, 60, 70), width=2 * S
)
draw_circle_number(80 * S, phase1_y + 25 * S, 1)
draw.text((100 * S, phase1_y + 12 * S), "HUMAN LOGIN", font=font_heading, fill=ORANGE)
draw.text((100 * S, phase1_y + 36 * S), "User authenticates via Vault userpass/LDAP/OIDC", font=font_small, fill=GREY)

# Human box
hx, hy = 100 * S, phase1_y + 70 * S
draw_rounded_rect((hx, hy, hx + 200 * S, hy + 80 * S), fill=DARK_CYAN_BG, outline=CYAN)
text_centered(hx + 100 * S, hy + 12 * S, "Human", font_heading, WHITE)
text_centered(hx + 100 * S, hy + 38 * S, "username", font_body, CYAN)
text_centered(hx + 100 * S, hy + 55 * S, "password", font_body, CYAN)

# VaultAuthenticator box
va_x, va_y = 430 * S, phase1_y + 70 * S
draw_rounded_rect((va_x, va_y, va_x + 280 * S, va_y + 80 * S), fill=DARK_MAGENTA_BG, outline=MAGENTA)
text_centered(va_x + 140 * S, va_y + 12 * S, "VaultAuthenticator", font_heading, WHITE)
text_centered(va_x + 140 * S, va_y + 38 * S, "hvac.auth.userpass", font_code, MAGENTA)
text_centered(va_x + 140 * S, va_y + 55 * S, ".login()", font_code, MAGENTA)

# Vault server box
vs_x, vs_y = 850 * S, phase1_y + 70 * S
draw_rounded_rect((vs_x, vs_y, vs_x + 280 * S, vs_y + 80 * S), fill=DARK_GREEN_BG, outline=GREEN)
text_centered(vs_x + 140 * S, vs_y + 12 * S, "Vault Server", font_heading, WHITE)
text_centered(vs_x + 140 * S, vs_y + 38 * S, "auth/userpass", font_code, GREEN)
text_centered(vs_x + 140 * S, vs_y + 55 * S, "returns token + policies", font_small, GREEN)

# Arrows
draw_arrow(hx + 200 * S, hy + 40 * S, va_x, va_y + 40 * S, color=CYAN, width=2)
draw_arrow(va_x + 280 * S, va_y + 40 * S, vs_x, vs_y + 40 * S, color=MAGENTA, width=2)

# Session box (result)
sess_x, sess_y = 250 * S, phase1_y + 180 * S
draw_rounded_rect((sess_x, sess_y, sess_x + 900 * S, sess_y + 50 * S), fill=(35, 35, 50), outline=YELLOW, width=1)
draw.text((sess_x + 15 * S, sess_y + 8 * S), "Session created:", font=font_label, fill=YELLOW)
draw.text((sess_x + 160 * S, sess_y + 8 * S), "human_id", font=font_code, fill=WHITE)
draw.text((sess_x + 160 * S, sess_y + 25 * S), "= \"alice\"", font=font_code, fill=GREY)
draw.text((sess_x + 320 * S, sess_y + 8 * S), "human_role", font=font_code, fill=WHITE)
draw.text((sess_x + 320 * S, sess_y + 25 * S), "= \"operator\"", font=font_code, fill=GREY)
draw.text((sess_x + 510 * S, sess_y + 8 * S), "vault_token", font=font_code, fill=WHITE)
draw.text((sess_x + 510 * S, sess_y + 25 * S), "= \"hvs.xxx...\"", font=font_code, fill=GREY)
draw.text((sess_x + 710 * S, sess_y + 8 * S), "ttl_seconds", font=font_code, fill=WHITE)
draw.text((sess_x + 710 * S, sess_y + 25 * S), "= 3600", font=font_code, fill=GREY)

# Arrow down from Vault
draw_arrow(vs_x + 140 * S, vs_y + 80 * S, sess_x + 450 * S, sess_y, color=GREEN, width=2)

# ═══════════════════════════════════════════════════════════════
# PHASE 2: POLICY RESOLUTION & IDENTITY CONTEXT
# ═══════════════════════════════════════════════════════════════
phase2_y = 400 * S
draw.rounded_rectangle(
    (40 * S, phase2_y, 1360 * S, phase2_y + 320 * S),
    radius=12 * S, fill=DARK_BG, outline=(60, 60, 70), width=2 * S
)
draw_circle_number(80 * S, phase2_y + 25 * S, 2)
draw.text((100 * S, phase2_y + 12 * S), "POLICY RESOLUTION & IDENTITY CONTEXT", font=font_heading, fill=ORANGE)
draw.text((100 * S, phase2_y + 36 * S), "Agent factory resolves allowed tools and builds composite identity", font=font_small, fill=GREY)

# PolicyEngine box
pe_x, pe_y = 100 * S, phase2_y + 75 * S
draw_rounded_rect((pe_x, pe_y, pe_x + 300 * S, pe_y + 100 * S), fill=DARK_ORANGE_BG, outline=ORANGE)
text_centered(pe_x + 150 * S, pe_y + 10 * S, "PolicyEngine", font_heading, WHITE)
text_centered(pe_x + 150 * S, pe_y + 35 * S, "resolve(role, agent_id)", font_code, ORANGE)
draw.text((pe_x + 15 * S, pe_y + 60 * S), "capabilities.yaml", font=font_code, fill=GREY)
draw.text((pe_x + 15 * S, pe_y + 77 * S), "(role, agent) \u2192 tools + TTL", font=font_small, fill=GREY)

# capabilities.yaml visual
cap_x, cap_y = 100 * S, phase2_y + 200 * S
draw_rounded_rect((cap_x, cap_y, cap_x + 300 * S, cap_y + 95 * S), fill=(30, 30, 35), outline=(80, 80, 90), width=1)
draw.text((cap_x + 10 * S, cap_y + 5 * S), "operator:", font=font_code, fill=YELLOW)
draw.text((cap_x + 10 * S, cap_y + 22 * S), "  data_agent:", font=font_code, fill=WHITE)
draw.text((cap_x + 10 * S, cap_y + 39 * S), "    allowed_tools:", font=font_code, fill=CYAN)
draw.text((cap_x + 10 * S, cap_y + 56 * S), "      [list, read, write...]", font=font_code, fill=GREY)
draw.text((cap_x + 10 * S, cap_y + 73 * S), "    max_gcp_token_ttl: \"5m\"", font=font_code, fill=GREEN)

# Arrow up from capabilities to PolicyEngine
draw_arrow(cap_x + 150 * S, cap_y, pe_x + 150 * S, pe_y + 100 * S, color=(80, 80, 90), width=1, dashed=True)

# IdentityContext box
ic_x, ic_y = 530 * S, phase2_y + 75 * S
draw_rounded_rect((ic_x, ic_y, ic_x + 380 * S, ic_y + 100 * S), fill=DARK_CYAN_BG, outline=CYAN)
text_centered(ic_x + 190 * S, ic_y + 10 * S, "IdentityContext", font_heading, WHITE)
draw.text((ic_x + 15 * S, ic_y + 38 * S), "agent_id", font=font_code, fill=CYAN)
draw.text((ic_x + 130 * S, ic_y + 38 * S), "human_role", font=font_code, fill=CYAN)
draw.text((ic_x + 260 * S, ic_y + 38 * S), "vault_token", font=font_code, fill=CYAN)
draw.text((ic_x + 15 * S, ic_y + 58 * S), "allowed_tools", font=font_code, fill=CYAN)
draw.text((ic_x + 175 * S, ic_y + 58 * S), "max_gcp_token_ttl", font=font_code, fill=CYAN)
draw.text((ic_x + 15 * S, ic_y + 78 * S), "gcp_impersonated_account", font=font_code, fill=CYAN)

# Arrow from PolicyEngine to IdentityContext
draw_arrow(pe_x + 300 * S, pe_y + 50 * S, ic_x, ic_y + 50 * S, color=ORANGE, width=2)

# Transport box
tr_x, tr_y = 530 * S, phase2_y + 210 * S
draw_rounded_rect((tr_x, tr_y, tr_x + 380 * S, tr_y + 85 * S), fill=(30, 30, 35), outline=(80, 80, 90), width=1)
draw.text((tr_x + 10 * S, tr_y + 5 * S), "Transport:", font=font_label, fill=YELLOW)
draw.text((tr_x + 10 * S, tr_y + 28 * S), "stdio:", font=font_code, fill=GREEN)
draw.text((tr_x + 80 * S, tr_y + 28 * S), "MCP_IDENTITY_CONTEXT env var", font=font_code, fill=GREY)
draw.text((tr_x + 10 * S, tr_y + 50 * S), "HTTP: ", font=font_code, fill=GREEN)
draw.text((tr_x + 80 * S, tr_y + 50 * S), "X-Identity-Context header", font=font_code, fill=GREY)
draw.text((tr_x + 80 * S, tr_y + 67 * S), "(base64-encoded JSON)", font=font_small, fill=GREY)

# Arrow from IdentityContext to Transport
draw_arrow(ic_x + 190 * S, ic_y + 100 * S, tr_x + 190 * S, tr_y, color=CYAN, width=2)

# build_agent() label
ba_x, ba_y = 1000 * S, phase2_y + 75 * S
draw_rounded_rect((ba_x, ba_y, ba_x + 300 * S, ba_y + 100 * S), fill=DARK_MAGENTA_BG, outline=MAGENTA)
text_centered(ba_x + 150 * S, ba_y + 10 * S, "build_agent()", font_heading, WHITE)
text_centered(ba_x + 150 * S, ba_y + 35 * S, "factory.py", font_code, MAGENTA)
draw.text((ba_x + 15 * S, ba_y + 58 * S), "1. Resolve policy", font=font_small, fill=GREY)
draw.text((ba_x + 15 * S, ba_y + 73 * S), "2. Build IdentityContext", font=font_small, fill=GREY)
draw.text((ba_x + 15 * S, ba_y + 88 * S), "3. Start MCP server", font=font_small, fill=GREY)

# Arrows to/from build_agent
draw_arrow(ba_x, ba_y + 30 * S, ic_x + 380 * S, ic_y + 30 * S, color=MAGENTA, width=1, dashed=True)

# ═══════════════════════════════════════════════════════════════
# PHASE 3: MCP SERVER TOOL FILTERING
# ═══════════════════════════════════════════════════════════════
phase3_y = 760 * S
draw.rounded_rectangle(
    (40 * S, phase3_y, 1360 * S, phase3_y + 230 * S),
    radius=12 * S, fill=DARK_BG, outline=(60, 60, 70), width=2 * S
)
draw_circle_number(80 * S, phase3_y + 25 * S, 3)
draw.text((100 * S, phase3_y + 12 * S), "MCP SERVER TOOL FILTERING", font=font_heading, fill=ORANGE)
draw.text((100 * S, phase3_y + 36 * S), "Server starts with only permitted tools visible to the LangChain agent", font=font_small, fill=GREY)

# MCP Server box
ms_x, ms_y = 100 * S, phase3_y + 70 * S
draw_rounded_rect((ms_x, ms_y, ms_x + 350 * S, ms_y + 80 * S), fill=DARK_CYAN_BG, outline=CYAN)
text_centered(ms_x + 175 * S, ms_y + 10 * S, "BaseMCPServer", font_heading, WHITE)
text_centered(ms_x + 175 * S, ms_y + 35 * S, "_get_visible_tools()", font_code, CYAN)
text_centered(ms_x + 175 * S, ms_y + 55 * S, "filters by allowed_tools", font=font_small, fill=GREY)

# All tools registry
at_x, at_y = 580 * S, phase3_y + 70 * S
draw_rounded_rect((at_x, at_y, at_x + 340 * S, at_y + 130 * S), fill=(30, 30, 35), outline=(80, 80, 90), width=1)
draw.text((at_x + 10 * S, at_y + 5 * S), "All registered tools:", font=font_label, fill=YELLOW)
tools = ["list_buckets", "read_object", "write_object", "delete_object",
         "query_bigquery", "list_datasets", "create_dataset"]
for i, tool in enumerate(tools):
    ty = at_y + 28 * S + i * 14 * S
    color = GREEN if i < 4 else BLUE
    draw.text((at_x + 15 * S, ty), f"\u2022 {tool}", font=font_code, fill=color)

# Filtered result
fr_x, fr_y = 1020 * S, phase3_y + 70 * S
draw_rounded_rect((fr_x, fr_y, fr_x + 300 * S, fr_y + 130 * S), fill=(30, 30, 35), outline=GREEN, width=1)
draw.text((fr_x + 10 * S, fr_y + 5 * S), "Visible to agent", font=font_label, fill=GREEN)
draw.text((fr_x + 10 * S, fr_y + 22 * S), "(analyst + data_agent):", font=font_small, fill=GREY)
filtered = ["list_buckets", "read_object", "query_bigquery", "list_datasets"]
for i, tool in enumerate(filtered):
    ty = fr_y + 45 * S + i * 16 * S
    draw.text((fr_x + 15 * S, ty), f"\u2713 {tool}", font=font_code, fill=GREEN)

# Arrows
draw_arrow(ms_x + 350 * S, ms_y + 40 * S, at_x, at_y + 40 * S, color=CYAN, width=2)
draw_arrow(at_x + 340 * S, at_y + 65 * S, fr_x, fr_y + 65 * S, color=GREEN, width=2)
text_centered(at_x + 510 * S, at_y + 40 * S, "policy", font_label, ORANGE)
text_centered(at_x + 510 * S, at_y + 55 * S, "filter", font_label, ORANGE)

# ═══════════════════════════════════════════════════════════════
# PHASE 4: GCP TOKEN ISSUANCE
# ═══════════════════════════════════════════════════════════════
phase4_y = 1030 * S
draw.rounded_rectangle(
    (40 * S, phase4_y, 1360 * S, phase4_y + 340 * S),
    radius=12 * S, fill=DARK_BG, outline=(60, 60, 70), width=2 * S
)
draw_circle_number(80 * S, phase4_y + 25 * S, 4)
draw.text((100 * S, phase4_y + 12 * S), "GCP TOKEN ISSUANCE", font=font_heading, fill=ORANGE)
draw.text((100 * S, phase4_y + 36 * S), "Tool handler requests short-lived GCP OAuth2 token via Vault", font=font_small, fill=GREY)

# Tool handler box
th_x, th_y = 100 * S, phase4_y + 70 * S
draw_rounded_rect((th_x, th_y, th_x + 260 * S, th_y + 80 * S), fill=DARK_CYAN_BG, outline=CYAN)
text_centered(th_x + 130 * S, th_y + 10 * S, "Tool Handler", font_heading, WHITE)
text_centered(th_x + 130 * S, th_y + 35 * S, "_get_gcp_token()", font_code, CYAN)
text_centered(th_x + 130 * S, th_y + 55 * S, "base_server.py", font=font_small, fill=GREY)

# GCPCredentialBroker box
gcb_x, gcb_y = 480 * S, phase4_y + 70 * S
draw_rounded_rect((gcb_x, gcb_y, gcb_x + 320 * S, gcb_y + 80 * S), fill=DARK_MAGENTA_BG, outline=MAGENTA)
text_centered(gcb_x + 160 * S, gcb_y + 10 * S, "GCPCredentialBroker", font_heading, WHITE)
text_centered(gcb_x + 160 * S, gcb_y + 35 * S, "get_access_token()", font_code, MAGENTA)
text_centered(gcb_x + 160 * S, gcb_y + 55 * S, "gcp_credentials.py", font=font_small, fill=GREY)

# Vault box
v2_x, v2_y = 920 * S, phase4_y + 70 * S
draw_rounded_rect((v2_x, v2_y, v2_x + 350 * S, v2_y + 80 * S), fill=DARK_GREEN_BG, outline=GREEN)
text_centered(v2_x + 175 * S, v2_y + 10 * S, "Vault GCP Secrets Engine", font_heading, WHITE)
text_centered(v2_x + 175 * S, v2_y + 35 * S, "gcp/impersonated-account/", font_code, GREEN)
text_centered(v2_x + 175 * S, v2_y + 55 * S, "data-agent-gcp/token", font_code, GREEN)

# Arrows phase 4 top row
draw_arrow(th_x + 260 * S, th_y + 40 * S, gcb_x, gcb_y + 40 * S, color=CYAN, width=2)
draw_arrow(gcb_x + 320 * S, gcb_y + 40 * S, v2_x, v2_y + 40 * S, color=MAGENTA, width=2)

# "uses human's vault_token" label
draw.text((gcb_x + 330 * S, gcb_y + 8 * S), "uses human's", font=font_small, fill=YELLOW)
draw.text((gcb_x + 330 * S, gcb_y + 23 * S), "vault_token", font=font_code, fill=YELLOW)

# Vault policy check callout
vpc_x, vpc_y = 920 * S, phase4_y + 170 * S
draw_rounded_rect((vpc_x, vpc_y, vpc_x + 350 * S, vpc_y + 70 * S), fill=(35, 35, 50), outline=YELLOW, width=1)
draw.text((vpc_x + 10 * S, vpc_y + 5 * S), "Vault policy check:", font=font_label, fill=YELLOW)
draw.text((vpc_x + 10 * S, vpc_y + 25 * S), "Does token's policy allow read on", font=font_small, fill=GREY)
draw.text((vpc_x + 10 * S, vpc_y + 42 * S), "gcp/impersonated-account/*/token ?", font=font_code, fill=GREEN)

draw_arrow(v2_x + 175 * S, v2_y + 80 * S, vpc_x + 175 * S, vpc_y, color=YELLOW, width=1, dashed=True)

# GCP generateAccessToken
gcp_x, gcp_y = 480 * S, phase4_y + 180 * S
draw_rounded_rect((gcp_x, gcp_y, gcp_x + 320 * S, gcp_y + 60 * S), fill=DARK_BLUE_BG, outline=BLUE)
text_centered(gcp_x + 160 * S, gcp_y + 10 * S, "GCP IAM API", font_heading, WHITE)
text_centered(gcp_x + 160 * S, gcp_y + 35 * S, "generateAccessToken()", font_code, BLUE)

draw_arrow(v2_x + 100 * S, v2_y + 80 * S, gcp_x + 260 * S, gcp_y, color=GREEN, width=2)

# OAuth2 token result
tk_x, tk_y = 100 * S, phase4_y + 270 * S
draw_rounded_rect((tk_x, tk_y, tk_x + 1200 * S, tk_y + 50 * S), fill=(35, 35, 50), outline=GREEN, width=1)
draw.text((tk_x + 15 * S, tk_y + 8 * S), "GCP OAuth2 token returned:", font=font_label, fill=GREEN)
draw.text((tk_x + 250 * S, tk_y + 8 * S), "token_ttl = 300s (5 min)", font=font_code, fill=WHITE)
draw.text((tk_x + 560 * S, tk_y + 8 * S), "effective_ttl = min(vault_ttl, policy_max)", font=font_code, fill=YELLOW)
draw.text((tk_x + 250 * S, tk_y + 28 * S), "Cached in memory only \u2014 never written to disk", font=font_small, fill=GREY)

draw_arrow(gcp_x + 160 * S, gcp_y + 60 * S, tk_x + 600 * S, tk_y, color=BLUE, width=2)

# ═══════════════════════════════════════════════════════════════
# PHASE 5: TTL ENFORCEMENT (bottom)
# ═══════════════════════════════════════════════════════════════
phase5_y = 1410 * S
draw.rounded_rectangle(
    (40 * S, phase5_y, 1360 * S, phase5_y + 160 * S),
    radius=12 * S, fill=DARK_BG, outline=(60, 60, 70), width=2 * S
)
draw_circle_number(80 * S, phase5_y + 25 * S, 5)
draw.text((100 * S, phase5_y + 12 * S), "DUAL-LAYER 5-MINUTE TTL ENFORCEMENT", font=font_heading, fill=ORANGE)

# Layer 1
l1_x, l1_y = 100 * S, phase5_y + 55 * S
draw_rounded_rect((l1_x, l1_y, l1_x + 560 * S, l1_y + 90 * S), fill=DARK_GREEN_BG, outline=GREEN, width=1)
draw.text((l1_x + 15 * S, l1_y + 8 * S), "Layer 1: Vault GCP impersonated account", font=font_label, fill=GREEN)
draw.text((l1_x + 15 * S, l1_y + 32 * S), "ttl = \"300\"", font=font_code, fill=WHITE)
draw.text((l1_x + 180 * S, l1_y + 32 * S), "in vault_init.sh", font=font_small, fill=GREY)
draw.text((l1_x + 15 * S, l1_y + 55 * S), "Server-side: Vault passes lifetime to", font=font_small, fill=GREY)
draw.text((l1_x + 15 * S, l1_y + 70 * S), "GCP generateAccessToken API", font=font_small, fill=GREY)

# Layer 2
l2_x, l2_y = 740 * S, phase5_y + 55 * S
draw_rounded_rect((l2_x, l2_y, l2_x + 560 * S, l2_y + 90 * S), fill=DARK_ORANGE_BG, outline=ORANGE, width=1)
draw.text((l2_x + 15 * S, l2_y + 8 * S), "Layer 2: Application policy", font=font_label, fill=ORANGE)
draw.text((l2_x + 15 * S, l2_y + 32 * S), "max_gcp_token_ttl: \"5m\"", font=font_code, fill=WHITE)
draw.text((l2_x + 290 * S, l2_y + 32 * S), "in capabilities.yaml", font=font_small, fill=GREY)
draw.text((l2_x + 15 * S, l2_y + 55 * S), "Client-side: BaseMCPServer computes", font=font_small, fill=GREY)
draw.text((l2_x + 15 * S, l2_y + 70 * S), "effective_ttl = min(vault_ttl, policy_max)", font=font_small, fill=GREY)

# Save
out = os.path.join(os.path.dirname(__file__), "vault-auth-flow-gcp-credentials.png")
img.save(out, dpi=(300, 300))
print(f"Saved {W}x{H} image to {out}")
