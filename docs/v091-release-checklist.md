# v0.91 公開前チェックリスト

2026-11-26 にユーザーが E3-2 を採用し、公開準備を承認した。正式公開の承認待ち。2026-11-27 に Claude Code が画面のない Chromium（SwiftShader）で公開候補 `1c080deb7c167250efb2d055b927c9768964160b` を検証した（ゲーム本体は `4ec7bae`、試遊版は `1c080de`）。

以下は公開前の確認コマンド。ブラウザーテストは Playwright と Chromium が使える環境で1本ずつ実行し、必要なテストには `THREE_JS` でローカルの three.js r128 を指定する。`OLD_HTML` には main `79ed170` の v0.90 の `index.html` を指定する。

## main に入れる前

| チェック | 確認とコマンド | 結果 |
|---|---|---|
| ☑ | GitHub の main が `79ed1704ae86e16cd589fa47fac671a628a4339d` のままか `git ls-remote --exit-code origin refs/heads/main` で確認する。候補のコミットをチェックアウトした状態で `git merge-base --is-ancestor 79ed170 HEAD` が終了コード0になり、fast-forward できることを確認する。 | Claude Code の確認では main は `79ed170` のまま。`p3e3-search` は main から fast-forward 可能。 |
| ☑ | 本編の版表示を `rg -n '<span class="tver">' index.html` で確認する。`tail -c 14 index.html` で末尾が `</body></html>`（改行なし）であることを確認する。 | 作業フォルダの `index.html` で版表示 v0.91 と末尾 `</body></html>`（改行なし）を確認。 |
| ☑ | `rg -n "const SAVE_KEY='eiheiji_vs_beasts_v010'" index.html` で本編の保存キーを確認する。`node tests/chapter2-save.cjs` で `v:1`、インライン script の構文、既存のセーブ互換を確認する。 | 本編の保存キーは作業フォルダで確認。`chapter2-save` 合格。 |
| ☑ | `python3 tests/p3e3-search-browser.py` で E3-2 の239項目を確認する。 | `p3e3-search-browser` 239項目すべて合格。独立レビュー後の追加項目を含む。 |
| ☑ | 同じ `python3 tests/p3e3-search-browser.py` のセーブ項目で、古いセーブで始めると未調査であること、v0.90 の実ページで保存し直したセーブから調査・地図の記録を復元でき、既存の進行・装備・持ち物も残ること、「はじめから」で調査と地図が初期化されることを確認する。 | 合格。v0.90 の実際のページで再保存する巻き戻り試験を含む。 |
| ☑ | PC と iPhone の大きさのブラウザーで、農家の入口、スズキが近いときの操作、調査と地図、画面の配置を確認する。`E3_SHOTS=確認画像 python3 tests/p3e3-search-browser.py`、`HUD_SHOTS=確認画像 python3 tests/hud-layout-browser.py`、`node tests/p3e3-farm-preview.cjs`。 | `p3e3-search-browser` 239項目・`hud-layout` 107項目が合格。`p3e3-farm-preview` は PC 1280×720 と iPhone 390×844 で合格。 |
| ☑ | 農家・本部・整備工場跡の回帰。`python3 tests/p3e3-farm-browser.py`、`python3 tests/p3b-hq-browser.py`、`python3 tests/p3c-requests-browser.py`。 | `p3e3-farm-browser` 30項目・`p3b-hq` 34項目・`p3c-requests` 30項目が合格。 |
| ☐ | 住民・拠点管理・依頼の回帰。`python3 tests/p3c-residents-browser.py`、`python3 tests/p3c-manage-browser.py`、`python3 tests/p3c-requests-browser.py`。 | `p3c-residents` 23項目・`p3c-requests` 30項目が合格。`p3c-manage` は結果の記録なし。 |
| ☐ | 料理・薬草・地図の回帰。`python3 tests/p3d-cook-browser.py`、`python3 tests/kamado-browser.py`、`node tests/p3e2-herb.cjs`、`python3 tests/p3e-forest-browser.py`、`python3 tests/kamishihi-browser.py`、`python3 tests/p3e3-search-browser.py`。 | `p3d-cook` 12項目・`p3e2-herb`・`p3e-forest-browser`・`p3e3-search-browser` が合格。`kamado`・`kamishihi` は結果の記録なし。 |
| ☐ | スズキと初遭遇の回帰。`python3 tests/suzuki-browser.py`、`python3 tests/suzuki-combat-browser.py`、`python3 tests/suzuki-rescue-browser.py`、`python3 tests/suzuki-save-browser.py`、`python3 tests/suzuki-defense-browser.py`、`python3 tests/story-f-browser.py`、`python3 tests/story-f-touch-browser.py`。 | `suzuki` 21項目・`suzuki-combat` 19項目・`suzuki-rescue` 17項目・`story-f-browser` 43項目（2回目）が合格。`story-f-browser` の初回は同時実行の負荷で途中停止。`suzuki-save`・`story-f-touch` は下記の既知の失敗。`suzuki-defense` は結果の記録なし。 |
| ☑ | カメラ・画面の配置・地域の回帰。`node tests/cam-pitch-browser.cjs`、`python3 tests/hud-layout-browser.py`、`python3 tests/region-browser.py`。 | `cam-pitch-browser` 57項目・`hud-layout` 107項目・`region` 9項目が合格。 |
| ☑ | KEI truck の回帰。`node tests/truck-physics.cjs`、`node tests/truck-sound.cjs`、`python3 tests/kei-truck-glb-browser.py`、`python3 tests/kei-truck-systems-browser.py`。 | `truck-physics`・`truck-sound`・`kei-truck-glb` 21項目が合格。`kei-truck-systems` は2回目に既知のドア1件のみ失敗（0.3 rad）。初回に同時実行の負荷で失敗した他の2件は再実行で合格。 |
| ☑ | セーブの回帰。`node tests/chapter2-save.cjs`、`python3 tests/p3e3-search-browser.py`、`python3 tests/suzuki-save-browser.py`。 | `chapter2-save`・`p3e3-search-browser` が合格。`suzuki-save` は main と同じ既知の3件が失敗。 |
| ☑ | 本編の v0.91 に揃えた試遊版7つを作り直す。実行コマンドは下記。 | 7つとも v0.91 で作り直し、Codex の出力と Claude Code の手元の生成結果がすべてバイト一致。保存キー・設定キーは本編と別。 |
| ☑ | 森・古い農家の生成結果と保存済みの版が1バイト単位で一致することを確認する。`node tests/p3e2-preview-build.cjs`、`node tests/p3e3-preview-build.cjs`。試遊版として起動して確認するには `node tests/p3e2-forest-preview.cjs`、`node tests/p3e3-farm-preview.cjs`。 | `p3e2-preview-build`・`p3e3-preview-build` はバイト一致。`p3e2-forest-preview`・`p3e3-farm-preview` は起動確認に合格。 |
| ☑ | 実装を担当した Codex とは別の Codex に原則読み取りだけの独立レビューを依頼し、指摘と対応を記録する。差分確認は `git diff 79ed170...HEAD`。重点は既存機能の破壊・セーブ互換・ゲームの進行・iPhone の操作・性能・二重の処理と報酬・テストの不足・テストの期待そのものの誤り。 | 別の Codex が読み取りのみで独立レビュー。中2件・低4件。写しの `s` を 0〜255 の整数に限定し、入室の暗転中の調査を止め、テストを追加した。遊んでいる途中の保存失敗の通知（ゲーム全体の現行仕様。引き継ぎ §7 に記録済み）と、ミニマップの描画ごとに薬草を選び直す処理（12か所、影響は小さい）は対応を見送った。 |

