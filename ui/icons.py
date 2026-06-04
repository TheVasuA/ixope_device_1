"""
Liquid Glass Icons — iOS 26 inspired glassmorphism design.

Three styles:
  'glass'  — Frosted liquid glass with multi-layer highlights (default)
  'white'  — Pure white line icons, no background
  'color'  — iOS multi-color per-icon palette

Features:
  - Multi-layer glass effect: base + radial gradient + top reflection + inner shadow
  - Rounded stroke endings (Image.LINE_CAPS via Pillow)
  - Higher resolution vector rendering with anti-aliased polygons
  - Press state variant (lighter + cyan tint) for touch feedback
"""
import math
import json
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PIL import ImageTk
from ..config import settings


# ─── Font loading (for battery percentage text) ─────────────────────────────
_FONT_CACHE = {}


def _load_font(px):
    """Load a bold TrueType font at the given pixel size, with fallbacks.

    Tries common Linux (DejaVu) and Windows (Arial) paths so the battery
    percentage renders crisply on both the Radxa device and dev machines.
    Falls back to PIL's bitmap default if none are found.
    """
    px = max(6, int(px))
    if px in _FONT_CACHE:
        return _FONT_CACHE[px]
    candidates = [
        # SF Pro — installed on the device under common Linux paths
        "/usr/share/fonts/truetype/sfpro/SFProDisplay-Bold.otf",
        "/usr/share/fonts/truetype/sfpro/SFProDisplay-Semibold.otf",
        "/usr/share/fonts/truetype/sfpro/SFProText-Bold.otf",
        "/usr/share/fonts/opentype/sfpro/SF-Pro-Display-Bold.otf",
        "/usr/share/fonts/opentype/sfpro/SF-Pro-Text-Bold.otf",
        "/usr/local/share/fonts/SFProDisplay-Bold.otf",
        # Fallback: DejaVu (standard on all Debian/Ubuntu/Raspbian)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        # Windows dev machine
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "DejaVuSans-Bold.ttf",
        "arial.ttf",
    ]
    font = None
    for p in candidates:
        try:
            font = ImageFont.truetype(p, px)
            break
        except Exception:
            continue
    if font is None:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
    _FONT_CACHE[px] = font
    return font


SCHEMES = {
    'glass': {
        # iPhone 16 liquid glass — nearly invisible tinted shell with a soft
        # specular highlight at the top. The icon "floats" over the live feed.
        'bg_top':       (200, 220, 255, 28),     # faint blue-white tint
        'bg_bot':       (120, 140, 180, 18),     # barely-there cool gradient
        'rim':          (255, 255, 255, 30),     # whisper-thin white edge
        'halo':         (200, 230, 255, 18),     # soft outer diffusion
        'highlight':    (255, 255, 255, 70),     # top specular (the "liquid" cue)
        'inner_shadow': (0, 0, 0, 12),           # subtle depth at the bottom
        'stroke':       (255, 255, 255),
        'stroke_width': 2,
        'feather':      11,                      # wider blur = softer edge
    },
    'white': {
        # Pure minimal — almost no background, just the glyph with a faint
        # halo glow so it reads against any camera content.
        'bg_top':       (255, 255, 255, 6),
        'bg_bot':       (255, 255, 255, 3),
        'rim':          (255, 255, 255, 15),
        'halo':         (255, 255, 255, 14),
        'highlight':    (255, 255, 255, 18),
        'inner_shadow': (0, 0, 0, 0),
        'stroke':       (255, 255, 255),
        'stroke_width': 2,
        'feather':      8,
    },
    'color': {
        # Tinted liquid glass — same translucent shell as 'glass' but the
        # glyph renders in its icon-specific color instead of white.
        'bg_top':       (180, 200, 240, 28),
        'bg_bot':       (100, 120, 160, 18),
        'rim':          (255, 255, 255, 25),
        'halo':         (160, 200, 255, 16),
        'highlight':    (255, 255, 255, 65),
        'inner_shadow': (0, 0, 0, 10),
        'stroke':       (255, 255, 255),
        'stroke_width': 2,
        'feather':      11,
    },
}

