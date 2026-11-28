#!/usr/bin/env python3
"""E3-3aの検収用HTMLを、確認済みの本編から生成する。"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
REF = 'b8086b1013ae354446d57a6faa76822872be5d01'
BLOB = '1e53254dd7f39b28f06e8dd2cafc48c4f6948c0d'
KEYS = {
    'eiheiji_vs_beasts_v010': ('save', 1),
    'REWILDED_EIHEIJI_SETTINGS': ('sound', 1),
    'eiheiji_weatherEffects': ('weatherEffects', 1),
    'eiheiji_shadow': ('shadow', 2),
    'eiheiji_perf': ('perf', 2),
    'eiheiji_aimMode': ('aimMode', 3),
    'eiheiji_detail': ('detail', 2),
    'eiheiji_camPitch': ('camPitch', 1),
    '__t': ('probe', 2),
}


def replace(src, old, new, count=1):
    actual = src.count(old)
    if actual != count:
        raise ValueError(f'置換箇所の件数が異なる（{actual}/{count}）: {old}')
    return src.replace(old, new)


def build(src):
    preview_keys = {}
    for key, (suffix, count) in KEYS.items():
        isolated = 'eiheiji_p3e3shop_' + suffix
        preview_keys[key] = isolated
        src = replace(src, repr(key), repr(isolated), count)

    # 定数経由を含め、元のページの保存先がすべて試遊版専用であることを確認する。
    constants = dict(re.findall(r"\bconst\s+(\w+)\s*=\s*'([^']+)'", src))
    destinations = set()
    for match in re.finditer(r'\blocalStorage\b', src):
        call = re.match(r"\.(?:getItem|setItem|removeItem)\(\s*(?:'([^']+)'|(\w+))\s*[,)]",
                        src[match.end():match.end() + 180])
        if call:
            key = call[1] or constants.get(call[2])
            destinations.add(key)
        elif not any(start <= match.start() < end for start, end in comments(src)):
            raise ValueError('未対応のlocalStorage操作がある')
    if destinations != set(preview_keys.values()):
        raise ValueError('想定外の保存先がある')

    # 許可したキーだけを扱う。共有オリジンでも他の版のキーと一括消去を保護する。
    allowed = json.dumps(list(preview_keys.values()), separators=(',', ':'))
    guard = f"""<script>
(() => {{
  const allowed = new Set({allowed});
  const storage = Storage.prototype;
  const get = storage.getItem, set = storage.setItem, remove = storage.removeItem;
  storage.getItem = function(key) {{
    key = String(key);
    return allowed.has(key) ? get.call(this, key) : null;
  }};
  storage.setItem = function(key, value) {{
    key = String(key);
    if (allowed.has(key)) set.call(this, key, value);
  }};
  storage.removeItem = function(key) {{
    key = String(key);
    if (allowed.has(key)) remove.call(this, key);
  }};
  storage.clear = function() {{}};
}})();
</script>"""
    head = '<head><meta charset=utf8>'
    src = replace(src, head, head + '<meta name="robots" content="noindex">' + guard)
    src = replace(src, '<span class="tver">v0.91 デモ版　第二章・上志比の森林</span>',
                  '<span class="tver">E3-3a よろず屋 iPhone検収用・ブラウザー未検証</span>')
    src = replace(src, '<button class="pri" id="btnNew">ゲーム開始</button>',
                  '<button class="pri" id="btnNew">よろず屋の前から始める</button>')
    anchor = '    <p id="pauseInfo"'
    src = replace(src, anchor, '''    <div class="lbl">よろず屋の検収</div>
    <div class="btns" style="margin-bottom:10px;flex-wrap:wrap">
      <button id="shopPreviewSuzuki" type="button">スズキ</button>
      <button id="shopPreviewTime" type="button">時刻</button>
    </div>
''' + anchor)
    src = replace(src, "$('btnNew').onclick=()=>{ audioInit(); startNew(); };",
                  "$('btnNew').onclick=shopPreviewStart;")
    src = replace(src, "$('btnContinue').onclick=()=>{ audioInit(); continueGame(); };",
                  "$('btnContinue').onclick=()=>{ audioInit(); SHOP_PREVIEW.active=true; continueGame(); };")
    src = replace(src, "$('btnRestart').onclick=()=>{ try{ localStorage.removeItem(SAVE_KEY);}catch(e){} startNew(); };",
                  "$('btnRestart').onclick=shopPreviewStart;")
    src = replace(src, "$('saveNote').textContent=storageOK?(hasSave?'セーブデータがあります。「ゲーム開始」を選ぶと最初からになります。':'進行は自動でこのブラウザに保存されます。'):",
                  "$('saveNote').textContent=storageOK?(hasSave?'試遊版のセーブがあります。店先から始めると試遊版を新しく始めます。':'試遊版の進行は本編と別に保存されます。'):")
    src = replace(src, 'function updateEnemies(dt){', 'function updateEnemies(dt){\n  shopPreviewShelter();')
    src = replace(src, "$('pause').hidden=false; f11Pause(); f31Pause();",
                  "$('pause').hidden=false; f11Pause(); f31Pause(); shopPreviewRefresh();")
    runtime = Path(__file__).with_name('p3e3-shop-preview.js').read_text(encoding='utf-8')
    anchor = '// タイトル\nconst hasSave=!!readSave();'
    return replace(src, anchor, runtime + '\n' + anchor)


def comments(src):
    # この版では、localStorageを含むコメントは独立した行にある。
    return (match.span() for match in re.finditer(r'(?m)^\s*//[^\n]*localStorage[^\n]*', src))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='出力する試遊版HTMLのパス')
    args = parser.parse_args()
    data = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{REF}:index.html'])
    blob = hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()
    if blob != BLOB:
        raise SystemExit(f'元のindex.htmlのblobが異なる: {blob}')
    output = build(data.decode('utf-8')).encode('utf-8')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(output)
    print(f'{args.out} ／ 元 {REF} ／ SHA-256 {hashlib.sha256(output).hexdigest()}')


if __name__ == '__main__':
    main()
