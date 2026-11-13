# REWILDED EIHEIJI — Claude 向けの作業ルール

このリポジトリで作業する Claude は、最初にこのファイルを読み、必ず守ること。返答はすべて日本語。

## 基準
- 現行コードの唯一の基準は、このリポジトリの `main/index.html`（1ファイルのブラウザ3Dゲーム、three.js r128）。
- 公開先：https://alphalpha722514.github.io/REWILDED-EIHEIJI/（main を GitHub Pages で配信）。
- 古いHTML・試作・過去の会話内のコードで、丸ごと上書きしない。

## 開発体制（2026-11-11 ユーザー決定）
| 担当 | 役割 |
|---|---|
| ユーザー | 総監督。企画・物語・キャラクターデザインの最終決定、Tripo AI での3D生成、必要に応じて Blender、試遊、承認 |
| ChatGPT | 仕様の整理、Claude 向けの実装プロンプト、Tripo 用のイメージ画像（ユーザーが受け渡す） |
| Claude | 技術実装。コード解析、P0〜P7 の実装、AI・戦闘、リギング・アニメーション、Three.js への統合、軽量化、セーブ互換、GitHub 反映、テスト |

### 各フェーズの手順
1. Claude が現状整理を作る：開発目標／実装状況（コミット番号つき）／過去の確定仕様／不明な仕様／必要な3Dモデル／既存システムとの依存関係／技術的な問題／推奨する開発順序。
2. ユーザーが ChatGPT と相談する。
3. ChatGPT が Claude 向けの実装プロンプトを作り、ユーザーが送る。
4. Claude が実装する。プロンプトは実装前に現行コードと照合する。**確定仕様やコードと矛盾する箇所は変えずに報告する。**
5. ユーザーが試遊・確認し、修正を依頼する。

### 3Dモデル（2026-11-12 P2 指示書 v3.0 で更新）
- **味方側のキャラクター（プレイヤー・村人・スズキなど新しい味方）は Claude が作る。** 今の画風（`makeHumanClassic`）にそろえ、正式に入れる前に確認用の画像（`tools/char-studio.py`）でユーザーの承認を得る。
- **敵（野生動物・ボス）は従来どおり**「ChatGPT で画像 → ユーザーが Tripo で生成 → 必要なら Blender で調整 → Claude が統合」。完成済みのモデルは再生成しない。
- **外見を保てる修正方法が確立するまで、プレイヤーモデルそのものの全面的な作り直しはしない**（2026-11-12 ユーザー方針）。体の作りを変えたら、防具なしの主人公・村人が main と画素単位で同じか比べる。
- モデルが必要になったら、`docs/asset-registry.md` の【3Dモデル制作依頼】の12項目の形式でユーザーに知らせる。
- モデル待ちの間も、AI・判定・HP・イベント・会話・カメラ・セーブ・UI は仮モデルで先に作る。仮モデルを正式アセットとして扱わない。差し替えやすい構造にする。
- 元モデルと加工後のモデルは別ファイルで管理し、版を `docs/asset-registry.md` に記録する。
- Blender などの外部ソフトを直接操作できないときは、実行用スクリプトか手順を渡す。**実行していない作業を、実行したように報告しない。**

## 仕様の優先順位
1. ユーザーが最新の指示で明示的に確定した事項
2. ユーザーが承認した最新のフェーズ別仕様
3. 過去に確定した設定・台詞・ゲームルール
4. 最新の引き継ぎ仕様書（Handoff v2.0）
5. Claude や ChatGPT の未承認の提案

- 実装状況はコードで確かめる。コードと確定仕様が違うときは、どちらかを正しいと決めつけずに差分を報告する。
- Q61〜Q301 など、原文を確認できない決定事項を推測で補わない。
- 物語・キャラクター・重要なゲームルールを独断で確定しない。暫定の数値は「暫定」と明記する。
- 第3〜5章は、ユーザーが確定するまで企画段階。正式に実装しない。

## 壊さないもの
- セーブ：`docs/save-and-flags.md` の「変えてはいけない項目」を守る（`SAVE_KEY='eiheiji_vs_beasts_v010'`、`v:1`、既存キー名、旧セーブの読み込み）。
- 確定した台詞（ヌシの遺言など）、UI、既存機能。
- プレイヤーと村人の体：v0.54.1 で v0.32.1 のやわらかい体に戻した（`docs/character-classic-body.md`）。プレイヤーはくねくね無し。防具の見た目は v0.65 で「着替え」に変えた（2026-11-13 ユーザー採用。初期の服も脱げる。防具は初期の服と同じ作り方の丸ごとの服。`docs/p2-investigation.md`）。鱗の防具の形は不採用で、ユーザーの改善要求待ち（`docs/mutant-scale-uses.md`）。