試遊版7つは以下のコマンドで作り直した。森と古い農家は REF `4ec7bae7ff7743dfcfae233a252534ad4127b4ce`、BLOB `0ca510a9e5f7373a45fa189ce67750eb599eff48` を指定した。

```sh
python3 tools/build-p1-preview.py
python3 tools/build-p2-suzuki-preview.py
python3 tools/build-p2-story-preview.py
python3 tools/build-p2-mutant-preview.py
python3 tools/build-p2-kami-preview.py
python3 tools/build-p3e2-forest-preview.py
python3 tools/build-p3e3-farm-preview.py
```

### 追加の合格結果

- Node：`chapter2-defense`・`classic-body`・`death-penalty`・`combat-aim`・`hurt-drop`・`p3e2-felling`・`p3e2-truck-logs`・`p3e2-forest-sound`・`p3e2-prompt-ui`。 `p3e2-prompt-ui` は2回目に合格し、初回はテスト2本の同時実行の負荷で失敗した。
- ブラウザー：`p3d-fishing` 13項目・`kami-wild` 32項目・`wardrobe` 6項目。

## 既知の課題と新しい回帰

`docs/handoff-claude-code.md` §7 の記録と、候補と比較対象を同じ条件で確認した結果を照合する。新しく出た失敗は対象 SHA・テスト項目・実行条件とともに記録する。

