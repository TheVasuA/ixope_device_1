"""
HTML Templates - Liquid Glass iOS-style medical UI.

Design language:
  • Liquid glass chips (Apple iOS 18 / visionOS style) with blur + saturation
  • Refined SF-Symbols-style SVG icons with gradient strokes
  • Light blue accent that lifts on hover with a small delay + gentle magnify
  • High-contrast typography for clinical readability
  • Pure CSS, no external CDN, no JS frameworks
"""

# ─── Base CSS (shared across all pages) ──────────────────────────────────────
BASE_CSS = """
:root {
    /* ─── Surface colors ─────────────────────────────────────────────── */
    --bg-base:        #06070d;
    --bg-deep:        #0a0c14;
    --bg-elev:        #11141d;
    --bg-card:        rgba(22, 26, 38, 0.45);
    --bg-glass:       rgba(255, 255, 255, 0.04);
    --bg-glass-2:     rgba(255, 255, 255, 0.07);

    /* ─── Borders / strokes ──────────────────────────────────────────── */
    --stroke:         rgba(255, 255, 255, 0.10);
    --stroke-strong:  rgba(255, 255, 255, 0.18);
    --stroke-glow:    rgba(125, 211, 252, 0.55);

    /* ─── Typography ─────────────────────────────────────────────────── */
    --t-primary:      #f3f5fb;
    --t-secondary:    #98a0b8;
    --t-muted:        #5a6178;

    /* ─── Brand / accent (cyan/sky — iOS 26 Liquid Glass tint) ───────── */
    --accent:         #5ac8fa;          /* iOS system cyan */
    --accent-soft:    #7dd3fc;          /* lifted hover tint */
    --accent-bright:  #a5e8ff;          /* peak refraction highlight */
    --accent-deep:    #0a84ff;          /* pressed / focus */
    --accent-glow:    rgba(90, 200, 250, 0.20);
    --accent-halo:    rgba(125, 211, 252, 0.38);
    --accent-bloom:   rgba(165, 232, 255, 0.55);

    /* ─── Status ─────────────────────────────────────────────────────── */
    --ok:             #30d158;
    --warn:           #ff9f0a;
    --bad:            #ff453a;

    /* ─── Geometry ───────────────────────────────────────────────────── */
    --r-lg:           22px;
    --r-md:           16px;
    --r-sm:           12px;

    /* ─── Motion: glass-settling easings ─────────────────────────────── */
    /* "settle" = strong overshoot then float into rest */
    --ease-settle:    cubic-bezier(0.16, 1.36, 0.32, 1);
    /* "glide" = silky linearish out for color/glow */
    --ease-glide:     cubic-bezier(0.22, 1, 0.36, 1);
    /* "flow" = slow viscous return for the press release */
    --ease-flow:      cubic-bezier(0.65, 0, 0.35, 1);

    --t-fast:         220ms;
    --t-norm:         360ms;
    --t-slow:         520ms;
    --t-glassy:       620ms;            /* used on the magnify "settle" */
    --t-delay:        90ms;              /* the small "settling" delay */

    /* ─── Shadows ────────────────────────────────────────────────────── */
    --sh-1:  0 1px 0 rgba(255,255,255,0.06) inset, 0 10px 30px rgba(0,0,0,0.40);
    --sh-2:  0 1px 0 rgba(255,255,255,0.10) inset, 0 18px 50px rgba(0,0,0,0.55);
    --sh-glow: 0 0 0 1px var(--stroke-glow), 0 12px 40px var(--accent-halo);

    /* ─── Refractive edge — the iOS 26 "thick glass rim" stack ───────── */
    /* outer drop, inner top sheen, inner bottom shadow, edge bevel */
    --refract:
        0 1px 0 rgba(255,255,255,0.18) inset,
        0 -1px 0 rgba(0,0,0,0.30) inset,
        0 0 0 0.5px rgba(255,255,255,0.08) inset,
        0 14px 40px rgba(0,0,0,0.35),
        0 2px 6px rgba(0,0,0,0.25);
    --refract-hover:
        0 1px 0 rgba(255,255,255,0.32) inset,
        0 -1px 0 rgba(0,0,0,0.20) inset,
        0 0 0 0.5px rgba(165,232,255,0.30) inset,
        0 22px 60px rgba(0,0,0,0.45),
        0 0 36px var(--accent-halo),
        0 4px 14px rgba(125,211,252,0.30);
}

* { margin: 0; padding: 0; box-sizing: border-box; }
*:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 6px; }

html, body { height: 100%; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text',
                 'Inter', 'Segoe UI', system-ui, sans-serif;
    font-feature-settings: "ss01", "cv11";
    background: var(--bg-base);
    color: var(--t-primary);
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    letter-spacing: -0.01em;
}

/* Ambient gradient — soft medical aurora */
body::before {
    content: '';
    position: fixed; inset: 0;
    background:
      radial-gradient(900px 600px at 12% 18%, rgba(90, 200, 250, 0.10), transparent 60%),
      radial-gradient(700px 500px at 88% 10%, rgba(125, 211, 252, 0.07), transparent 55%),
      radial-gradient(900px 700px at 50% 100%, rgba(48, 209, 88, 0.05), transparent 60%);
    pointer-events: none;
    z-index: 0;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
    position: relative;
    z-index: 1;
}

h1, h2, h3 { letter-spacing: -0.02em; }
.section-title {
    font-size: 18px;
    font-weight: 650;
    margin-bottom: 16px;
    color: var(--t-primary);
}

/* ════════════════════════════════════════════════════════════════════════
   LIQUID GLASS — iOS 26 multi-layer system
   Layers (bottom → top):
     1. backdrop-filter: blur + saturate + contrast + brightness
        (saturation pops the hue behind glass; contrast deepens the refraction;
         brightness lifts the median so dark backgrounds still read as glass)
     2. background gradient: angular wash so the glass has a "thickness" feel
     3. ::before — refractive top sheen (concentrated highlight at top edge)
     4. ::after  — caustic / bloom layer (light-blue glow leaking under it)
     5. inset shadows: top white rim + bottom dark rim = bevelled glass edge
   ════════════════════════════════════════════════════════════════════════ */
.glass {
    position: relative;
    background:
        linear-gradient(155deg,
            rgba(255,255,255,0.10) 0%,
            rgba(255,255,255,0.03) 38%,
            rgba(255,255,255,0.01) 62%,
            rgba(255,255,255,0.06) 100%),
        var(--bg-card);
    backdrop-filter:        blur(26px) saturate(200%) contrast(115%) brightness(110%);
    -webkit-backdrop-filter: blur(26px) saturate(200%) contrast(115%) brightness(110%);
    border: 1px solid var(--stroke);
    border-radius: var(--r-lg);
    box-shadow: var(--refract);
    isolation: isolate;
}
/* Top sheen — the wet/liquid highlight along the upper rim */
.glass::before {
    content: '';
    position: absolute; inset: 0;
    border-radius: inherit;
    background: linear-gradient(
        180deg,
        rgba(255,255,255,0.22) 0%,
        rgba(255,255,255,0.05) 30%,
        rgba(255,255,255,0)    55%,
        rgba(255,255,255,0.04) 100%
    );
    pointer-events: none;
    mix-blend-mode: screen;
    opacity: 0.9;
}

/* ════════════════════════════════════════════════════════════════════════
   NAVBAR
   ════════════════════════════════════════════════════════════════════════ */
.navbar {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 14px;
    margin-bottom: 24px;
    background:
        linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02)),
        var(--bg-card);
    backdrop-filter:        blur(28px) saturate(200%) contrast(115%) brightness(108%);
    -webkit-backdrop-filter: blur(28px) saturate(200%) contrast(115%) brightness(108%);
    border: 1px solid var(--stroke);
    border-radius: 20px;
    box-shadow: var(--refract);
    position: sticky; top: 12px; z-index: 50;
}

.navbar .logo {
    font-size: 17px;
    font-weight: 700;
    letter-spacing: -0.5px;
    margin-right: auto;
    padding: 0 10px;
}
.navbar .logo span {
    background: linear-gradient(135deg, var(--accent), var(--accent-soft));
    -webkit-background-clip: text;
            background-clip: text;
    color: transparent;
}

.navbar a {
    display: inline-flex; align-items: center; gap: 7px;
    color: var(--t-secondary);
    text-decoration: none;
    font-size: 13.5px;
    font-weight: 550;
    padding: 8px 14px;
    border-radius: 12px;
    transition:
        color        var(--t-norm)  var(--ease-glide)  var(--t-delay),
        background   var(--t-norm)  var(--ease-glide)  var(--t-delay),
        box-shadow   var(--t-slow)  var(--ease-glide)  var(--t-delay),
        transform    var(--t-glassy) var(--ease-settle) var(--t-delay);
}
.navbar a:hover {
    color: var(--accent-soft);
    background: var(--accent-glow);
    transform: translateY(-1px) scale(1.04);
    box-shadow: inset 0 0 0 1px var(--stroke-glow), 0 6px 18px var(--accent-halo);
}
.navbar a.active {
    color: var(--accent);
    background: var(--accent-glow);
    box-shadow: inset 0 0 0 1px var(--stroke-glow);
}
.navbar a svg {
    transition: transform var(--t-glassy) var(--ease-settle) var(--t-delay);
}
.navbar a:hover svg { transform: scale(1.18); }

/* ════════════════════════════════════════════════════════════════════════
   CARDS
   ════════════════════════════════════════════════════════════════════════ */
.card {
    position: relative;
    padding: 22px;
    background:
        linear-gradient(155deg,
            rgba(255,255,255,0.08) 0%,
            rgba(255,255,255,0.02) 40%,
            rgba(255,255,255,0.01) 60%,
            rgba(255,255,255,0.05) 100%),
        var(--bg-card);
    backdrop-filter:        blur(24px) saturate(195%) contrast(115%) brightness(108%);
    -webkit-backdrop-filter: blur(24px) saturate(195%) contrast(115%) brightness(108%);
    border: 1px solid var(--stroke);
    border-radius: var(--r-lg);
    box-shadow: var(--refract);
    transition:
        transform     var(--t-glassy) var(--ease-settle) var(--t-delay),
        border-color  var(--t-norm)   var(--ease-glide)  var(--t-delay),
        box-shadow    var(--t-slow)   var(--ease-glide)  var(--t-delay),
        background    var(--t-slow)   var(--ease-glide)  var(--t-delay);
    isolation: isolate;
}
/* Top rim sheen */
.card::before {
    content: '';
    position: absolute; inset: 0;
    border-radius: inherit;
    background: linear-gradient(180deg,
        rgba(255,255,255,0.18) 0%,
        rgba(255,255,255,0.04) 28%,
        rgba(255,255,255,0)    52%,
        rgba(255,255,255,0.03) 100%);
    pointer-events: none;
    mix-blend-mode: screen;
    opacity: 0.85;
}
/* Cyan caustic bloom that breathes in on hover */
.card::after {
    content: '';
    position: absolute; inset: -1px;
    border-radius: inherit;
    background:
        radial-gradient(120% 80% at 50% 110%, var(--accent-halo), transparent 60%),
        radial-gradient(80% 60% at 50% -10%, rgba(165,232,255,0.20), transparent 65%);
    pointer-events: none;
    opacity: 0;
    transition: opacity var(--t-slow) var(--ease-glide) var(--t-delay);
    z-index: -1;
}
.card:hover {
    transform: translateY(-3px) scale(1.012);
    border-color: var(--stroke-glow);
    box-shadow: var(--refract-hover);
}
.card:hover::after { opacity: 1; }
.card:active {
    transform: translateY(-1px) scale(0.998);
    transition-duration: 140ms;
}

/* ════════════════════════════════════════════════════════════════════════
   GRIDS
   ════════════════════════════════════════════════════════════════════════ */
.grid-2 { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.grid-3 { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.grid-4 { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 14px; }

/* ════════════════════════════════════════════════════════════════════════
   GLASS ICON CHIP — iOS 26 "Liquid Glass" specimen
   ────────────────────────────────────────────────────────────────────────
   Construction:
     • The chip itself is the primary glass slab — backdrop-filter does
       blur+saturate+contrast+brightness so content behind it bends realistically.
     • Background is two stacked gradients: a light angular wash (thickness)
       on top of a tint (the chip's color identity).
     • Inset shadows form the bevel — bright top rim + dark bottom rim — and
       a subtle inner stroke gives the "edge of glass" line.
     • ::before is the upper specular highlight (the wet shine).
     • ::after is the cyan caustic that grows on hover (refractive bloom).
     • The inner SVG carries its own drop-shadow so it floats above the bevel.
   ════════════════════════════════════════════════════════════════════════ */
.gicon {
    --gicon-size: 56px;
    --gicon-tint: rgba(125, 211, 252, 0.18);

    width: var(--gicon-size);
    height: var(--gicon-size);
    display: inline-flex;
    align-items: center;
    justify-content: center;

    /* Squircle radius — close to iOS app icon proportion */
    border-radius: calc(var(--gicon-size) * 0.30);

    /* Layered backgrounds: thickness wash → tint */
    background:
        linear-gradient(155deg,
            rgba(255,255,255,0.22) 0%,
            rgba(255,255,255,0.06) 35%,
            rgba(255,255,255,0.02) 60%,
            rgba(255,255,255,0.10) 100%),
        var(--gicon-tint);

    /* The actual refraction layer */
    backdrop-filter:        blur(18px) saturate(200%) contrast(118%) brightness(112%);
    -webkit-backdrop-filter: blur(18px) saturate(200%) contrast(118%) brightness(112%);

    border: 1px solid rgba(255,255,255,0.16);

    /* Refractive bevel stack: inner top rim, inner bottom rim, edge line, drop */
    box-shadow:
        0 1px 0 rgba(255,255,255,0.30) inset,
        0 -1px 0 rgba(0,0,0,0.28) inset,
        0 0 0 0.5px rgba(255,255,255,0.10) inset,
        0 8px 22px rgba(0,0,0,0.32),
        0 2px 6px rgba(0,0,0,0.22);

    color: var(--accent);
    position: relative;
    isolation: isolate;
    overflow: visible;        /* let the cyan halo bleed past the chip */
    will-change: transform;

    transition:
        transform     var(--t-glassy) var(--ease-settle) var(--t-delay),
        color         var(--t-norm)   var(--ease-glide)  var(--t-delay),
        box-shadow    var(--t-slow)   var(--ease-glide)  var(--t-delay),
        border-color  var(--t-norm)   var(--ease-glide)  var(--t-delay),
        background    var(--t-slow)   var(--ease-glide)  var(--t-delay),
        backdrop-filter var(--t-slow) var(--ease-glide)  var(--t-delay);
}

/* Specular top sheen — the wet liquid look */
.gicon::before {
    content: '';
    position: absolute;
    left: 10%; right: 10%; top: 6%;
    height: 42%;
    border-radius: 50%;
    background:
        radial-gradient(ellipse at 50% 0%,
            rgba(255,255,255,0.65) 0%,
            rgba(255,255,255,0.18) 38%,
            transparent 70%);
    filter: blur(2px);
    pointer-events: none;
    opacity: 0.9;
    transition:
        opacity   var(--t-norm)   var(--ease-glide)  var(--t-delay),
        transform var(--t-glassy) var(--ease-settle) var(--t-delay);
    z-index: 2;
}

/* Caustic / refractive bloom — cyan light leaking from beneath the slab */
.gicon::after {
    content: '';
    position: absolute;
    inset: -55%;
    border-radius: 50%;
    background:
        radial-gradient(closest-side,
            var(--accent-bloom) 0%,
            var(--accent-halo)  40%,
            transparent 72%);
    opacity: 0;
    pointer-events: none;
    transition:
        opacity   var(--t-slow)   var(--ease-glide)  var(--t-delay),
        transform var(--t-glassy) var(--ease-settle) var(--t-delay);
    z-index: -1;
    filter: blur(6px);
}

.gicon svg {
    width: 56%;
    height: 56%;
    z-index: 1;
    filter:
        drop-shadow(0 1px 0 rgba(0,0,0,0.45))
        drop-shadow(0 0 6px rgba(125,211,252,0.0));
    transition:
        transform var(--t-glassy) var(--ease-settle) var(--t-delay),
        filter    var(--t-slow)   var(--ease-glide)  var(--t-delay);
}

/* ─── Hover: the "settle" — small magnify, cyan glow, deeper refraction ─ */
.gicon:hover,
.card:hover .gicon,
.scope-card:hover .gicon {
    transform: translateY(-4px) scale(1.10);
    color: var(--accent-bright);
    border-color: var(--stroke-glow);
    background:
        linear-gradient(155deg,
            rgba(255,255,255,0.30) 0%,
            rgba(255,255,255,0.10) 35%,
            rgba(255,255,255,0.04) 60%,
            rgba(255,255,255,0.14) 100%),
        rgba(125, 211, 252, 0.26);
    backdrop-filter:        blur(22px) saturate(220%) contrast(125%) brightness(118%);
    -webkit-backdrop-filter: blur(22px) saturate(220%) contrast(125%) brightness(118%);
    box-shadow:
        0 1px 0 rgba(255,255,255,0.45) inset,
        0 -1px 0 rgba(0,0,0,0.18) inset,
        0 0 0 0.5px rgba(165,232,255,0.40) inset,
        0 14px 36px rgba(0,0,0,0.42),
        0 0 28px var(--accent-halo),
        0 4px 16px rgba(125,211,252,0.40);
}
.gicon:hover::before,
.card:hover .gicon::before,
.scope-card:hover .gicon::before {
    opacity: 1;
    transform: translateY(-1px) scale(1.04);
}
.gicon:hover::after,
.card:hover .gicon::after,
.scope-card:hover .gicon::after {
    opacity: 1;
    transform: scale(1.05);
}
.gicon:hover svg,
.card:hover .gicon svg,
.scope-card:hover .gicon svg {
    transform: scale(1.08);
    filter:
        drop-shadow(0 1px 0 rgba(0,0,0,0.45))
        drop-shadow(0 0 10px rgba(165,232,255,0.55));
}

/* ─── Press: viscous compress, no instant snap ──────────────────────── */
.gicon:active,
.card:active .gicon,
.scope-card:active .gicon {
    transform: translateY(-1px) scale(0.98);
    transition:
        transform 160ms var(--ease-flow) 0ms,
        box-shadow 160ms var(--ease-flow) 0ms;
}

/* ════════════════════════════════════════════════════════════════════════
   CLICK ANIMATION — liquid ripple + glass squish + shimmer sweep
   ────────────────────────────────────────────────────────────────────────
   Trigger: JS adds .gicon-tap on click (auto-removed when animation ends).
   Three layers run in parallel for a single 720ms beat:
     1. .gicon       → @keyframes liquid-squish     (squish → magnify → settle)
     2. .gicon-ripple → @keyframes liquid-ripple    (radial wave radiates out)
     3. .gicon-shine  → @keyframes liquid-shine     (specular bar sweeps across)
   ════════════════════════════════════════════════════════════════════════ */

/* Stage container needs to allow ripple/shine to live inside the chip */
.gicon { overflow: hidden; }              /* keep shine inside the slab */
.gicon::after { overflow: visible; }      /* but caustic still bleeds out */

/* The squish-magnify-settle dance (compound transform on the chip itself) */
@keyframes liquid-squish {
    0%   { transform: translateY(0)    scale(1.00); }
    14%  { transform: translateY(2px)  scale(0.92, 1.04); }   /* compress + spread */
    32%  { transform: translateY(-6px) scale(1.18, 1.10); }   /* peak magnify */
    55%  { transform: translateY(-3px) scale(1.05, 1.03); }
    78%  { transform: translateY(-1px) scale(1.02, 1.01); }
    100% { transform: translateY(0)    scale(1.00); }
}

/* Same dance, slightly less extreme, for the SVG inside */
@keyframes liquid-glyph {
    0%   { transform: scale(1);    filter: drop-shadow(0 0 0 transparent); }
    20%  { transform: scale(0.92); }
    35%  { transform: scale(1.20); filter: drop-shadow(0 0 14px var(--accent-bloom)); }
    60%  { transform: scale(1.05); filter: drop-shadow(0 0 10px var(--accent-halo)); }
    100% { transform: scale(1);    filter: drop-shadow(0 0 0 transparent); }
}

/* Ripple — a circle scaled from origin (set via --rx/--ry inline by JS) */
@keyframes liquid-ripple {
    0%   { transform: translate(-50%,-50%) scale(0);   opacity: 0.55; }
    40%  { opacity: 0.40; }
    100% { transform: translate(-50%,-50%) scale(2.6); opacity: 0;    }
}

/* Shine — diagonal specular bar sweeps left → right */
@keyframes liquid-shine {
    0%   { transform: translateX(-120%) skewX(-18deg); opacity: 0;    }
    20%  { opacity: 0.9;  }
    100% { transform: translateX(220%)  skewX(-18deg); opacity: 0;    }
}

/* Bloom pulse — the cyan ::after halo throbs once on click */
@keyframes liquid-bloom {
    0%   { opacity: 0;    transform: scale(0.85); }
    35%  { opacity: 1;    transform: scale(1.10); }
    100% { opacity: 0;    transform: scale(1.25); }
}

.gicon-tap {
    animation: liquid-squish 720ms var(--ease-settle) forwards;
}
.gicon-tap svg {
    animation: liquid-glyph 720ms var(--ease-settle) forwards;
}
.gicon-tap::after {
    animation: liquid-bloom 720ms var(--ease-glide) forwards;
}

/* Ripple element — JS injects this with .gicon-ripple class + --rx/--ry */
.gicon-ripple {
    position: absolute;
    left: var(--rx, 50%);
    top:  var(--ry, 50%);
    width: 140%;
    height: 140%;
    border-radius: 50%;
    background:
        radial-gradient(closest-side,
            rgba(255,255,255,0.55) 0%,
            rgba(165,232,255,0.40) 35%,
            rgba(125,211,252,0.10) 65%,
            transparent 80%);
    pointer-events: none;
    transform: translate(-50%,-50%) scale(0);
    z-index: 3;
    mix-blend-mode: screen;
    filter: blur(1px);
    animation: liquid-ripple 620ms var(--ease-glide) forwards;
}

/* Shine element — diagonal highlight bar */
.gicon-shine {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
    border-radius: inherit;
    z-index: 2;
}
.gicon-shine::before {
    content: '';
    position: absolute;
    top: -20%; bottom: -20%;
    left: 0;
    width: 40%;
    background: linear-gradient(90deg,
        transparent 0%,
        rgba(255,255,255,0.45) 45%,
        rgba(165,232,255,0.55) 50%,
        rgba(255,255,255,0.45) 55%,
        transparent 100%);
    filter: blur(3px);
    animation: liquid-shine 720ms var(--ease-glide) forwards;
    opacity: 0;
}

/* Image-card click animation — same language, scaled for rectangles */
@keyframes card-tap {
    0%   { transform: translateY(0) scale(1); }
    18%  { transform: translateY(1px) scale(0.985, 1.010); }
    40%  { transform: translateY(-5px) scale(1.04, 1.025); }
    100% { transform: translateY(-3px) scale(1.015); }
}
.image-card.gicon-tap,
.card.gicon-tap {
    animation: card-tap 520ms var(--ease-settle) forwards;
}

/* ─── Color-tinted variants — chip identity color when at rest ──────── */
.gicon--green   { --gicon-tint: rgba(48, 209, 88, 0.20);  color: var(--ok); }
.gicon--orange  { --gicon-tint: rgba(255, 159, 10, 0.20); color: var(--warn); }
.gicon--purple  { --gicon-tint: rgba(191, 90, 242, 0.20); color: #bf5af2; }
.gicon--blue    { --gicon-tint: rgba(10, 132, 255, 0.22); color: var(--accent); }
.gicon--cyan    { --gicon-tint: rgba(90, 200, 250, 0.22); color: var(--accent); }

/* On hover, every variant unifies to the cyan accent for consistent feedback */
.gicon--green:hover,  .card:hover .gicon--green,  .scope-card:hover .gicon--green,
.gicon--orange:hover, .card:hover .gicon--orange, .scope-card:hover .gicon--orange,
.gicon--purple:hover, .card:hover .gicon--purple, .scope-card:hover .gicon--purple,
.gicon--blue:hover,   .card:hover .gicon--blue,   .scope-card:hover .gicon--blue,
.gicon--cyan:hover,   .card:hover .gicon--cyan,   .scope-card:hover .gicon--cyan {
    color: var(--accent-bright);
    border-color: var(--stroke-glow);
}

/* ─── Sizes ─────────────────────────────────────────────────────────── */
.gicon--xs { --gicon-size: 28px; border-radius: 9px; }
.gicon--sm { --gicon-size: 36px; }
.gicon--lg { --gicon-size: 64px; }
.gicon--xl { --gicon-size: 80px; }

/* ════════════════════════════════════════════════════════════════════════
   SCOPE CARDS
   ════════════════════════════════════════════════════════════════════════ */
.scope-card {
    text-align: center;
    padding: 28px 18px 22px;
    cursor: pointer;
    user-select: none;
}
.scope-card .gicon { margin: 0 auto 14px; }
.scope-card h3 {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 4px;
    color: var(--t-primary);
}
.scope-card .stats {
    font-size: 12.5px;
    color: var(--t-muted);
    font-variant-numeric: tabular-nums;
}

/* ════════════════════════════════════════════════════════════════════════
   LIVE FEED
   ════════════════════════════════════════════════════════════════════════ */
.live-container {
    position: relative;
    border-radius: var(--r-lg);
    overflow: hidden;
    border: 1px solid var(--stroke);
    margin-bottom: 24px;
    box-shadow: var(--sh-2);
    background: #000;
}
.live-container img { width: 100%; display: block; }

.live-badge {
    position: absolute; top: 14px; left: 14px;
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 11px;
    background: rgba(255, 69, 58, 0.92);
    color: #fff;
    font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
    border-radius: 999px;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 6px 16px rgba(255,69,58,0.35);
}
.live-badge::before {
    content: '';
    width: 7px; height: 7px; border-radius: 50%;
    background: #fff;
    box-shadow: 0 0 6px #fff;
    animation: live-pulse 1.6s ease-in-out infinite;
}
@keyframes live-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%      { opacity: 0.45; transform: scale(0.85); }
}

/* ════════════════════════════════════════════════════════════════════════
   IMAGE & VIDEO CARDS
   ════════════════════════════════════════════════════════════════════════ */
.image-card {
    border-radius: var(--r-md);
    overflow: hidden;
    cursor: pointer;
    position: relative;
    border: 1px solid var(--stroke);
    background: var(--bg-elev);
    transition:
        transform     var(--t-glassy) var(--ease-settle) var(--t-delay),
        border-color  var(--t-norm)   var(--ease-glide)  var(--t-delay),
        box-shadow    var(--t-slow)   var(--ease-glide)  var(--t-delay);
}
.image-card img {
    width: 100%; height: 160px; object-fit: cover; display: block;
    transition: transform var(--t-glassy) var(--ease-settle) var(--t-delay);
}
.image-card:hover {
    transform: translateY(-3px) scale(1.015);
    border-color: var(--stroke-glow);
    box-shadow: 0 14px 36px rgba(0,0,0,0.5),
                0 0 0 1px var(--stroke-glow),
                0 0 28px var(--accent-halo);
}
.image-card:hover img { transform: scale(1.07); }
.image-card .overlay {
    position: absolute; left: 0; right: 0; bottom: 0;
    padding: 10px 12px;
    font-size: 11px; line-height: 1.4;
    color: rgba(255,255,255,0.92);
    background: linear-gradient(transparent, rgba(0,0,0,0.85));
}

.video-card { padding: 14px; }
.video-card video {
    width: 100%;
    border-radius: var(--r-sm);
    margin-bottom: 10px;
    background: #000;
    display: block;
}
.video-card .meta {
    font-size: 12px;
    color: var(--t-muted);
    font-variant-numeric: tabular-nums;
    line-height: 1.5;
}

/* ════════════════════════════════════════════════════════════════════════
   BUTTONS — liquid glass pill
   ════════════════════════════════════════════════════════════════════════ */
.btn {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 9px 16px;
    font-family: inherit;
    font-size: 13px; font-weight: 550; line-height: 1;
    color: var(--t-primary);
    background:
        linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02)),
        var(--bg-glass);
    border: 1px solid var(--stroke);
    border-radius: 999px;
    backdrop-filter:        blur(16px) saturate(190%) contrast(115%) brightness(108%);
    -webkit-backdrop-filter: blur(16px) saturate(190%) contrast(115%) brightness(108%);
    cursor: pointer;
    text-decoration: none;
    box-shadow:
        0 1px 0 rgba(255,255,255,0.18) inset,
        0 -1px 0 rgba(0,0,0,0.20) inset,
        0 4px 12px rgba(0,0,0,0.30);
    transition:
        color        var(--t-norm)   var(--ease-glide)  var(--t-delay),
        background   var(--t-norm)   var(--ease-glide)  var(--t-delay),
        border-color var(--t-norm)   var(--ease-glide)  var(--t-delay),
        transform    var(--t-glassy) var(--ease-settle) var(--t-delay),
        box-shadow   var(--t-slow)   var(--ease-glide)  var(--t-delay);
}
.btn:hover {
    color: var(--accent-bright);
    background:
        linear-gradient(180deg, rgba(165,232,255,0.18), rgba(125,211,252,0.10)),
        var(--accent-glow);
    border-color: var(--stroke-glow);
    transform: translateY(-2px) scale(1.04);
    box-shadow:
        0 1px 0 rgba(255,255,255,0.32) inset,
        0 -1px 0 rgba(0,0,0,0.16) inset,
        0 8px 22px var(--accent-halo),
        0 0 18px rgba(125,211,252,0.30);
}
.btn:active {
    transform: translateY(0) scale(0.97);
    transition-duration: 140ms;
}
.btn svg { transition: transform var(--t-glassy) var(--ease-settle) var(--t-delay); }
.btn:hover svg { transform: scale(1.14); }

.btn-danger:hover {
    color: var(--bad);
    background: rgba(255, 69, 58, 0.16);
    border-color: rgba(255, 69, 58, 0.55);
    box-shadow:
        0 1px 0 rgba(255,255,255,0.28) inset,
        0 -1px 0 rgba(0,0,0,0.18) inset,
        0 8px 22px rgba(255, 69, 58, 0.28);
}

/* ════════════════════════════════════════════════════════════════════════
   TABS
   ════════════════════════════════════════════════════════════════════════ */
.tabs {
    display: inline-flex;
    gap: 2px;
    padding: 4px;
    background:
        linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)),
        var(--bg-card);
    border: 1px solid var(--stroke);
    border-radius: 14px;
    backdrop-filter:        blur(18px) saturate(190%) contrast(115%) brightness(108%);
    -webkit-backdrop-filter: blur(18px) saturate(190%) contrast(115%) brightness(108%);
    box-shadow: var(--refract);
}
.tab {
    padding: 8px 16px;
    font-size: 12.5px; font-weight: 550;
    color: var(--t-secondary);
    border-radius: 10px;
    cursor: pointer;
    user-select: none;
    transition:
        color      var(--t-norm)   var(--ease-glide)  var(--t-delay),
        background var(--t-norm)   var(--ease-glide)  var(--t-delay),
        transform  var(--t-glassy) var(--ease-settle) var(--t-delay);
}
.tab:hover { color: var(--accent-bright); transform: translateY(-1px) scale(1.03); }
.tab.active {
    background:
        linear-gradient(180deg, rgba(165,232,255,0.18), rgba(125,211,252,0.08)),
        var(--accent-glow);
    color: var(--accent);
    box-shadow:
        inset 0 0 0 1px var(--stroke-glow),
        0 4px 14px var(--accent-halo);
}

/* ════════════════════════════════════════════════════════════════════════
   STATUS / EMPTY
   ════════════════════════════════════════════════════════════════════════ */
.status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    display: inline-block;
}
.status-dot.online  { background: var(--ok);  box-shadow: 0 0 8px var(--ok); }
.status-dot.offline { background: var(--bad); box-shadow: 0 0 8px var(--bad); }

.empty {
    grid-column: 1 / -1;
    text-align: center;
    padding: 56px 20px;
    color: var(--t-muted);
    font-size: 13px;
}

/* ════════════════════════════════════════════════════════════════════════
   ACCESSIBILITY — respect users who prefer reduced motion
   ════════════════════════════════════════════════════════════════════════ */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        transition-duration: 0.01ms !important;
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
    }
    .gicon:hover, .card:hover .gicon { transform: none; }
}

/* ════════════════════════════════════════════════════════════════════════
   RESPONSIVE
   ════════════════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
    .container { padding: 14px; }
    .navbar { padding: 8px 10px; flex-wrap: wrap; gap: 4px; }
    .navbar a { padding: 7px 10px; font-size: 12.5px; }
    .grid-2 { grid-template-columns: 1fr; }
    .image-card img { height: 140px; }
}
"""

