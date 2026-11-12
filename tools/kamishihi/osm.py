"""保存した OSM（gzip）を読む小さな道具（上志比の地図づくり用）。"""
import gzip
import os
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'data', 'kamishihi', 'raw')


def load(names=('kamishihi_w', 'kamishihi_e', 'calib')):
    nodes, ways, rels = {}, {}, []
    for nm in names:
        root = ET.fromstring(gzip.open(os.path.join(RAW, f'osm_{nm}.osm.gz')).read())
        for n in root.iter('node'):
            nodes[n.get('id')] = (float(n.get('lat')), float(n.get('lon')), {t.get('k'): t.get('v') for t in n.iter('tag')})
        for w in root.iter('way'):
            ways[w.get('id')] = ([nd.get('ref') for nd in w.iter('nd')], {t.get('k'): t.get('v') for t in w.iter('tag')})
        for r in root.iter('relation'):
            rels.append(([(m.get('type'), m.get('ref'), m.get('role')) for m in r.iter('member')], {t.get('k'): t.get('v') for t in r.iter('tag')}))
    return nodes, ways, rels


def coords(nodes, refs):
    return [(nodes[r][0], nodes[r][1]) for r in refs if r in nodes]