# Press state — bright filled light cyan with strong glow
# Acts as both visual feedback AND a clear "selected" highlight
PRESS_BG_TOP = (220, 240, 255, 245)      # Almost solid bright sky blue
PRESS_BG_BOT = (140, 200, 255, 245)      # Solid medium cyan
PRESS_RIM = (255, 255, 255, 255)         # Bright white rim
PRESS_HIGHLIGHT = (255, 255, 255, 180)   # Strong inner highlight
PRESS_GLOW = (100, 180, 255, 120)        # Outer glow bleed

# iOS-style per-icon colors (only used in 'color' scheme)
ICON_COLORS = {
    0: (192, 192, 200),   # camera - silver
    1: (255, 69, 58),     # video - red
    2: (50, 215, 75),     # scope - green
    3: (10, 132, 255),    # wifi - blue
    4: (255, 214, 10),    # main bulb - yellow
    9: (255, 159, 10),    # folder - orange
    10: (152, 152, 157),  # settings - gray
    13: (50, 215, 75),    # battery - green
}

BULB_COLORS_MAP = {
    5: (10, 132, 255), 6: (255, 214, 10), 7: (255, 159, 10),
    8: (50, 215, 75), 11: (100, 210, 255), 12: (191, 90, 242),
}


def _load_icon_scheme():
    try:
        p = os.path.join(settings.BASE_PATH, "icon_scheme.json")
        if os.path.exists(p):
            with open(p, 'r') as f:
                return json.load(f).get('scheme', 'glass')
    except:
        pass
    return 'glass'


