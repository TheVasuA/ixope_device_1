"""
Secondary Windows for 480x480 Round Display.
All text colors follow theme. All content fits within circle.
Usable area: x=60-420, y=50-430 (inscribed in 480px circle).
"""
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import os
import subprocess
import threading
import json
import math
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
IOS_GLASS_DARK_FILL  = "#8a90a4"     # mid neutral; alpha 90 makes it gray
IOS_GLASS_LIGHT_FILL = "#ffffff"     # white at low alpha = frosted white
IOS_GLASS_DARK_ALPHA  = 70           # how much of the panel bleeds through (dark)
IOS_GLASS_LIGHT_ALPHA = 160          # in light mode we need more opacity

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


# ═══════════════════════════════════════════════════════════════════════════════
# BASE WINDOW - Round display aware layout system
# Samsung Watch design guidelines: content within 70% inscribed circle
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
                                fill=self.c['text'], font=("Arial", 13, "bold"))

    def _bg(self):
        """Flat circular background with subtle inner ring."""
        img = Image.new("RGBA", (self.S, self.S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if self.mode == 'dark':
            d.ellipse([0, 0, self.S, self.S], fill=(14, 14, 22, 255))
            # Subtle inner ring for depth
            d.ellipse([4, 4, self.S-4, self.S-4], outline=(30, 30, 45, 255), width=1)
        else:
            d.ellipse([0, 0, self.S, self.S], fill=(242, 242, 248, 255))
            d.ellipse([4, 4, self.S-4, self.S-4], outline=(220, 220, 230, 255), width=1)
        self._bgp = ImageTk.PhotoImage(img)
        self.cv.create_image(self.CX, self.CY, image=self._bgp)

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
        self.cv.create_text(x, y, text=txt, fill=txt_col, font=("Arial", 10, "bold"), tags=tag)

    # Cache of smooth-pill PhotoImages — keyed by (col, w, h, border, alpha) so
    # we don't re-render the same image every frame.
    def _smooth_pill(self, x, y, txt, col, tag="c", w=100, h=32, txt_col=None,
                     font=("Arial", 10, "bold"), border=None, alpha=255):
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
        key = (fill, w, h, border, radius)
        photo = self._card_cache.get(key)
        if photo is None:
            scale = 3
            W, H = w * scale, h * scale
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle([0, 0, W - 1, H - 1],
                                radius=radius * scale,
                                fill=self._hex_to_rgba(fill))
            if border:
                bcol, bw = border
                d.rounded_rectangle([0, 0, W - 1, H - 1],
                                    radius=radius * scale,
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
                    danger=False, success=False, font=("Arial", 10, "bold"),
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
        self._draw()
        self.cv.bind("<Button-1>", self._click)
        self.cv.bind("<B1-Motion>", self._drag)

    def _draw(self):
        if self._page == 'country':
            self._draw_country()
        else:
            self._draw_main()

    def _refresh(self):
        self.cv.delete("all")
        self._bg()
        title = "REGION" if self._page == 'country' else "SETTINGS"
        self.cv.create_text(self.CX, self.TITLE_Y, text=title,
                            fill=self.c['text'], font=("Arial", 13, "bold"))
        self._draw()

    def _draw_main(self):
        cx, c = self.CX, self.c

        # Section labels
        section_lbl  = c['text_secondary']
        section_font = ("Arial", 9, "bold")
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
                         font=("Arial", 11, "bold"))

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
                                font=("Arial", 12, "bold"),
                                tags="c")
            self.cv.create_text(cx, oy1 + 58,
                                text="Are you sure you want to shut down?",
                                fill=self.c['text_secondary'],
                                font=("Arial", 10),
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

    # ─── REGION sub-page: country search keyboard ─────────────────────
    def _draw_country(self):
        """
        Country selection sub-page.
          • TOP    → search field + top 2 matches (frosted neutral pills)
          • MIDDLE → keyboard
          • BOTTOM → DONE / BACK action row
        """
        cx, c = self.CX, self.c
        search = self._search

        # Search field
        sw = self._safe_width(78)
        fx1 = cx - sw // 2 + 8
        fx2 = cx + sw // 2 - 8
        self.cv.create_rectangle(fx1, 64, fx2, 96,
                                 fill=c['card_bg'],
                                 outline=c['accent'], width=2, tags="c")
        disp = search if search else "Type country name…"
        sc = c['text'] if search else c['text_secondary']
        self.cv.create_text(fx1 + 14, 80, text=disp[-26:], anchor='w',
                            fill=sc, font=("Arial", 11), tags="c")

        # Result rows — top 2 matches as iOS green active pills
        countries = _SORTED_COUNTRIES
        if search:
            countries = [n for n in countries
                         if search.lower() in n.lower()]
        cur_name = get_saved_country_name()
        self._cs_items = []
        for i, name in enumerate(countries[:2]):
            y = 116 + i * 30
            row_w = sw - 16
            rx1 = cx - row_w // 2
            rx2 = cx + row_w // 2
            is_active = (name == cur_name)
            if is_active:
                self._smooth_pill(cx, y, "", IOS_GREEN,
                                  w=row_w, h=26, alpha=255)
                txt_col = self._pill_text_color(IOS_GREEN)
            else:
                ncol, nalpha = self._neutral_fill()
                self._smooth_pill(cx, y, "", ncol,
                                  w=row_w, h=26, alpha=nalpha)
                txt_col = c['text']
            self.cv.create_text(cx, y, text=name, fill=txt_col,
                                font=("Arial", 10, "bold"), tags="c")
            self._cs_items.append((name, rx1, y - 13, rx2, y + 13))

        # Separator
        self.cv.create_line(fx1 + 16, 178, fx2 - 16, 178,
                            fill=c['card_border'], width=1, tags="c")

        # Keyboard
        self._keys = {}
        self._draw_keyboard(start_y=184)

        # DONE / BACK
        ay = self.ACTION_Y + 6
        self._glass_pill(cx - 64, ay, "DONE", w=110, h=34, active=True)
        self._glass_pill(cx + 64, ay, "BACK", w=110, h=34)
        self._cs_done_z = (cx - 119, ay - 17, cx - 9,  ay + 17)
        self._cs_back_z = (cx + 9,   ay - 17, cx + 119, ay + 17)

    # Reuse the same keyboard renderer that WifiWindow uses.
    # We import-by-method to avoid pulling the entire WifiWindow into the
    # MRO — just borrow the method bound to this instance.
    def _draw_keyboard(self, start_y=82):
        WifiWindow._draw_keyboard(self, start_y=start_y)

    def _kk(self, x, y, ch, w, h):
        WifiWindow._kk(self, x, y, ch, w, h)

    def _rddl(self):
        self.cv.delete("dl")
        rel = (self._delay - 3) / 27.0
        fx = self._sx1 + int((self._sx2 - self._sx1) * rel)
        self.cv.create_line(self._sx1, self._dly, fx, self._dly,
                            fill=self.c['warning'], width=6, capstyle="round", tags="dl")
        self.cv.create_oval(fx - 11, self._dly - 11, fx + 11, self._dly + 11,
                            fill="white", outline=self.c['warning'], width=2, tags="dl")
        self.cv.create_text(self.CX, self._dly + 22, text=f"{self._delay}s",
                            fill=self.c['text'], font=("Arial", 10, "bold"), tags="dl")

    def _click(self, event):
        x, y = event.x, event.y

        # ─── Country sub-page handling ────────────────────────────────
        if self._page == 'country':
            # Result row tap
            for name, x1, y1, x2, y2 in self._cs_items:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self._select_country(name)
                    return
            # DONE — accept first match if any, else just go back
            if hasattr(self, '_cs_done_z'):
                x1, y1, x2, y2 = self._cs_done_z
                if x1 <= x <= x2 and y1 <= y <= y2:
                    matches = ([n for n in _SORTED_COUNTRIES
                                if not self._search
                                or self._search.lower() in n.lower()])
                    if matches:
                        self._select_country(matches[0])
                    else:
                        self._page = 'main'
                        self._refresh()
                    return
            # BACK — go to main settings without changing anything
            if hasattr(self, '_cs_back_z'):
                x1, y1, x2, y2 = self._cs_back_z
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self._page = 'main'
                    self._refresh()
                    return
            # Keys
            for ch, (x1, y1, x2, y2) in self._keys.items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    if   ch == "⌫":     self._search = self._search[:-1]
                    elif ch == "CAPS":  self._caps = not self._caps
                    elif ch in ("!#+", "ABC"):
                        self._sym_mode = not self._sym_mode
                    elif ch == " ":     self._search += ' '
                    else:               self._search += ch
                    self._refresh()
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
                    self._refresh()
                return
        for sid, (x1, y1, x2, y2) in self._schz.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                self._isch = sid
                if self.main_app and hasattr(self.main_app, '_icons'):
                    self.main_app._icons.set_scheme(sid)
                if self.main_app and hasattr(self.main_app, 'refresh_icons'):
                    self.main_app.refresh_icons()
                self._refresh()
                return
        # Slider hit (delay)
        if self._sx1 - 12 <= x <= self._sx2 + 12 and self._dly - 16 <= y <= self._dly + 16:
            self._setdl(x)

    def _select_country(self, name):
        """Persist + apply the country, then return to main settings."""
        code = COUNTRIES.get(name, 'US')
        save_country(code)
        self._page = 'main'
        self._refresh()

    def _drag(self, event):
        if self._page == 'country':
            return
        x, y = event.x, event.y
        if self._dly - 20 <= y <= self._dly + 20:
            self._setdl(x)

    def _setdl(self, x):
        rel = max(0.0, min(1.0, (x - self._sx1) / max(1, self._sx2 - self._sx1)))
        self._delay = max(3, min(30, int(3 + rel * 27 + 0.5)))
        settings.UI_HIDE_DELAY_MS = self._delay * 1000
        self._rddl()

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
        self._refresh()

    def _reset_defaults(self):
        """Reset all settings to factory defaults (no brightness anymore)."""
        self._delay = 20
        self._isch = 'glass'
        settings.UI_HIDE_DELAY_MS = 20000
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
        super().__init__(root, main_app, "Wi-Fi")
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
        # Country selection now lives in SETTINGS. WiFi window always goes
        # straight to network scan. (We still write a default if the user
        # somehow opens WiFi without ever visiting Settings — keeps `nmcli`
        # happy.)
        if not self._has_saved_country():
            self._save_country('US')
        self._draw_scan()
        self.cv.bind("<Button-1>", self._click)
        self.cv.bind("<B1-Motion>", self._ondrag)
        self.cv.bind("<ButtonRelease-1>", lambda e: setattr(self, '_drag_y', None))

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
          • Each network is a frosted neutral pill
          • Row layout: [SSID label | signal bars]
          • All rows equal width (chord at narrowest visible row)
          • REFRESH / EXIT action row uses the same glass pill pattern
        """
        self._page = 'scan'
        self._clr()
        cx, c = self.S // 2, self.c

        # Title
        self.cv.create_text(cx, 50, text="Wi-Fi NETWORKS",
                            fill=c['text'], font=("Arial", 13, "bold"), tags="c")

        # Action row drawn at bottom regardless of scan state
        if not self._nets:
            self.cv.create_text(cx, self.CY,
                                text="Scanning…",
                                fill=c['text_secondary'],
                                font=("Arial", 12, "bold"), tags="c")
            threading.Thread(target=self._do_scan, daemon=True).start()
            self._draw_scan_actions()
            return

        # ─── List geometry ─────────────────────────────────────────────
        self._items = []
        list_top = 78
        list_bot = self.ACTION_Y - 32
        row_h = 40
        gap = 6

        # Equal-width rows: chord at the narrowest visible row position
        first_y = list_top + row_h // 2
        last_y  = list_bot - row_h // 2
        narrowest = min(self._safe_width(first_y),
                        self._safe_width(last_y))
        row_w = max(0, narrowest - 32)
        x1 = cx - row_w // 2
        x2 = cx + row_w // 2

        # ─── Render network pills (scrollable) ─────────────────────────
        ssid_font = ("Arial", 12, "bold")
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

            # SSID — left-aligned with breathing room from the rounded edge
            self.cv.create_text(x1 + 22, y,
                                text=net['ssid'][:22],
                                anchor='w', fill=c['text'],
                                font=ssid_font, tags="c")

            # Signal bars (4) — iOS green when active
            bars = min(4, max(1, net['signal'] // 25))
            bar_x = x2 - 32
            inactive_bar = ("#3a3a4a" if self.mode == 'dark'
                            else "#c0c4cc")
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
        self._glass_pill(cx - 64, ay, "REFRESH", w=116, h=36, active=True,
                         font=("Arial", 11, "bold"))
        self._glass_pill(cx + 64, ay, "EXIT", w=116, h=36, danger=True,
                         font=("Arial", 11, "bold"))
        self._refresh_zone = (cx - 122, ay - 18, cx - 6,  ay + 18)
        self._exit_zone    = (cx + 6,   ay - 18, cx + 122, ay + 18)

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
          • TOP    (y ≤ 168)  → SSID label + password input (large) + eye toggle
          • MIDDLE (y > 168)  → keyboard
          • BOTTOM (y = 442)  → OK / CANCEL action row
        No overlapping text, generous spacing, large hit targets.
        """
        self._page = 'pw'
        self._clr()
        cx, c = self.S // 2, self.c

        # ─── TOP ZONE ─────────────────────────────────────────────────
        # SSID label
        self.cv.create_text(cx, 56, text="CONNECT TO",
                            fill=c['text_secondary'],
                            font=("Arial", 9, "bold"), tags="c")
        ssid = (self._ssid or "")[:20]
        self.cv.create_text(cx, 76, text=ssid,
                            fill=c['accent'],
                            font=("Arial", 12, "bold"), tags="c")

        # Password field — taller, wider, with internal padding so the
        # placeholder/dots never crowd the eye toggle.
        sw = self._safe_width(118)
        fx1 = cx - sw // 2 + 8
        fx2 = cx + sw // 2 - 8
        eye_pad = 38                                          # space reserved for eye toggle
        ifx2 = fx2 - eye_pad

        # Field bounds: y=98..148 (50 px tall — big finger target)
        self.cv.create_rectangle(fx1, 98, ifx2, 148,
                                 fill=c['card_bg'],
                                 outline=c['accent'], width=2, tags="c")

        # Password content — clipped to internal text region (10px inset
        # from each side so chars never overlap field border).
        if self._pw:
            disp = self._pw if self._show_pw else "•" * min(len(self._pw), 22)
        else:
            disp = "Enter Password"
        pc = c['text'] if self._pw else c['text_secondary']
        self.cv.create_text(fx1 + 14, 123, text=disp[-22:], anchor='w',
                            fill=pc, font=("Arial", 13), tags="c")

        # Eye / show-password toggle — sits in the reserved eye_pad band
        ex, ey = fx2 - eye_pad // 2, 123
        ec = c['accent'] if self._show_pw else c['text_secondary']
        # Larger, easier to tap eye glyph
        self.cv.create_oval(ex - 11, ey - 7, ex + 11, ey + 7,
                            outline=ec, width=2, tags="c")
        self.cv.create_oval(ex - 4, ey - 4, ex + 4, ey + 4,
                            fill=ec, tags="c")
        if not self._show_pw:
            self.cv.create_line(ex - 11, ey + 9, ex + 11, ey - 9,
                                fill=ec, width=2, tags="c")
        # Generous touch zone (covers the whole eye_pad band)
        self._eye_z = (ifx2, 98, fx2, 148)

        # Subtle separator below the field, above the keyboard
        self.cv.create_line(fx1 + 16, 165, fx2 - 16, 165,
                            fill=c['card_border'], width=1, tags="c")

        # ─── KEYBOARD ─────────────────────────────────────────────────
        self._keys = {}
        self._draw_keyboard(start_y=174)

        # ─── ACTION ROW: OK / CANCEL ──────────────────────────────────
        # Kept clear of the keyboard's bottom edge.
        ay = 446
        self._glass_pill(cx - 64, ay, "OK",     w=110, h=34, success=True)
        self._glass_pill(cx + 64, ay, "CANCEL", w=110, h=34, danger=True)
        self._conn_z = (cx - 119, ay - 17, cx - 9,  ay + 17)
        self._canc_z = (cx + 9,   ay - 17, cx + 119, ay + 17)

    def _draw_keyboard(self, start_y=82):
        """
        QWERTY keyboard for 480×480 round display.
          • Large keys (32-46 px wide) for easy fingertip targeting.
          • Per-row chord clamps row width — keys never overlap the round bezel.
          • Action row holds symbols / caps / space / backspace centered (no
            isolated corner buttons that would land where the panel curves).
          • Hit zones === drawn key bounds (1:1 with visuals).
        """
        cx = self.S // 2
        # Generous safe radius — keys stay well clear of the curved bezel
        R = 200
        sym_mode = getattr(self, '_sym_mode', False)

        if sym_mode:
            rows = ["1234567890", "!@#$%^&*()", "-_=+[]{}/\\", ".,;:'\"?!~`"]
        elif self._caps:
            rows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
        else:
            rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]

        total_rows = len(rows) + 1                            # + action row
        # Keyboard ends at y=432 (ACTION_ROW at 446 sits below)
        v_avail = 432 - start_y
        row_h = max(34, min(46, v_avail // (total_rows + 1)))  # bigger keys
        gap = 4

        self._keys = {}

        for ri, row in enumerate(rows):
            ky = start_y + ri * (row_h + gap) + row_h // 2
            n = len(row)
            dy = abs(ky - cx)
            if dy >= R:
                continue
            chord_w = 2 * math.sqrt(R * R - dy * dy)
            avail_w = chord_w - 28                            # bezel padding
            kw = max(32, min(46, int((avail_w - (n - 1) * gap) / n)))
            total_kw = n * kw + (n - 1) * gap
            sx = cx - total_kw // 2

            for ci, ch in enumerate(row):
                kx = sx + ci * (kw + gap) + kw // 2
                self._kk(kx, ky, ch, kw, row_h - 2)

        # ─── Action row: symbols / caps / space / backspace (centered) ──
        ay = start_y + len(rows) * (row_h + gap) + row_h // 2
        dy = abs(ay - cx)
        if dy < R:
            chord_w = 2 * math.sqrt(R * R - dy * dy)
            avail_w = chord_w - 28
            sym_lbl = "ABC" if sym_mode else "!#+"
            sym_w   = min(64, int(avail_w * 0.18))
            caps_w  = min(64, int(avail_w * 0.18))
            back_w  = min(60, int(avail_w * 0.16))
            gaps_total = 3 * gap
            space_w = max(96, avail_w - sym_w - caps_w - back_w - gaps_total)
            row_total = sym_w + caps_w + space_w + back_w + gaps_total
            sx = cx - row_total // 2
            x = sx + sym_w // 2
            self._kk(x, ay, sym_lbl, sym_w, row_h - 2)
            x += sym_w // 2 + gap + caps_w // 2
            self._kk(x, ay, "CAPS", caps_w, row_h - 2)
            x += caps_w // 2 + gap + space_w // 2
            self._kk(x, ay, " ", space_w, row_h - 2)
            x += space_w // 2 + gap + back_w // 2
            self._kk(x, ay, "⌫", back_w, row_h - 2)

    def _kk(self, x, y, ch, w, h):
        """
        Draw a single rounded key — large, theme-aware, touch-target sized.
        Hit zone === drawn rect (no offset).
        """
        hw, hh = w // 2, h // 2
        r = min(8, hh)                                        # corner radius
        bg = "#2c2c3a" if self.mode == 'dark' else "#e8ecf2"
        bd = "#5a607a" if self.mode == 'dark' else "#aab2c2"
        txt_col = self.c['text']

        # Rounded body
        self.cv.create_rectangle(x-hw+r, y-hh, x+hw-r, y+hh, fill=bg, outline="", tags="c")
        self.cv.create_rectangle(x-hw, y-hh+r, x+hw, y+hh-r, fill=bg, outline="", tags="c")
        self.cv.create_oval(x-hw,        y-hh,        x-hw+2*r, y-hh+2*r, fill=bg, outline="", tags="c")
        self.cv.create_oval(x+hw-2*r,    y-hh,        x+hw,     y-hh+2*r, fill=bg, outline="", tags="c")
        self.cv.create_oval(x-hw,        y+hh-2*r,    x-hw+2*r, y+hh,     fill=bg, outline="", tags="c")
        self.cv.create_oval(x+hw-2*r,    y+hh-2*r,    x+hw,     y+hh,     fill=bg, outline="", tags="c")
        # Subtle top/bottom hairlines for definition
        self.cv.create_line(x-hw+r, y-hh, x+hw-r, y-hh, fill=bd, tags="c")
        self.cv.create_line(x-hw+r, y+hh, x+hw-r, y+hh, fill=bd, tags="c")

        # Label — bigger fonts on bigger keys
        d = "␣" if ch == " " else ch
        if len(d) > 2:
            fs = max(9, min(11, w // 5))                      # multi-char (CAPS, ABC)
        elif len(d) == 1:
            fs = max(12, min(16, w // 3))                     # single char keys — big
        else:
            fs = max(10, min(13, w // 4))                     # 2-char (!#+, etc.)
        self.cv.create_text(x, y, text=d, fill=txt_col,
                            font=("Arial", fs, "bold"), tags="c")
        self._keys[ch] = (x - hw, y - hh, x + hw, y + hh)

    def _k(self, x, y, ch, w, h):
        """Alias for backward compat."""
        self._kk(x, y, ch, w, h)

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
            for ssid,x1,y1,x2,y2 in self._items:
                if x1<=x<=x2 and y1<=y<=y2:
                    self._ssid=ssid; self._pw=""; self._show_pw=False; self._draw_pw(); return
        elif self._page == 'pw':
            # Eye
            if hasattr(self,'_eye_z'):
                x1,y1,x2,y2=self._eye_z
                if x1<=x<=x2 and y1<=y<=y2: self._show_pw=not self._show_pw; self._draw_pw(); return
            # Keys
            for ch,(x1,y1,x2,y2) in self._keys.items():
                if x1<=x<=x2 and y1<=y<=y2:
                    if ch=="⌫": self._pw=self._pw[:-1]
                    elif ch=="CAPS": self._caps=not self._caps
                    elif ch in ("!#+","ABC"):
                        self._sym_mode = not getattr(self, '_sym_mode', False)
                    elif ch=="⏎": self._do_connect(); return
                    elif ch==" ": self._pw+=" "
                    else: self._pw+=ch
                    self._draw_pw(); return
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
                if self._page=='country':
                    self._scroll=max(0,min(getattr(self,'_max_scroll',0),self._scroll+dy)); self._draw_country()
                else:
                    self._scan_scroll=max(0,min(getattr(self,'_scan_max',0),self._scan_scroll+dy)); self._draw_scan()

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
                # Success → show the Connected Devices page
                self.win.after(0, self._draw_devices)
            else:
                self.win.after(0, lambda: self._msg("FAILED", self.c['danger']))

        threading.Thread(target=go, daemon=True).start()
        self._msg("CONNECTING...", self.c['warning'])

    def _msg(self, t, col):
        self.cv.delete("msg")
        self.cv.create_text(self.S // 2, self.S // 2, text=t,
                            fill=col, font=("Arial", 13, "bold"), tags="msg")
        # On a hard failure, return to the password screen after a beat
        if t == "FAILED":
            self.win.after(1600, self._draw_pw)

    # ─── Connected devices view ──────────────────────────────────────
    def _gather_net_info(self):
        """Get current SSID, IP, gateway, and LAN clients (best-effort)."""
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
        # IP + gateway via `ip route` / `hostname -I`
        try:
            r = subprocess.run(['hostname', '-I'],
                               capture_output=True, text=True, timeout=3)
            ips = r.stdout.strip().split()
            if ips:
                info['ip'] = ips[0]
        except Exception:
            pass
        try:
            r = subprocess.run(['ip', 'route', 'show', 'default'],
                               capture_output=True, text=True, timeout=3)
            parts = r.stdout.strip().split()
            if 'via' in parts:
                info['gateway'] = parts[parts.index('via') + 1]
        except Exception:
            pass
        # LAN devices via `arp -n` (kernel ARP table) — non-invasive
        try:
            r = subprocess.run(['arp', '-n'],
                               capture_output=True, text=True, timeout=4)
            for line in r.stdout.split('\n')[1:]:
                parts = line.split()
                if len(parts) >= 3 and parts[0] != '?':
                    ip = parts[0]
                    mac = parts[2] if len(parts) > 2 else ''
                    if mac and mac != '<incomplete>':
                        info['devices'].append((ip, mac))
                elif len(parts) >= 3 and '.' in parts[0]:
                    ip = parts[0]
                    mac = parts[2] if len(parts) > 2 else ''
                    if mac and mac != '<incomplete>':
                        info['devices'].append((ip, mac))
        except Exception:
            pass
        return info

    def _draw_devices(self):
        """Connected: show network details + LAN devices (post-connect)."""
        self._page = 'devices'
        self._clr()
        cx, c = self.S // 2, self.c

        # Title
        self.cv.create_text(cx, 50, text="✓ CONNECTED",
                            fill=c['success'],
                            font=("Arial", 12, "bold"), tags="c")

        info = self._gather_net_info()

        # Compact info card (3 rows: SSID / IP / GATEWAY)
        sw = self._safe_width(96)
        cx1 = cx - sw // 2 + 12
        cx2 = cx + sw // 2 - 12
        for row, (label, value) in enumerate([
            ("SSID",    (info['ssid'] or '—')[:20]),
            ("IP",      info['ip']),
            ("GATEWAY", info['gateway']),
        ]):
            ry = 82 + row * 28
            self.cv.create_text(cx1 + 8, ry, text=label, anchor='w',
                                fill=c['text_secondary'],
                                font=("Arial", 9, "bold"), tags="c")
            self.cv.create_text(cx2 - 8, ry, text=value, anchor='e',
                                fill=c['text'],
                                font=("Arial", 10, "bold"), tags="c")

        # Separator
        self.cv.create_line(cx1 + 16, 176, cx2 - 16, 176,
                            fill=c['card_border'], width=1, tags="c")

        # Devices header
        self.cv.create_text(cx, 192,
                            text=f"DEVICES ({len(info['devices'])})",
                            fill=c['text_secondary'],
                            font=("Arial", 9, "bold"), tags="c")

        # Devices list
        list_top = 208
        list_bot = self.ACTION_Y - 40
        row_h = 28
        max_rows = max(1, (list_bot - list_top) // row_h)
        if not info['devices']:
            self.cv.create_text(cx, (list_top + list_bot) // 2,
                                text="No other devices detected",
                                fill=c['text_secondary'],
                                font=("Arial", 10), tags="c")
        else:
            for i, (ip, mac) in enumerate(info['devices'][:max_rows]):
                y = list_top + i * row_h + row_h // 2
                rsw = self._safe_width(y) - 24
                rx1 = cx - rsw // 2
                rx2 = cx + rsw // 2
                self.cv.create_rectangle(rx1, y - 12, rx2, y + 12,
                                         fill=c['card_bg'],
                                         outline=c['card_border'], tags="c")
                self.cv.create_text(rx1 + 12, y, text=ip, anchor='w',
                                    fill=c['text'],
                                    font=("Arial", 9, "bold"), tags="c")
                self.cv.create_text(rx2 - 12, y, text=mac, anchor='e',
                                    fill=c['text_secondary'],
                                    font=("Arial", 8), tags="c")

        # Action row — REFRESH / DONE
        ay = self.ACTION_Y
        self._glass_pill(cx - 64, ay, "REFRESH", w=110, h=34, active=True)
        self._glass_pill(cx + 64, ay, "DONE",    w=110, h=34)
        self._dev_refresh_z = (cx - 119, ay - 17, cx - 9,   ay + 17)
        self._dev_done_z    = (cx + 9,   ay - 17, cx + 119, ay + 17)


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
               else None)

        n = len(self.SCOPES)
        list_top = self.CONTENT_TOP + 6
        list_bot = self.ACTION_Y - 32
        avail = list_bot - list_top
        gap = 8
        item_h = max(44, min(56, (avail - (n - 1) * gap) // n))
        total_h = n * item_h + (n - 1) * gap
        start_y = list_top + (avail - total_h) // 2

        # Equal-width rows — use the chord at the narrowest row so all four
        # scope pills line up perfectly regardless of round-display geometry.
        first_y = start_y + item_h // 2
        last_y  = start_y + (n - 1) * (item_h + gap) + item_h // 2
        narrowest = min(self._safe_width(first_y), self._safe_width(last_y))
        row_w = max(0, narrowest - 32)
        x1 = cx - row_w // 2
        x2 = cx + row_w // 2

        icon_size = item_h - 18                        # icon fits inside row
        label_font = ("Arial", 15, "bold")              # bumped from 13

        for i, (sid, label) in enumerate(self.SCOPES):
            y = start_y + i * (item_h + gap) + item_h // 2
            is_active = (sid == cur)

            if is_active:
                # ── Active: iOS green pill, white icon + label ──
                self._smooth_pill(
                    cx, y, "",
                    IOS_GREEN,
                    w=row_w, h=item_h,
                    alpha=255,
                )
                txt_col = self._pill_text_color(IOS_GREEN)
                icon_col = "#ffffff"
            else:
                # ── Inactive: frosted neutral pill, muted icon + text ──
                neutral_col, neutral_alpha = self._neutral_fill()
                self._smooth_pill(
                    cx, y, "",
                    neutral_col,
                    w=row_w, h=item_h,
                    alpha=neutral_alpha,
                )
                txt_col = c['text']
                icon_col = c['text_secondary']

            # ─── Layout: 1/3 left zone for icon (centered), 2/3 right zone
            # for label (left-aligned at the start of that zone).
            #
            #   |←——— row_w ———→|
            #   | icon  | label                  |
            #   |←1/3→|←———— 2/3 ————→|
            third = row_w // 3
            ix = x1 + third // 2                       # icon centered in left third
            lx = x1 + third + 4                        # label starts at 2/3 boundary

            icon = self._scope_icon(sid, icon_size, icon_col)
            self.cv.create_image(ix, y, image=icon, tags="c")
            self.cv.create_text(lx, y, text=label, anchor='w',
                                fill=txt_col,
                                font=label_font, tags="c")

            # Whole row is the touch target
            self._zones[sid] = (x1, y - item_h // 2, x2, y + item_h // 2)

        # EXIT — danger-styled pill at the action row
        ay = self.ACTION_Y + 4
        exit_w = max(110, min(160, row_w // 2))
        self._glass_pill(cx, ay, "EXIT", w=exit_w, h=38, danger=True,
                         font=("Arial", 11, "bold"))
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
                                font=("Arial", 11, "bold"), tags="c")

            # Toggle pill — green (success) when ON, frosted neutral when OFF
            pill_w, pill_h = 56, item_h - 14
            pill_x = x2 - pill_w // 2 - 14
            self._glass_pill(pill_x, y,
                             "ON" if is_on else "OFF",
                             w=pill_w, h=pill_h,
                             success=is_on,
                             font=("Arial", 9, "bold"))

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
                         font=("Arial", 11, "bold"))
        self._glass_pill(cx + (action_pill_w // 2 + gap_a // 2), ay,
                         "EXIT",
                         w=action_pill_w, h=36,
                         font=("Arial", 11, "bold"))
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
                             font=("Arial", 9, "bold"))
            self._tz[sid] = (tx - tab_w // 2, ty - tab_h // 2,
                             tx + tab_w // 2, ty + tab_h // 2)

        # ─── IMG/VID toggle (compact, sits right under scope tabs) ────
        sub_y = ty + tab_h // 2 + 20
        sub_w, sub_h = 88, 28
        sub_gap = 12
        self._glass_pill(cx - (sub_w + sub_gap) // 2, sub_y, "IMG",
                         w=sub_w, h=sub_h,
                         active=(self._tab == 'images'),
                         font=("Arial", 10, "bold"))
        self._glass_pill(cx + (sub_w + sub_gap) // 2, sub_y, "VID",
                         w=sub_w, h=sub_h,
                         active=(self._tab == 'videos'),
                         font=("Arial", 10, "bold"))
        self._imgz = (cx - (sub_w + sub_gap) // 2 - sub_w // 2,
                      sub_y - sub_h // 2,
                      cx - (sub_w + sub_gap) // 2 + sub_w // 2,
                      sub_y + sub_h // 2)
        self._vidz = (cx + (sub_w + sub_gap) // 2 - sub_w // 2,
                      sub_y - sub_h // 2,
                      cx + (sub_w + sub_gap) // 2 + sub_w // 2,
                      sub_y + sub_h // 2)

        # ─── 3x2 thumbnail grid — fills the middle, larger thumbs ─────
        # Action row now sits at y ≈ 396, so the grid has the whole space
        # between sub_y+sub_h/2+10 and ~370 to play with.
        self._fz = []
        action_y = self.ACTION_Y - 16            # action row pulled up
        grid_top = sub_y + sub_h // 2 + 12
        grid_bot = action_y - 30                 # leaves room for page indicator
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
                                font=("Arial", 12, "bold"), tags="c")
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
                            font=("Arial", 9, "bold"), tags="c")

        # ─── Action row: ◀  EXIT  ▶ ───────────────────────────────────
        ay = action_y
        nav_w, exit_w, h = 56, 96, 36
        nav_gap = 16
        prev_x = cx - (exit_w // 2 + nav_gap + nav_w // 2)
        next_x = cx + (exit_w // 2 + nav_gap + nav_w // 2)

        if self._page > 0:
            self._glass_pill(prev_x, ay, "◀", w=nav_w, h=h,
                             font=("Arial", 14, "bold"))
            self._prevpz = (prev_x - nav_w // 2, ay - h // 2,
                            prev_x + nav_w // 2, ay + h // 2)
        else:
            self._prevpz = (-1, -1, -1, -1)

        self._glass_pill(cx, ay, "EXIT", w=exit_w, h=h, danger=True,
                         font=("Arial", 11, "bold"))
        self._exit_zone = (cx - exit_w // 2, ay - h // 2,
                           cx + exit_w // 2, ay + h // 2)

        if self._items and (self._page + 1) * self.PER_PAGE < len(self._items):
            self._glass_pill(next_x, ay, "▶", w=nav_w, h=h,
                             font=("Arial", 14, "bold"))
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
                                font=("Arial", 11, "bold"), tags="c")

        # Filename + counter
        self.cv.create_text(cx, self.TITLE_Y - 16,
                            text=item['filename'][:24],
                            fill=c['text'],
                            font=("Arial", 10, "bold"), tags="c")
        self.cv.create_text(cx, self.TITLE_Y,
                            text=f"{self._pidx + 1} / {len(self._items)}",
                            fill=c['text_secondary'],
                            font=("Arial", 9), tags="c")

        # Action row — ◀ / BACK / ▶
        ay = self.ACTION_Y
        if self._pidx > 0:
            self._glass_pill(cx - 88, ay, "◀", w=58, h=36,
                             font=("Arial", 14, "bold"))
            self._pz = (cx - 117, ay - 18, cx - 59, ay + 18)
        else:
            self._pz = (-1, -1, -1, -1)

        self._glass_pill(cx, ay, "BACK", w=110, h=36, active=True)
        self._exit_zone = (cx - 55, ay - 18, cx + 55, ay + 18)

        if self._pidx < len(self._items) - 1:
            self._glass_pill(cx + 88, ay, "▶", w=58, h=36,
                             font=("Arial", 14, "bold"))
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
            self.cv.create_text(cx, self.CY, text="Not found",
                                fill=c['danger'],
                                font=("Arial", 11, "bold"), tags="c")
            return
        self._vcap = cv2.VideoCapture(fp)
        if not self._vcap.isOpened():
            self.cv.create_text(cx, self.CY, text="Cannot play",
                                fill=c['danger'],
                                font=("Arial", 11, "bold"), tags="c")
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
                            font=("Arial", 10, "bold"), tags="c")

        fps = self._vcap.get(cv2.CAP_PROP_FPS) or 25
        self._vdelay = max(25, int(1000 / fps))
        # Control row sits a little below the video frame's bottom edge
        self._video_ay = 380
        self._draw_video_controls()
        self._video_frame()

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
        playpause_glyph = "▶" if not self._video_playing else "⏸"

        slots = [-1.5, -0.5, 0.5, 1.5]
        # rewind, play/pause, stop, forward
        states = [
            ("⏮", "rewind",    {}),
            (playpause_glyph, "playpause", {"active": True}),
            ("⏹", "stop",      {"danger": True}),
            ("⏭", "forward",   {}),
        ]
        self._video_zones = {}
        for slot, (lbl, key, kw) in zip(slots, states):
            x = int(cx + slot * (ctrl_w + gap))
            self._glass_pill(x, ay, lbl, tag="vc",
                             w=ctrl_w, h=ctrl_h,
                             font=("Arial", 13, "bold"),
                             **kw)
            self._video_zones[key] = (x - ctrl_w // 2, ay - ctrl_h // 2,
                                       x + ctrl_w // 2, ay + ctrl_h // 2)

        # BACK to grid — sits at the very bottom action zone
        back_y = 432
        self._glass_pill(cx, back_y, "BACK TO GALLERY", tag="vc",
                         w=180, h=30,
                         font=("Arial", 10, "bold"))
        self._video_zones['back'] = (cx - 90, back_y - 15,
                                      cx + 90, back_y + 15)

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
