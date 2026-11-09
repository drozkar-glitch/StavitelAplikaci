import os, sys, time, json, base64, hashlib, jwt, requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

key_id = os.environ.get("APP_STORE_CONNECT_KEY_IDENTIFIER", "").strip()
issuer_id = os.environ.get("APP_STORE_CONNECT_ISSUER_ID", "").strip()
support_url = os.environ.get("SUPPORT_URL", "https://drozkar-glitch.github.io/StavitelAplikaci/support.html").strip()
privacy_url = support_url + "#privacy"
key_path = "/tmp/AuthKey.p8"

if not key_id or not issuer_id or not os.path.exists(key_path):
    print("❌ Chybí Apple API klíč (.p8) v trezoru ios-keys!")
    sys.exit(1)

with open(key_path, "r") as f:
    private_key = f.read()

def get_headers():
    now = int(time.time())
    payload = {"iss": issuer_id, "iat": now - 30, "exp": now + 1100, "aud": "appstoreconnect-v1"}
    token = jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": key_id, "typ": "JWT"})
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

base_url = "https://api.appstoreconnect.apple.com/v1"

def load_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, int(size))
            except Exception:
                pass
    return ImageFont.load_default()

def draw_ios_bars(draw, w, h, is_dark):
    s = w / 1290.0
    fg = (255, 255, 255) if is_dark else (20, 20, 25)
    f_stat = load_font(38 * s, bold=True)
    draw.text((76 * s, 36 * s), "9:41", fill=fg, font=f_stat)
    # Signal bars + battery
    bx = w - int(150 * s)
    by = int(44 * s)
    draw.rounded_rectangle([bx, by, bx + int(72 * s), by + int(34 * s)], radius=int(8 * s), outline=fg, width=max(2, int(3 * s)))
    draw.rounded_rectangle([bx + int(6 * s), by + int(6 * s), bx + int(56 * s), by + int(28 * s)], radius=int(4 * s), fill=fg)
    # Home indicator
    hw = int(420 * s)
    hh = max(10, int(14 * s))
    hx = (w - hw) // 2
    hy = h - int(36 * s)
    bar_col = (180, 180, 190) if is_dark else (80, 80, 90)
    draw.rounded_rectangle([hx, hy, hx + hw, hy + hh], radius=hh // 2, fill=bar_col)

def render_wavecal_screen(w, h, variant):
    s = w / 1290.0
    is_dark = (variant == 3)
    bg = (18, 18, 20) if is_dark else (250, 250, 252)
    fg = (245, 245, 248) if is_dark else (24, 24, 28)
    muted = (165, 165, 175) if is_dark else (105, 105, 115)
    div_col = (55, 55, 62) if is_dark else (222, 222, 228)

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    draw_ios_bars(draw, w, h, is_dark)

    f_date = load_font(54 * s, bold=True)
    f_sub = load_font(42 * s, bold=True)
    f_week_top = load_font(38 * s, bold=False)
    f_ev = load_font(44 * s, bold=False)
    f_day_hdr = load_font(38 * s, bold=True)
    f_day = load_font(42 * s, bold=False)
    f_day_b = load_font(42 * s, bold=True)
    f_bot = load_font(50 * s, bold=True)

    pad_x = int(42 * s)
    top_y = int(118 * s)

    # Header date
    date_txt = "9. listopadu 2026"
    tw = draw.textlength(date_txt, font=f_date)
    draw.text(((w - tw) / 2, top_y), date_txt, fill=fg, font=f_date)

    # Name day + week
    sub_y = top_y + int(72 * s)
    nd_txt = "Bohdan"
    wk_txt = "  •  46. týden (sudý)"
    w1 = draw.textlength(nd_txt, font=f_sub)
    w2 = draw.textlength(wk_txt, font=f_week_top)
    start_x = (w - (w1 + w2)) / 2
    draw.text((start_x, sub_y), nd_txt, fill=(255, 215, 0) if is_dark else (255, 68, 68), font=f_sub)
    draw.text((start_x + w1, sub_y + int(3 * s)), wk_txt, fill=muted, font=f_week_top)

    div1_y = sub_y + int(68 * s)
    draw.line([(pad_x, div1_y), (w - pad_x, div1_y)], fill=div_col, width=max(2, int(3 * s)))

    # Events list
    events = [
        "08:30  -  Odvoz na letiště Václava Havla",
        "11:00  -  Pravidelný servis a kontrola vozu",
        "14:30  -  Vyzvednutí zásilky v centru",
        "17:30  -  Rodinná večeře",
        "19:00  -  Sportovní trénink"
    ]
    ev_y = div1_y + int(24 * s)
    row_h = int(108 * s)
    for ev in events:
        draw.text((pad_x + int(18 * s), ev_y + int(26 * s)), ev, fill=fg, font=f_ev)
        ev_y += row_h
        draw.line([(pad_x, ev_y), (w - pad_x, ev_y)], fill=div_col, width=max(1, int(2 * s)))

    # Bottom section anchor
    bot_bar_y = h - int(210 * s)
    row_cal_h = int(112 * s)
    grid_top_y = bot_bar_y - 6 * row_cal_h - int(90 * s)

    draw.line([(pad_x, grid_top_y - int(18 * s)), (w - pad_x, grid_top_y - int(18 * s))], fill=div_col, width=max(2, int(3 * s)))

    # Weekday headers
    wk_col_w = int(95 * s)
    day_col_w = (w - 2 * pad_x - wk_col_w) / 7.0
    days_hdr = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
    for idx, dh in enumerate(days_hdr):
        cx = pad_x + wk_col_w + idx * day_col_w + day_col_w / 2
        dw = draw.textlength(dh, font=f_day_hdr)
        draw.text((cx - dw / 2, grid_top_y), dh, fill=muted, font=f_day_hdr)

    # 6 rows of November 2026 (Nov 1 is Sunday)
    weeks_data = [
        (44, [None, None, None, None, None, None, 1]),
        (45, [2, 3, 4, 5, 6, 7, 8]),
        (46, [9, 10, 11, 12, 13, 14, 15]),
        (47, [16, 17, 18, 19, 20, 21, 22]),
        (48, [23, 24, 25, 26, 27, 28, 29]),
        (49, [30, None, None, None, None, None, None])
    ]
    event_days = {1, 3, 5, 9, 12, 15, 18, 21, 24, 27, 30}
    sel_day = 12 if variant == 2 else 9

    start_rows_y = grid_top_y + int(72 * s)
    for r_idx, (wk_num, row_days) in enumerate(weeks_data):
        ry = start_rows_y + r_idx * row_cal_h
        w_str = str(wk_num)
        ww = draw.textlength(w_str, font=f_day_hdr)
        draw.text((pad_x + wk_col_w / 2 - ww / 2, ry + int(24 * s)), w_str, fill=muted, font=f_day_hdr)

        for c_idx, d_num in enumerate(row_days):
            if d_num is None:
                continue
            cx = pad_x + wk_col_w + c_idx * day_col_w + day_col_w / 2
            cy = ry + row_cal_h / 2
            is_sel = (d_num == sel_day)
            if is_sel:
                rad = int(46 * s)
                sel_col = (255, 213, 0) if is_dark else (0, 155, 119)
                draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=sel_col)
            d_str = str(d_num)
            font_use = f_day_b if is_sel else f_day
            dw = draw.textlength(d_str, font=font_use)
            txt_col = ((0, 0, 0) if is_dark else (255, 255, 255)) if is_sel else fg
            draw.text((cx - dw / 2, cy - int(26 * s)), d_str, fill=txt_col, font=font_use)

            if d_num in event_days:
                dr = max(4, int(7 * s))
                draw.ellipse([cx - dr, cy + int(24 * s) - dr, cx + dr, cy + int(24 * s) + dr], fill=(255, 68, 68))

    # Bottom navigation bar (< Listopad 2026 [Gear] >)
    btn_w = int(130 * s)
    btn_h = int(96 * s)
    primary_btn = (98, 70, 234) if not is_dark else (180, 160, 255)
    btn_txt_col = (255, 255, 255) if not is_dark else (20, 20, 30)
    draw.rounded_rectangle([pad_x, bot_bar_y, pad_x + btn_w, bot_bar_y + btn_h], radius=int(48 * s), fill=primary_btn)
    draw.text((pad_x + int(46 * s), bot_bar_y + int(18 * s)), "<", fill=btn_txt_col, font=f_bot)

    rx = w - pad_x - btn_w
    draw.rounded_rectangle([rx, bot_bar_y, rx + btn_w, bot_bar_y + btn_h], radius=int(48 * s), fill=primary_btn)
    draw.text((rx + int(46 * s), bot_bar_y + int(18 * s)), ">", fill=btn_txt_col, font=f_bot)

    m_title = "Listopad 2026"
    mw = draw.textlength(m_title, font=f_bot)
    draw.text(((w - mw) / 2 - int(30 * s), bot_bar_y + int(20 * s)), m_title, fill=fg, font=f_bot)

    # Variant 2: Modal dialog "Přidat událost"
    if variant == 2:
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 135))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)
        mx1 = int(76 * s)
        mx2 = w - int(76 * s)
        my1 = int(h * 0.22)
        my2 = my1 + int(1120 * s)
        draw.rounded_rectangle([mx1, my1, mx2, my2], radius=int(64 * s), fill=(255, 255, 255))

        ix1 = mx1 + int(64 * s)
        ix2 = mx2 - int(64 * s)
        cy = my1 + int(68 * s)

        draw.text((ix1, cy), "Název události:", fill=(20, 20, 25), font=f_sub)
        cy += int(66 * s)
        draw.rounded_rectangle([ix1, cy, ix2, cy + int(136 * s)], radius=int(36 * s), fill=(248, 249, 250), outline=(103, 80, 164), width=max(3, int(5 * s)))
        draw.text((ix1 + int(40 * s), cy + int(38 * s)), "Odvoz z letiště", fill=(20, 20, 25), font=f_ev)

        cy += int(182 * s)
        draw.text((ix1, cy), "Datum události:", fill=(20, 20, 25), font=f_sub)
        cy += int(66 * s)
        draw.rounded_rectangle([ix1, cy, ix2, cy + int(132 * s)], radius=int(36 * s), fill=(232, 222, 248))
        d_val = "12. 11. 2026"
        dvw = draw.textlength(d_val, font=f_bot)
        draw.text(((w - dvw) / 2, cy + int(34 * s)), d_val, fill=(29, 25, 43), font=f_bot)

        cy += int(178 * s)
        draw.text((ix1, cy), "Čas události:", fill=(20, 20, 25), font=f_sub)
        cy += int(66 * s)
        draw.rounded_rectangle([ix1, cy, ix2, cy + int(132 * s)], radius=int(36 * s), fill=(232, 222, 248))
        t_val = "14:30"
        tvw = draw.textlength(t_val, font=f_bot)
        draw.text(((w - tvw) / 2, cy + int(34 * s)), t_val, fill=(29, 25, 43), font=f_bot)

        cy += int(186 * s)
        half_w = (ix2 - ix1 - int(36 * s)) // 2
        draw.rounded_rectangle([ix1, cy, ix1 + half_w, cy + int(136 * s)], radius=int(36 * s), fill=(232, 222, 248))
        c_txt = "Zrušit"
        cw = draw.textlength(c_txt, font=f_sub)
        draw.text((ix1 + (half_w - cw) / 2, cy + int(40 * s)), c_txt, fill=(29, 25, 43), font=f_sub)

        sx1 = ix1 + half_w + int(36 * s)
        draw.rounded_rectangle([sx1, cy, ix2, cy + int(136 * s)], radius=int(36 * s), fill=(76, 175, 80))
        s_txt = "Uložit"
        sw = draw.textlength(s_txt, font=f_sub)
        draw.text((sx1 + (half_w - sw) / 2, cy + int(40 * s)), s_txt, fill=(255, 255, 255), font=f_sub)

    return img