# ─── Shared JS — liquid click animation wired to all interactive elements ────
# Listens for click/touch on .gicon, .card, .image-card, .btn, .navbar a, .tab.
# Spawns a ripple at the exact click point, plus a sweeping shine bar.
# Auto-removes on animationend so it can re-fire on every click.
BASE_JS = """
(function() {
    'use strict';

    const TAP_TARGETS = '.gicon, .scope-card, .card, .image-card, .btn, .navbar a, .tab';

    function spawnRipple(host, x, y) {
        // Click point relative to the host element (as percentages)
        const rect = host.getBoundingClientRect();
        const rx = ((x - rect.left) / rect.width)  * 100;
        const ry = ((y - rect.top)  / rect.height) * 100;

        // Ripple layer
        const ripple = document.createElement('span');
        ripple.className = 'gicon-ripple';
        ripple.style.setProperty('--rx', rx + '%');
        ripple.style.setProperty('--ry', ry + '%');
        host.appendChild(ripple);
        ripple.addEventListener('animationend', () => ripple.remove(), { once: true });

        // Shine sweep — only on glass-bodied elements where it reads
        if (host.classList.contains('gicon') ||
            host.classList.contains('btn')   ||
            host.classList.contains('card')) {
            const shine = document.createElement('span');
            shine.className = 'gicon-shine';
            host.appendChild(shine);
            shine.addEventListener('animationend', () => shine.remove(), { once: true });
            // Fallback timer in case animationend doesn't fire (Safari quirks)
            setTimeout(() => shine.remove(), 900);
        }
    }

    function squish(host) {
        // Don't stack the squish animation if the user spam-clicks
        host.classList.remove('gicon-tap');
        // Force reflow so the next add re-triggers the animation
        void host.offsetWidth;
        host.classList.add('gicon-tap');
        host.addEventListener('animationend', function onEnd(e) {
            if (e.target === host) {
                host.classList.remove('gicon-tap');
                host.removeEventListener('animationend', onEnd);
            }
        });
    }

    function handleTap(e) {
        const host = e.target.closest(TAP_TARGETS);
        if (!host) return;

        // Position uses pointer coords with touch fallback
        const pt = e.touches && e.touches[0] ? e.touches[0] : e;
        const x = pt.clientX, y = pt.clientY;

        // If the click was on a card, animate the inner .gicon too (compound)
        const innerGicon = host.querySelector(':scope > .gicon');

        // Find an element whose computed position is non-static (so absolute
        // children anchor to it). .gicon, .btn already are. For cards we add
        // ripple to the card itself; the .gicon child runs its own squish.
        const rippleHost = host.matches('.gicon, .btn, .card, .image-card') ? host : host;
        // Make sure the host can contain absolutely-positioned children
        const cs = getComputedStyle(rippleHost);
        if (cs.position === 'static') rippleHost.style.position = 'relative';

        spawnRipple(rippleHost, x, y);
        squish(host);
        if (innerGicon) squish(innerGicon);
    }

    // Use pointerdown for snappy feedback (fires before click on touch+mouse)
    document.addEventListener('pointerdown', handleTap, { passive: true });

    // Honor reduced-motion preference — skip ripple/shine entirely
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        document.removeEventListener('pointerdown', handleTap);
    }
})();
"""

