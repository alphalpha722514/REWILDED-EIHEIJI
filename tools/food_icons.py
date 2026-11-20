#!/usr/bin/env python3
"""料理の絵（ChatGPT で作った画像）をゲーム用に整える。docs/food-image-request.md

元の絵：assets/food/src/<料理ID>.png（受け取ったまま。消さない）
ゲーム用：assets/food/<料理ID>.webp（256×256・背景は透明。WebP にして 19枚で約360KB。PNG だと約1.8MB）
- 不透明に近い所（透明度 240 以上）はすべて不透明にそろえる（元の絵は 252 前後でわずかに透けていた）
- 縁の半透明の画素は、内側の色で塗り直す（背景を抜いたときの色のにじみを消す）
- 絵のある所だけを切り出し、正方形の真ん中に置いて（余白 4%）、256×256 に縮める
使い方：python3 tools/food_icons.py [料理ID …]
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'assets', 'food', 'src')
OUT = os.path.join(ROOT, 'assets', 'food')
SIZE = 256
MARGIN = 0.04


def build(fid):
    im = Image.open(os.path.join(SRC, fid + '.png')).convert('RGBA')
    a = np.array(im).astype(np.float32)
    al = a[..., 3]
    al[al >= 240] = 255
    al[al < 12] = 0
    # 縁の色：不透明な所の色を外へ広げる（重みつきのぼかし）
    w = (al >= 250).astype(np.float32)
    rgb = a[..., :3]
    acc = rgb * w[..., None]
    wsum = w.copy()
    for r in (2, 6, 14):
        b_acc = np.stack([gaussian_filter(acc[..., c], r) for c in range(3)], -1)
        b_w = gaussian_filter(wsum, r)
        fill = (w < 0.5) & (b_w > 1e-3)
        rgb[fill] = b_acc[fill] / b_w[fill][..., None]
        w = np.maximum(w, fill.astype(np.float32))
        acc = rgb * w[..., None]
        wsum = w.copy()
    a[..., :3] = rgb
    a[..., 3] = al
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    bb = im.getbbox()
    im = im.crop(bb)
    side = int(max(im.size) * (1 + MARGIN * 2))
    sq = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    sq = sq.convert('RGBa').resize((SIZE, SIZE), Image.LANCZOS).convert('RGBA')
    out = os.path.join(OUT, fid + '.webp')
    sq.save(out, quality=88, method=6)
    return out, os.path.getsize(out)


if __name__ == '__main__':
    ids = sys.argv[1:] or sorted(f[:-4] for f in os.listdir(SRC) if f.endswith('.png'))
    tot = 0
    for fid in ids:
        out, n = build(fid)
        tot += n
        print(f'{fid}: {n // 1024}KB')
    print(f'合計 {tot // 1024}KB（{len(ids)}枚）')