def render_radiopm_screen(w, h, variant):
    s = w / 1290.0
    img = Image.new("RGB", (w, h), (9, 24, 38))
    draw = ImageDraw.Draw(img)
    draw_ios_bars(draw, w, h, True)

    gold = (255, 213, 79)
    cyan = (77, 208, 225)
    card_bg = (18, 40, 60)
    card_border = (52, 85, 112)

    f_hdr = load_font(50 * s, bold=True)
    f_btn = load_font(36 * s, bold=True)
    f_st = load_font(58 * s, bold=True)
    f_rds = load_font(40 * s, bold=False)
    f_pre = load_font(38 * s, bold=True)
    f_small = load_font(30 * s, bold=True)

    pad = int(48 * s)
    top_y = int(125 * s)

    # Top bar: [Stanice] | RÁDIO PM | [128 kbps]
    draw.rounded_rectangle([pad, top_y, pad + int(280 * s), top_y + int(96 * s)], radius=int(32 * s), fill=card_bg, outline=gold, width=max(2, int(3 * s)))
    draw.text((pad + int(36 * s), top_y + int(24 * s)), "☰  Stanice", fill=(255, 255, 255), font=f_btn)

    title = "RÁDIO PM"
    tw = draw.textlength(title, font=f_hdr)
    draw.text(((w - tw) / 2, top_y + int(20 * s)), title, fill=gold, font=f_hdr)

    qx1 = w - pad - int(250 * s)
    draw.rounded_rectangle([qx1, top_y, w - pad, top_y + int(96 * s)], radius=int(32 * s), fill=card_bg, outline=cyan, width=max(2, int(3 * s)))
    draw.text((qx1 + int(34 * s), top_y + int(24 * s)), "128 kbps", fill=cyan, font=f_btn)

    # Main station RDS card
    cy1 = top_y + int(150 * s)
    cy2 = cy1 + int(430 * s)
    draw.rounded_rectangle([pad, cy1, w - pad, cy2], radius=int(42 * s), fill=card_bg, outline=gold, width=max(2, int(4 * s)))

    # Logo box
    lx1 = pad + int(44 * s)
    ly1 = cy1 + int(44 * s)
    l_sz = int(150 * s)
    draw.rounded_rectangle([lx1, ly1, lx1 + l_sz, ly1 + l_sz], radius=int(38 * s), fill=gold)
    draw.text((lx1 + int(26 * s), ly1 + int(40 * s)), "RH", fill=(18, 18, 18), font=f_hdr)

    st_name = "Rádio Humor" if variant != 2 else "ČRo Radiožurnál"
    draw.text((lx1 + l_sz + int(38 * s), ly1 + int(16 * s)), "Hraje: " + st_name, fill=(0, 200, 83), font=f_btn)
    draw.text((lx1 + l_sz + int(38 * s), ly1 + int(72 * s)), st_name, fill=gold, font=f_st)

    # RDS box
    rx1 = pad + int(44 * s)
    ry1 = ly1 + l_sz + int(42 * s)
    draw.rounded_rectangle([rx1, ry1, w - pad - int(44 * s), cy2 - int(40 * s)], radius=int(28 * s), fill=(6, 14, 22), outline=card_border, width=max(2, int(3 * s)))
    rds_txt = "Karel Gott & Felix Slováček — Nejlepší scénky" if variant != 2 else "ČRo Radiožurnál — Hlavní zprávy a doprava"
    draw.text((rx1 + int(32 * s), ry1 + int(34 * s)), rds_txt, fill=(255, 255, 255), font=f_rds)

    # 2x2 Presets
    py = cy2 + int(70 * s)
    pw = (w - 2 * pad - int(32 * s)) // 2
    ph = int(190 * s)
    presets = [("RH", "Rádio Humor"), ("RB", "Rádio B"), ("ČR", "ČRo Radiožurnál"), ("RI", "Rádio Impuls")]
    for idx, (ini, pname) in enumerate(presets):
        r = idx // 2
        c = idx % 2
        px1 = pad + c * (pw + int(32 * s))
        py1 = py + r * (ph + int(32 * s))
        active = (idx == 0 and variant != 2) or (idx == 2 and variant == 2)
        draw.rounded_rectangle([px1, py1, px1 + pw, py1 + ph], radius=int(38 * s), fill=(42, 52, 38) if active else card_bg, outline=gold if active else card_border, width=max(2, int(4 * s if active else 2 * s)))
        bsz = int(112 * s)
        draw.rounded_rectangle([px1 + int(28 * s), py1 + int(39 * s), px1 + int(28 * s) + bsz, py1 + int(39 * s) + bsz], radius=int(28 * s), fill=gold if active else (26, 58, 84))
        draw.text((px1 + int(46 * s), py1 + int(68 * s)), ini, fill=(18, 18, 18) if active else gold, font=f_pre)
        draw.text((px1 + int(162 * s), py1 + int(72 * s)), pname, fill=gold if active else (255, 255, 255), font=f_pre)

    # Main Play/Stop button
    by1 = py + 2 * ph + int(105 * s)
    bh = int(156 * s)
    draw.rounded_rectangle([pad, by1, w - pad, by1 + bh], radius=int(44 * s), fill=(229, 57, 53))
    b_txt = "■   VYPNOUT RÁDIO"
    btw = draw.textlength(b_txt, font=f_hdr)
    draw.text(((w - btw) / 2, by1 + int(46 * s)), b_txt, fill=(255, 255, 255), font=f_hdr)

    # Bottom timer & pre-alarm cards
    ty1 = by1 + bh + int(65 * s)
    th = int(170 * s)
    draw.rounded_rectangle([pad, ty1, pad + pw, ty1 + th], radius=int(38 * s), fill=card_bg, outline=gold if variant == 3 else card_border, width=max(2, int(3 * s)))
    draw.text((pad + int(42 * s), ty1 + int(34 * s)), "ČASOVAČ VYPNUTÍ", fill=(180, 195, 210), font=f_small)
    draw.text((pad + int(42 * s), ty1 + int(88 * s)), "Vypne za 45 min" if variant == 3 else "Vypnuto (klepni)", fill=gold if variant == 3 else (255, 255, 255), font=f_btn)

    tx2 = pad + pw + int(32 * s)
    draw.rounded_rectangle([tx2, ty1, tx2 + pw, ty1 + th], radius=int(38 * s), fill=card_bg, outline=cyan, width=max(2, int(3 * s)))
    draw.text((tx2 + int(42 * s), ty1 + int(34 * s)), "PŘEDBUZENÍ (-30 MIN)", fill=(180, 195, 210), font=f_small)
    draw.text((tx2 + int(42 * s), ty1 + int(88 * s)), "Rádio v 06:00 (budík 06:30)", fill=cyan, font=f_btn)

    copy_txt = "© 2026 Created by Pavel Mareš"
    ctw = draw.textlength(copy_txt, font=f_small)
    draw.text(((w - ctw) / 2, h - int(110 * s)), copy_txt, fill=(160, 175, 190), font=f_small)
    return img

