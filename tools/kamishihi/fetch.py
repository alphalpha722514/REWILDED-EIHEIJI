#!/usr/bin/env python3
"""上志比の地理データを取得して data/kamishihi/raw/ に保存する（P2 作業B）。

一度取得したら保存したものを使う（取得元に何度も負担をかけない）。取り直すときは --force。

取得するもの
- OpenStreetMap（API 0.6 の範囲取得）：道路・鉄道・建物・田畑・森・川など。利用条件：ODbL（© OpenStreetMap contributors）
- 国土地理院 標高タイル（5m の dem5a、無い所は 10m の dem）：利用条件：国土地理院コンテンツ利用規約（出典の明記）

使い方：python3 tools/kamishihi/fetch.py [--force]
"""
import datetime
import gzip
import json
import math
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'data', 'kamishihi', 'raw')
FORCE = '--force' in sys.argv
UA = 'REWILDED-EIHEIJI map builder (github.com/alphalpha722514/REWILDED-EIHEIJI)'

# 範囲：光明寺の駅の西（座標合わせ用）〜市荒川の東。南北は九頭竜川から南の山すそまで
OSM_BOXES = {
    'calib': (136.333, 36.078, 136.352, 36.092),     # 光明寺の地図と座標を合わせるための小さな範囲（下志比・光明寺の駅）
    'kamishihi_w': (136.352, 36.066, 136.392, 36.095),
    'kamishihi_e': (136.392, 36.062, 136.432, 36.092),
}
DEM_BOX = (136.352, 36.060, 136.432, 36.096)


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def tile(lon, lat, z):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    r = math.radians(lat)
    y = int((1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n)
    return x, y


def save_gz(path, data):
    with gzip.open(path, 'wb', compresslevel=9) as f:
        f.write(data)


def main():
    os.makedirs(RAW, exist_ok=True)
    src_path = os.path.join(RAW, 'sources.json')
    sources = json.load(open(src_path, encoding='utf8')) if os.path.exists(src_path) else {}
    today = datetime.date.today().isoformat()
    for name, (w, s, e, n) in OSM_BOXES.items():
        path = os.path.join(RAW, f'osm_{name}.osm.gz')
        if os.path.exists(path) and not FORCE:
            continue
        url = f'https://api.openstreetmap.org/api/0.6/map?bbox={w},{s},{e},{n}'
        print('OSM', name, url)
        data = get(url)
        save_gz(path, data)
        sources[f'osm_{name}'] = {'url': url, 'date': today, 'bytes': len(data), 'license': 'ODbL 1.0 (© OpenStreetMap contributors)'}
        time.sleep(3)
    z = 15
    x0, y1 = tile(DEM_BOX[0], DEM_BOX[1], z)
    x1, y0 = tile(DEM_BOX[2], DEM_BOX[3], z)
    got = {'dem5a': 0, 'dem': 0, 'none': 0}
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            path = os.path.join(RAW, f'dem_{z}_{tx}_{ty}.txt.gz')
            if os.path.exists(path) and not FORCE:
                continue
            data = None
            for kind, zz in (('dem5a', 15), ('dem', 14)):
                if kind == 'dem':  # 10m は z14 の1枚を4分の1ずつ使う
                    url = f'https://cyberjapandata.gsi.go.jp/xyz/dem/14/{tx // 2}/{ty // 2}.txt'
                else:
                    url = f'https://cyberjapandata.gsi.go.jp/xyz/dem5a/15/{tx}/{ty}.txt'
                try:
                    d = get(url)
                    if d and b'e' in d[:4000] and d.count(b'e') > 60000:  # ほとんど欠けている 5m は使わない
                        continue
                    data = (kind, url, d)
                    break
                except Exception:
                    continue
            if not data:
                got['none'] += 1
                continue
            kind, url, d = data
            save_gz(path, (kind + '\n').encode() + d)
            got[kind] += 1
            time.sleep(0.4)
    # 10m（z14）も取っておく：5m は川の水面などが欠けているので、その穴を埋める
    x0b, y1b = tile(DEM_BOX[0], DEM_BOX[1], 14)
    x1b, y0b = tile(DEM_BOX[2], DEM_BOX[3], 14)
    for ty in range(y0b, y1b + 1):
        for tx in range(x0b, x1b + 1):
            path = os.path.join(RAW, f'dem10_14_{tx}_{ty}.txt.gz')
            if os.path.exists(path) and not FORCE:
                continue
            url = f'https://cyberjapandata.gsi.go.jp/xyz/dem/14/{tx}/{ty}.txt'
            save_gz(path, get(url))
            got['dem'] += 1
            time.sleep(0.4)
    import glob
    got = {'dem5a_z15': len(glob.glob(os.path.join(RAW, 'dem_15_*'))), 'dem10_z14': len(glob.glob(os.path.join(RAW, 'dem10_14_*')))}
    sources['gsi_dem'] = {'tiles': f'z{z} x{x0}-{x1} y{y0}-{y1}', 'date': sources.get('gsi_dem', {}).get('date', today), 'kinds': got,
                          'url': 'https://cyberjapandata.gsi.go.jp/xyz/dem5a/15/{x}/{y}.txt と dem/14/{x}/{y}.txt（5m の欠けを 10m で埋める）',
                          'license': '国土地理院コンテンツ利用規約（出典：国土地理院 標高タイル）'}
    json.dump(sources, open(src_path, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print('done', got)


main()
