#!/usr/bin/env python3
"""上志比の地図データ（data/kamishihi/kamishihi-map.js）を作る（P2 作業B）。

元データ：data/kamishihi/raw/（tools/kamishihi/fetch.py で取得。OpenStreetMap・国土地理院 標高タイル）
座標の決め方は光明寺の地図と同じ（下志比・光明寺の駅と踏切から逆算。docs/p2-kamishihi-map.md）：
  東西 x = 0.8 × 東へのメートル、南北 z = −0.8 ×（北へのメートル）、高さ = 0.8 ×（標高 − 44m）− 11.5
縮尺は承認済みの案1：牧福島〜山王は0.8倍のまま、山王の東〜市荒川の手前の田畑だけ東西を詰める（0.15倍）。
光明寺と座標が重ならないよう、x は REGION_X0（4000）より東に置く。

使い方：python3 tools/kamishihi/build_map.py
"""
import base64
import json
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dem  # noqa: E402
import osm  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'data', 'kamishihi', 'kamishihi-map.js')

S = 0.8
LON0, LAT0 = 136.3476, 36.089             # 光明寺の地図の原点（逆算した値）
MX = 111320 * math.cos(math.radians(36.089))
MY = 110950
SEG = [(136.3770, 136.4005, 0.8), (136.4005, 136.4145, 0.15), (136.4145, 136.4245, 0.8)]  # 東西の区間と縮尺
LAT_S, LAT_N = 36.0712, 36.0881
X0 = 5000.0                               # 西の端の x
STEP = 3.2                                # 格子の間隔（光明寺と同じ。実際の4m）
HREF, SHIFT = 44.0, -11.5


def xg(lon):
    x = X0
    for a, b, s in SEG:
        lo = min(max(lon, a), b)
        x += (lo - a) * MX * s
    if lon < SEG[0][0]:
        x -= (SEG[0][0] - lon) * MX * SEG[0][2]
    if lon > SEG[-1][1]:
        x += (lon - SEG[-1][1]) * MX * SEG[-1][2]
    return x


def lon_of(x):
    t = X0
    for a, b, s in SEG:
        w = (b - a) * MX * s
        if x <= t + w or (a, b, s) == SEG[-1]:
            return a + (x - t) / (MX * s)
        t += w
    return SEG[-1][1]


def zg(lat):
    return -S * (lat - LAT0) * MY


def lat_of(z):
    return LAT0 - z / (S * MY)


def scale_at(lon):
    for a, b, s in SEG:
        if a <= lon <= b:
            return s
    return SEG[0][2] if lon < SEG[0][0] else SEG[-1][2]


def hgame(elev):
    return S * (elev - HREF) + SHIFT


def P(la, lo):
    return (round(xg(lo), 2), round(zg(la), 2))


def poly_area_m2(c):
    pts = [((lo - c[0][1]) * MX, (la - c[0][0]) * MY) for la, lo in c]
    a = 0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def min_rect(c):
    """建物の外形を、向きのある長方形に（実際のメートル）。"""
    pts = [((lo - c[0][1]) * MX, (la - c[0][0]) * MY) for la, lo in c]
    best = None
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        ang = math.atan2(y2 - y1, x2 - x1)
        ca, sa = math.cos(-ang), math.sin(-ang)
        rx = [x * ca - y * sa for x, y in pts]
        ry = [x * sa + y * ca for x, y in pts]
        area = (max(rx) - min(rx)) * (max(ry) - min(ry))
        if best is None or area < best[0]:
            cx, cy = (max(rx) + min(rx)) / 2, (max(ry) + min(ry)) / 2
            best = (area, max(rx) - min(rx), max(ry) - min(ry), ang, cx * math.cos(ang) - cy * math.sin(ang), cx * math.sin(ang) + cy * math.cos(ang))
    _, l, w, ang, ox, oy = best
    lat = c[0][0] + oy / MY
    lon = c[0][1] + ox / MX
    return lat, lon, l, w, ang