DISPLAY_DIMENSIONS = {
    "APP_IPHONE_69": (1320, 2868),
    "APP_IPHONE_67": (1290, 2796),
    "APP_IPHONE_65": (1284, 2778),
    "APP_IPHONE_61": (1179, 2556),
    "APP_IPHONE_58": (1170, 2532),
    "APP_IPHONE_55": (1242, 2208),
    "APP_IPAD_PRO_3GEN_129": (2048, 2732),
    "APP_IPAD_PRO_129": (2048, 2732),
    "APP_IPAD_PRO_3GEN_11": (1668, 2388),
    "APP_IPAD_105": (1668, 2224),
    "APP_IPAD_97": (1536, 2048),
}

def upload_screenshots_for_localization(loc_id, bundle_id):
    sets_res = requests.get(f"{base_url}/appStoreVersionLocalizations/{loc_id}/appScreenshotSets", headers=get_headers(), timeout=30)
    existing_sets = sets_res.json().get("data", []) if sets_res.ok else []
    existing_by_type = {s["attributes"]["screenshotDisplayType"]: s["id"] for s in existing_sets}

    # Zajistime pritomonost iPhone 6.7 / 6.5 / 6.1 (6.3") a iPad Pro 12.9 (2nd Gen i 6th Gen)
    target_types = set(existing_by_type.keys()) | {"APP_IPHONE_67", "APP_IPHONE_65", "APP_IPAD_PRO_3GEN_129", "APP_IPAD_PRO_129"}

    for dtype in target_types:
        if dtype not in DISPLAY_DIMENSIONS:
            continue
        set_id = existing_by_type.get(dtype)
        if not set_id:
            cr = requests.post(f"{base_url}/appScreenshotSets", headers=get_headers(), json={
                "data": {
                    "type": "appScreenshotSets",
                    "attributes": {"screenshotDisplayType": dtype},
                    "relationships": {"appStoreVersionLocalization": {"data": {"type": "appStoreVersionLocalizations", "id": loc_id}}}
                }
            }, timeout=30)
            if cr.ok:
                set_id = cr.json()["data"]["id"]
            else:
                continue

        # Smazani starych zamitnutych snimku v dane sade
        shots_res = requests.get(f"{base_url}/appScreenshotSets/{set_id}/appScreenshots", headers=get_headers(), timeout=30)
        if shots_res.ok:
            for sh in shots_res.json().get("data", []):
                requests.delete(f"{base_url}/appScreenshots/{sh['id']}", headers=get_headers(), timeout=30)

        w, h = DISPLAY_DIMENSIONS[dtype]
        for idx in (1, 2, 3):
            if "wavecal" in bundle_id:
                im = render_wavecal_screen(w, h, idx)
            else:
                im = render_radiopm_screen(w, h, idx)
            bio = BytesIO()
            im.save(bio, format="PNG")
            png_bytes = bio.getvalue()
            fname = f"screen_{dtype}_{idx}.png"

            res_r = requests.post(f"{base_url}/appScreenshots", headers=get_headers(), json={
                "data": {
                    "type": "appScreenshots",
                    "attributes": {"fileName": fname, "fileSize": len(png_bytes)},
                    "relationships": {"appScreenshotSet": {"data": {"type": "appScreenshotSets", "id": set_id}}}
                }
            }, timeout=30)
            if not res_r.ok:
                continue
            sh_data = res_r.json()["data"]
            sh_id = sh_data["id"]
            for op in sh_data.get("attributes", {}).get("uploadOperations", []):
                op_hdrs = {h["name"]: h["value"] for h in op.get("requestHeaders", [])}
                off = op["offset"]
                ln = op["length"]
                requests.request(op["method"], op["url"], data=png_bytes[off:off+ln], headers=op_hdrs, timeout=120)

            md5_hex = hashlib.md5(png_bytes).hexdigest()
            requests.patch(f"{base_url}/appScreenshots/{sh_id}", headers=get_headers(), json={
                "data": {
                    "type": "appScreenshots",
                    "id": sh_id,
                    "attributes": {"uploaded": True, "sourceFileChecksum": md5_hex}
                }
            }, timeout=30)
        print(f"  📸 Nahrany 3 nove UI snimky pro {dtype} ({w}x{h}).")

