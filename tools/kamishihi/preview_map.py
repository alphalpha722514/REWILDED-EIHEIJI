#!/usr/bin/env python3
"""上志比の地図データを上から見た画像にする（確認用）。使い方：python3 tools/kamishihi/preview_map.py 出力.png"""
import base64, json, math, struct, sys
from PIL import Image, ImageDraw
s = open('data/kamishihi/kamishihi-map.js', encoding='utf8').read(); d = json.loads(s[s.index('=') + 1:s.rindex(';')])
g = d['grid']; nx, ny = g['nx'], g['ny']; X0, Z0, ST = g['x0'], g['z0'], g['step']
cb = base64.b64decode(d['cls']); C = [(cb[n >> 1] >> (4 if n & 1 else 0)) & 15 for n in range(nx * ny)]
q = struct.unpack('<%dH' % (nx * ny), base64.b64decode(d['terrain'])); H = [v / 50 - 40 for v in q]
pal = {0: (118, 152, 74), 1: (52, 78, 44), 2: (64, 110, 124), 4: (132, 166, 86), 5: (150, 146, 138)}
img = Image.new('RGB', (nx, ny)); px = img.load(); hmin, hmax = min(H), max(H)
for k in range(ny):
    for i in range(nx):
        c = pal.get(C[k * nx + i], (255, 0, 255)); sh = 0.7 + 0.45 * (H[k * nx + i] - hmin) / (hmax - hmin + 1e-6); px[i, k] = tuple(min(255, int(v * sh)) for v in c)
img = img.resize((nx * 2, ny * 2)); dr = ImageDraw.Draw(img)
T = lambda p: ((p[0] - X0) / ST * 2, (p[1] - Z0) / ST * 2)
for f in d['farms']: dr.polygon([T(p) for p in f], outline=(200, 190, 120))
for s2 in d['streams']: dr.line([T(p) for p in s2['p']], fill=(60, 120, 220), width=2)
for r in d['roads']: dr.line([T(p) for p in r['p']], fill=(230, 120, 60) if r['k'] in ('trunk', 'primary', 'secondary', 'tertiary') else (90, 90, 90), width=3 if r['w'] > 5 else 1)
for r in d['rails']: dr.line([T(p) for p in r], fill=(20, 20, 20), width=2)
for b in d['bld']:
    x, z, l, w, rot = b[:5]; c, sn = math.cos(rot), math.sin(rot)
    dr.polygon([T((x + a * l / 2 * c - e * w / 2 * sn, z + a * l / 2 * sn + e * w / 2 * c)) for a, e in [(-1, -1), (1, -1), (1, 1), (-1, 1)]], fill=(120, 60, 50))
for st in d['pts']['station']: x, y = T(st); dr.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(0, 0, 0))
a = d['arrival']; x, y = T((a['x'], a['z'])); dr.ellipse((x - 9, y - 9, x + 9, y + 9), outline=(255, 0, 0), width=3)
pl = d['play']; dr.rectangle([T((pl['minX'], pl['minZ'])), T((pl['maxX'], pl['maxZ']))], outline=(255, 255, 0), width=2)
img.save(sys.argv[1]); print('h', round(hmin, 1), round(hmax, 1), d['pts']['station'])
