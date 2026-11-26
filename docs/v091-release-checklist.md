# v0.91 公開前チェックリスト

2026-11-26 にユーザーが E3-2 を採用し、公開準備を承認した。正式公開の承認待ち。Claude Code が実行したコマンド、対象 SHA、合否、関連するログを各結果欄に記入する。

以下のコマンドは次の工程で使う。ブラウザーテストは Playwright と Chromium が使える環境で1本ずつ実行し、必要なテストには `THREE_JS` でローカルの three.js r128 を指定する。`OLD_HTML` には main `79ed170` の v0.90 の `index.html` を指定する。

## main に入れる前

| チェック | 確認とコマンド | 結果 |
|---|---|---|
| ☐ | GitHub の main が `79ed1704ae86e16cd589fa47fac671a628a4339d` のままか `git ls-remote --exit-code origin refs/heads/main` で確認する。候補のコミットをチェックアウトした状態で `git merge-base --is-ancestor 79ed170 HEAD` が終了コード0になり、fast-forward できることを確認する。 | |
| ☐ | 本編の版表示を `rg -n '<span class="tver">' index.html` で確認する。`tail -c 14 index.html` で末尾が `</body></html>`（改行なし）であることを確認する。 | |
| ☐ | `rg -n "const SAVE_KEY='eiheiji_vs_beasts_v010'" index.html` で本編の保存キーを確認する。`node tests/chapter2-save.cjs` で `v:1`、インライン script の構文、既存のセーブ互換を確認する。 | |
| ☐ | `python3 tests/p3e3-search-browser.py` で E3-2 の197項目を確認する。 | |
| ☐ | 同じ `python3 tests/p3e3-search-browser.py` のセーブ項目で、古いセーブで始めると未調査であること、v0.90 の実ページで保存し直したセーブから調査・地図の記録を復元でき、既存の進行・装備・持ち物も残ること、「はじめから」で調査と地図が初期化されることを確認する。 | |
| ☐ | PC と iPhone の大きさのブラウザーで、農家の入口、スズキが近いときの操作、調査と地図、画面の配置を確認する。`E3_SHOTS=確認画像 python3 tests/p3e3-search-browser.py`、`HUD_SHOTS=確認画像 python3 tests/hud-layout-browser.py`、`node tests/p3e3-farm-preview.cjs`。 | |
| ☐ | 農家・本部・整備工場跡の回帰。`python3 tests/p3e3-farm-browser.py`、`python3 tests/p3b-hq-browser.py`、`python3 tests/p3c-requests-browser.py`。 | |
| ☐ | 住民・拠点管理・依頼の回帰。`python3 tests/p3c-residents-browser.py`、`python3 tests/p3c-manage-browser.py`、`python3 tests/p3c-requests-browser.py`。 | |
| ☐ | 料理・薬草・地図の回帰。`python3 tests/p3d-cook-browser.py`、`python3 tests/kamado-browser.py`、`node tests/p3e2-herb.cjs`、`python3 tests/p3e-forest-browser.py`、`python3 tests/kamishihi-browser.py`、`python3 tests/p3e3-search-browser.py`。 | |
| ☐ | スズキと初遭遇の回帰。`python3 tests/suzuki-browser.py`、`python3 tests/suzuki-combat-browser.py`、`python3 tests/suzuki-rescue-browser.py`、`python3 tests/suzuki-save-browser.py`、`python3 tests/suzuki-defense-browser.py`、`python3 tests/story-f-browser.py`、`python3 tests/story-f-touch-browser.py`。 | |
| ☐ | カメラ・画面の配置・地域の回帰。`node tests/cam-pitch-browser.cjs`、`python3 tests/hud-layout-browser.py`、`python3 tests/region-browser.py`。 | |
| ☐ | KEI truck の回帰。`node tests/truck-physics.cjs`、`node tests/truck-sound.cjs`、`python3 tests/kei-truck-glb-browser.py`、`python3 tests/kei-truck-systems-browser.py`。 | |
| ☐ | セーブの回帰。`node tests/chapter2-save.cjs`、`python3 tests/p3e3-search-browser.py`、`python3 tests/suzuki-save-browser.py`。 | |
| ☐ | 次の作業で本編の v0.91 に揃えた試遊版7つを作り直す。実行コマンドは下記。 | |
| ☐ | 森・古い農家の生成結果と保存済みの版が1バイト単位で一致することを確認する。`node tests/p3e2-preview-build.cjs`、`node tests/p3e3-preview-build.cjs`。試遊版として起動して確認するには `node tests/p3e2-forest-preview.cjs`、`node tests/p3e3-farm-preview.cjs`。 | |
| ☐ | 実装を担当した Codex とは別の Codex に原則読み取りだけの独立レビューを依頼し、指摘と対応を記録する。差分確認は `git diff 79ed170...HEAD`。重点は既存機能の破壊・セーブ互換・ゲームの進行・iPhone の操作・性能・二重の処理と報酬・テストの不足・テストの期待そのものの誤り。 | |