# ─── Liquid Glass SF-Symbol-style SVG Icons ──────────────────────────────────
# All icons share viewBox="0 0 24 24", round joins/caps, 1.6 stroke for finesse,
# and leverage `currentColor` so the parent .gicon hue propagates.
ICONS_SVG = {
    'home': (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M3.5 11 12 4l8.5 7"/>'
        '<path d="M5.5 9.8V19a1.5 1.5 0 0 0 1.5 1.5h3.5V15a1.5 1.5 0 0 1 3 0v5.5H17a1.5 1.5 0 0 0 1.5-1.5V9.8"/>'
        '</svg>'
    ),
    'stethoscope': (
        # Earpieces (top), tubing curving down into a Y, chest-piece bell at right
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M5 3v5a4 4 0 0 0 4 4h0a4 4 0 0 0 4-4V3"/>'
        '<path d="M5 3h1.5M11.5 3H13"/>'
        '<path d="M9 12v3a5 5 0 0 0 5 5h0a4 4 0 0 0 4-4v-1.2"/>'
        '<circle cx="18" cy="11.5" r="2.3"/>'
        '<circle cx="18" cy="11.5" r="0.6" fill="currentColor"/>'
        '</svg>'
    ),
    'image': (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<rect x="3" y="4.5" width="18" height="15" rx="3.5"/>'
        '<circle cx="8.5" cy="10" r="1.6"/>'
        '<path d="m4 17 4.5-4.5a2 2 0 0 1 2.8 0L16 17"/>'
        '<path d="m13 14 2-2a2 2 0 0 1 2.8 0L21 15.2"/>'
        '</svg>'
    ),
    'video': (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<rect x="2.5" y="6.5" width="13.5" height="11" rx="3"/>'
        '<path d="m16 12 5-3v9l-5-3z"/>'
        '</svg>'
    ),
    'live': (
        '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
        '<circle cx="12" cy="12" r="6"/>'
        '</svg>'
    ),
    'eye': (   # Ophthalmoscope
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M2.5 12C4.5 7.5 8 5 12 5s7.5 2.5 9.5 7c-2 4.5-5.5 7-9.5 7s-7.5-2.5-9.5-7Z"/>'
        '<circle cx="12" cy="12" r="3.2"/>'
        '<circle cx="12" cy="12" r="1" fill="currentColor"/>'
        '</svg>'
    ),
    'ear': (   # Otoscope — abstract ear canal
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M9 4.5a6 6 0 0 1 9 5.5c0 2.6-1.7 3.5-3 4.5s-1.5 2.5-2.5 3.5-3 1.2-4.2 0-1.3-3-.3-4.2c1-1.2 2.5-1.7 2.5-3.3a2.5 2.5 0 1 0-5 0"/>'
        '</svg>'
    ),
    'derm': (  # Dermatoscope — magnifier on skin
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<circle cx="10.5" cy="10.5" r="6"/>'
        '<path d="M15 15l5 5"/>'
        '<path d="M8.5 9.5h4M10.5 7.5v4" opacity="0.7"/>'
        '</svg>'
    ),
    'microscope': (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M9 3.5h4l1 2-1 2H9l-1-2z"/>'
        '<path d="M11 7.5v6"/>'
        '<path d="M8 13.5h6"/>'
        '<path d="M7 17.5a5 5 0 0 0 10 0"/>'
        '<path d="M3.5 20.5h17"/>'
        '<path d="M11 17.5h2"/>'
        '</svg>'
    ),
    'download': (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M12 4v11"/>'
        '<path d="m7 11 5 5 5-5"/>'
        '<path d="M5 19.5h14"/>'
        '</svg>'
    ),
    'trash': (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M4 6.5h16"/>'
        '<path d="M9.5 6.5V5a1.5 1.5 0 0 1 1.5-1.5h2A1.5 1.5 0 0 1 14.5 5v1.5"/>'
        '<path d="M6.5 6.5 7.4 19a2 2 0 0 0 2 1.8h5.2a2 2 0 0 0 2-1.8l.9-12.5"/>'
        '<path d="M10 10.5v6M14 10.5v6"/>'
        '</svg>'
    ),
    'refresh': (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M3.5 12a8.5 8.5 0 0 1 14.5-6"/>'
        '<path d="M19 3v4.5h-4.5"/>'
        '<path d="M20.5 12a8.5 8.5 0 0 1-14.5 6"/>'
        '<path d="M5 21v-4.5h4.5"/>'
        '</svg>'
    ),
}