def inside(px, py, poly):
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi:
            c = not c
        j = i
    return c


def main():
    nodes, ways, rels = osm.load()
    W = xg(SEG[-1][1]) - X0
    nx = int(math.ceil(W / STEP)) + 1
    z0, z1 = zg(LAT_N), zg(LAT_S)
    ny = int(math.ceil((z1 - z0) / STEP)) + 1
    print('grid', nx, ny, 'size', round(W), round(z1 - z0))
    # ---- 標高 ----
    H = [0.0] * (nx * ny)
    E = [0.0] * (nx * ny)
    for k in range(ny):
        lat = lat_of(z0 + k * STEP)
        for i in range(nx):
            lon = lon_of(X0 + i * STEP)
            e = dem.elev(lat, lon)
            E[k * nx + i] = e if e is not None else 80.0
    # ---- 水（九頭竜川の水面の多角形） ----
    water_polys = []
    for members, t in rels:
        if t.get('natural') == 'water' or t.get('water') == 'river':
            for typ, ref, role in members:
                if typ == 'way' and role == 'outer' and ref in ways:
                    water_polys.append(ways[ref][0])
    for refs, t in ways.values():
        if t.get('natural') == 'water' and refs and refs[0] == refs[-1]:
            water_polys.append(refs)
    # 外周の線をつないで輪にする（多角形の外側の線は分割されている）
    segs = [osm.coords(nodes, r) for r in water_polys]
    rings = []
    segs = [s for s in segs if len(s) > 1]
    while segs:
        ring = segs.pop(0)
        changed = True
        while changed and ring[0] != ring[-1]:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == ring[-1]:
                    ring += s[1:]; segs.pop(i); changed = True; break
                if s[-1] == ring[-1]:
                    ring += list(reversed(s))[1:]; segs.pop(i); changed = True; break
        rings.append([P(la, lo) for la, lo in ring])
    # ---- 分類 0:草地 1:森 2:水 4:田畑 5:家のまわり ----
    C = [0] * (nx * ny)
    import numpy as np
    Ea = np.array(E).reshape(ny, nx)
    # 近くの低い所（谷の底）からの高さで山を見分ける
    from scipy.ndimage import minimum_filter, uniform_filter
    low = minimum_filter(Ea, size=int(400 / STEP))
    gy, gx = np.gradient(Ea, 4.0)
    slope = np.hypot(gx, gy)
    forest = (Ea - low > 14) | (slope > 0.22)
    for k in range(ny):
        for i in range(nx):
            if forest[k, i]:
                C[k * nx + i] = 1
    for ring in rings:
        xs = [p[0] for p in ring]; zs = [p[1] for p in ring]
        i0, i1 = max(0, int((min(xs) - X0) / STEP)), min(nx - 1, int((max(xs) - X0) / STEP) + 1)
        k0, k1 = max(0, int((min(zs) - z0) / STEP)), min(ny - 1, int((max(zs) - z0) / STEP) + 1)
        for k in range(k0, k1 + 1):
            for i in range(i0, i1 + 1):
                if inside(X0 + i * STEP, z0 + k * STEP, ring):
                    C[k * nx + i] = 2
    # ---- 田畑 ----
    farms = []
    for refs, t in ways.values():
        if t.get('landuse') == 'farmland' and refs and refs[0] == refs[-1]:
            c = osm.coords(nodes, refs)
            p = [P(la, lo) for la, lo in c]
            if any(X0 - 20 < x < X0 + W + 20 and z0 - 20 < z < z1 + 20 for x, z in p):
                farms.append(p)
                xs = [q[0] for q in p]; zs = [q[1] for q in p]
                for k in range(max(0, int((min(zs) - z0) / STEP)), min(ny - 1, int((max(zs) - z0) / STEP) + 1) + 1):
                    for i in range(max(0, int((min(xs) - X0) / STEP)), min(nx - 1, int((max(xs) - X0) / STEP) + 1) + 1):
                        if C[k * nx + i] != 2 and inside(X0 + i * STEP, z0 + k * STEP, p):
                            C[k * nx + i] = 4
    # ---- 建物 ----
    bld = []
    for refs, t in ways.values():
        if 'building' not in t or not refs or refs[0] != refs[-1]:
            continue
        c = osm.coords(nodes, refs)[:-1]
        if len(c) < 3:
            continue
        la, lo, l, w, ang = min_rect(c)
        x, z = P(la, lo)
        if not (X0 + 15 < x < X0 + W - 15 and z0 + 15 < z < z1 - 15):
            continue
        area = poly_area_m2(c)
        if area < 8:
            continue
        rot = -ang  # 東が +x、北が −z なので向きは反転
        bld.append([x, z, round(l * S, 2), round(w * S, 2), round(rot, 4), round(area), 0, 0, scale_at(lo)])
    # 縮めた区間では、重なる建物を間引く（大きいものを残す）
    bld.sort(key=lambda b: -b[5])
    kept = []
    for b in bld:
        if b[8] < 0.5 and any(math.hypot(b[0] - q[0], b[1] - q[1]) < (max(b[2], b[3]) + max(q[2], q[3])) * 0.6 for q in kept):
            continue
        kept.append(b)
    for b in kept:  # 家が3軒以上かたまる所は「集落の中」（庭木・家の種類に使う）
        n = sum(1 for q in kept if abs(q[0] - b[0]) < 40 and abs(q[1] - b[1]) < 40)
        b[6] = 1 if n >= 6 else 0
    bld = [b[:8] for b in kept]
    for b in bld:
        i, k = int((b[0] - X0) / STEP), int((b[1] - z0) / STEP)
        for dk in range(-3, 4):
            for di in range(-3, 4):
                ii, kk = i + di, k + dk
                if 0 <= ii < nx and 0 <= kk < ny and C[kk * nx + ii] in (0, 1, 4):
                    C[kk * nx + ii] = 5
    # ---- 道・線路・川 ----
    RW = {'trunk': 7.6, 'primary': 7.0, 'secondary': 6.4, 'tertiary': 6.0, 'unclassified': 4.8, 'residential': 4.4, 'service': 3.4, 'track': 2.8, 'path': 1.5, 'footway': 1.6}
    roads, rails, streams = [], [], []

    def clip(pts):
        out, cur = [], []
        for p in pts:
            if X0 - 10 < p[0] < X0 + W + 10 and z0 - 10 < p[1] < z1 + 10:
                cur.append(p)
            else:
                if len(cur) > 1:
                    out.append(cur)
                cur = []
        if len(cur) > 1:
            out.append(cur)
        return out

    for refs, t in ways.values():
        c = osm.coords(nodes, refs)
        if len(c) < 2:
            continue
        pts = [P(la, lo) for la, lo in c]
        k = t.get('highway')
        if k in RW:
            for piece in clip(pts):
                roads.append({'k': k, 'w': RW[k], 'b': 1 if t.get('bridge') == 'yes' else 0, 'l': int(t.get('layer', 0) or 0), 'tn': 1 if t.get('tunnel') == 'yes' else 0, 'n': t.get('name', ''), 'p': piece})
        elif t.get('railway') == 'rail':
            for piece in clip(pts):
                rails.append(piece)
        elif t.get('waterway') in ('river', 'stream', 'ditch', 'canal') and t.get('name') != '九頭竜川':
            w = 7.0 if t['waterway'] == 'river' else (2.2 if t['waterway'] == 'stream' else 1.6)
            for piece in clip(pts):
                streams.append({'w': w, 'n': t.get('name', ''), 'cul': 1 if t.get('tunnel') == 'culvert' else 0, 'p': piece})
    # ---- 目印 ----
    pts = {'station': [], 'crossing': [], 'worship': []}
    for nid, (la, lo, t) in nodes.items():
        x, z = P(la, lo)
        if not (X0 < x < X0 + W and z0 < z < z1):
            continue
        if t.get('railway') in ('station', 'halt'):
            pts['station'].append([x, z, t.get('name', '')])
        elif t.get('railway') == 'level_crossing':
            pts['crossing'].append([x, z])
        elif t.get('amenity') == 'place_of_worship':
            pts['worship'].append([x, z, t.get('name', '')])
    # ---- 高さ（水の所は少し下げ、水面は別に作る） ----
    for n in range(nx * ny):
        H[n] = hgame(E[n]) - (1.2 if C[n] == 2 else 0)
    q = struct.pack('<%dH' % (nx * ny), *[max(0, min(65535, int(round((h + 40) * 50)))) for h in H])
    cb = bytearray((nx * ny + 1) // 2)
    for n, c in enumerate(C):
        cb[n >> 1] |= (c & 15) << (4 if n & 1 else 0)
    WLV = [round(hgame(E[n]) + 0.05, 2) if C[n] == 2 else 0 for n in range(nx * ny)]
    wq = struct.pack('<%dH' % (nx * ny), *[max(0, min(65535, int(round((h + 40) * 50)))) if h else 0 for h in WLV])
    # ---- 着く場所（国道416号、光明寺から来る西の端）と、光明寺へ戻る出口 ----
    r416 = [r for r in roads if r['n'] == '国道416号']
    west = min((p for r in r416 for p in r['p']), key=lambda p: p[0])
    # 範囲の西の端（X0+24）から 30 入った所に着く。出口は西の端そのもの（着いてすぐ戻ってしまわないように離す）
    arrival = {'x': round(max(west[0], X0 + 24) + 30, 1), 'z': round(west[1], 1), 'facing': round(math.pi / 2, 3)}
    for r in r416:  # 道の上に合わせる
        for a, b in zip(r['p'], r['p'][1:]):
            if (a[0] - arrival['x']) * (b[0] - arrival['x']) <= 0 and a[0] != b[0]:
                f = (arrival['x'] - a[0]) / (b[0] - a[0])
                arrival['z'] = round(a[1] + f * (b[1] - a[1]), 1)
    def road_z(x, dflt):
        for r in r416:
            for a, b in zip(r['p'], r['p'][1:]):
                if (a[0] - x) * (b[0] - x) <= 0 and a[0] != b[0]:
                    return round(a[1] + (x - a[0]) / (b[0] - a[0]) * (b[1] - a[1]), 1)
        return dflt
    data = {
        'name': '上志比', 'S': S, 'grid': {'x0': X0, 'z0': round(z0, 2), 'step': STEP, 'nx': nx, 'ny': ny},
        'play': {'minX': X0 + 24, 'maxX': round(X0 + W - 24, 1), 'minZ': round(z0 + 24, 1), 'maxZ': round(z1 - 24, 1)},
        'terrain': base64.b64encode(q).decode(), 'cls': base64.b64encode(bytes(cb)).decode(), 'water': base64.b64encode(wq).decode(),
        'roads': roads, 'rails': rails, 'streams': streams, 'farms': farms, 'bld': bld, 'pts': pts,
        'arrival': arrival, 'exitWest': {'x': X0 + 24, 'z': road_z(X0 + 24, arrival['z']), 'r': 12},
        'seg': SEG, 'lon0': LON0, 'lat0': LAT0,
        'credit': '地形：国土地理院 標高タイル（5mメッシュ）を加工／道・建物・田畑・川：© OpenStreetMap contributors（ODbL）',
        'sources': json.load(open(os.path.join(ROOT, 'data', 'kamishihi', 'raw', 'sources.json'), encoding='utf8')),
    }
    js = 'window.KAMISHIHI_MAP=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n'
    open(OUT, 'w', encoding='utf8').write(js)
    print('wrote', OUT, len(js), 'roads', len(roads), 'rails', len(rails), 'streams', len(streams), 'farms', len(farms), 'bld', len(bld), 'water rings', len(rings), 'arrival', arrival)


main()