## 作業の進め方
- main へ入れる前に、作業ブランチで検証する。変更は小さく分ける。
- テスト：`node tests/chapter2-save.cjs`、`node tests/chapter2-defense.cjs`、`node tests/classic-body.cjs`、`node tests/death-penalty.cjs`、`node tests/combat-aim.cjs`。地域の往復は `python3 tests/region-browser.py`、上志比は `python3 tests/kamishihi-browser.py`（`KAMI_SHOTS=フォルダ` で画面を撮る）、変異したサルは `python3 tests/mutant-browser.py`、主人公の着替え（初期の服の見た目が変わっていないか）は `python3 tests/wardrobe-browser.py`、鱗の装備は `python3 tests/scale-gear-browser.py`、かまどの料理は `python3 tests/kamado-browser.py`（どれも画面のない Chromium、各数分）。防衛戦の勝率は `tools/defense-sim.cjs`（`docs/p1-sim-baseline.md`）、変異したサルとの1対1は `tools/mutant-duel-sim.cjs`（`docs/mutant-monkey-ai.md`）。画面の確認は Playwright（SwiftShader）で起動と表示を見る。
- 報告では「コードに存在／コミット済み／公開済み／PCで確認／iPhoneで確認」を区別する。実機で確かめていないことを確認済みと書かない。
- 各フェーズで、変更履歴・使った3Dアセットと版・実装済み／未実装・テスト結果・未解決の不具合・セーブ互換・次の工程を `docs/` に残す。

## 文書
| ファイル | 内容 |
|---|---|
| `docs/save-and-flags.md` | セーブ項目・章フラグ・イベントID |
| `docs/asset-registry.md` | 3Dアセットの台帳と制作依頼の形式 |
| `docs/character-classic-body.md` | プレイヤー・村人の体の決定と検証 |
| `docs/chapter2-progress.md` | 第2章の実装状況 |
| `docs/chapter2-map-plan.md` | 上志比マップの調査と計画 |
| `docs/phase-p1-status.md` | P1 の現状整理 |
| `docs/phase-p2-status.md` | P2 の現状整理（上志比マップと移動） |
| `docs/p2-region.md` | 地域の仕組み（光明寺は常駐・ほかは一時、座標のずらし、移動・失敗時の復旧・セーブ） |
| `docs/p2-kamishihi-map.md` | 上志比の地図（出典・利用条件・座標と縮尺・広さ・作り直し方・ゲーム内の作り・確認・未実装） |
| `docs/mutant-monkey-glb-check.md` | 変異したサル（Tripo の GLB）の検査・軽量化の試作・修正方針・確認事項。道具は `tools/models/` |
| `docs/mutant-monkey-rig.md` | 変異したサルの骨・重み・動き（rig 1）・ゲーム用データ・確認動画の作り方 |
| `docs/mutant-monkey-ai.md` | 変異したサルの AI（暫定の強さ・攻撃・初遭遇は逃げ去る・v0.62 の強敵化と「変異した鱗」・強さの測定結果）と試遊版 `previews/p2-mutant/` |
| `docs/mutant-scale-uses.md` | 変異した鱗の使い道（2026-11-13 決定）と v0.63〜v0.64 の実装：かまど・変換炉・蒼鱗／変異鱗の武器・鱗の飛去来器・蒼鱗／変異した鱗の防具・衝撃波・未定の事項 |
| `docs/kamado-cooking-plan.md` | かまどの料理と食材の種類（v0.66）：ユーザー決定・食材・料理の決まり方・未定の事項 |
| `docs/p2-investigation.md` | P2 統合指示書 v3.0 への初期調査（防具の原因・地理データ・スズキ・順序・確認事項） |
| `docs/p1-sim-baseline.md` | 防衛戦の勝率測定ツールと基準値 |
| `docs/p1-balance-report.md` | P1 の測定結果・調整（v0.55・v0.56 で反映）・未確認事項 |
| `docs/death-penalty.md` | 倒れたときの代償（v0.56） |
| `docs/combat-aim.md` | 攻撃の向きと当たり判定（v0.58） |

- キャラクターの確認画像：`python3 tools/char-studio.py 出力.png player suzuki gen`（`player@forest` で防具の組を着せる。`STUDIO_POSE=1` で動きの姿勢。`STUDIO_HTML` で別の index.html）。鱗の防具（蒼鱗・変異した鱗）は `python3 tools/scale-armor-studio.py 出力.png`。
- 試遊版の作り方：`python3 tools/build-p1-preview.py`（防衛戦。A／B／C ボタン。`previews/p1-balance/`）と `python3 tools/build-p2-mutant-preview.py`（変異したサル。`previews/p2-mutant/`）。どちらも本編をコピーして試遊用の保存キーを足す。本編を変えたら作り直す。
