"""
Secondary Windows for 480x480 Round Display.
All text colors follow theme. All content fits within circle.
Usable area: x=60-420, y=50-430 (inscribed in 480px circle).
"""
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import os
import subprocess
import threading
import json
import math
import time
import cv2
from ..config import settings
from ..storage import FileManager


def _get_theme():
    try:
        p = os.path.join(settings.BASE_PATH, "mode_config.json")
        if os.path.exists(p):
            with open(p, 'r') as f:
                return json.load(f).get('mode', 'dark')
    except:
        pass
    return 'dark'

def _save_theme(mode):
    try:
        p = os.path.join(settings.BASE_PATH, "mode_config.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            json.dump({'mode': mode}, f)
    except:
        pass

def _tc(mode='dark'):
    """Theme colors shortcut."""
    return settings.THEME_DARK if mode == 'dark' else settings.THEME_LIGHT


# ─── iOS-style palette shared across all windows ─────────────────────────────
# Frosted "neutral" pill colors — alpha < 255 so the canvas behind shows
# through the way iOS Control Center pills do.
IOS_GLASS_DARK_FILL  = "#8a90a4"     # mid neutral
IOS_GLASS_LIGHT_FILL = "#ffffff"     # white
IOS_GLASS_DARK_ALPHA  = 200          # solid visible buttons in dark mode
IOS_GLASS_LIGHT_ALPHA = 220          # solid visible buttons in light mode

# iOS system colors used by status pills
IOS_RED    = "#ff453a"
IOS_GREEN  = "#30d158"
IOS_BLUE   = "#0a84ff"
IOS_CYAN   = "#5ac8fa"


# ─── Country list (ISO 3166-1) — shared by SettingsWindow and WifiWindow ────
COUNTRIES = {
    'Afghanistan':'AF','Albania':'AL','Algeria':'DZ','Andorra':'AD',
    'Angola':'AO','Argentina':'AR','Armenia':'AM','Australia':'AU',
    'Austria':'AT','Azerbaijan':'AZ','Bahamas':'BS','Bahrain':'BH',
    'Bangladesh':'BD','Barbados':'BB','Belarus':'BY','Belgium':'BE',
    'Belize':'BZ','Benin':'BJ','Bhutan':'BT','Bolivia':'BO',
    'Bosnia and Herzegovina':'BA','Botswana':'BW','Brazil':'BR',
    'Brunei':'BN','Bulgaria':'BG','Burkina Faso':'BF','Burundi':'BI',
    'Cambodia':'KH','Cameroon':'CM','Canada':'CA','Cape Verde':'CV',
    'Central African Republic':'CF','Chad':'TD','Chile':'CL','China':'CN',
    'Colombia':'CO','Comoros':'KM','Congo':'CG','Costa Rica':'CR',
    'Croatia':'HR','Cuba':'CU','Cyprus':'CY','Czech Republic':'CZ',
    'Denmark':'DK','Djibouti':'DJ','Dominica':'DM',
    'Dominican Republic':'DO','Ecuador':'EC','Egypt':'EG',
    'El Salvador':'SV','Equatorial Guinea':'GQ','Eritrea':'ER',
    'Estonia':'EE','Ethiopia':'ET','Fiji':'FJ','Finland':'FI',
    'France':'FR','Gabon':'GA','Gambia':'GM','Georgia':'GE',
    'Germany':'DE','Ghana':'GH','Greece':'GR','Grenada':'GD',
    'Guatemala':'GT','Guinea':'GN','Guyana':'GY','Haiti':'HT',
    'Honduras':'HN','Hong Kong':'HK','Hungary':'HU','Iceland':'IS',
    'India':'IN','Indonesia':'ID','Iran':'IR','Iraq':'IQ',
    'Ireland':'IE','Israel':'IL','Italy':'IT','Jamaica':'JM',
    'Japan':'JP','Jordan':'JO','Kazakhstan':'KZ','Kenya':'KE',
    'Kuwait':'KW','Kyrgyzstan':'KG','Laos':'LA','Latvia':'LV',
    'Lebanon':'LB','Lesotho':'LS','Liberia':'LR','Libya':'LY',
    'Liechtenstein':'LI','Lithuania':'LT','Luxembourg':'LU',
    'Macedonia':'MK','Madagascar':'MG','Malawi':'MW','Malaysia':'MY',
    'Maldives':'MV','Mali':'ML','Malta':'MT','Mauritania':'MR',
    'Mauritius':'MU','Mexico':'MX','Moldova':'MD','Monaco':'MC',
    'Mongolia':'MN','Montenegro':'ME','Morocco':'MA','Mozambique':'MZ',
    'Myanmar':'MM','Namibia':'NA','Nepal':'NP','Netherlands':'NL',
    'New Zealand':'NZ','Nicaragua':'NI','Niger':'NE','Nigeria':'NG',
    'North Korea':'KP','Norway':'NO','Oman':'OM','Pakistan':'PK',
    'Panama':'PA','Papua New Guinea':'PG','Paraguay':'PY','Peru':'PE',
    'Philippines':'PH','Poland':'PL','Portugal':'PT','Qatar':'QA',
    'Romania':'RO','Russia':'RU','Rwanda':'RW','Saudi Arabia':'SA',
    'Senegal':'SN','Serbia':'RS','Seychelles':'SC','Sierra Leone':'SL',
    'Singapore':'SG','Slovakia':'SK','Slovenia':'SI','Somalia':'SO',
    'South Africa':'ZA','South Korea':'KR','Spain':'ES','Sri Lanka':'LK',
    'Sudan':'SD','Suriname':'SR','Sweden':'SE','Switzerland':'CH',
    'Syria':'SY','Taiwan':'TW','Tajikistan':'TJ','Tanzania':'TZ',
    'Thailand':'TH','Togo':'TG','Trinidad and Tobago':'TT','Tunisia':'TN',
    'Turkey':'TR','Turkmenistan':'TM','UAE':'AE','Uganda':'UG',
    'Ukraine':'UA','United Kingdom':'GB','United States':'US',
    'Uruguay':'UY','Uzbekistan':'UZ','Venezuela':'VE','Vietnam':'VN',
    'Yemen':'YE','Zambia':'ZM','Zimbabwe':'ZW',
}
_SORTED_COUNTRIES = sorted(COUNTRIES.keys())
COUNTRY_PREF_FILE = "wifi_country.json"


def get_saved_country_code():
    """Return the saved 2-letter country code or None."""
    try:
        p = os.path.join(settings.BASE_PATH, COUNTRY_PREF_FILE)
        if os.path.exists(p):
            with open(p, 'r') as f:
                return json.load(f).get('code')
    except Exception:
        pass
    return None


def get_saved_country_name():
    """Return the human name for the saved country, or None."""
    code = get_saved_country_code()
    if not code:
        return None
    for name, c in COUNTRIES.items():
        if c == code:
            return name
    return None


def save_country(code):
    """Persist the country code to disk and apply via `iw reg set`."""
    try:
        os.makedirs(settings.BASE_PATH, exist_ok=True)
        p = os.path.join(settings.BASE_PATH, COUNTRY_PREF_FILE)
        with open(p, 'w') as f:
            json.dump({'code': code}, f)
    except Exception:
        pass
    try:
        subprocess.run(['sudo', 'iw', 'reg', 'set', code],
                       timeout=5, capture_output=True)
    except Exception:
        pass


def apply_saved_country():
    """Re-apply the saved regulatory domain at boot (called once by MedicalUI)."""
    code = get_saved_country_code()
    if code:
        try:
            subprocess.run(['sudo', 'iw', 'reg', 'set', code],
                           timeout=5, capture_output=True)
        except Exception:
            pass


# ─── SF Pro font resolution ───────────────────────────────────────────────────
# Resolved lazily on the first BaseWindow init (tkfont.families() needs Tk).
# Priority: SF Pro Display → SF Pro Text → Helvetica Neue → Inter →
#           DejaVu Sans → Helvetica → Arial (final fallback)
# Install SF Pro on Linux with:
#   sudo mkdir -p /usr/share/fonts/truetype/sfpro
#   sudo cp SF-Pro*.otf /usr/share/fonts/truetype/sfpro/
#   sudo fc-cache -fv
_SF_FONT: str = "Arial"          # updated in place by _init_sf_font()
_SF_FONT_RESOLVED = False


def _init_sf_font() -> None:
    """Detect the best SF Pro-style font and update _SF_FONT."""
    global _SF_FONT, _SF_FONT_RESOLVED
    _SF_FONT_RESOLVED = True
    try:
        available = set(tkfont.families())
        for candidate in (
            "SF Pro Display",
            "SF Pro Text",
            "SF Pro",
            ".SF NS Display",
            ".AppleSystemUIFont",
            "Helvetica Neue",
            "Inter",
            "DejaVu Sans",
            "Helvetica",
        ):
            if candidate in available:
                _SF_FONT = candidate
                return
    except Exception:
        pass
    # Keep Arial as final fallback


# ═══════════════════════════════════════════════════════════════════════════════
# BASE WINDOW - Round display aware layout system
#  content within 70% inscribed circle
# ═══════════════════════════════════════════════════════════════════════════════
class BaseWindow:
    S = 480       # display pixel size
    CX = 240      # center x
    CY = 240      # center y
    R = 240       # display radius
    SR = 170      # safe content radius (70.7% of display)
    # Derived safe zones
    TITLE_Y = 75  # title text y position
    CONTENT_TOP = 100
    CONTENT_BOT = 365
    ACTION_Y = 390  # action buttons y
    # Horizontal safe bounds at different y positions
    # At center: full 340px width. At top/bottom: narrower.

    def __init__(self, root, main_app, title=""):
        global _SF_FONT_RESOLVED
        if not _SF_FONT_RESOLVED:
            _init_sf_font()
        self.root = root
        self.main_app = main_app
        self.mode = _get_theme()
        self.c = _tc(self.mode)
        self.win = tk.Toplevel(root)
        self.win.geometry(f"{self.S}x{self.S}+{root.winfo_x()}+{root.winfo_y()}")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="black")
        self.cv = tk.Canvas(self.win, width=self.S, height=self.S, bg="black", highlightthickness=0)
        self.cv.pack()
        self._bg()
        if title:
            self.cv.create_text(self.CX, self.TITLE_Y, text=title,
                                fill=self.c['text'], font=(_SF_FONT, 15, "bold"))

    def _bg(self):
        """Semi-transparent circular background — camera feed shows through
        at ~50% behind the window content (frosted dark overlay effect)."""
        img = Image.new("RGBA", (self.S, self.S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if self.mode == 'dark':
            # Background at 50% fill → combined with 80% window alpha ≈ 40% opaque
            # (60% camera visible through the background)
            d.ellipse([0, 0, self.S, self.S], fill=(14, 14, 22, 128))
            d.ellipse([4, 4, self.S-4, self.S-4], outline=(30, 30, 45, 80), width=1)
        else:
            d.ellipse([0, 0, self.S, self.S], fill=(242, 242, 248, 128))
            d.ellipse([4, 4, self.S-4, self.S-4], outline=(220, 220, 230, 80), width=1)
        self._bgp = ImageTk.PhotoImage(img)
        self.cv.create_image(self.CX, self.CY, image=self._bgp)
        # Window at 80% opacity — buttons/text are 80% visible,
        # background (already at 50% fill alpha) appears ~40% total.
        try:
            self.win.attributes('-alpha', 0.8)
        except (tk.TclError, AttributeError):
            pass

    def _safe_width(self, y):
        """Get available content width at a given y position (circle chord)."""
        dy = abs(y - self.CY)
        if dy >= self.SR:
            return 0
        return int(2 * math.sqrt(self.SR * self.SR - dy * dy))

    def is_open(self):
        try: return self.win and self.win.winfo_exists()
        except: return False

    def bring_to_front(self):
        if self.is_open(): self.win.lift()

    def close(self):
        if self.win:
            try: self.win.destroy()
            except: pass
            self.win = None
        # Restore icons on the main camera screen
        if self.main_app and hasattr(self.main_app, '_show_all_icons'):
            self.main_app._show_all_icons()

    def _pill(self, x, y, txt, col, tag="c", w=100, h=32, txt_col=None):
        """
        Pill button — sized for touch (min 48px touch target).

        Text color is auto-picked for contrast against the pill fill:
          • Dark fills (#000-#555) → white text
          • Bright fills (accents) → white text in dark mode, dark text in light mode
        Caller can override with `txt_col`.
        """
        r = h // 2
        self.cv.create_oval(x-w//2, y-r, x-w//2+h, y+r, fill=col, outline="", tags=tag)
        self.cv.create_oval(x+w//2-h, y-r, x+w//2, y+r, fill=col, outline="", tags=tag)
        self.cv.create_rectangle(x-w//2+r, y-r, x+w//2-r, y+r, fill=col, outline="", tags=tag)

        if txt_col is None:
            txt_col = self._pill_text_color(col)
        self.cv.create_text(x, y, text=txt, fill=txt_col, font=(_SF_FONT, 12, "bold"), tags=tag)

    # Cache of smooth-pill PhotoImages — keyed by (col, w, h, border, alpha) so
    # we don't re-render the same image every frame.
    def _smooth_pill(self, x, y, txt, col, tag="c", w=100, h=32, txt_col=None,
                     font=(_SF_FONT, 12, "bold"), border=None, alpha=255):
        """
        iOS Control-Center style glass pill.

        Layers (bottom → top):
          1. Base fill at `alpha` (lower alpha = frosted-translucent over the
             window background — true iPhone Control Center feel)
          2. Top vertical sheen (white fading from rim to mid-height)
          3. Top-left radial highlight (the "lit from upper-left" cue)
          4. Outer 1 px white rim at low alpha (the iOS frosted edge)
          5. Optional caller-specified border on top of #4

        `alpha` defaults to 255 for solid colored pills (accent / success /
        danger). Pass 90-180 for unselected/neutral pills to get the proper
        translucent gray look from the dark/light canvas behind it.
        """
        if not hasattr(self, "_pill_cache"):
            self._pill_cache = {}
        key = (col, w, h, border, alpha)
        photo = self._pill_cache.get(key)
        if photo is None:
            photo = self._render_glass_pill(col, w, h, border, alpha)
            self._pill_cache[key] = photo

        self.cv.create_image(x, y, image=photo, tags=tag)

        if txt_col is None:
            txt_col = self._pill_text_color(col)
        self.cv.create_text(x, y, text=txt, fill=txt_col, font=font, tags=tag)

    def _render_glass_pill(self, col, w, h, border=None, alpha=255):
        """iPhone glass pill renderer — see _smooth_pill for the layer model."""
        scale = 3
        W, H = w * scale, h * scale
        R = H // 2
        base_rgb = self._hex_to_rgba(col)[:3]

        # Master shape mask — every layer below is paste-clipped through it
        shape_mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(shape_mask).rounded_rectangle(
            [0, 0, W - 1, H - 1], radius=R, fill=255,
        )

        # ── 1. Base fill at requested alpha ──
        img = Image.new("RGBA", (W, H), (*base_rgb, alpha))

        # ── 2. Vertical sheen: white at top fades to mid-height,
        #       gentle black wash from mid to bottom for depth ──
        sheen = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sheen)
        for yy in range(H):
            t = yy / max(1, H - 1)
            if t < 0.55:
                a = int((1 - t / 0.55) ** 2 * 80)
                sd.line([(0, yy), (W, yy)], fill=(255, 255, 255, a))
            else:
                tt = (t - 0.55) / 0.45
                a = int(tt * 22)
                sd.line([(0, yy), (W, yy)], fill=(0, 0, 0, a))
        img = Image.alpha_composite(img, sheen)

        # ── 3. Top-left radial highlight (iOS "lit corner") ──
        spot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(spot).ellipse(
            [-int(W * 0.20), -int(H * 0.60),
             int(W * 0.62),  int(H * 0.72)],
            fill=(255, 255, 255, 55),
        )
        spot = spot.filter(ImageFilter.GaussianBlur(radius=6 * scale))
        img = Image.alpha_composite(img, spot)

        # ── 4. Outer 1 px white rim — the frosted edge ──
        rim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(rim).rounded_rectangle(
            [0, 0, W - 1, H - 1], radius=R,
            outline=(255, 255, 255, 70),
            width=max(1, scale),
        )
        img = Image.alpha_composite(img, rim)

        # ── 5. Caller-specified border (e.g. accent ring on active state) ──
        if border:
            bcol, bw = border
            br = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(br).rounded_rectangle(
                [0, 0, W - 1, H - 1], radius=R,
                outline=self._hex_to_rgba(bcol),
                width=bw * scale,
            )
            img = Image.alpha_composite(img, br)

        # Final paste-through-mask: any AA residue stays inside the pill
        final = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        final.paste(img, (0, 0), shape_mask)

        final = final.resize((w, h), Image.LANCZOS)
        return ImageTk.PhotoImage(final)

    @staticmethod
    def _hex_to_rgba(h):
        """Accept '#rrggbb' or already-tuple, return (r, g, b, 255)."""
        if isinstance(h, tuple):
            if len(h) == 3:
                return (*h, 255)
            return h
        h = h.lstrip("#")
        if len(h) == 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
        return (255, 255, 255, 255)

    def _smooth_card(self, x1, y1, x2, y2, fill, tag="c",
                     border=None, radius=14):
        """
        Anti-aliased rounded card (row background, info card, etc.).
        Like _smooth_pill but rectangular with configurable corner radius.
        """
        if not hasattr(self, "_card_cache"):
            self._card_cache = {}
        w, h = x2 - x1, y2 - y1
        if w <= 0 or h <= 0:
            return
            
        key = (fill, w, h, border, radius)
        photo = self._card_cache.get(key)
        if photo is None:
            scale = 3
            W, H = w * scale, h * scale
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            
            if radius > 0:
                d.rounded_rectangle([0, 0, W - 1, H - 1],
                                    radius=radius * scale,
                                    fill=self._hex_to_rgba(fill))
            else:
                d.rectangle([0, 0, W - 1, H - 1], fill=self._hex_to_rgba(fill))
                
            if border:
                bcol, bw = border
                if radius > 0:
                    d.rounded_rectangle([0, 0, W - 1, H - 1],
                                        radius=radius * scale,
                                        outline=self._hex_to_rgba(bcol),
                                        width=bw * scale)
                else:
                    d.rectangle([0, 0, W - 1, H - 1],
                                outline=self._hex_to_rgba(bcol),
                                width=bw * scale)
            img = img.resize((w, h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._card_cache[key] = photo
        # Anchored at top-left
        self.cv.create_image(x1, y1, image=photo, anchor="nw", tags=tag)

    def _pill_text_color(self, fill_hex):
        """Pick the most readable text color for a given pill fill."""
        # Strip leading '#'
        h = fill_hex.lstrip('#')
        if len(h) != 6:
            return "white"
        try:
            r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16)
        except ValueError:
            return "white"
        # Perceived luminance (Rec. 709)
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        # Bright fills get dark text; dark fills get white text
        return "#0a0a14" if lum > 160 else "white"

    def _clr(self):
        # "c" = main content layer, "msg" = transient overlay (e.g. "CONNECTING…").
        # Both must be cleared on every page transition so a previous page's
        # status text never bleeds into the next page.
        # Wrapped in try/except because background callbacks (Wi-Fi scan,
        # connect) can fire after the user already closed the window.
        try:
            self.cv.delete("c")
            self.cv.delete("msg")
            self.cv.delete("kb")
            self.cv.delete("cs_overlay")
            self.cv.delete("cs_list")
            self.cv.delete("status")
            self.cv.delete("spin")
            self.cv.delete("kf")
        except tk.TclError:
            pass

    # ─── iOS-style neutral pill helpers ──────────────────────────────
    # These wrap _smooth_pill with the right (color, alpha) combo for the
    # current theme so every window uses the same Control-Center look.
    def _neutral_fill(self):
        """Frosted-gray base color + alpha for the current theme."""
        if self.mode == 'dark':
            return IOS_GLASS_DARK_FILL, IOS_GLASS_DARK_ALPHA
        return IOS_GLASS_LIGHT_FILL, IOS_GLASS_LIGHT_ALPHA

    def _glass_pill(self, x, y, txt, w=100, h=32, *, active=False,
                    danger=False, success=False, font=(_SF_FONT, 12, "bold"),
                    tag="c"):
        """
        One-call iOS pill. Picks the right color/alpha based on state:
          • active   → accent (cyan-blue) opaque
          • danger   → iOS red opaque
          • success  → iOS green opaque
          • default  → frosted neutral (translucent gray/white)

        All pills share the same glass treatment from _smooth_pill so the
        whole UI feels like Control Center.
        """
        if active:
            col, alpha = self.c['accent'], 255
        elif danger:
            col, alpha = IOS_RED, 255
        elif success:
            col, alpha = IOS_GREEN, 255
        else:
            col, alpha = self._neutral_fill()
        self._smooth_pill(x, y, txt, col, tag=tag, w=w, h=h,
                          font=font, alpha=alpha)

    # ═══════════════════════════════════════════════════════════════════════════════
    # UNIVERSAL UI COMPONENTS (Keyboards & Status Overlays)
    # ═══════════════════════════════════════════════════════════════════════════════
    def draw_key(self, x, y, ch, w, h, tag="kb"):
        """Universal pill-key renderer with intelligent font scaling."""
        hw, hh = w // 2, h // 2
        r = min(6, hh)
        bg = "#3a3f55" if self.mode == 'dark' else "#e8ecf2"
        bd = "#5a607a" if self.mode == 'dark' else "#aab2c2"
        kbtag = f"c {tag}"

        # High-performance pseudo-rounded rect
        self.cv.create_rectangle(x-hw+r, y-hh, x+hw-r, y+hh, fill=bg, outline="", tags=kbtag)
        self.cv.create_rectangle(x-hw, y-hh+r, x+hw, y+hh-r, fill=bg, outline="", tags=kbtag)
        self.cv.create_oval(x-hw, y-hh, x-hw+2*r, y-hh+2*r, fill=bg, outline="", tags=kbtag)
        self.cv.create_oval(x+hw-2*r, y-hh, x+hw, y-hh+2*r, fill=bg, outline="", tags=kbtag)
        self.cv.create_oval(x-hw, y+hh-2*r, x-hw+2*r, y+hh, fill=bg, outline="", tags=kbtag)
        self.cv.create_oval(x+hw-2*r, y+hh-2*r, x+hw, y+hh, fill=bg, outline="", tags=kbtag)
        self.cv.create_line(x-hw+r, y-hh, x+hw-r, y-hh, fill=bd, tags=kbtag)
        self.cv.create_line(x-hw+r, y+hh, x+hw-r, y+hh, fill=bd, tags=kbtag)

        d = "␣" if ch == " " else ch
        if len(d) > 2: fs = max(12, min(15, w // 5))
        elif len(d) == 1: fs = max(15, min(22, int(w / 2.5)))
        else: fs = max(12, min(15, w // 4))
        self.cv.create_text(x, y, text=d, fill=self.c['text'], font=(_SF_FONT, fs, "bold"), tags=kbtag)
        return (x - hw, y - hh, x + hw, y + hh)

    def draw_keyboard(self, start_y, end_y, layout='full', caps=False, sym_mode=False):
        """Universal keyboard layout engine. Safely wraps keys within circular bounds."""
        cx, R, keys = self.S // 2, 210 if layout == 'compact' else 200, {}
        
        if sym_mode: rows = ["1234567890", "!@#$%^&*()", "-_=+[]{}/\\", ".,;:'\"?|~`"]
        elif caps: rows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
        else: rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
        
        row_h = max(26, min(46, (end_y - start_y) // (len(rows) + 1) - 2))
        gap = 2 if layout == 'compact' else 4

        # Standard QWERTY / Symbol rows
        for ri, row in enumerate(rows):
            ky = start_y + ri * (row_h + gap) + row_h // 2
            dy = abs(ky - self.CY)
            if dy >= R: continue
            
            avail_w = 2 * math.sqrt(max(0, R * R - dy * dy)) - (16 if layout == 'compact' else 28)
            kw = max(30, min(46, int((avail_w - (len(row) - 1) * gap) / len(row))))
            sx = cx - (len(row) * kw + (len(row) - 1) * gap) // 2
            
            for ci, ch in enumerate(row):
                keys[ch] = self.draw_key(sx + ci * (kw + gap) + kw // 2, ky, ch, kw, row_h - 2)
                
        # Action row (Space, Backspace, Modifiers)
        ay = start_y + len(rows) * (row_h + gap) + row_h // 2
        dy = abs(ay - self.CY)
        if dy < R:
            avail_w = 2 * math.sqrt(max(0, R * R - dy * dy)) - (16 if layout == 'compact' else 28)
            if layout == 'compact':
                sw, bw = max(70, int(avail_w * 0.55)), min(50, int(avail_w * 0.25))
                sx = cx - (sw + bw + 8) // 2
                keys[" "] = self.draw_key(sx + sw // 2, ay, " ", sw, row_h - 2)
                keys["⌫"] = self.draw_key(sx + sw + 8 + bw // 2, ay, "⌫", bw, row_h - 2)
            else:
                sl, sw, cw, bw = "ABC" if sym_mode else "!#+", min(64, int(avail_w * 0.18)), min(64, int(avail_w * 0.18)), min(60, int(avail_w * 0.16))
                spw = max(96, avail_w - sw - cw - bw - 3 * gap)
                sx = cx - (sw + cw + spw + bw + 3 * gap) // 2
                keys[sl] = self.draw_key(sx + sw // 2, ay, sl, sw, row_h - 2)
                keys["CAPS"] = self.draw_key(sx + sw + gap + cw // 2, ay, "CAPS", cw, row_h - 2)
                keys[" "] = self.draw_key(sx + sw + cw + 2 * gap + spw // 2, ay, " ", spw, row_h - 2)
                keys["⌫"] = self.draw_key(sx + sw + cw + spw + 3 * gap + bw // 2, ay, "⌫", bw, row_h - 2)
        return keys

    def flash_key(self, x1, y1, x2, y2, ch, callback=None):
        """Universal key touch feedback. Accents the key and provides a glowing ring."""
        cx, cy, w, h = (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1
        r, pad, accent = min(8, h // 2), 5, self.c['accent']
        gx1, gy1, gx2, gy2 = x1 - pad, y1 - pad, x2 + pad, y2 + pad
        
        # Glowing aura outline
        for k in [gx1, gx1+r, x1, x1+r]:
            self.cv.create_rectangle(k, gy1 if k in (gx1, gx1+r) else y1, x2+pad if k in (gx1, gx1+r) else x2, gy2 if k in (gx1, gx1+r) else y2, fill=accent, outline="", tags="kf")
        
        d = "␣" if ch == " " else ch
        fs = max(15, min(22, int(w / 2.5))) if len(d) == 1 else max(12, min(15, w // 4))
        self.cv.create_text(cx, cy, text=d, fill=self._pill_text_color(accent), font=(_SF_FONT, fs, "bold"), tags="kf")
        
        def _clear():
            try: self.cv.delete("kf")
            except tk.TclError: pass
            if callback: callback()
            
        self.cv.after(110, _clear)

    def show_status_overlay(self, title, subtitle, accent, spinner=False, show_icon=True):
        """Universal status banner for blocking actions (Wi-Fi, updates)."""
        self.cv.delete("status", "spin", "kb", "c kb")
        cx, c, by1, by2 = self.S // 2, self.c, 150, self.ACTION_Y - 18
        self._status_visible = True
        
        self._smooth_card(cx - 168, by1, cx + 168, by2, fill=c['card_bg'], border=(accent, 2), radius=18, tag="status")
        mid = (by1 + by2) // 2
        self.cv.create_text(cx, mid + 12, text=title, fill=accent, font=(_SF_FONT, 18, "bold"), tags="status")
        if subtitle: self.cv.create_text(cx, mid + 38, text=subtitle, fill=c['text_secondary'], font=(_SF_FONT, 12, "bold"), tags="status")
        
        if spinner:
            self._spin_angle = 0
            self._status_icon_box = (cx - 26, mid - 58, cx + 26, mid - 6)
            self._animate_overlay_spinner(accent)
        elif show_icon:
            self.cv.create_oval(cx - 26, mid - 58, cx + 26, mid - 6, outline=accent, width=5, tags="status")
            self.cv.create_line(cx - 11, mid - 43, cx + 11, mid - 21, fill=accent, width=5, tags="status")
            self.cv.create_line(cx + 11, mid - 43, cx - 11, mid - 21, fill=accent, width=5, tags="status")

    def _animate_overlay_spinner(self, accent):
        if not getattr(self, '_status_visible', False) or not self.is_open(): return
        self.cv.delete("spin")
        self._spin_angle = (getattr(self, '_spin_angle', 0) - 18) % 360
        self.cv.create_arc(*getattr(self, '_status_icon_box', (self.S//2 - 26, 180, self.S//2 + 26, 232)), start=self._spin_angle, extent=270, style="arc", outline=accent, width=5, tags="spin")
        self.win.after(60, lambda: self._animate_overlay_spinner(accent))

# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
class SettingsWindow(BaseWindow):
    """
    Settings — three sections evenly spaced inside the round display.
       1. THEME       (Dark / Light)
       2. ICON STYLE  (Glass / White / Color)
       3. ICON HIDE DELAY  (slider, 3-30 s)
       4. Action row  (RESET / SHUTDOWN / EXIT)
    Brightness control removed — handled at OS / hardware level.
    """
    def __init__(self, root, main_app):
        super().__init__(root, main_app, "SETTINGS")
        self._delay = getattr(settings, 'UI_HIDE_DELAY_MS', 20000) // 1000
        self._isch = main_app._icons.scheme if main_app and hasattr(main_app, '_icons') else 'glass'
        # Sub-page state machine
        self._page = 'main'                # 'main' | 'country'
        self._shutdown_confirm = False
        # Country search state
        self._search = ''
        self._caps = False
        self._sym_mode = False
        self._keys = {}
        self._cs_items = []
        self._press_name = None             # country row pending tap
        self._press_moved = False
        # Country scrolling
        self._country_scroll_y = 0.0
        self._country_scroll_max = 0
        self._filtered_countries = []
        self._kb_visible = False  # country keyboard hidden until search tapped
        self._draw()
        self.cv.bind("<Button-1>", self._click)
        self.cv.bind("<B1-Motion>", self._drag)
        self.cv.bind("<ButtonRelease-1>", self._onrelease)

    def _draw(self):
        if self._page == 'country':
            self._draw_country()
        else:
            self._draw_main()

    def _refresh(self):
        self.cv.delete("all")
        self._bg()
        if self._page != 'country':
            self.cv.create_text(self.CX, self.TITLE_Y, text="SETTINGS", fill=self.c['text'], font=(_SF_FONT, 15, "bold"))
        self._draw()

    def _draw_main(self):
        cx, c = self.CX, self.c

        # Section labels
        section_lbl  = c['text_secondary']
        section_font = (_SF_FONT, 11, "bold")
        track_color  = "#3a3f55" if self.mode == 'dark' else "#c8ccd8"

        # ── Tighter spacing now that we have 4 sections instead of 3 ──
        sec_h = 50
        top   = self.CONTENT_TOP - 2

        # ─── Section 1: THEME ─────────────────────────────────────────
        s1y = top + 4
        self.cv.create_text(cx, s1y, text="THEME",
                            fill=section_lbl, font=section_font, tags="c")
        ty = s1y + 22
        self._glass_pill(cx - 56, ty, "DARK",
                         w=98, h=28, active=(self.mode == 'dark'))
        self._glass_pill(cx + 56, ty, "LIGHT",
                         w=98, h=28, active=(self.mode == 'light'))

        # ─── Section 2: ICON STYLE ────────────────────────────────────
        s2y = top + sec_h + 2
        self.cv.create_text(cx, s2y, text="ICON STYLE",
                            fill=section_lbl, font=section_font, tags="c")
        isy = s2y + 22
        self._schz = {}
        for i, (sid, lbl) in enumerate([('glass', 'GLASS'),
                                        ('white', 'WHITE'),
                                        ('color', 'COLOR')]):
            sx = cx - 84 + i * 84
            self._glass_pill(sx, isy, lbl, w=78, h=26,
                             active=(sid == self._isch))
            self._schz[sid] = (sx - 39, isy - 13, sx + 39, isy + 13)

        # ─── Section 3: ICON HIDE DELAY ───────────────────────────────
        s3y = top + sec_h * 2 + 2
        self.cv.create_text(cx, s3y, text="ICON HIDE DELAY",
                            fill=section_lbl, font=section_font, tags="c")
        self._dly = s3y + 22
        sw = self._safe_width(self._dly)
        self._sx1 = cx - sw // 2 + 30
        self._sx2 = cx + sw // 2 - 30
        self.cv.create_line(self._sx1, self._dly, self._sx2, self._dly,
                            fill=track_color, width=5, capstyle="round", tags="c")
        self._rddl()

        # ─── Section 4: REGION (country selection) ────────────────────
        s4y = top + sec_h * 3 + 20
        self.cv.create_text(cx, s4y, text="REGION",
                            fill=section_lbl, font=section_font, tags="c")
        ry = s4y + 28
        # Show current country as a tappable pill that opens the sub-page
        country_name = get_saved_country_name() or "Not set"
        # Trim long names so the pill never overflows
        display = country_name if len(country_name) <= 18 else country_name[:17] + "…"
        self._glass_pill(cx, ry, display, w=200, h=30,
                         active=False,
                         font=(_SF_FONT, 13, "bold"))

        # ─── Action row: RESET / SHUTDOWN / EXIT ──────────────────────
        ay = self.ACTION_Y + 4
        chord = self._safe_width(ay) - 28
        pill_w = max(78, min(102, (chord - 20) // 3))
        gap = 10
        self._glass_pill(cx - (pill_w + gap), ay, "RESET", w=pill_w, h=34)
        self._glass_pill(cx,                  ay, "SHUTDOWN",
                         w=pill_w, h=34, danger=True)
        self._glass_pill(cx + (pill_w + gap), ay, "EXIT", w=pill_w, h=34)

        # Hit zones
        self._zones = {
            'dark':     (cx - 110, ty - 14, cx - 6,   ty + 14),
            'light':    (cx + 6,   ty - 14, cx + 110, ty + 14),
            'region':   (cx - 100, ry - 15, cx + 100, ry + 15),
            'reset':    (cx - (pill_w + gap) - pill_w // 2, ay - 17,
                         cx - (pill_w + gap) + pill_w // 2, ay + 17),
            'shutdown': (cx - pill_w // 2, ay - 17, cx + pill_w // 2, ay + 17),
            'exit':     (cx + (pill_w + gap) - pill_w // 2, ay - 17,
                         cx + (pill_w + gap) + pill_w // 2, ay + 17),
        }
        if self._shutdown_confirm:
            overlay_w = self._safe_width(self.CY) - 40
            overlay_h = 150
            ox1 = cx - overlay_w // 2
            oy1 = 120
            ox2 = cx + overlay_w // 2
            oy2 = oy1 + overlay_h
            self._smooth_card(ox1, oy1, ox2, oy2,
                              fill=self.c['card_bg'],
                              border=(self.c['accent'], 2),
                              tag='c')
            self.cv.create_text(cx, oy1 + 26,
                                text="Confirm shutdown",
                                fill=self.c['text'],
                                font=(_SF_FONT, 14, "bold"),
                                tags="c")
            self.cv.create_text(cx, oy1 + 58,
                                text="Are you sure you want to shut down?",
                                fill=self.c['text_secondary'],
                                font=(_SF_FONT, 12),
                                tags="c")
            self._glass_pill(cx - 64, oy2 - 32, "CANCEL",
                             w=120, h=34, tag='c')
            self._glass_pill(cx + 64, oy2 - 32, "SHUTDOWN",
                             w=120, h=34, danger=True, tag='c')
            self._shutdown_confirm_z = {
                'cancel':   (cx - 64 - 60, oy2 - 32 - 17,
                             cx - 64 + 60, oy2 - 32 + 17),
                'shutdown': (cx + 64 - 60, oy2 - 32 - 17,
                             cx + 64 + 60, oy2 - 32 + 17),
            }
        else:
            self._shutdown_confirm_z = None

    # --- REGION sub-page: WiFi-style scrollable country list ---
    def _draw_country(self):
        cx, c = self.CX, self.c
        kb_visible = getattr(self, '_kb_visible', False)
        search = self._search.lower() if self._search else ''
        countries = [n for n in _SORTED_COUNTRIES if not search or search in n.lower()]
        self._filtered_countries = countries

        # Title
        self.cv.create_text(cx, 52, text='REGION', fill=c['text'], font=('Arial', 13, 'bold'), tags='c')

        # Search field (pill-shaped, wide)
        field_y, field_h = 74, 34
        # Use a wider radius than the conservative safe-zone so more text fits
        _fdy = abs(field_y + field_h // 2 - self.CY)
        _fr = 210
        field_w = int(2 * math.sqrt(max(0, _fr**2 - _fdy**2))) - 20
        fx1, fx2 = cx - field_w // 2, cx + field_w // 2
        ring = c['accent'] if kb_visible else c['card_border']
        self._smooth_pill(cx, field_y + field_h // 2, '', ring, w=field_w, h=field_h, alpha=200, tag='c', border=(ring, 2))
        self._smooth_pill(cx, field_y + field_h // 2, '', c['card_bg'], w=field_w - 4, h=field_h - 4, alpha=230, tag='c')
        if self._search:
            disp = self._search
            sc = c['text']
        else:
            disp = 'Search...'
            sc = c['text_secondary']
        # Clip text to fit inside the pill (show tail of typed text)
        search_font = tkfont.Font(family='Arial', size=13, weight='bold')
        text_avail = field_w - 50  # padding for left inset + clear button
        while disp and search_font.measure(disp) > text_avail:
            disp = disp[1:] if self._search else disp[:-1]
        self.cv.create_text(fx1 + 18, field_y + field_h // 2, text=disp,
                           anchor='w', fill=sc,
                           font=('Arial', 13, 'bold'), tags='c')
        if self._search:
            clr_x = fx2 - 16
            self.cv.create_text(clr_x, field_y + field_h // 2, text='X', fill=c['accent'], font=('Arial', 12, 'bold'), tags='c')
            self._clear_zone = (clr_x - 14, field_y, clr_x + 14, field_y + field_h)
        else:
            self._clear_zone = None
        self._search_zone = (fx1, field_y, fx2, field_y + field_h)

        # Country list (scrollable, WiFi-style pill rows)
        list_top = field_y + field_h + 10
        list_bot = 220 if kb_visible else self.ACTION_Y - 50
        row_h, gap = 38, 5
        visible_h = list_bot - list_top
        total_h = len(countries) * (row_h + gap) - gap if countries else 0
        self._country_scroll_max = max(0.0, total_h - visible_h)
        self._country_scroll_y = max(0.0, min(self._country_scroll_max, getattr(self, '_country_scroll_y', 0.0)))
        row_radius = 210
        def _chord(yy):
            dy = abs(yy - self.CY)
            return 2 * math.sqrt(max(0, row_radius**2 - dy**2)) if dy < row_radius else 100
        row_w = max(100, int(min(_chord(list_top), _chord(list_bot))) - 20)
        self._cs_items = []
        cur_name = get_saved_country_name()
        if not countries:
            self.cv.create_text(cx, (list_top + list_bot) // 2, text='No country found', fill=c['text_secondary'], font=('Arial', 12, 'bold'), tags='c')
        else:
            for i, name in enumerate(countries):
                y = list_top + i * (row_h + gap) + row_h // 2 - self._country_scroll_y
                # Only draw rows fully within the visible area (no overlap below)
                if y - row_h // 2 < list_top - 2 or y + row_h // 2 > list_bot + 2:
                    continue
                is_active = (name == cur_name)
                if is_active:
                    self._smooth_pill(cx, y, '', c['accent'], w=row_w, h=row_h, alpha=255, tag='c')
                    txt_col = self._pill_text_color(c['accent'])
                else:
                    ncol, nalpha = self._neutral_fill()
                    self._smooth_pill(cx, y, '', ncol, w=row_w, h=row_h, alpha=nalpha, tag='c')
                    txt_col = c['text']
                dn = name if len(name) <= 22 else name[:21] + '...'
                self.cv.create_text(cx, y, text=dn, fill=txt_col, font=('Arial', 12, 'bold'), tags='c')
                self._cs_items.append((name, cx - row_w//2, int(y) - row_h//2, cx + row_w//2, int(y) + row_h//2))

        # Scroll indicators
        if self._country_scroll_y > 0:
            self.cv.create_text(cx, list_top - 6, text='\u25b2', fill=c['text_secondary'], font=('Arial', 9), tags='c')
        if self._country_scroll_y < self._country_scroll_max:
            self.cv.create_text(cx, list_bot + 6, text='\u25bc', fill=c['text_secondary'], font=('Arial', 9), tags='c')

        # Keyboard (when search focused)
        self._keys = {}
        if kb_visible:
            self._keys = self.draw_keyboard(start_y=list_bot + 14, end_y=self.ACTION_Y - 6, layout='compact')

        # BACK button
        ay = self.ACTION_Y + 10
        self._glass_pill(cx, ay, 'BACK', w=90, h=30, tag='c')
        self._cs_back_z = (cx - 45, ay - 15, cx + 45, ay + 15)

        # Drag zone covers the full list area
        self._list_drag_zone = (0, list_top, self.S, list_bot)


    def _rddl(self):
        self.cv.delete("dl")
        rel = (self._delay - 3) / 27.0
        fx = self._sx1 + int((self._sx2 - self._sx1) * rel)
        self.cv.create_line(self._sx1, self._dly, fx, self._dly,
                            fill=self.c['warning'], width=6, capstyle="round", tags="dl")
        self.cv.create_oval(fx - 11, self._dly - 11, fx + 11, self._dly + 11,
                            fill="white", outline=self.c['warning'], width=2, tags="dl")
        self.cv.create_text(self.CX, self._dly + 22, text=f"{self._delay}s",
                            fill=self.c['text'], font=(_SF_FONT, 12, "bold"), tags="dl")

    def _click(self, event):
        x, y = event.x, event.y

        # ─── Country sub-page handling ────────────────────────────────
        if self._page == 'country':
            # Clear button tap
            if hasattr(self, '_clear_zone') and self._clear_zone:
                x1, y1, x2, y2 = self._clear_zone
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self._search = ''
                    self._country_scroll_y = 0.0
                    self._refresh()
                    return
            
            # Search field tap → show keyboard
            if hasattr(self, '_search_zone') and self._search_zone:
                x1, y1, x2, y2 = self._search_zone
                if x1 <= x <= x2 and y1 <= y <= y2:
                    if not getattr(self, '_kb_visible', False):
                        self._kb_visible = True
                        self._country_scroll_y = 0.0
                        self._refresh()
                    return
            
            # Country list item: Immediate "Tap to select" visual feedback
            for name, x1, y1, x2, y2 in getattr(self, '_cs_items', []):
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self._press_name = name
                    self._press_x = x
                    self._press_y = y
                    self._press_moved = False
                    self._smooth_pill((x1+x2)//2, (y1+y2)//2, "", self.c['accent'], w=x2-x1, h=y2-y1, alpha=255, tag="c cs_list")
                    self.cv.create_text(self.CX, (y1+y2)//2, text=name, anchor='center', fill=self._pill_text_color(self.c['accent']), font=(_SF_FONT, 15, "bold"), tags="c cs_list")
                    self.cv.tag_lower("cs_list", "cs_overlay")
                    return
            
            # BACK button — if keyboard open, close it first; else leave page
            if hasattr(self, '_cs_back_z'):
                x1, y1, x2, y2 = self._cs_back_z
                if x1 <= x <= x2 and y1 <= y <= y2:
                    if getattr(self, '_kb_visible', False):
                        self._kb_visible = False
                        self._country_scroll_y = 0.0
                        self._refresh()
                    else:
                        self._page = 'main'
                        self._refresh()
                    return
            
            # Keyboard keys
            for ch, (x1, y1, x2, y2) in self._keys.items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    # Apply input immediately so fast typing never drops a key
                    if ch == "⌫":     # Backspace
                        self._search = self._search[:-1]
                    elif ch == " ":   # Space
                        self._search += ' '
                    else:             # Regular key
                        self._search += ch
                    self._country_scroll_y = 0.0  # Reset scroll on edit
                    # Show touch feedback, then redraw
                    self.flash_key(x1, y1, x2, y2, ch, callback=self._refresh)
                    return
            return

        # ─── Main page ────────────────────────────────────────────────
        if self._shutdown_confirm and self._shutdown_confirm_z:
            for n, (x1, y1, x2, y2) in self._shutdown_confirm_z.items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    if n == 'cancel':
                        self._shutdown_confirm = False
                        self._refresh()
                        return
                    if n == 'shutdown':
                        self._shutdown_confirm = False
                        self._perform_shutdown()
                        return
            return

        for n, (x1, y1, x2, y2) in self._zones.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                if   n == 'dark':     self._setmode('dark')
                elif n == 'light':    self._setmode('light')
                elif n == 'shutdown':
                    self._shutdown_confirm = True
                    self._refresh()
                    return
                elif n == 'exit':     self.close()
                elif n == 'reset':    self._reset_defaults()
                elif n == 'region':
                    self._page = 'country'
                    self._search = ''
                    self._caps = False
                    self._sym_mode = False
                    self._kb_visible = False   # start without keyboard (7 countries)
                    self._country_scroll_y = 0.0
                    self._refresh()
                return
        for sid, (x1, y1, x2, y2) in self._schz.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                self._isch = sid
                if self.main_app and hasattr(self.main_app, '_icons'):
                    self.main_app._icons.set_scheme(sid)
                if self.main_app and hasattr(self.main_app, 'refresh_icons'):
                    self.main_app.refresh_icons()
                self._save_pref('icon_scheme', sid)
                self._refresh()
                return
        # Slider hit (delay)
        if self._sx1 - 12 <= x <= self._sx2 + 12 and self._dly - 16 <= y <= self._dly + 16:
            self._setdl(x)

    def _select_country(self, name):
        """Persist + apply the country, then return to main settings."""
        code = COUNTRIES.get(name, 'US')
        save_country(code)
        self._save_pref('country_code', code)
        self._page = 'main'
        self._country_scroll_y = 0.0
        self._kb_visible = False  # Reset keyboard state for next visit
        self._refresh()

    def _drag(self, event):
        x, y = event.x, event.y
        
        if self._page == 'country':
            if hasattr(self, '_list_drag_zone'):
                lx1, ly1, lx2, ly2 = self._list_drag_zone
                if lx1 <= x <= lx2 and ly1 <= y <= ly2:
                    if not hasattr(self, '_drag_start_y'):
                        self._drag_start_y = y
                        self._drag_start_scroll_y = getattr(self, '_country_scroll_y', 0.0)
                    else:
                        # 1:1 mapping → smooth, predictable scrolling
                        drag_delta = self._drag_start_y - y
                        new_scroll = self._drag_start_scroll_y + drag_delta
                        new_scroll = max(0.0, min(getattr(self, '_country_scroll_max', 0.0), new_scroll))
                        # Any real movement cancels a pending row-tap
                        if abs(drag_delta) > 3:
                            self._press_moved = True
                        if new_scroll != getattr(self, '_country_scroll_y', 0.0):
                            self._country_scroll_y = new_scroll
                            self._refresh()
            return
        
        # Original delay slider handling
        if self._dly - 20 <= y <= self._dly + 20:
            self._setdl(x)
    
    def _ondrag_end(self, event):
        """Clear drag state when drag ends."""
        if hasattr(self, '_drag_start_y'):
            delattr(self, '_drag_start_y')
            delattr(self, '_drag_start_scroll_y')

    def _onrelease(self, event):
        """Handle country row selection on release if the gesture was a tap."""
        if self._page != 'country':
            self._ondrag_end(event)
            return

        self._ondrag_end(event)
        name = getattr(self, '_press_name', None)
        if name is None:
            return

        self._press_name = None
        moved = getattr(self, '_press_moved', False)
        dx = abs(event.x - getattr(self, '_press_x', event.x))
        dy = abs(event.y - getattr(self, '_press_y', event.y))
        if moved or dx > 8 or dy > 8:
            return

        for n, x1, y1, x2, y2 in getattr(self, '_cs_items', []):
            if n == name and x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self._select_country(name)
                return

    def _setdl(self, x):
        rel = max(0.0, min(1.0, (x - self._sx1) / max(1, self._sx2 - self._sx1)))
        self._delay = max(3, min(30, int(3 + rel * 27 + 0.5)))
        settings.UI_HIDE_DELAY_MS = self._delay * 1000
        self._rddl()
        self._save_pref('icon_hide_delay_s', self._delay)

    def _perform_shutdown(self):
        if os.name == 'posix':
            os.system("sudo shutdown now")
        else:
            self.close()
            if self.main_app and hasattr(self.main_app, '_shutdown'):
                self.main_app._shutdown()

    def _setmode(self, mode):
        if mode == self.mode:
            return
        _save_theme(mode)
        self.mode = mode
        self.c = _tc(mode)
        if self.main_app:
            self.main_app.current_mode = mode
        self._save_pref('theme', mode)
        self._refresh()

    def _save_pref(self, key, value):
        """Persist a single preference key through the main app's prefs."""
        if self.main_app and hasattr(self.main_app, '_prefs'):
            self.main_app._prefs[key] = value
            self.main_app._save_prefs(self.main_app._prefs)

    def _reset_defaults(self):
        """Reset all settings to factory defaults (no brightness anymore)."""
        self._delay = 7
        self._isch = 'glass'
        settings.UI_HIDE_DELAY_MS = 7000
        if self.main_app and hasattr(self.main_app, '_icons'):
            self.main_app._icons.set_scheme('glass')
        if self.main_app and hasattr(self.main_app, 'refresh_icons'):
            self.main_app.refresh_icons()
        _save_theme('dark')
        self.mode = 'dark'
        self.c = _tc('dark')
        if self.main_app:
            self.main_app.current_mode = 'dark'
        self._refresh()


# ═══════════════════════════════════════════════════════════════════════════════
# WIFI - First shows menu (WiFi Scan / Country), then flows
# ═══════════════════════════════════════════════════════════════════════════════
class WifiWindow(BaseWindow):
    # Country list moved to module-level COUNTRIES (shared with Settings).

    # Backwards-compat aliases used by older code paths in this class
    COUNTRIES = COUNTRIES                                # noqa: F811

    @classmethod
    def _sorted_countries(cls):
        return _SORTED_COUNTRIES

    def __init__(self, root, main_app):
        # No BaseWindow title — each WiFi sub-page draws its own header.
        # (A BaseWindow title is untagged and would persist on every page.)
        super().__init__(root, main_app, "")
        self._page = 'menu'
        self._nets = []
        self._ssid = None
        self._pw = ""
        self._caps = False
        self._show_pw = False
        self._scroll = 0
        self._scan_scroll = 0
        self._drag_y = None
        self._search = ''
        self._connecting = False   # WiFi connect-in-progress (spinner) flag
        self._status_visible = False
        self._press_ssid = None    # SSID under a pending press (tap vs scroll)
        self._press_moved = False
        # Country selection now lives in SETTINGS. WiFi window always goes
        # straight to network scan. (We still write a default if the user
        # somehow opens WiFi without ever visiting Settings — keeps `nmcli`
        # happy.)
        if not self._has_saved_country():
            self._save_country('US')
        self._draw_scan()
        self.cv.bind("<Button-1>", self._click)
        self.cv.bind("<B1-Motion>", self._ondrag)
        self.cv.bind("<ButtonRelease-1>", self._onrelease)

    # ─── Country preference persistence (delegates to module helpers) ───
    def _has_saved_country(self):
        return get_saved_country_code() is not None

    def _save_country(self, code):
        save_country(code)

    def _select_country(self, name):
        """Apply the regulatory code, persist preference, and go to scan."""
        code = COUNTRIES.get(name, 'US')
        save_country(code)
        self._nets = []
        self._scan_scroll = 0
        self._draw_scan()

    def _draw_menu(self):
        # Country lives in Settings now — go straight to scan.
        self._draw_scan()

    def _draw_country(self):
        # Country selection moved to Settings. Skip straight to scan.
        self._draw_scan()

    def _draw_scan(self):
        """
        Network list — iOS-style pill rows.
          • Each network is a wide frosted pill
          • Row layout: [ SSID (left 3/4) | signal bars (right 1/4) ]
          • All rows equal width (chord at narrowest visible row)
          • Scrollable; REFRESH / EXIT action row at the bottom
        """
        self._page = 'scan'
        self._clr()
        cx, c = self.S // 2, self.c

        # Title (no "Wi-Fi" prefix — keep it short and clean)
        self.cv.create_text(cx, 50, text="NETWORKS",
                            fill=c['text'], font=(_SF_FONT, 15, "bold"), tags="c")

        # Action row drawn at bottom regardless of scan state
        if not self._nets:
            self.cv.create_text(cx, self.CY,
                                text="Scanning…",
                                fill=c['text_secondary'],
                                font=(_SF_FONT, 14, "bold"), tags="c")
            threading.Thread(target=self._do_scan, daemon=True).start()
            self._draw_scan_actions()
            return

        # ─── List geometry ─────────────────────────────────────────────
        self._items = []
        list_top = 80
        list_bot = self.ACTION_Y - 30
        row_h = 42
        gap = 6

        # Equal-width rows. Use a wider radius than the conservative safe-zone
        # (SR) so SSID rows are much wider, while the row corners still stay
        # clear of the physical 240px bezel. Width is bound by the row edge
        # nearest the bezel (the top row here).
        row_radius = 224
        def _chord(yy):
            d = abs(yy - self.CY)
            return 2 * math.sqrt(max(0.0, row_radius * row_radius - d * d))
        narrowest = min(_chord(list_top), _chord(list_bot))
        row_w = max(0, int(narrowest) - 14)
        x1 = cx - row_w // 2
        x2 = cx + row_w // 2

        # Split the row: SSID gets the left 3/4, signal the right 1/4.
        # A subtle divider keeps the two zones from ever visually merging.
        sig_zone_w = max(40, row_w // 4)
        split_x = x2 - sig_zone_w
        ssid_pad = 18

        # ─── Render network pills (scrollable) ─────────────────────────
        ssid_font = tkfont.Font(family=_SF_FONT, size=14, weight="bold")
        ssid_avail = (split_x - 6) - (x1 + ssid_pad)        # usable SSID width
        for i, net in enumerate(self._nets):
            y = list_top + i * (row_h + gap) - self._scan_scroll + row_h // 2
            # Skip rows outside the viewport
            if y < list_top - 10 or y > list_bot + 10:
                continue

            # Frosted neutral pill (whole row tappable)
            neutral_col, neutral_alpha = self._neutral_fill()
            self._smooth_pill(
                cx, y, "",
                neutral_col,
                w=row_w, h=row_h,
                alpha=neutral_alpha,
            )

            # SSID — left 3/4, fit to the available width (ellipsis if needed)
            ssid_txt = net['ssid']
            if ssid_font.measure(ssid_txt) > ssid_avail:
                while ssid_txt and ssid_font.measure(ssid_txt + "…") > ssid_avail:
                    ssid_txt = ssid_txt[:-1]
                ssid_txt += "…"
            self.cv.create_text(x1 + ssid_pad, y,
                                text=ssid_txt,
                                anchor='w', fill=c['text'],
                                font=ssid_font, tags="c")

            # Thin divider between SSID and signal zones
            self.cv.create_line(split_x, y - row_h // 2 + 8,
                                split_x, y + row_h // 2 - 8,
                                fill=c['card_border'], tags="c")

            # Signal bars (4) — centered in the right 1/4 zone, iOS green
            bars = min(4, max(1, net['signal'] // 25))
            inactive_bar = ("#3a3a4a" if self.mode == 'dark' else "#c0c4cc")
            group_w = 4 * 6 - 2                              # 4 bars, 6px pitch
            bar_x = split_x + (sig_zone_w - group_w) // 2
            for b in range(4):
                bh = 4 + b * 4
                bc = IOS_GREEN if b < bars else inactive_bar
                self.cv.create_rectangle(bar_x + b * 6,
                                         y + 8 - bh,
                                         bar_x + b * 6 + 4,
                                         y + 8,
                                         fill=bc, outline="", tags="c")

            # Touch zone == drawn pill bounds
            self._items.append((net['ssid'],
                                x1, y - row_h // 2,
                                x2, y + row_h // 2))

        # Scroll metric for drag handling
        total_h = len(self._nets) * (row_h + gap) - gap
        self._scan_max = max(0, total_h - (list_bot - list_top))

        self._draw_scan_actions()

    def _draw_scan_actions(self):
        """Action row for the scan page — REFRESH (green active) / EXIT (red)."""
        cx = self.S // 2
        ay = self.ACTION_Y + 6
        # Wider action buttons for easier tapping
        bw = 138
        off = bw // 2 + 6
        self._glass_pill(cx - off, ay, "REFRESH", w=bw, h=38, active=True,
                         font=(_SF_FONT, 13, "bold"))
        self._glass_pill(cx + off, ay, "EXIT", w=bw, h=38, danger=True,
                         font=(_SF_FONT, 13, "bold"))
        self._refresh_zone = (cx - off - bw // 2, ay - 19, cx - off + bw // 2, ay + 19)
        self._exit_zone    = (cx + off - bw // 2, ay - 19, cx + off + bw // 2, ay + 19)

    def _do_scan(self):
        try:
            r = subprocess.run(['nmcli','-t','-f','SSID,SIGNAL','dev','wifi','list'],
                               capture_output=True, text=True, timeout=15)
            nets, seen = [], set()
            for line in r.stdout.strip().split('\n'):
                parts = line.split(':')
                if len(parts)>=2 and parts[0] and parts[0] not in seen:
                    seen.add(parts[0])
                    nets.append({'ssid':parts[0],'signal':int(parts[1]) if parts[1].isdigit() else 50})
            nets.sort(key=lambda n: n['signal'], reverse=True)
            self._nets = nets
        except: self._nets = []
        if self.is_open(): self.win.after(0, self._draw_scan)

    def _draw_pw(self):
        """
        Password entry — round display split into clean zones:
          • TOP    → single "Connect to <SSID>" line (no overlap) + input
          • MIDDLE → keyboard
          • BOTTOM → OK / CANCEL action row (kept on-screen, above the bezel)
        """
        self._page = 'pw'
        self._status_visible = False
        self._clr()
        self._connecting = False   # stop any in-flight connecting spinner
        cx, c = self.S // 2, self.c

        # ─── TOP ZONE ─────────────────────────────────────────────────
        # Single line: "Connect to <SSID>" — no separate stacked labels that
        # would collide with the input box below.
        ssid = (self._ssid or "")[:18]
        self.cv.create_text(cx, 64, text=f"Connect to {ssid}",
                            fill=c['accent'],
                            font=(_SF_FONT, 14, "bold"), tags="c")

        # Password field — sized to match the country search input
        sw = self._safe_width(118)
        fx1 = cx - sw // 2 + 8
        fx2 = cx + sw // 2 - 8
        eye_pad = 40                                          # space reserved for eye toggle
        ifx2 = fx2 - eye_pad

        # Field bounds: y=88..132 (~44 px tall — big finger target)
        fld_y1, fld_y2 = 88, 132
        fld_cy = (fld_y1 + fld_y2) // 2
        self.cv.create_rectangle(fx1, fld_y1, ifx2, fld_y2,
                                 fill=c['card_bg'],
                                 outline=c['accent'], width=2, tags="c")

        # Password content — large bold text, clipped to the input box so it
        # never overflows. We trim from the LEFT (keep the tail visible) like a
        # real password field as the user keeps typing.
        text_x = fx1 + 14
        avail_text_w = (ifx2 - 10) - text_x        # usable width inside the box
        pw_font = tkfont.Font(family=_SF_FONT, size=17, weight="bold")
        if self._pw:
            full = self._pw if self._show_pw else "•" * len(self._pw)
            disp = full
            # Drop leading chars until the string fits the box width
            while disp and pw_font.measure(disp) > avail_text_w:
                disp = disp[1:]
            pc = c['text']
        else:
            disp = "Enter Password"
            # Placeholder may be longer than the box too — trim its tail
            while disp and pw_font.measure(disp) > avail_text_w:
                disp = disp[:-1]
            pc = c['text_secondary']
        self.cv.create_text(text_x, fld_cy, text=disp, anchor='w',
                            fill=pc, font=pw_font, tags="c")

        # Eye / show-password toggle — sits in the reserved eye_pad band
        ex, ey = fx2 - eye_pad // 2, fld_cy
        ec = c['accent'] if self._show_pw else c['text_secondary']
        self.cv.create_oval(ex - 11, ey - 7, ex + 11, ey + 7,
                            outline=ec, width=2, tags="c")
        self.cv.create_oval(ex - 4, ey - 4, ex + 4, ey + 4,
                            fill=ec, tags="c")
        if not self._show_pw:
            self.cv.create_line(ex - 11, ey + 9, ex + 11, ey - 9,
                                fill=ec, width=2, tags="c")
        # Generous touch zone (covers the whole eye_pad band)
        self._eye_z = (ifx2, fld_y1, fx2, fld_y2)

        # Subtle separator below the field, above the keyboard
        self.cv.create_line(fx1 + 16, 148, fx2 - 16, 148,
                            fill=c['card_border'], width=1, tags="c kb")

        # ─── KEYBOARD ─────────────────────────────────────────────────
        # Keyboard layout/size unchanged — it still renders from start_y but is
        # now bounded above the action row so OK/CANCEL stay on-screen.
        self._keys = self.draw_keyboard(start_y=158, end_y=self.ACTION_Y - 22, layout='full', caps=self._caps, sym_mode=getattr(self, '_sym_mode', False))

        # ─── ACTION ROW: OK / CANCEL ──────────────────────────────────
        # Pulled up to ACTION_Y so the pills sit on-screen within the round
        # bezel (the old y=446 pushed them off the bottom of the display).
        ay = self.ACTION_Y
        self._glass_pill(cx - 64, ay, "OK",     w=110, h=34, success=True, tag="c kb")
        self._glass_pill(cx + 64, ay, "CANCEL", w=110, h=34, danger=True, tag="c kb")
        self._conn_z = (cx - 119, ay - 17, cx - 9,  ay + 17)
        self._canc_z = (cx + 9,   ay - 17, cx + 119, ay + 17)


    def _click(self, event):
        x, y = event.x, event.y
        if self._page in ('menu', 'country_search', 'country'):
            # Country selection moved to Settings — go straight to scan.
            self._draw_scan()
            return
        elif self._page == 'scan':
            if hasattr(self,'_refresh_zone'):
                x1,y1,x2,y2=self._refresh_zone
                if x1<=x<=x2 and y1<=y<=y2: self._nets=[]; self._scan_scroll=0; self._draw_scan(); return
            if hasattr(self,'_exit_zone'):
                x1,y1,x2,y2=self._exit_zone
                if x1<=x<=x2 and y1<=y<=y2: self.close(); return
            # SSID rows: DON'T open on press. Record the gesture start; the
            # row only opens on release if the finger didn't move (a tap),
            # leaving press+drag free for scrolling the list.
            for ssid,x1,y1,x2,y2 in self._items:
                if x1<=x<=x2 and y1<=y<=y2:
                    self._press_ssid = ssid
                    self._press_x = x
                    self._press_y = y
                    self._press_t = time.monotonic()
                    self._press_moved = False
                    return
        elif self._page == 'pw':
            # Ignore all taps while a connection attempt is in progress
            # or while a failure banner is still visible.
            if getattr(self, '_connecting', False) or getattr(self, '_status_visible', False):
                return
            # Eye
            if hasattr(self,'_eye_z'):
                x1,y1,x2,y2=self._eye_z
                if x1<=x<=x2 and y1<=y<=y2: self._show_pw=not self._show_pw; self._draw_pw(); return
            # Keys
            for ch,(x1,y1,x2,y2) in self._keys.items():
                if x1<=x<=x2 and y1<=y<=y2:
                    # CAPS / symbol / connect just redraw — no flash needed
                    if ch=="CAPS":
                        self._caps=not self._caps; self._draw_pw(); return
                    if ch in ("!#+","ABC"):
                        self._sym_mode = not getattr(self, '_sym_mode', False)
                        self._draw_pw(); return
                    if ch=="⏎":
                        self._do_connect(); return
                    # Text-editing keys: apply immediately, then flash
                    if ch=="⌫": self._pw=self._pw[:-1]
                    elif ch==" ": self._pw+=" "
                    else: self._pw+=ch
                    self.flash_key(x1, y1, x2, y2, ch, callback=self._draw_pw)
                    return
            # Connect/Cancel
            if hasattr(self,'_conn_z'):
                x1,y1,x2,y2=self._conn_z
                if x1<=x<=x2 and y1<=y<=y2: self._do_connect(); return
            if hasattr(self,'_canc_z'):
                x1,y1,x2,y2=self._canc_z
                if x1<=x<=x2 and y1<=y<=y2: self._draw_scan(); return
        elif self._page == 'devices':
            if hasattr(self, '_dev_refresh_z'):
                x1, y1, x2, y2 = self._dev_refresh_z
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self._draw_devices()
                    return
            if hasattr(self, '_dev_done_z'):
                x1, y1, x2, y2 = self._dev_done_z
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self.close()
                    return

    def _ondrag(self, event):
        if self._page in ('country','scan'):
            if self._drag_y is None: self._drag_y=event.y; return
            dy = self._drag_y - event.y; self._drag_y=event.y
            if abs(dy)>2:
                # Any real movement cancels a pending row-tap so the gesture
                # is treated purely as a scroll.
                self._press_moved = True
                if self._page=='country':
                    self._scroll=max(0,min(getattr(self,'_max_scroll',0),self._scroll+dy)); self._draw_country()
                else:
                    self._scan_scroll=max(0,min(getattr(self,'_scan_max',0),self._scan_scroll+dy)); self._draw_scan()

    def _onrelease(self, event):
        """Open the pressed SSID only if it was a tap (no scrolling)."""
        self._drag_y = None
        if self._page != 'scan':
            return
        ssid = getattr(self, '_press_ssid', None)
        if ssid is None:
            return
        # Reset pending press state regardless of outcome
        self._press_ssid = None

        moved = getattr(self, '_press_moved', False)
        dx = abs(event.x - getattr(self, '_press_x', event.x))
        dy = abs(event.y - getattr(self, '_press_y', event.y))
        # A tap = finger stayed within a small radius and the list wasn't
        # scrolled. Otherwise it was a scroll gesture → do nothing.
        if not moved and dx <= 8 and dy <= 8:
            # Confirm the release is still over the same row
            for s, x1, y1, x2, y2 in self._items:
                if s == ssid and x1 <= event.x <= x2 and y1 <= event.y <= y2:
                    self._ssid = ssid
                    self._pw = ""
                    self._show_pw = False
                    self._draw_pw()
                    return

    def _draw_country_search(self):
        """Country selection moved to Settings. Stub redirects to scan."""
        self._draw_scan()

    def _do_connect(self):
        if not self._ssid or not self._pw:
            return

        def go():
            ok = False
            try:
                r = subprocess.run(
                    ['nmcli', 'dev', 'wifi', 'connect', self._ssid,
                     'password', self._pw],
                    capture_output=True, text=True, timeout=30,
                )
                ok = r.returncode == 0
            except Exception:
                ok = False
            if not self.is_open():
                return
            if ok:
                # Success → show the connected (IP) page
                self.win.after(0, self._draw_devices)
            else:
                self.win.after(0, self._show_failed)

        threading.Thread(target=go, daemon=True).start()
        self._status_visible = True
        self._show_connecting()

    def _show_connecting(self):
        """Animated 'Connecting…' banner shown while nmcli runs."""
        self._connecting = True
        self.show_status_overlay("Connecting…", f"to {(self._ssid or '')[:18]}", self.c['warning'], spinner=True)

    def _show_failed(self):
        """Red failure banner, then drop back to the password screen."""
        self._connecting = False
        self.show_status_overlay("Connection failed", "Check the password and try again", self.c['danger'], spinner=False)
        self.win.after(1800, self._draw_pw)

    def _msg(self, t, col):
        self.cv.delete("msg")
        self.cv.create_text(self.S // 2, self.S // 2, text=t,
                            fill=col, font=(_SF_FONT, 15, "bold"), tags="msg")

    # ─── Connected network info ──────────────────────────────────────
    def _gather_net_info(self):
        """Get current SSID and assigned IP address (best-effort)."""
        info = {'ssid': self._ssid or '', 'ip': '—',
                'gateway': '—', 'devices': []}
        # Active SSID via nmcli
        try:
            r = subprocess.run(
                ['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi'],
                capture_output=True, text=True, timeout=4)
            for line in r.stdout.strip().split('\n'):
                if line.startswith('yes:'):
                    info['ssid'] = line.split(':', 1)[1] or info['ssid']
                    break
        except Exception:
            pass
        # IP via `hostname -I` — the only network detail shown post-connect
        try:
            r = subprocess.run(['hostname', '-I'],
                               capture_output=True, text=True, timeout=3)
            ips = r.stdout.strip().split()
            if ips:
                info['ip'] = ips[0]
        except Exception:
            pass
        return info

    def _draw_devices(self):
        """Connected page: show the assigned IP address, then DONE."""
        self._page = 'devices'
        self._clr()
        self._connecting = False   # stop any in-flight connecting spinner
        cx, c = self.S // 2, self.c

        # Title
        self.cv.create_text(cx, 60, text="✓ CONNECTED",
                            fill=c['success'],
                            font=(_SF_FONT, 16, "bold"), tags="c")

        info = self._gather_net_info()

        # SSID (small, secondary) above the headline IP
        ssid = (info['ssid'] or '—')[:20]
        self.cv.create_text(cx, 150, text=ssid,
                            fill=c['text_secondary'],
                            font=(_SF_FONT, 13, "bold"), tags="c")

        # IP address — the only detail that matters here, shown large/centered
        self.cv.create_text(cx, 188, text="IP ADDRESS",
                            fill=c['text_secondary'],
                            font=(_SF_FONT, 12, "bold"), tags="c")
        self.cv.create_text(cx, 220, text=info['ip'],
                            fill=c['text'],
                            font=(_SF_FONT, 22, "bold"), tags="c")

        # Action row — DONE only (REFRESH removed)
        ay = self.ACTION_Y
        self._glass_pill(cx, ay, "DONE", w=140, h=36, active=True)
        self._dev_done_z = (cx - 70, ay - 18, cx + 70, ay + 18)
        # No refresh button on this page anymore
        self._dev_refresh_z = (-1, -1, -1, -1)


# ═══════════════════════════════════════════════════════════════════════════════
# SCOPE
# ═══════════════════════════════════════════════════════════════════════════════
class ScopeWindow(BaseWindow):
    """
    Scope picker — equal-width frosted pills with per-scope SVG-style icons.
    Layout per row: [icon | label]. Active row uses iOS green; inactive
    rows stay frosted neutral.
    """

    SCOPES = [
        ('opth',  'Ophthalmoscope'),
        ('otto',  'Otoscope'),
        ('derm',  'Dermatoscope'),
        ('micro', 'Microscope'),
    ]

    def __init__(self, root, main_app):
        super().__init__(root, main_app, "SELECT SCOPE")
        # PhotoImage cache so the icons survive Tk's GC
        self._scope_icons = {}
        self._draw()
        self.cv.bind("<Button-1>", self._click)

    # ─── Icon renderers (PIL → cached PhotoImage) ────────────────────
    def _scope_icon(self, sid, size, color):
        """
        Get a cached PhotoImage of the scope icon.
        Renders at 3× then downscales for AA.
        """
        key = (sid, size, color)
        if key in self._scope_icons:
            return self._scope_icons[key]

        scale = 3
        S = size * scale
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        rgba = self._hex_to_rgba(color)
        rgb = rgba[:3]
        w = max(2, int(S * 0.07))                     # stroke width

        if sid == 'opth':
            # Eye — outer almond, iris, pupil + a tiny highlight
            cx_, cy_ = S // 2, S // 2
            # Almond eye outline
            d.ellipse([int(S * 0.10), int(S * 0.30),
                       int(S * 0.90), int(S * 0.70)],
                      outline=rgb, width=w)
            # Iris
            d.ellipse([int(S * 0.36), int(S * 0.36),
                       int(S * 0.64), int(S * 0.64)],
                      outline=rgb, width=w)
            # Pupil
            d.ellipse([int(S * 0.45), int(S * 0.45),
                       int(S * 0.55), int(S * 0.55)],
                      fill=rgb)
            # Highlight glint
            d.ellipse([int(S * 0.40), int(S * 0.40),
                       int(S * 0.46), int(S * 0.46)],
                      fill=(255, 255, 255, 200))

        elif sid == 'otto':
            # Otoscope — handle + cone + tip (stylized as ear-light tool)
            # Handle (rectangle on top-left)
            d.rounded_rectangle(
                [int(S * 0.18), int(S * 0.10),
                 int(S * 0.42), int(S * 0.55)],
                radius=int(S * 0.06), outline=rgb, width=w,
            )
            # Cone (triangle pointing toward bottom-right)
            d.polygon(
                [(int(S * 0.42), int(S * 0.32)),
                 (int(S * 0.42), int(S * 0.60)),
                 (int(S * 0.82), int(S * 0.78))],
                outline=rgb, width=w,
            )
            # Tip dot
            d.ellipse(
                [int(S * 0.78), int(S * 0.74),
                 int(S * 0.86), int(S * 0.82)],
                fill=rgb,
            )
            # Eyepiece light at the back of the handle
            d.ellipse(
                [int(S * 0.22), int(S * 0.04),
                 int(S * 0.38), int(S * 0.18)],
                outline=rgb, width=w,
            )

        elif sid == 'derm':
            # Dermatoscope — magnifier with crosshair (skin examination)
            # Lens circle
            cx_, cy_ = int(S * 0.42), int(S * 0.42)
            r = int(S * 0.30)
            d.ellipse([cx_ - r, cy_ - r, cx_ + r, cy_ + r],
                      outline=rgb, width=w)
            # Crosshair inside the lens
            d.line([(cx_ - int(r * 0.6), cy_),
                    (cx_ + int(r * 0.6), cy_)],
                   fill=rgb, width=max(1, w - 1))
            d.line([(cx_, cy_ - int(r * 0.6)),
                    (cx_, cy_ + int(r * 0.6))],
                   fill=rgb, width=max(1, w - 1))
            # Handle (diagonal bar from lens to bottom-right)
            d.line([(cx_ + int(r * 0.71), cy_ + int(r * 0.71)),
                    (int(S * 0.85), int(S * 0.85))],
                   fill=rgb, width=int(w * 1.6))

        elif sid == 'micro':
            # Microscope — body, eyepiece, base
            # Eyepiece (top circle)
            d.ellipse(
                [int(S * 0.42), int(S * 0.10),
                 int(S * 0.62), int(S * 0.24)],
                outline=rgb, width=w,
            )
            # Body / arm — thick angled line from eyepiece to objective
            d.line(
                [(int(S * 0.52), int(S * 0.20)),
                 (int(S * 0.52), int(S * 0.45)),
                 (int(S * 0.32), int(S * 0.55))],
                fill=rgb, width=int(w * 1.4),
            )
            # Stage (horizontal bar)
            d.rectangle(
                [int(S * 0.20), int(S * 0.62),
                 int(S * 0.80), int(S * 0.68)],
                fill=rgb,
            )
            # Base (trapezoid)
            d.polygon(
                [(int(S * 0.22), int(S * 0.92)),
                 (int(S * 0.78), int(S * 0.92)),
                 (int(S * 0.70), int(S * 0.78)),
                 (int(S * 0.30), int(S * 0.78))],
                outline=rgb, width=w,
            )

        # Downscale with LANCZOS for smooth edges
        img = img.resize((size, size), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self._scope_icons[key] = photo
        return photo

    def _draw(self):
        cx, c = self.CX, self.c

        self._zones = {}
        cur = (self.main_app.current_scope
               if (self.main_app and self.main_app.scope_selected)
               else 'opth')

        grid_w = 340
        grid_h = 246
        gap = 14
        card_w = (grid_w - gap) // 2
        card_h = (grid_h - gap) // 2

        start_x = cx - grid_w // 2
        start_y = self.CY - grid_h // 2 - 12

        tints = {'opth': '#30d158', 'otto': '#0a84ff', 'derm': '#ff9f0a', 'micro': '#bf5af2'}

        for i, (sid, label) in enumerate(self.SCOPES):
            row = i // 2
            col = i % 2

            x1 = start_x + col * (card_w + gap)
            y1 = start_y + row * (card_h + gap)
            x2 = x1 + card_w
            y2 = y1 + card_h

            mid_x = (x1 + x2) // 2
            mid_y = (y1 + y2) // 2

            is_active = (sid == cur)

            if is_active:
                # Active: solid iOS green card
                self._smooth_card(x1, y1, x2, y2, fill=IOS_GREEN, radius=22, tag="c")
                txt_col = self._pill_text_color(IOS_GREEN)
                icon_col = "#ffffff"
                chip_col = "#ffffff"
                chip_alpha = 60
            else:
                # Inactive: frosted neutral card with colored tinted icon
                neutral_col, neutral_alpha = self._neutral_fill()
                rgb = self._hex_to_rgba(neutral_col)[:3]
                self._smooth_card(x1, y1, x2, y2, fill=(*rgb, neutral_alpha), radius=22, tag="c")
                txt_col = c['text']
                icon_col = tints.get(sid, c['accent'])
                chip_col = icon_col
                chip_alpha = 35

            # ── Icon Chip (Circle)
            self._smooth_pill(mid_x, mid_y - 18, "", chip_col, w=58, h=58, alpha=chip_alpha, tag="c")

            # ── Icon
            icon = self._scope_icon(sid, 36, icon_col)
            self.cv.create_image(mid_x, mid_y - 18, image=icon, tags="c")

            # ── Label
            fs = 14 if len(label) < 11 else 13
            self.cv.create_text(mid_x, mid_y + 28, text=label, anchor='center',
                                fill=txt_col, font=(_SF_FONT, fs, "bold"), tags="c")

            self._zones[sid] = (x1, y1, x2, y2)

        # EXIT — danger-styled pill at the action row
        ay = self.ACTION_Y + 4
        exit_w = 160
        self._glass_pill(cx, ay, "EXIT", w=exit_w, h=38, danger=True,
                         font=(_SF_FONT, 13, "bold"))
        self._zones['exit'] = (cx - exit_w // 2, ay - 19,
                               cx + exit_w // 2, ay + 19)

    def _click(self, event):
        x, y = event.x, event.y
        for n, zone in self._zones.items():
            x1, y1, x2, y2 = zone
            if x1 <= x <= x2 and y1 <= y <= y2:
                if n == 'exit':
                    self.close()
                else:
                    self.main_app.set_scope(n)
                    self.main_app._show_message(f"SCOPE: {n.upper()}", "cyan")
                    self.close()
                return


# ═══════════════════════════════════════════════════════════════════════════════
# LED CONTROL - List view with on/off toggles
# ═══════════════════════════════════════════════════════════════════════════════
class LEDWindow(BaseWindow):
    """LED control list — shows each light with on/off toggle button."""

    LED_NAMES = {
        5: "Blue LED",
        6: "Main LED",
        7: "Non-Polarized",
        8: "Polarized",
        11: "Non-Polar (New)",
        12: "Polar (New)",
    }

    def __init__(self, root, main_app):
        super().__init__(root, main_app, "LIGHTS")
        self._draw()
        self.cv.bind("<Button-1>", self._click)

    def _draw(self):
        self._clr()
        cx, c = self.CX, self.c
        leds = self.main_app._leds if self.main_app else None
        self._zones = {}

        items = list(self.LED_NAMES.items())
        n = len(items)
        list_top = self.CONTENT_TOP + 4
        list_bot = self.ACTION_Y - 36
        avail = list_bot - list_top
        gap = 6
        item_h = max(34, min(44, (avail - (n - 1) * gap) // n))
        total_h = n * item_h + (n - 1) * gap
        start_y = list_top + (avail - total_h) // 2

        # ─── Equal-width row sizing ──
        # Find the chord at the EXTREME rows (first and last) and use that
        # for every row, so all 6 LEDs have identical width regardless of
        # where they fall on the round display.
        first_y = start_y + item_h // 2
        last_y  = start_y + (n - 1) * (item_h + gap) + item_h // 2
        narrowest = min(self._safe_width(first_y), self._safe_width(last_y))
        row_w = max(0, narrowest - 32)
        x1 = cx - row_w // 2
        x2 = cx + row_w // 2

        for i, (idx, name) in enumerate(items):
            y = start_y + i * (item_h + gap) + item_h // 2
            is_on = leds.get_state(idx) if leds else False

            # Row card — FULL PILL shape (no rect corners), all 6 equal width
            self._smooth_card(
                x1, y - item_h // 2, x2, y + item_h // 2,
                fill=c['card_bg'],
                border=(c['accent'] if is_on else c['card_border'], 1),
                radius=item_h // 2,                       # full pill
            )

            # LED name (left, with breathing room from the rounded edge)
            self.cv.create_text(x1 + 22, y, text=name, anchor='w',
                                fill=c['text'],
                                font=(_SF_FONT, 13, "bold"), tags="c")

            # Toggle pill — green (success) when ON, frosted neutral when OFF
            pill_w, pill_h = 56, item_h - 14
            pill_x = x2 - pill_w // 2 - 14
            self._glass_pill(pill_x, y,
                             "ON" if is_on else "OFF",
                             w=pill_w, h=pill_h,
                             success=is_on,
                             font=(_SF_FONT, 11, "bold"))

            # Whole row is the touch target
            self._zones[idx] = (x1, y - item_h // 2, x2, y + item_h // 2)

        # ─── Action row: ALL OFF / EXIT — equal width, full pills ──
        ay = self.ACTION_Y + 6
        # Same row width as the LED rows so the action row visually aligns
        gap_a = 14
        action_pill_w = (row_w - gap_a) // 2
        # Clamp so we don't get awkwardly tiny pills
        action_pill_w = max(96, min(140, action_pill_w))
        self._glass_pill(cx - (action_pill_w // 2 + gap_a // 2), ay,
                         "ALL OFF",
                         w=action_pill_w, h=36, danger=True,
                         font=(_SF_FONT, 13, "bold"))
        self._glass_pill(cx + (action_pill_w // 2 + gap_a // 2), ay,
                         "EXIT",
                         w=action_pill_w, h=36,
                         font=(_SF_FONT, 13, "bold"))
        self._zones['alloff'] = (
            cx - (action_pill_w + gap_a // 2), ay - 18,
            cx - gap_a // 2,                   ay + 18,
        )
        self._zones['exit'] = (
            cx + gap_a // 2,                   ay - 18,
            cx + (action_pill_w + gap_a // 2), ay + 18,
        )

    def _click(self, event):
        x, y = event.x, event.y
        for key, (x1, y1, x2, y2) in self._zones.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                if key == 'exit':
                    self.close()
                elif key == 'alloff':
                    if self.main_app:
                        self.main_app._leds.all_off()
                    self._draw()
                elif isinstance(key, int):
                    if self.main_app:
                        self.main_app._leds.toggle(key)
                    self._draw()
                return


# ═══════════════════════════════════════════════════════════════════════════════
# FOLDER - Circular Gallery (Samsung Watch / Wear OS style)
# ═══════════════════════════════════════════════════════════════════════════════
class FolderWindow(BaseWindow):
    """Gallery for 480x480 round display. 3x2 rounded thumbnails, safe-zone aware."""
    COLS, ROWS, PER_PAGE = 3, 2, 6

    def __init__(self, root, main_app):
        super().__init__(root, main_app, "GALLERY")
        # Gallery needs full opacity so images/videos are 100% visible
        try:
            self.win.attributes('-alpha', 1.0)
        except (tk.TclError, AttributeError):
            pass
        self._scope = 'all'
        self._tab = 'images'
        self._items = []
        self._view = 'grid'
        self._pidx = 0
        self._pphoto = None
        self._thumbs = []
        self._page = 0
        self._video_playing = False
        self._video_after = None
        self._draw_grid()
        self.cv.bind("<Button-1>", self._click)

    def _clr(self):
        self._stop_video()
        try:
            self.cv.delete("c")
            self.cv.delete("msg")
            self.cv.delete("vc")   # video control pills must not linger on other views
        except tk.TclError:
            pass
        self._thumbs = []

    def _load(self):
        if self._tab == 'images':
            if self._scope == 'all':
                self._items = []
                for s in settings.SCOPE_IMAGE_FOLDERS:
                    self._items.extend(FileManager.list_images(s))
                self._items.sort(key=lambda x: x['created'], reverse=True)
            else:
                self._items = FileManager.list_images(self._scope)
        else:
            self._items = FileManager.list_videos(self._scope if self._scope != 'all' else None)

    def _fpath(self, item):
        fn = item['filename']
        # Prefer the real on-disk folder recorded at list time. This is robust
        # when browsing 'all' scopes, where an item's `scope` may be empty even
        # though the file lives in a scope subfolder.
        d = item.get('dir')
        if d:
            return os.path.join(d, fn)
        if self._tab == 'images':
            return os.path.join(settings.SCOPE_IMAGE_FOLDERS.get(item.get('scope',''), settings.IMAGE_BASE), fn)
        return os.path.join(settings.SCOPE_VIDEO_FOLDERS.get(item.get('scope',''), settings.VIDEO_BASE), fn)

    def _make_thumb(self, item, size):
        """Rounded square thumbnail."""
        fp = self._fpath(item)
        img = None
        try:
            if self._tab == 'images' and os.path.exists(fp):
                img = Image.open(fp)
            elif self._tab == 'videos' and os.path.exists(fp):
                cap = cv2.VideoCapture(fp); ret, f = cap.read(); cap.release()
                if ret: img = Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        except: pass
        t = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(t)
        r = size // 5
        d.rounded_rectangle([0, 0, size-1, size-1], radius=r, fill=(30, 30, 42, 255))
        if img:
            img.thumbnail((size-4, size-4), Image.LANCZOS)
            t.paste(img, ((size-img.width)//2, (size-img.height)//2))
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, size-1, size-1], radius=r, fill=255)
            t.putalpha(mask)
        if self._tab == 'videos':
            d2 = ImageDraw.Draw(t)
            d2.polygon([(size//2-7, size//2-9),(size//2-7, size//2+9),(size//2+9, size//2)], fill=(255,255,255,180))
        return ImageTk.PhotoImage(t)

    def _draw_grid(self):
        self._view = 'grid'
        self._clr()
        cx, c = self.CX, self.c
        self._load()

        # ─── Title ─────────────────────────────────────────────────────
        # Title sits at TITLE_Y already drawn by BaseWindow. Just keep
        # tight spacing below it.

        # ─── Scope filter tabs (compact, generous gaps) ────────────────
        tabs = [('all', 'ALL'), ('opth', 'OPT'), ('otto', 'OTO'),
                ('derm', 'DRM'), ('micro', 'MIC')]
        self._tz = {}
        chord = self._safe_width(self.CONTENT_TOP)
        gap = 8
        tab_w = max(58, (chord - 20 - (len(tabs) - 1) * gap) // len(tabs))
        tab_h = 30
        total = len(tabs) * tab_w + (len(tabs) - 1) * gap
        sx = cx - total // 2
        ty = self.CONTENT_TOP + 4
        for i, (sid, lbl) in enumerate(tabs):
            tx = sx + i * (tab_w + gap) + tab_w // 2
            self._glass_pill(tx, ty, lbl, w=tab_w, h=tab_h,
                             active=(sid == self._scope),
                             font=(_SF_FONT, 11, "bold"))
            self._tz[sid] = (tx - tab_w // 2, ty - tab_h // 2,
                             tx + tab_w // 2, ty + tab_h // 2)

        # ─── IMG/VID toggle (compact, sits right under scope tabs) ────
        sub_y = ty + tab_h // 2 + 20
        sub_w, sub_h = 88, 28
        sub_gap = 12
        self._glass_pill(cx - (sub_w + sub_gap) // 2, sub_y, "IMG",
                         w=sub_w, h=sub_h,
                         active=(self._tab == 'images'),
                         font=(_SF_FONT, 12, "bold"))
        self._glass_pill(cx + (sub_w + sub_gap) // 2, sub_y, "VID",
                         w=sub_w, h=sub_h,
                         active=(self._tab == 'videos'),
                         font=(_SF_FONT, 12, "bold"))
        self._imgz = (cx - (sub_w + sub_gap) // 2 - sub_w // 2,
                      sub_y - sub_h // 2,
                      cx - (sub_w + sub_gap) // 2 + sub_w // 2,
                      sub_y + sub_h // 2)
        self._vidz = (cx + (sub_w + sub_gap) // 2 - sub_w // 2,
                      sub_y - sub_h // 2,
                      cx + (sub_w + sub_gap) // 2 + sub_w // 2,
                      sub_y + sub_h // 2)

        # ─── 3x2 thumbnail grid — fills the middle, larger thumbs ─────
        # Action row sits near the bottom of the screen (y ≈ 396) so the grid
        # has the whole space between sub_y+sub_h/2+10 and the page indicator.
        self._fz = []
        action_y = self.ACTION_Y + 6             # action row pinned to bottom
        grid_top = sub_y + sub_h // 2 + 12
        grid_bot = action_y - 34                 # leaves room for page indicator
        ggap = 10
        # 3 cols × 2 rows — bigger thumbs (was 88 max; now fills available)
        th = min(108, (grid_bot - grid_top - (self.ROWS - 1) * ggap) // self.ROWS)
        # Width-constrained as well so 3 across fits the chord at the grid mid-y
        grid_mid_y = (grid_top + grid_bot) // 2
        max_grid_w = self._safe_width(grid_mid_y) - 24
        max_th_w = (max_grid_w - (self.COLS - 1) * ggap) // self.COLS
        th = min(th, max_th_w)

        gw = self.COLS * (th + ggap) - ggap
        gsx = cx - gw // 2
        if not self._items:
            self.cv.create_text(cx, (grid_top + grid_bot) // 2,
                                text="No files",
                                fill=c['text_secondary'],
                                font=(_SF_FONT, 14, "bold"), tags="c")
        else:
            page_items = self._items[self._page * self.PER_PAGE:
                                     (self._page + 1) * self.PER_PAGE]
            for i, item in enumerate(page_items):
                row, gcol = i // self.COLS, i % self.COLS
                tx = gsx + gcol * (th + ggap) + th // 2
                ty2 = grid_top + row * (th + ggap) + th // 2
                # Drop thumbs that would clip the bezel
                if math.sqrt((tx - cx) ** 2 + (ty2 - self.CY) ** 2) < self.SR + 18:
                    ph = self._make_thumb(item, th)
                    self._thumbs.append(ph)
                    self.cv.create_image(tx, ty2, image=ph, tags="c")
                    self._fz.append((self._page * self.PER_PAGE + i,
                                     tx - th // 2, ty2 - th // 2,
                                     tx + th // 2, ty2 + th // 2))

        # ─── Page indicator — clear gap from action row below ─────────
        tp = max(1, (len(self._items) + self.PER_PAGE - 1) // self.PER_PAGE) if self._items else 1
        page_y = action_y - 26
        self.cv.create_text(cx, page_y,
                            text=f"Page {self._page + 1} of {tp}",
                            fill=c['text_secondary'],
                            font=(_SF_FONT, 11, "bold"), tags="c")

        # ─── Action row: ◀  EXIT  ▶ ───────────────────────────────────
        ay = action_y
        nav_w, exit_w, h = 48, 90, 34
        nav_gap = 14
        prev_x = cx - (exit_w // 2 + nav_gap + nav_w // 2)
        next_x = cx + (exit_w // 2 + nav_gap + nav_w // 2)

        if self._page > 0:
            self._glass_pill(prev_x, ay, "◀", w=nav_w, h=h,
                             font=(_SF_FONT, 16, "bold"))
            self._prevpz = (prev_x - nav_w // 2, ay - h // 2,
                            prev_x + nav_w // 2, ay + h // 2)
        else:
            self._prevpz = (-1, -1, -1, -1)

        self._glass_pill(cx, ay, "EXIT", w=exit_w, h=h, danger=True,
                         font=(_SF_FONT, 13, "bold"))
        self._exit_zone = (cx - exit_w // 2, ay - h // 2,
                           cx + exit_w // 2, ay + h // 2)

        if self._items and (self._page + 1) * self.PER_PAGE < len(self._items):
            self._glass_pill(next_x, ay, "▶", w=nav_w, h=h,
                             font=(_SF_FONT, 16, "bold"))
            self._nextpz = (next_x - nav_w // 2, ay - h // 2,
                            next_x + nav_w // 2, ay + h // 2)
        else:
            self._nextpz = (-1, -1, -1, -1)

    def _draw_preview(self):
        """Image preview — large back/next/prev pills, theme-aware."""
        self._view = 'preview'
        self._clr()
        cx, c = self.CX, self.c

        if self._pidx >= len(self._items):
            self._draw_grid()
            return
        item = self._items[self._pidx]
        try:
            fp = self._fpath(item)
            if os.path.exists(fp):
                img = Image.open(fp)
                img.thumbnail((self.SR * 2 - 20, self.SR * 2 - 80),
                              Image.LANCZOS)
                self._pphoto = ImageTk.PhotoImage(img)
                self.cv.create_image(cx, self.CY - 18,
                                     image=self._pphoto, tags="c")
        except Exception:
            self.cv.create_text(cx, self.CY, text="Cannot open",
                                fill=c['danger'],
                                font=(_SF_FONT, 13, "bold"), tags="c")

        # Filename + counter
        self.cv.create_text(cx, self.TITLE_Y - 16,
                            text=item['filename'][:24],
                            fill=c['text'],
                            font=(_SF_FONT, 12, "bold"), tags="c")
        self.cv.create_text(cx, self.TITLE_Y,
                            text=f"{self._pidx + 1} / {len(self._items)}",
                            fill=c['text_secondary'],
                            font=(_SF_FONT, 11), tags="c")

        # Action row — ◀ / BACK / ▶
        ay = self.ACTION_Y
        if self._pidx > 0:
            self._glass_pill(cx - 88, ay, "◀", w=58, h=36,
                             font=(_SF_FONT, 16, "bold"))
            self._pz = (cx - 117, ay - 18, cx - 59, ay + 18)
        else:
            self._pz = (-1, -1, -1, -1)

        self._glass_pill(cx, ay, "BACK", w=110, h=36, active=True)
        self._exit_zone = (cx - 55, ay - 18, cx + 55, ay + 18)

        if self._pidx < len(self._items) - 1:
            self._glass_pill(cx + 88, ay, "▶", w=58, h=36,
                             font=(_SF_FONT, 16, "bold"))
            self._nz = (cx + 59, ay - 18, cx + 117, ay + 18)
        else:
            self._nz = (-1, -1, -1, -1)

    def _play_video_inline(self, item):
        """
        Inline video player.
        Layout:
          • Title row at TITLE_Y
          • Video frame: smaller so the control row sits clearly below it
          • Controls: rewind / play-pause / stop / forward — placed at y=412
            (just below the video frame, not crammed at the screen bottom)
        """
        self._view = 'video'
        self._clr()
        cx, c = self.CX, self.c
        fp = self._fpath(item)
        if not os.path.exists(fp):
            self.cv.create_text(cx, self.CY - 30, text="Video not found",
                                fill=c['danger'],
                                font=(_SF_FONT, 13, "bold"), tags="c")
            self._video_error_back()
            return
        self._vcap = cv2.VideoCapture(fp)
        if not self._vcap.isOpened():
            self.cv.create_text(cx, self.CY - 30, text="Cannot play video",
                                fill=c['danger'],
                                font=(_SF_FONT, 13, "bold"), tags="c")
            self.cv.create_text(cx, self.CY, text="(unsupported format/codec)",
                                fill=c['text_secondary'],
                                font=(_SF_FONT, 11), tags="c")
            self._video_error_back()
            return
        self._video_playing = True
        self._video_item = item
        self._vphoto = None

        # Video frame area: shrunk so controls sit cleanly below
        # Frame center: y=200, max size 320×260 → frame bottom ≈ 330
        self._video_fy = 200
        self._video_fmax = (320, 260)
        self._vitem = self.cv.create_image(cx, self._video_fy, tags="c")

        # Title (filename)
        self.cv.create_text(cx, self.TITLE_Y - 16,
                            text=item['filename'][:24],
                            fill=c['text'],
                            font=(_SF_FONT, 12, "bold"), tags="c")

        fps = self._vcap.get(cv2.CAP_PROP_FPS) or 25
        self._vdelay = max(25, int(1000 / fps))
        # Control row sits a little below the video frame's bottom edge
        self._video_ay = 380
        self._draw_video_controls()
        self._video_frame()

    def _video_error_back(self):
        """Guaranteed escape button shown when a video can't be played, so the
        user is never trapped on the error screen."""
        cx = self.CX
        self._video_playing = False
        back_y = self.ACTION_Y
        self._glass_pill(cx, back_y, "BACK TO GALLERY", tag="vc",
                         w=190, h=36, active=True,
                         font=(_SF_FONT, 13, "bold"))
        self._video_zones = {
            'back': (cx - 95, back_y - 18, cx + 95, back_y + 18),
        }

    def _draw_video_controls(self):
        """
        Render the Play/Pause/Stop control row sized to the round display.
        Controls sit just below the video frame (not at ACTION_Y which would
        overlap the video). The Play↔Pause icon swaps in real time.
        """
        self.cv.delete("vc")
        cx = self.CX
        ay = getattr(self, '_video_ay', self.ACTION_Y)

        ctrl_w, ctrl_h = 60, 38
        gap = 10

        slots = [-1.5, -0.5, 0.5, 1.5]
        # rewind, play/pause, stop, forward — icons are drawn as vector shapes
        # (NOT font glyphs) so they always render regardless of the system font.
        states = [
            ("rewind",    "prev",                        {}),
            ("playpause", "pause" if self._video_playing else "play",
                                                          {"active": True}),
            ("stop",      "stop",                         {"danger": True}),
            ("forward",   "next",                         {}),
        ]
        self._video_zones = {}
        for slot, (key, shape, kw) in zip(slots, states):
            x = int(cx + slot * (ctrl_w + gap))
            # Pill background only (empty label) …
            self._glass_pill(x, ay, "", tag="vc",
                             w=ctrl_w, h=ctrl_h, **kw)
            # … then the icon drawn on top
            self._draw_media_glyph(x, ay, shape)
            self._video_zones[key] = (x - ctrl_w // 2, ay - ctrl_h // 2,
                                       x + ctrl_w // 2, ay + ctrl_h // 2)

        # BACK to grid — text label is fine (plain ASCII)
        back_y = 432
        self._glass_pill(cx, back_y, "BACK TO GALLERY", tag="vc",
                         w=180, h=30,
                         font=(_SF_FONT, 12, "bold"))
        self._video_zones['back'] = (cx - 90, back_y - 15,
                                      cx + 90, back_y + 15)

    def _draw_media_glyph(self, x, y, shape, size=13, color="white"):
        """Draw a media-control icon as vector shapes (font-independent)."""
        s = size
        if shape == "play":
            self.cv.create_polygon(x - s*0.5, y - s, x - s*0.5, y + s,
                                   x + s, y,
                                   fill=color, outline="", tags="vc")
        elif shape == "pause":
            bw = max(3, s // 3)
            self.cv.create_rectangle(x - s*0.6, y - s, x - s*0.6 + bw, y + s,
                                     fill=color, outline="", tags="vc")
            self.cv.create_rectangle(x + s*0.6 - bw, y - s, x + s*0.6, y + s,
                                     fill=color, outline="", tags="vc")
        elif shape == "stop":
            self.cv.create_rectangle(x - s*0.8, y - s*0.8, x + s*0.8, y + s*0.8,
                                     fill=color, outline="", tags="vc")
        elif shape == "prev":   # ⏮  bar + back triangle
            self.cv.create_rectangle(x - s, y - s, x - s + 3, y + s,
                                     fill=color, outline="", tags="vc")
            self.cv.create_polygon(x + s*0.7, y - s, x + s*0.7, y + s,
                                   x - s*0.4, y,
                                   fill=color, outline="", tags="vc")
        elif shape == "next":   # ⏭  forward triangle + bar
            self.cv.create_polygon(x - s*0.7, y - s, x - s*0.7, y + s,
                                   x + s*0.4, y,
                                   fill=color, outline="", tags="vc")
            self.cv.create_rectangle(x + s - 3, y - s, x + s, y + s,
                                     fill=color, outline="", tags="vc")

    def _video_toggle_playpause(self):
        """Toggle between play and pause without releasing the capture."""
        if not hasattr(self, '_vcap') or not self._vcap:
            return
        self._video_playing = not self._video_playing
        # Cancel any in-flight frame so the new state is clean
        if hasattr(self, '_video_after') and self._video_after:
            try:
                self.win.after_cancel(self._video_after)
            except Exception:
                pass
            self._video_after = None
        self._draw_video_controls()
        if self._video_playing:
            self._video_frame()

    def _video_seek(self, delta_seconds):
        """Seek relative to the current frame position."""
        if not hasattr(self, '_vcap') or not self._vcap:
            return
        try:
            fps = self._vcap.get(cv2.CAP_PROP_FPS) or 25
            cur = self._vcap.get(cv2.CAP_PROP_POS_FRAMES) or 0
            total = self._vcap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            target = max(0, min(total - 1, cur + delta_seconds * fps))
            self._vcap.set(cv2.CAP_PROP_POS_FRAMES, target)
        except Exception:
            pass
        # When paused, render one frame at the new position
        if not self._video_playing:
            ret, frame = self._vcap.read()
            if ret:
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                fmax = getattr(self, '_video_fmax', (self.SR * 2, self.SR * 2 - 40))
                img.thumbnail(fmax, Image.LANCZOS)
                self._vphoto = ImageTk.PhotoImage(img)
                self.cv.itemconfig(self._vitem, image=self._vphoto)
                try:
                    self._vcap.set(
                        cv2.CAP_PROP_POS_FRAMES,
                        max(0, self._vcap.get(cv2.CAP_PROP_POS_FRAMES) - 1))
                except Exception:
                    pass

    def _video_frame(self):
        if (not self._video_playing
                or not hasattr(self, '_vcap') or not self._vcap):
            return
        ret, frame = self._vcap.read()
        if not ret:
            # End of stream — pause on last frame
            self._video_playing = False
            self._draw_video_controls()
            return
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        fmax = getattr(self, '_video_fmax', (self.SR * 2, self.SR * 2 - 40))
        img.thumbnail(fmax, Image.LANCZOS)
        self._vphoto = ImageTk.PhotoImage(img)
        self.cv.itemconfig(self._vitem, image=self._vphoto)
        self._video_after = self.win.after(self._vdelay, self._video_frame)

    def _stop_video(self):
        self._video_playing = False
        if hasattr(self,'_video_after') and self._video_after:
            try: self.win.after_cancel(self._video_after)
            except: pass
            self._video_after = None
        if hasattr(self,'_vcap') and self._vcap:
            self._vcap.release(); self._vcap = None

    def _click(self, event):
        x, y = event.x, event.y
        if self._view == 'video':
            for key, (x1, y1, x2, y2) in getattr(self, '_video_zones', {}).items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    if   key == 'playpause': self._video_toggle_playpause()
                    elif key == 'stop':      self._stop_video(); self._draw_grid()
                    elif key == 'back':      self._stop_video(); self._draw_grid()
                    elif key == 'rewind':    self._video_seek(-5)
                    elif key == 'forward':   self._video_seek(+5)
                    return
            return
        if self._view == 'preview':
            if hasattr(self,'_pz'):
                x1,y1,x2,y2=self._pz
                if x1<=x<=x2 and y1<=y<=y2 and self._pidx>0: self._pidx-=1; self._draw_preview(); return
            if hasattr(self,'_nz'):
                x1,y1,x2,y2=self._nz
                if x1<=x<=x2 and y1<=y<=y2 and self._pidx<len(self._items)-1: self._pidx+=1; self._draw_preview(); return
            if hasattr(self,'_exit_zone'):
                x1,y1,x2,y2=self._exit_zone
                if x1<=x<=x2 and y1<=y<=y2: self._draw_grid(); return
            return
        # Grid view
        for sid,(x1,y1,x2,y2) in self._tz.items():
            if x1<=x<=x2 and y1<=y<=y2: self._scope=sid; self._page=0; self._draw_grid(); return
        if hasattr(self,'_imgz'):
            x1,y1,x2,y2=self._imgz
            if x1<=x<=x2 and y1<=y<=y2: self._tab='images'; self._page=0; self._draw_grid(); return
        if hasattr(self,'_vidz'):
            x1,y1,x2,y2=self._vidz
            if x1<=x<=x2 and y1<=y<=y2: self._tab='videos'; self._page=0; self._draw_grid(); return
        if hasattr(self,'_prevpz'):
            x1,y1,x2,y2=self._prevpz
            if x1<=x<=x2 and y1<=y<=y2 and self._page>0: self._page-=1; self._draw_grid(); return
        if hasattr(self,'_nextpz'):
            x1,y1,x2,y2=self._nextpz
            if x1<=x<=x2 and y1<=y<=y2: self._page+=1; self._draw_grid(); return
        if hasattr(self,'_exit_zone'):
            x1,y1,x2,y2=self._exit_zone
            if x1<=x<=x2 and y1<=y<=y2: self.close(); return
        for idx,x1,y1,x2,y2 in self._fz:
            if x1<=x<=x2 and y1<=y<=y2:
                if idx<len(self._items):
                    if self._tab=='images': self._pidx=idx; self._draw_preview()
                    else: self._play_video_inline(self._items[idx])
                return