def save_icon_scheme(scheme_name):
    try:
        p = os.path.join(settings.BASE_PATH, "icon_scheme.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            json.dump({'scheme': scheme_name}, f)
    except:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# LIQUID GLASS BASE — Multi-layer rendering for premium feel
# ═══════════════════════════════════════════════════════════════════════════════

def _make_glass_base(size, scheme, pressed=False):
    """
    Render iOS 26 style liquid glass.

    For the RESTING state the base is fully transparent — icons are just
    their white/colored vector glyph floating over the live camera feed
    with no dark background at all (iPhone 16 liquid-glass aesthetic).

    For the PRESSED state (touch feedback) a bright cyan-filled circle
    appears so the user sees clear tap feedback.
    """
    s = SCHEMES[scheme]

    # Resting state: completely transparent base (no dark circle)
    if not pressed:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        return img, ImageDraw.Draw(img)

    # ─── Pressed state: visible feedback ─────────────────────────────
    R = size * 2
    img = Image.new('RGBA', (R, R), (0, 0, 0, 0))
    pad = 6

    # Outer cyan caustic glow
    glow = Image.new('RGBA', (R, R), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([pad - 4, pad - 4, R - pad + 4, R - pad + 4],
               fill=PRESS_GLOW)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=18))
    img = Image.alpha_composite(img, glow)

    # Body fill (bright cyan gradient)
    mask = Image.new('L', (R, R), 0)
    ImageDraw.Draw(mask).ellipse([pad, pad, R-pad, R-pad], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=4))

    grad = Image.new('RGBA', (R, R), (0, 0, 0, 0))
    gd2 = ImageDraw.Draw(grad)
    for y in range(pad, R - pad):
        t = (y - pad) / max(1, (R - 2 * pad))
        t = t * t * (3 - 2 * t)
        r = int(PRESS_BG_TOP[0] * (1-t) + PRESS_BG_BOT[0] * t)
        g = int(PRESS_BG_TOP[1] * (1-t) + PRESS_BG_BOT[1] * t)
        b = int(PRESS_BG_TOP[2] * (1-t) + PRESS_BG_BOT[2] * t)
        a = int(PRESS_BG_TOP[3] * (1-t) + PRESS_BG_BOT[3] * t)
        gd2.line([(pad, y), (R-pad, y)], fill=(r, g, b, a))
    grad.putalpha(mask)
    img = Image.alpha_composite(img, grad)

    # Top specular highlight
    hl = Image.new('RGBA', (R, R), (0, 0, 0, 0))
    hd2 = ImageDraw.Draw(hl)
    hd2.ellipse([pad + 16, pad + 8, R - pad - 16, R // 2 - 4],
                fill=PRESS_HIGHLIGHT)
    hl = hl.filter(ImageFilter.GaussianBlur(radius=4))
    img = Image.alpha_composite(img, hl)

    # White rim
    rim = Image.new('RGBA', (R, R), (0, 0, 0, 0))
    ImageDraw.Draw(rim).ellipse([pad, pad, R-pad, R-pad],
                                outline=PRESS_RIM, width=3)
    img = Image.alpha_composite(img, rim)

    img = img.resize((size, size), Image.LANCZOS)
    return img, ImageDraw.Draw(img)


# ═══════════════════════════════════════════════════════════════════════════════
# HIGH-QUALITY VECTOR ICONS — drawn at 2x resolution, downscaled for smoothness
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_with_aa(size, draw_fn):
    """Draw icon at 2x resolution with given draw function, then downscale for AA."""
    R = size * 2
    overlay = Image.new('RGBA', (R, R), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    draw_fn(od, R)
    return overlay.resize((size, size), Image.LANCZOS)


def _stroke_camera(d, R, c, w):
    """Camera body + lens at 2R resolution."""
    cx, cy = R // 2, R // 2
    w *= 2
    # Body
    d.rounded_rectangle([cx-30, cy-20, cx+30, cy+24], radius=8, outline=c, width=w)
    # Top notch (where viewfinder sits)
    d.rounded_rectangle([cx-12, cy-26, cx+10, cy-18], radius=4, outline=c, width=w)
    # Lens outer
    d.ellipse([cx-14, cy-10, cx+14, cy+18], outline=c, width=w)
    # Lens inner
    d.ellipse([cx-6, cy-2, cx+6, cy+10], outline=c, width=w)
    # Lens dot (highlight)
    d.ellipse([cx-2, cy+2, cx+4, cy+8], fill=c)
    # Flash dot
    d.ellipse([cx+18, cy-12, cx+24, cy-6], fill=c)


def _stroke_video(d, R, c, w):
    cx, cy = R // 2, R // 2
    w *= 2
    # Body (rounded rectangle)
    d.rounded_rectangle([cx-32, cy-18, cx+12, cy+18], radius=6, outline=c, width=w)
    # Lens triangle
    pts = [(cx+16, cy-14), (cx+40, cy), (cx+16, cy+14)]
    d.polygon(pts, outline=c, fill=None)
    for i in range(len(pts)):
        d.line([pts[i], pts[(i+1) % len(pts)]], fill=c, width=w)


def _stroke_video_rec(d, R):
    cx, cy = R // 2, R // 2
    # Solid red recording dot
    d.ellipse([cx-28, cy-28, cx+28, cy+28], fill=(255, 69, 58))
    # Inner glow
    d.ellipse([cx-8, cy-16, cx+6, cy-4], fill=(255, 200, 200, 180))


def _stroke_scope(d, R, c, w):
    cx, cy = R // 2, R // 2
    w *= 2
    r = 28
    d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=c, width=w)
    # Crosshair (extended outside circle)
    d.line([cx, cy-r-8, cx, cy+r+8], fill=c, width=w)
    d.line([cx-r-8, cy, cx+r+8, cy], fill=c, width=w)
    # Center dot
    d.ellipse([cx-5, cy-5, cx+5, cy+5], fill=c)


def _stroke_wifi(d, R, c, w):
    cx, cy = R // 2, R // 2 + 8
    w *= 2
    # 3 arcs
    for r in [40, 28, 16]:
        d.arc([cx-r, cy-r-8, cx+r, cy+r-8], start=225, end=315, fill=c, width=w)
    # Bottom dot
    d.ellipse([cx-4, cy+4, cx+4, cy+12], fill=c)


def _stroke_bulb_main(d, R, c, w):
    cx, cy = R // 2, R // 2
    w *= 2
    r = 20
    # Bulb body
    d.ellipse([cx-r, cy-r-6, cx+r, cy+r-6], outline=c, width=w)
    # Rays
    for ang in range(0, 360, 45):
        rad = math.radians(ang)
        x1 = cx + int((r+4) * math.cos(rad))
        y1 = cy - 6 + int((r+4) * math.sin(rad))
        x2 = cx + int((r+12) * math.cos(rad))
        y2 = cy - 6 + int((r+12) * math.sin(rad))
        d.line([x1, y1, x2, y2], fill=c, width=w)
    # Base
    d.rectangle([cx-8, cy+r-2, cx+8, cy+r+10], outline=c, width=w)


def _stroke_folder(d, R, c, w):
    cx, cy = R // 2, R // 2
    w *= 2
    # Folder body
    d.rounded_rectangle([cx-32, cy-12, cx+32, cy+24], radius=6, outline=c, width=w)
    # Tab
    d.rounded_rectangle([cx-32, cy-24, cx-4, cy-8], radius=4, outline=c, width=w, fill=c)


def _stroke_settings(d, R, c, w):
    cx, cy = R // 2, R // 2
    w *= 2
    ro, ri = 30, 18
    # Gear teeth
    for i in range(8):
        ang = math.radians(i * 45 + 22.5)
        x = cx + int(ro * math.cos(ang))
        y = cy + int(ro * math.sin(ang))
        d.ellipse([x-6, y-6, x+6, y+6], fill=c)
    # Center ring
    d.ellipse([cx-ri, cy-ri, cx+ri, cy+ri], outline=c, width=w)
    # Inner dot
    d.ellipse([cx-8, cy-8, cx+8, cy+8], fill=c)


def _stroke_battery(d, R, c, w, level=None):
    """
    Horizontal battery glyph, fully contained within the RxR canvas.

    Geometry is derived from R (= 2 × icon size) so the whole battery —
    body + tip — always fits and never clips at the edges.

    • `level` (0-100) controls the inner fill width. When None, defaults to
      a representative 75% so the icon still looks "alive" before a real
      reading is wired in.
    • The percentage number is drawn centered inside the body.
    """
    cx, cy = R // 2, R // 2
    w *= 2
    lvl = 75 if level is None else max(0, min(100, int(level)))

    # Reserve room for the tip on the right; keep margins so nothing clips.
    margin = max(6, R // 12)
    tip_w = max(4, R // 16)
    body_w = R - margin * 2 - tip_w
    body_h = int(body_w * 0.46)
    x1 = margin
    y1 = cy - body_h // 2
    x2 = x1 + body_w
    y2 = y1 + body_h
    rad = max(3, body_h // 4)

    # Body outline
    d.rounded_rectangle([x1, y1, x2, y2], radius=rad, outline=c, width=w)
    # Tip
    tip_h = max(6, body_h // 3)
    d.rounded_rectangle(
        [x2 + 1, cy - tip_h // 2, x2 + tip_w, cy + tip_h // 2],
        radius=max(1, tip_w // 3), fill=c,
    )

    # Inner fill — proportional to level, with a small inset from the outline
    inset = w + max(2, R // 28)
    fmax = (x2 - inset) - (x1 + inset)
    fw = int(fmax * (lvl / 100.0))
    if fw > 0:
        # Low battery → red, otherwise use the stroke color
        fill_col = (255, 69, 58) if lvl <= 20 else c
        d.rounded_rectangle(
            [x1 + inset, y1 + inset, x1 + inset + fw, y2 - inset],
            radius=max(1, rad - inset // 2), fill=fill_col,
        )

    # Percentage text centered inside the body
    txt = f"{lvl}"
    font = _load_font(int(body_h * 0.62))
    if font is not None:
        try:
            bbox = d.textbbox((0, 0), txt, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = cx - tw // 2 - bbox[0]
            ty = cy - th // 2 - bbox[1]
            # Choose a readable text color: dark over a bright fill that
            # covers the center, else the stroke color.
            covers_center = (x1 + inset + fw) >= cx
            if covers_center and lvl > 20:
                tcol = (15, 18, 26)
            else:
                tcol = c
            d.text((tx, ty), txt, font=font, fill=tcol)
        except Exception:
            pass


def _stroke_bulb(d, R, c, w, color, is_on):
    """LED bulb — outline when off, glowing fill when on."""
    cx, cy = R // 2, R // 2
    w *= 2
    r = 26
    if is_on:
        # Outer glow
        for i in range(6):
            alpha = max(0, 60 - i * 10)
            glow = (color[0], color[1], color[2], alpha)
            d.ellipse([cx-r-i*3, cy-r-i*3, cx+r+i*3, cy+r+i*3], fill=glow)
        # Solid bulb
        d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=color)
        # Highlight
        d.ellipse([cx-8, cy-14, cx+4, cy-4], fill=(255, 255, 255, 150))
    else:
        d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=c, width=w)
        d.line([cx-6, cy+6, cx, cy-6], fill=c, width=w//2)
        d.line([cx, cy-6, cx+6, cy+6], fill=c, width=w//2)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSE: glass base + vector overlay
# ═══════════════════════════════════════════════════════════════════════════════

def _stroke_color(scheme, base_color, pressed):
    """
    Pick the stroke color for an icon glyph.

    • Resting:
        - 'color' scheme  → use the icon's own tint (`base_color`)
        - 'glass'/'white' → use scheme stroke (white)
    • Pressed (touch feedback):
        - all schemes go to a bright cyan-shifted variant so the icon
          visibly "lights up" without losing its identity color.
    """
    if pressed:
        # Bright sky-cyan for touch feedback. In 'color' scheme we pull the
        # base_color toward cyan so we keep some of the icon identity.
        if scheme == 'color' and base_color:
            r, g, b = base_color[:3]
            # Lerp 60% toward (140, 220, 255)
            return (int(r * 0.4 + 140 * 0.6),
                    int(g * 0.4 + 220 * 0.6),
                    int(b * 0.4 + 255 * 0.6))
        return (165, 232, 255)
    # Resting
    if base_color:
        return base_color
    return SCHEMES[scheme]['stroke']


def _compose(size, scheme, draw_fn, pressed=False):
    """
    Render glass base + draw vector icon on top.

    For the 'white' scheme the glyph gets a soft drop shadow so it doesn't
    look flat against the live camera feed (a common readability problem
    with pure-line icons).
    """
    base, _ = _make_glass_base(size, scheme, pressed=pressed)
    overlay = _draw_with_aa(size, draw_fn)

    if scheme == 'white' and not pressed:
        # Build a blurred dark twin of the overlay as a drop shadow
        shadow = Image.new('RGBA', overlay.size, (0, 0, 0, 0))
        # Use only the alpha channel so the shadow follows the glyph
        alpha = overlay.split()[-1]
        # Tint shadow black at ~55% strength
        shadow_layer = Image.new('RGBA', overlay.size, (0, 0, 0, 0))
        # Paste a black image masked by overlay alpha
        black = Image.new('RGBA', overlay.size, (0, 0, 0, 140))
        shadow_layer.paste(black, (0, 0), alpha)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=2))
        # Composite shadow first, then overlay on top
        result = Image.alpha_composite(base, shadow_layer)
        result = Image.alpha_composite(result, overlay)
        return result

    return Image.alpha_composite(base, overlay)


def _icon_camera(size, scheme, color, pressed=False):
    c = _stroke_color(scheme, color, pressed)
    w = SCHEMES[scheme]['stroke_width']
    return _compose(size, scheme, lambda d, R: _stroke_camera(d, R, c, w), pressed)


def _icon_video(size, scheme, color, pressed=False):
    c = _stroke_color(scheme, color, pressed)
    w = SCHEMES[scheme]['stroke_width']
    return _compose(size, scheme, lambda d, R: _stroke_video(d, R, c, w), pressed)


def _icon_video_rec(size, scheme, pressed=False):
    base, _ = _make_glass_base(size, scheme, pressed=pressed)
    overlay = _draw_with_aa(size, _stroke_video_rec)
    return Image.alpha_composite(base, overlay)


def _icon_scope(size, scheme, color, pressed=False):
    c = _stroke_color(scheme, color, pressed)
    w = SCHEMES[scheme]['stroke_width']
    return _compose(size, scheme, lambda d, R: _stroke_scope(d, R, c, w), pressed)


def _icon_wifi(size, scheme, color, pressed=False):
    c = _stroke_color(scheme, color, pressed)
    w = SCHEMES[scheme]['stroke_width']
    return _compose(size, scheme, lambda d, R: _stroke_wifi(d, R, c, w), pressed)


def _icon_bulb_main(size, scheme, color, pressed=False):
    c = _stroke_color(scheme, color, pressed)
    w = SCHEMES[scheme]['stroke_width']
    return _compose(size, scheme, lambda d, R: _stroke_bulb_main(d, R, c, w), pressed)


def _icon_folder(size, scheme, color, pressed=False):
    c = _stroke_color(scheme, color, pressed)
    w = SCHEMES[scheme]['stroke_width']
    return _compose(size, scheme, lambda d, R: _stroke_folder(d, R, c, w), pressed)


def _icon_settings(size, scheme, color, pressed=False):
    c = _stroke_color(scheme, color, pressed)
    w = SCHEMES[scheme]['stroke_width']
    return _compose(size, scheme, lambda d, R: _stroke_settings(d, R, c, w), pressed)


def _icon_battery(size, scheme, color, pressed=False, level=None, opacity=1.0):
    c = _stroke_color(scheme, color, pressed)
    w = SCHEMES[scheme]['stroke_width']
    img = _compose(size, scheme,
                   lambda d, R: _stroke_battery(d, R, c, w, level=level),
                   pressed)
    if opacity < 1.0:
        # Scale the whole icon's alpha channel so it reads as translucent
        # against the live camera feed (status pip, not a control).
        img = img.convert("RGBA")
        alpha = img.split()[-1].point(lambda a: int(a * opacity))
        img.putalpha(alpha)
    return img


def _icon_bulb(size, scheme, color, is_on=False, pressed=False):
    s = SCHEMES[scheme]
    c = _stroke_color(scheme, None, pressed)
    w = s['stroke_width']
    base, _ = _make_glass_base(size, scheme, pressed=pressed)
    overlay = _draw_with_aa(size, lambda d, R: _stroke_bulb(d, R, c, w, color, is_on))
    return Image.alpha_composite(base, overlay)


# ═══════════════════════════════════════════════════════════════════════════════
# ICON MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class IconManager:
    """
    Liquid Glass icon manager with iOS 26 style rendering.

    Generates:
      - Default icons (off state)
      - Pressed icons (cyan-tinted, slightly larger feel)
      - Bulb ON variants (glowing)
      - Recording icon
      - Ripple animation frames (10-frame cyan wave)
    """

    # Tap ripple animation: pre-rendered cyan caustic frames played at click
    RIPPLE_FRAMES = 10

    def __init__(self, scheme=None):
        self.scheme = scheme or _load_icon_scheme()
        self.icons = []           # PhotoImage list (off/default)
        self.icons_pressed = []   # PhotoImage list (pressed state)
        self.icons_on = {}        # idx -> PhotoImage (bulb ON)
        self.video_rec_icon = None
        self.battery_mini_icon = None  # tiny variant when UI is auto-hidden
        self.ripple_frames = []   # PhotoImage list (animated ripple)
        self._battery_level = 75  # current battery % (updated at runtime)
        self._battery_cache = {}
        self._battery_big_cache = {}
        self._generate_all()

    def _make_ripple_frames(self, base_size):
        """
        Build N PhotoImage frames of an expanding cyan ripple.
        Frame i: radius scales 0.20 → 1.60, alpha fades 220 → 0, ring widens.
        Canvas is 2x base_size so the ripple can radiate past the icon.

        Geometry safety:
          • Ring width is clamped to never exceed the radius (otherwise the
            inner-ring inset bbox goes negative and PIL raises
            "x1 must be greater than or equal to x0").
          • Inner crisp ring is skipped entirely when the radius is too
            small to fit it.
        """
        frames = []
        canvas = base_size * 2
        for i in range(self.RIPPLE_FRAMES):
            t = i / max(1, self.RIPPLE_FRAMES - 1)
            scale = 0.20 + 1.40 * (1 - (1 - t) ** 2)         # eased outward
            radius = max(3, int((base_size // 2) * scale))
            alpha = int(220 * (1 - t) ** 1.5)
            # Ring width tapers from thick to thin AND can't exceed radius
            ring_w = max(2, int(8 * (1 - t) + 2))
            ring_w = min(ring_w, max(2, radius - 2))         # ← key fix

            # Render at 2x for AA, then downscale
            R = canvas * 2
            cR = R // 2
            rR = radius * 2
            wR = ring_w * 2

            img = Image.new('RGBA', (R, R), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)

            # Outer faint bloom (always safe — bbox is rR + wR*2 > 0)
            if alpha > 30:
                d.ellipse(
                    [cR - rR - wR * 2, cR - rR - wR * 2,
                     cR + rR + wR * 2, cR + rR + wR * 2],
                    fill=(140, 220, 255, max(0, alpha // 4)),
                )

            # Main caustic ring
            d.ellipse(
                [cR - rR, cR - rR, cR + rR, cR + rR],
                outline=(180, 230, 255, alpha), width=wR,
            )

            # Inner crisp highlight ring — only if there's room
            inner_inset = wR
            if rR - inner_inset > 2:
                inner_w = max(1, wR // 2)
                d.ellipse(
                    [cR - rR + inner_inset, cR - rR + inner_inset,
                     cR + rR - inner_inset, cR + rR - inner_inset],
                    outline=(255, 255, 255, min(255, alpha + 20)),
                    width=inner_w,
                )

            img = img.filter(ImageFilter.GaussianBlur(radius=2))
            img = img.resize((canvas, canvas), Image.LANCZOS)
            frames.append(ImageTk.PhotoImage(img))
        return frames

    def _generate_all(self):
        size = settings.ICON_SIZE
        s = self.scheme

        def col(idx):
            return ICON_COLORS.get(idx) if s == 'color' else None

        # Default state
        gens = [
            lambda sz: _icon_camera(sz, s, col(0)),
            lambda sz: _icon_video(sz, s, col(1)),
            lambda sz: _icon_scope(sz, s, col(2)),
            lambda sz: _icon_wifi(sz, s, col(3)),
            lambda sz: _icon_bulb_main(sz, s, col(4)),
            lambda sz: _icon_bulb(sz, s, BULB_COLORS_MAP[5]),
            lambda sz: _icon_bulb(sz, s, BULB_COLORS_MAP[6]),
            lambda sz: _icon_bulb(sz, s, BULB_COLORS_MAP[7]),
            lambda sz: _icon_bulb(sz, s, BULB_COLORS_MAP[8]),
            lambda sz: _icon_folder(sz, s, col(9)),
            lambda sz: _icon_settings(sz, s, col(10)),
            lambda sz: _icon_bulb(sz, s, BULB_COLORS_MAP[11]),
            lambda sz: _icon_bulb(sz, s, BULB_COLORS_MAP[12]),
            lambda sz: _icon_battery(sz, s, col(13)),
        ]

        # Pressed state versions (cyan tint)
        gens_pressed = [
            lambda sz: _icon_camera(sz, s, col(0), pressed=True),
            lambda sz: _icon_video(sz, s, col(1), pressed=True),
            lambda sz: _icon_scope(sz, s, col(2), pressed=True),
            lambda sz: _icon_wifi(sz, s, col(3), pressed=True),
            lambda sz: _icon_bulb_main(sz, s, col(4), pressed=True),
            lambda sz: _icon_bulb(sz, s, BULB_COLORS_MAP[5], pressed=True),
            lambda sz: _icon_bulb(sz, s, BULB_COLORS_MAP[6], pressed=True),
            lambda sz: _icon_bulb(sz, s, BULB_COLORS_MAP[7], pressed=True),
            lambda sz: _icon_bulb(sz, s, BULB_COLORS_MAP[8], pressed=True),
            lambda sz: _icon_folder(sz, s, col(9), pressed=True),
            lambda sz: _icon_settings(sz, s, col(10), pressed=True),
            lambda sz: _icon_bulb(sz, s, BULB_COLORS_MAP[11], pressed=True),
            lambda sz: _icon_bulb(sz, s, BULB_COLORS_MAP[12], pressed=True),
            lambda sz: _icon_battery(sz, s, col(13), pressed=True),
        ]

        self.icons = [ImageTk.PhotoImage(g(size)) for g in gens]
        # Pressed state at slightly larger size for "magnification" feel
        press_size = int(size * 1.08)
        self.icons_pressed = [ImageTk.PhotoImage(g(press_size)) for g in gens_pressed]

        # Battery is the system status pip — render it at a smaller size
        # so it doesn't compete with the primary controls on the outer ring.
        # Two sizes are stored:
        #   • normal   — when the rest of the icon ring is visible
        #   • mini     — when the rest is auto-hidden (further reduced)
        battery_size = getattr(settings, 'BATTERY_ICON_SIZE', 46)
        battery_big = getattr(settings, 'BATTERY_ICON_SIZE_HIDDEN', 60)
        self._battery_size = battery_size
        self._battery_big = battery_big
        self._battery_color = ICON_COLORS.get(13) if s == 'color' else None
        # Opacity is state-dependent: full when the icon ring is visible,
        # reduced (translucent status pip) when all icons are hidden on idle.
        self._battery_opacity = getattr(settings, 'BATTERY_OPACITY', 1.0)
        self._battery_opacity_hidden = getattr(settings, 'BATTERY_OPACITY_HIDDEN', 0.5)
        self._battery_cache = {}     # level -> PhotoImage (normal size, full opacity)
        self._battery_big_cache = {}  # level -> PhotoImage (idle size, reduced opacity)
        try:
            bat_color = self._battery_color
            op = self._battery_opacity
            bat_img = _icon_battery(battery_size, s, bat_color,
                                    level=self._battery_level, opacity=op)
            self.icons[13] = ImageTk.PhotoImage(bat_img)
            bat_pressed = _icon_battery(int(battery_size * 1.08), s,
                                        bat_color, pressed=True,
                                        level=self._battery_level, opacity=op)
            self.icons_pressed[13] = ImageTk.PhotoImage(bat_pressed)
            # Enlarged + translucent variant for the idle/auto-hide state
            bat_big_img = _icon_battery(battery_big, s, bat_color,
                                        level=self._battery_level,
                                        opacity=self._battery_opacity_hidden)
            self.battery_mini_icon = ImageTk.PhotoImage(bat_big_img)
        except Exception:
            self.battery_mini_icon = None

        # Bulb ON variants (always use bulb color, regardless of scheme)
        for idx, color in BULB_COLORS_MAP.items():
            img = _icon_bulb(size, s, color, is_on=True)
            self.icons_on[idx] = ImageTk.PhotoImage(img)

        # Recording icon
        self.video_rec_icon = ImageTk.PhotoImage(_icon_video_rec(size, s))

        # Ripple animation frames (10-frame cyan wave for click feedback)
        self.ripple_frames = self._make_ripple_frames(size)

    def set_scheme(self, scheme_name):
        if scheme_name in SCHEMES and scheme_name != self.scheme:
            # Keep old refs alive to prevent TclError mid-update
            self._old_icons = self.icons
            self._old_pressed = self.icons_pressed
            self._old_on = self.icons_on
            self._old_rec = self.video_rec_icon
            self.scheme = scheme_name
            save_icon_scheme(scheme_name)
            # Battery glyphs are color/scheme dependent — drop cached levels
            self._battery_cache = {}
            self._battery_big_cache = {}
            self._generate_all()

    def get(self, index, is_on=False, pressed=False):
        """Get icon — supports pressed and bulb-on states."""
        if pressed and 0 <= index < len(self.icons_pressed):
            return self.icons_pressed[index]
        if is_on and index in self.icons_on:
            return self.icons_on[index]
        if 0 <= index < len(self.icons):
            return self.icons[index]
        return None

    def get_recording_icon(self):
        return self.video_rec_icon

    def set_battery_level(self, level):
        """Update the battery percentage. Returns True if the level changed
        (so the caller knows whether to refresh the on-canvas icon)."""
        try:
            lvl = max(0, min(100, int(level)))
        except (TypeError, ValueError):
            return False
        if lvl == self._battery_level:
            return False
        self._battery_level = lvl
        # Refresh the primary battery icon used by the normal-state ring
        try:
            img = _icon_battery(self._battery_size, self.scheme,
                                self._battery_color, level=lvl,
                                opacity=self._battery_opacity)
            self.icons[13] = ImageTk.PhotoImage(img)
        except Exception:
            pass
        return True

    def get_battery_icon(self, big=False):
        """Return a battery PhotoImage for the current level (cached per level).

        `big=True` returns the enlarged, translucent status-pip variant shown
        when the rest of the UI is auto-hidden on idle. The visible-state icon
        uses full opacity; the idle variant uses the reduced opacity.
        """
        lvl = self._battery_level
        cache = self._battery_big_cache if big else self._battery_cache
        if lvl not in cache:
            size = self._battery_big if big else self._battery_size
            op = self._battery_opacity_hidden if big else self._battery_opacity
            try:
                img = _icon_battery(size, self.scheme,
                                    self._battery_color, level=lvl,
                                    opacity=op)
                cache[lvl] = ImageTk.PhotoImage(img)
            except Exception:
                return self.battery_mini_icon if big else self.get(13)
        return cache[lvl]

    def get_ripple_frame(self, frame_index):
        """Return the i-th ripple animation frame (clamped)."""
        if not self.ripple_frames:
            return None
        i = max(0, min(len(self.ripple_frames) - 1, frame_index))
        return self.ripple_frames[i]

    def ripple_frame_count(self):
        return len(self.ripple_frames)