def icon(name, cls=""):
    """Return inline SVG icon. Optional CSS class for sizing tweaks."""
    svg = ICONS_SVG.get(name, "")
    if cls and svg:
        svg = svg.replace("<svg ", f'<svg class="{cls}" ', 1)
    return svg


def _gicon(name, variant="blue", size=""):
    """Wrap an SVG inside a liquid-glass chip container."""
    cls = f"gicon gicon--{variant}"
    if size:
        cls += f" gicon--{size}"
    return f'<span class="{cls}">{icon(name)}</span>'


# ─── Page Templates ──────────────────────────────────────────────────────────

INDEX_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#06070d">
    <title>IXOPE Medical</title>
    <style>{BASE_CSS}</style>
</head>
<body>
<div class="container">
    <nav class="navbar">
        <div class="logo">IX<span>OPE</span></div>
        <a href="/" class="active">{icon('stethoscope')} Live</a>
        <a href="/images">{icon('image')} Images</a>
        <a href="/videos">{icon('video')} Videos</a>
    </nav>

    <div class="live-container">
        <div class="live-badge">LIVE</div>
        <img src="/live_feed" alt="Live Feed">
    </div>

    <h2 class="section-title">Scopes</h2>
    <div class="grid-2">
        <div class="card scope-card" onclick="location.href='/scope/opth'">
            {_gicon('eye', 'green', 'lg')}
            <h3>Ophthalmoscope</h3>
            <div class="stats" id="opth-stats">—</div>
        </div>
        <div class="card scope-card" onclick="location.href='/scope/otto'">
            {_gicon('ear', 'blue', 'lg')}
            <h3>Otoscope</h3>
            <div class="stats" id="otto-stats">—</div>
        </div>
        <div class="card scope-card" onclick="location.href='/scope/derm'">
            {_gicon('derm', 'orange', 'lg')}
            <h3>Dermatoscope</h3>
            <div class="stats" id="derm-stats">—</div>
        </div>
        <div class="card scope-card" onclick="location.href='/scope/micro'">
            {_gicon('microscope', 'purple', 'lg')}
            <h3>Microscope</h3>
            <div class="stats" id="micro-stats">—</div>
        </div>
    </div>