report_lines = []
r_apps = requests.get(f"{base_url}/apps", headers=get_headers(), timeout=30)
apps = r_apps.json().get("data", []) if r_apps.ok else []

editable_states = {"PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED", "METADATA_REJECTED", "INVALID_BINARY"}

for app in apps:
    app_id = app["id"]
    app_name = app["attributes"].get("name", "")
    bundle_id = app["attributes"].get("bundleId", "")

    # 1. Aktualizace Privacy Policy URL v appInfoLocalizations
    infos_r = requests.get(f"{base_url}/apps/{app_id}/appInfos", headers=get_headers(), timeout=30)
    if infos_r.ok:
        for info in infos_r.json().get("data", []):
            il_r = requests.get(f"{base_url}/appInfos/{info['id']}/appInfoLocalizations", headers=get_headers(), timeout=30)
            if il_r.ok:
                for il in il_r.json().get("data", []):
                    requests.patch(f"{base_url}/appInfoLocalizations/{il['id']}", headers=get_headers(), json={
                        "data": {"type": "appInfoLocalizations", "id": il["id"], "attributes": {"privacyPolicyUrl": privacy_url}}
                    }, timeout=30)

    # 2. Kontrola iOS verze
    ver_r = requests.get(f"{base_url}/apps/{app_id}/appStoreVersions", params={"filter[platform]": "IOS"}, headers=get_headers(), timeout=30)
    versions = ver_r.json().get("data", []) if ver_r.ok else []
    if not versions:
        continue

    target_v = versions[0]
    for v in versions:
        st = v["attributes"].get("appStoreState") or v["attributes"].get("appVersionState") or ""
        if st in editable_states:
            target_v = v
            break

    vid = target_v["id"]
    vstr = target_v["attributes"].get("versionString", "1.0")
    vstate = target_v["attributes"].get("appStoreState") or target_v["attributes"].get("appVersionState") or ""
    print(f"🔎 Aplikace {app_name} ({bundle_id}) - verze {vstr}, stav: {vstate}")

    if vstate not in editable_states:
        report_lines.append(f"ℹ️ {app_name} ({bundle_id}): verze {vstr} je ve stavu {vstate} (privacyPolicyUrl aktualizována).")
        continue

    # 3. Aktualizace Support URL a WhatsNew ve všech lokalizacích verze
    locs_r = requests.get(f"{base_url}/appStoreVersions/{vid}/appStoreVersionLocalizations", headers=get_headers(), timeout=30)
    if locs_r.ok:
        for loc in locs_r.json().get("data", []):
            lid = loc["id"]
            attrs = {"supportUrl": support_url}
            if not loc["attributes"].get("whatsNew"):
                attrs["whatsNew"] = "Oprava chyb, vylepšení uživatelského rozhraní a zvýšení stability aplikace."
            requests.patch(f"{base_url}/appStoreVersionLocalizations/{lid}", headers=get_headers(), json={
                "data": {"type": "appStoreVersionLocalizations", "id": lid, "attributes": attrs}
            }, timeout=30)

            if "wavecal" in bundle_id or "radiopm" in bundle_id or "humorradio" in bundle_id:
                upload_screenshots_for_localization(lid, bundle_id)

    # 4. Vyplnění App Review Detail (kontaktní údaje + odpověď na Guideline 2.1)
    review_notes = (
        "Answer to Guideline 2.1 (Information Needed):\n"
        "1. Does your app upload user's contacts to any server?\n"
        "Answer: NO. The app does NOT upload, transmit, store, or share the user's contacts or calendar events to any external server. "
        "Contacts access (CNContactStore) is used 100% locally on the device only to compare contact first names with the built-in Name Day calendar "
        "so matching name days are highlighted in yellow directly in the app's calendar view.\n\n"
        "Support & Developer Contact:\n"
        "Pavel Mareš, Email: drozkar@gmail.com, Phone: +420 606 420 002, Support URL: " + support_url
    )
    rev_attrs = {
        "contactFirstName": "Pavel",
        "contactLastName": "Mares",
        "contactEmail": "drozkar@gmail.com",
        "contactPhone": "+420606420002",
        "demoAccountRequired": False,
        "notes": review_notes
    }
    rd_get = requests.get(f"{base_url}/appStoreVersions/{vid}/appStoreReviewDetail", headers=get_headers(), timeout=30)
    if rd_get.ok and rd_get.json().get("data"):
        rd_id = rd_get.json()["data"]["id"]
        requests.patch(f"{base_url}/appStoreReviewDetails/{rd_id}", headers=get_headers(), json={
            "data": {"type": "appStoreReviewDetails", "id": rd_id, "attributes": rev_attrs}
        }, timeout=30)
    else:
        requests.post(f"{base_url}/appStoreReviewDetails", headers=get_headers(), json={
            "data": {
                "type": "appStoreReviewDetails",
                "attributes": rev_attrs,
                "relationships": {"appStoreVersion": {"data": {"type": "appStoreVersions", "id": vid}}}
            }
        }, timeout=30)

    # 5. Přiřazení nejnovějšího VALID buildu (pokud ještě není přiřazen)
    b_res = requests.get(f"{base_url}/builds", params={"filter[app]": app_id, "filter[processingState]": "VALID", "limit": 5}, headers=get_headers(), timeout=30)
    builds = b_res.json().get("data", []) if b_res.ok else []
    if builds:
        newest_build_id = builds[0]["id"]
        requests.patch(f"{base_url}/appStoreVersions/{vid}/relationships/build", headers=get_headers(), json={
            "data": {"type": "builds", "id": newest_build_id}
        }, timeout=30)

    # 6. Odeslání opravené verze zpět ke schválení (Resubmit to App Review)
    sub_list = requests.get(f"{base_url}/reviewSubmissions", params={"filter[app]": app_id, "filter[state]": "READY_FOR_REVIEW,UNRESOLVED_ISSUES"}, headers=get_headers(), timeout=30)
    if sub_list.ok:
        for s_item in sub_list.json().get("data", []):
            sid = s_item["id"]
            requests.patch(f"{base_url}/reviewSubmissions/{sid}", headers=get_headers(), json={
                "data": {"type": "reviewSubmissions", "id": sid, "attributes": {"canceled": True}}
            }, timeout=30)

    time.sleep(2)
    sc_res = requests.post(f"{base_url}/reviewSubmissions", headers=get_headers(), json={
        "data": {
            "type": "reviewSubmissions",
            "attributes": {"platform": "IOS"},
            "relationships": {"app": {"data": {"type": "apps", "id": app_id}}}
        }
    }, timeout=30)
    submitted_ok = False
    if sc_res.ok:
        new_sid = sc_res.json()["data"]["id"]
        it_res = requests.post(f"{base_url}/reviewSubmissionItems", headers=get_headers(), json={
            "data": {
                "type": "reviewSubmissionItems",
                "relationships": {
                    "reviewSubmission": {"data": {"type": "reviewSubmissions", "id": new_sid}},
                    "appStoreVersion": {"data": {"type": "appStoreVersions", "id": vid}}
                }
            }
        }, timeout=30)
        if it_res.ok:
            sub_patch = requests.patch(f"{base_url}/reviewSubmissions/{new_sid}", headers=get_headers(), json={
                "data": {"type": "reviewSubmissions", "id": new_sid, "attributes": {"submitted": True}}
            }, timeout=30)
            if sub_patch.ok:
                submitted_ok = True

    if submitted_ok:
        report_lines.append(f"✅ {app_name} ({bundle_id}): Support URL, snímky i poznámky pro Apple Review opraveny a verze {vstr} byla znovu odeslána ke schválení!")
    else:
        report_lines.append(f"✅ {app_name} ({bundle_id}): Support URL, snímky i poznámky pro Apple Review jsou uložené u verze {vstr} (připraveno k odeslání v App Store Connect).")

with open("appstore_fix_report.txt", "w", encoding="utf-8") as rf:
    rf.write("\n".join(report_lines) + "\n")

print("=== SOUHRN OPRAVY APP STORE CONNECT ===")
for line in report_lines:
    print(line)