試遊版の作り直しは次の作業で実施する。森と古い農家は生成元を v0.91 に合わせた REF と BLOB を設定してから実行する。

```sh
python3 tools/build-p1-preview.py
python3 tools/build-p2-suzuki-preview.py
python3 tools/build-p2-story-preview.py
python3 tools/build-p2-mutant-preview.py
python3 tools/build-p2-kami-preview.py
python3 tools/build-p3e2-forest-preview.py
python3 tools/build-p3e3-farm-preview.py
```

## 既知の課題と新しい回帰

`docs/handoff-claude-code.md` §7 の記録と、候補と比較対象を同じ条件で確認した結果を照合する。新しく出た失敗は対象 SHA・テスト項目・実行条件とともに記録する。

| チェック | 確認とコマンド | 結果 |
|---|---|---|
| ☐ | 初遭遇の会話のテストの揺れ（改善課題・未解決・原因未特定）。`python3 tests/story-f-touch-browser.py`。 | |
| ☐ | main でもスズキの体力が期待より1多い既知の3件。`python3 tests/suzuki-save-browser.py`。 | |
| ☐ | iPhone の大きさで入口から離れ、スズキのそばでタップしても指示のモードにならなかった件。main と同じ版でも同じ。実機では未確認・原因未調査。`python3 -m http.server 8000` で候補と比較版を配信し、iPhone の大きさとタッチ入力を設定したブラウザーで同じ操作を確認する。 | |
| ☐ | 試遊メニューを閉じた直後に E キーで入れなかった1回と、その後の3回の入力記録。`node tests/p3e3-farm-preview.cjs`。 | |
| ☐ | 「スズキが5秒以内に蔵へ来る」が1回だけ失敗し、その後は合格した件。`python3 tests/p3e3-farm-browser.py`。 | |
| ☐ | 拠点本部の入口で同じ操作の競合が起きるかは未調査。`python3 tests/p3b-hq-browser.py` で本部の回帰を確認し、`python3 -m http.server 8000` で起動して、スズキが入口付近について来た状態で入室操作とスズキへの指示を確認する。 | |
| ☐ | 上の6件と新しい回帰を区別して記録する。`rg -n '初遭遇の会話|suzuki-save-browser|指示の画面|E キー|5秒以内に蔵|競合' docs/handoff-claude-code.md` で既存の記録と照合する。 | |

## 正式公開の後

| チェック | 確認とコマンド | 結果 |
|---|---|---|
| ☐ | GitHub Pages の配信が成功し、配信 SHA が統合した main と一致することを確認する。`gh run list --workflow 'pages build and deployment' --branch main --limit 3 --json headSha,status,conclusion,url`。公開ページの版表示は `curl -fsSL https://alphalpha722514.github.io/REWILDED-EIHEIJI/ \| rg -o '<span class="tver">v0\.91[^<]*'` で確認する。PC と iPhone で公開ページを開き、表示と起動を確認する。 | |