</div>
<script>
['opth','otto','derm','micro'].forEach(s => {{
    fetch(`/scope/${{s}}/stats`).then(r=>r.json()).then(d => {{
        document.getElementById(s+'-stats').textContent =
            `${{d.images}} image${{d.images===1?'':'s'}} · ${{d.videos}} video${{d.videos===1?'':'s'}}`;
    }}).catch(()=>{{}});
}});
</script>
<script>{BASE_JS}</script>
</body>
</html>"""


IMAGES_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#06070d">
    <title>Images · IXOPE</title>
    <style>{BASE_CSS}</style>
</head>
<body>
<div class="container">
    <nav class="navbar">
        <div class="logo">IX<span>OPE</span></div>
        <a href="/">{icon('stethoscope')} Live</a>
        <a href="/images" class="active">{icon('image')} Images</a>
        <a href="/videos">{icon('video')} Videos</a>
    </nav>

    <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; margin-bottom:20px;">
        <h2 class="section-title" style="margin:0;">All Images</h2>
        <div class="tabs" id="scope-tabs">
            <div class="tab active" data-scope="all"   onclick="filterScope(event,'all')">All</div>
            <div class="tab"        data-scope="opth"  onclick="filterScope(event,'opth')">Opth</div>
            <div class="tab"        data-scope="otto"  onclick="filterScope(event,'otto')">Oto</div>
            <div class="tab"        data-scope="derm"  onclick="filterScope(event,'derm')">Derm</div>
            <div class="tab"        data-scope="micro" onclick="filterScope(event,'micro')">Micro</div>
        </div>
    </div>

    <div class="grid-4" id="images-grid">
        <div class="empty">Loading…</div>
    </div>
</div>
<script>
let allImages = [];
async function load() {{
    try {{
        const r = await fetch('/api/images');
        allImages = await r.json();
        display(allImages);
    }} catch (e) {{
        document.getElementById('images-grid').innerHTML =
            '<div class="empty">Failed to load images</div>';
    }}
}}
function display(imgs) {{
    const g = document.getElementById('images-grid');
    if (!imgs.length) {{ g.innerHTML = '<div class="empty">No images found</div>'; return; }}
    g.innerHTML = imgs.map(i => `
        <div class="image-card" onclick="window.open('${{i.path}}','_blank')">
            <img src="${{i.path}}" loading="lazy" alt="${{i.filename}}">
            <div class="overlay">${{i.filename}}<br>${{(i.size/1024).toFixed(0)}} KB</div>
        </div>
    `).join('');
}}
function filterScope(ev, s) {{
    document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
    ev.currentTarget.classList.add('active');
    display(s==='all' ? allImages : allImages.filter(i=>i.scope===s));
}}
load();
</script>
<script>{BASE_JS}</script>
</body>
</html>"""


