"""保存した国土地理院の標高タイル（z15）から、緯度経度の標高を求める。"""
import glob
import gzip
import math
import os

RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'kamishihi', 'raw')
Z = 15
_tiles = {}
_t10 = {}


def _load():
    if _tiles:
        return
    for p in glob.glob(os.path.join(RAW, f'dem_{Z}_*_*.txt.gz')):
        _, _, tx, ty = os.path.basename(p).split('.')[0].split('_')
        lines = gzip.open(p).read().decode().split('\n')
        rows = [l.split(',') for l in lines[1:] if l.strip()]
        _tiles[(int(tx), int(ty))] = [[(float(v) if v != 'e' else None) for v in r] for r in rows]
    for p in glob.glob(os.path.join(RAW, 'dem10_14_*_*.txt.gz')):
        _, _, tx, ty = os.path.basename(p).split('.')[0].split('_')
        rows = [l.split(',') for l in gzip.open(p).read().decode().split('\n') if l.strip()]
        _t10[(int(tx), int(ty))] = [[(float(v) if v != 'e' else None) for v in r] for r in rows]


def _pix(lat, lon):
    n = 2 ** Z * 256
    x = (lon + 180) / 360 * n
    r = math.radians(lat)
    y = (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n
    return x - 0.5, y - 0.5  # 画素の中心


def _at(px, py):
    tx, ty = int(px // 256), int(py // 256)
    t = _tiles.get((tx, ty))
    if not t:
        return None
    return t[int(py - ty * 256)][int(px - tx * 256)]


def _bil(at, px, py):
    x0, y0 = math.floor(px), math.floor(py)
    fx, fy = px - x0, py - y0
    vals = [(at(x0, y0), (1 - fx) * (1 - fy)), (at(x0 + 1, y0), fx * (1 - fy)), (at(x0, y0 + 1), (1 - fx) * fy), (at(x0 + 1, y0 + 1), fx * fy)]
    s = sum(v * w for v, w in vals if v is not None)
    ws = sum(w for v, w in vals if v is not None)
    return s / ws if ws > 0.75 else None


def _at10(px, py):
    tx, ty = int(px // 256), int(py // 256)
    t = _t10.get((tx, ty))
    if not t:
        return None
    return t[int(py - ty * 256)][int(px - tx * 256)]


def elev(lat, lon):
    """5m を使い、欠けていれば 10m で埋める。"""
    _load()
    px, py = _pix(lat, lon)
    v = _bil(_at, px, py)
    if v is not None:
        return v
    n = 2 ** 14 * 256
    x = (lon + 180) / 360 * n - 0.5
    r = math.radians(lat)
    y = (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n - 0.5
    return _bil(_at10, x, y)


def elev5_only(lat, lon):
    _load()
    px, py = _pix(lat, lon)
    x0, y0 = math.floor(px), math.floor(py)
    fx, fy = px - x0, py - y0
    vals = [(_at(x0, y0), (1 - fx) * (1 - fy)), (_at(x0 + 1, y0), fx * (1 - fy)), (_at(x0, y0 + 1), (1 - fx) * fy), (_at(x0 + 1, y0 + 1), fx * fy)]
    s = sum(v * w for v, w in vals if v is not None)
    ws = sum(w for v, w in vals if v is not None)
    return s / ws if ws > 0 else None