| チェック | 確認とコマンド | 結果 |
|---|---|---|
| ☑ | 初遭遇の会話のテストの揺れ（改善課題・未解決・原因未特定）。`python3 tests/story-f-touch-browser.py`。 | 「カットの間はスティック・行動ボタンが効かない」と「初遭遇の会話」が失敗。どちらも既知の改善課題で未解決。 |
| ☑ | main でもスズキの体力が期待より1多い既知の3件。`python3 tests/suzuki-save-browser.py`。 | main と同じ3件が失敗。スズキの体力が期待より1多い。 |
| ☐ | iPhone の大きさで入口から離れ、スズキのそばでタップしても指示のモードにならなかった件。main と同じ版でも同じ。実機では未確認・原因未調査。`python3 -m http.server 8000` で候補と比較版を配信し、iPhone の大きさとタッチ入力を設定したブラウザーで同じ操作を確認する。 | 今回の個別操作の結果は記録なし。 |
| ☐ | 試遊メニューを閉じた直後に E キーで入れなかった1回と、その後の3回の入力記録。`node tests/p3e3-farm-preview.cjs`。 | `p3e3-farm-preview` は合格。この操作の個別結果は記録なし。 |
| ☑ | 「スズキが5秒以内に蔵へ来る」が1回だけ失敗し、その後は合格した件。`python3 tests/p3e3-farm-browser.py`。 | `p3e3-farm-browser` 30項目すべて合格。 |
| ☐ | 拠点本部の入口で同じ操作の競合が起きるかは未調査。`python3 tests/p3b-hq-browser.py` で本部の回帰を確認し、`python3 -m http.server 8000` で起動して、スズキが入口付近について来た状態で入室操作とスズキへの指示を確認する。 | `p3b-hq` 34項目すべて合格。入口での個別操作の結果は記録なし。 |
| ☑ | 上の6件と新しい回帰を区別して記録する。`rg -n '初遭遇の会話\|suzuki-save-browser\|指示の画面\|E キー\|5秒以内に蔵\|競合' docs/handoff-claude-code.md` で既存の記録と照合する。 | 報告された失敗は既知の項目か実行環境によるもの。`story-f-browser` の「戦いが始まるとスズキが言う（0回）」は main 相当（`f552300`）でも同条件で失敗し、公開候補では2回目に合格。引き継ぎ §7.2 に記録した。 |

Claude Code の検証では、リポジトリ外にある Playwright の Python 代替の中継に Locator の `get_by_text`・`get_by_role` などを追加した。一部の失敗は、この中継の対応不足によるものだった。

## 正式公開の後

| チェック | 確認とコマンド | 結果 |
|---|---|---|
| ☐ | GitHub Pages の配信が成功し、配信 SHA が統合した main と一致することを確認する。`gh run list --workflow 'pages build and deployment' --branch main --limit 3 --json headSha,status,conclusion,url`。公開ページの版表示は `curl -fsSL https://alphalpha722514.github.io/REWILDED-EIHEIJI/ \| rg -o '<span class="tver">v0\.91[^<]*'` で確認する。PC と iPhone で公開ページを開き、表示と起動を確認する。 | |