VIDEOS_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#06070d">
    <title>Videos · IXOPE</title>
    <style>{BASE_CSS}</style>
</head>
<body>
<div class="container">
    <nav class="navbar">
        <div class="logo">IX<span>OPE</span></div>
        <a href="/">{icon('stethoscope')} Live</a>
        <a href="/images">{icon('image')} Images</a>
        <a href="/videos" class="active">{icon('video')} Videos</a>
    </nav>

    <h2 class="section-title">All Videos</h2>

    <div class="grid-3" id="videos-grid">
        <div class="empty">Loading…</div>
    </div>
</div>
<script>
async function load() {{
    try {{
        const r = await fetch('/api/videos');
        const videos = await r.json();
        const g = document.getElementById('videos-grid');
        if (!videos.length) {{ g.innerHTML = '<div class="empty">No videos found</div>'; return; }}
        g.innerHTML = videos.map(v => `
            <div class="card video-card">
                <video controls preload="metadata" playsinline>
                    <source src="${{v.path}}" type="video/mp4">
                </video>
                <div class="meta">${{v.filename}}</div>
                <div class="meta">${{(v.size/1048576).toFixed(1)}} MB</div>
                <div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
                    <a class="btn" href="${{v.path}}" target="_blank" rel="noopener">{icon('download')} Open</a>
                    <button class="btn btn-danger" onclick="del('${{v.filename}}')">{icon('trash')} Delete</button>
                </div>
            </div>
        `).join('');
    }} catch (e) {{
        document.getElementById('videos-grid').innerHTML =
            '<div class="empty">Failed to load videos</div>';
    }}
}}
function del(f) {{
    if (!confirm('Delete '+f+'?')) return;
    fetch('/video/'+f, {{method:'DELETE'}}).then(r=>r.json()).then(()=>load());
}}
load();
</script>
<script>{BASE_JS}</script>
</body>
</html>"""
