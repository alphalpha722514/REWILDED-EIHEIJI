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
- プレイヤーと村人の体：v0.54.1 で v0.32.1 のやわらかい体に戻した（`docs/character-classic-body.md`）。プレイヤーはくねくね無し。防具の見た目は v0.65 で「着替え」に変えた（2026-11-13 ユーザー採用。初期の服も脱げる。防具は初期の服と同じ作り方の丸ごとの服。`docs/p2-investigation.md`）。鱗の防具の形は v0.76 で改修指示書（2026-11-16）どおり作り直した（体を測って沿わせる厚みのある板と立体の鱗。2026-11-16 ユーザーの修正指示（蒼鱗の兜で髪を残す・脚の後ろも覆う）を反映して main へ。`docs/scale-armor-v2.md`）。

## 作業の進め方
- main へ入れる前に、作業ブランチで検証する。変更は小さく分ける。
- テスト：`node tests/chapter2-save.cjs`、`node tests/chapter2-defense.cjs`、`node tests/classic-body.cjs`、`node tests/death-penalty.cjs`、`node tests/combat-aim.cjs`。地域の往復は `python3 tests/region-browser.py`、上志比は `python3 tests/kamishihi-browser.py`（`KAMI_SHOTS=フォルダ` で画面を撮る）、変異したサルは `python3 tests/mutant-browser.py`、主人公の着替え（初期の服の見た目が変わっていないか）は `python3 tests/wardrobe-browser.py`、鱗の装備は `python3 tests/scale-gear-browser.py`、鱗の防具の形（8種類の着替え・演出・骨・セーブ・重さ）は `python3 tests/scale-armor2-browser.py`、かまどの料理は `python3 tests/kamado-browser.py`、上志比の獣・採集・伐採は `python3 tests/kami-wild-browser.py`、サルの要塞と侵入経路は `python3 tests/kami-fort-browser.py`、要塞のサルの見張り・巡回・通報と物資の再補充は `python3 tests/kami-watch-browser.py`、武器の GLB（見た目の差し替え・当たり・作る・飛去来器・セーブ）は `python3 tests/weapon-glb-browser.py`（`WGT_NOGLB=1` で読めないときの確認）、スズキの仲間 AI は `python3 tests/suzuki-browser.py`（ついて来る・指示）と `python3 tests/suzuki-combat-browser.py`（戦い）と `python3 tests/suzuki-rescue-browser.py`（倒れる・助け起こす）と `python3 tests/suzuki-save-browser.py`（セーブ・地域をまたぐ状態）と `python3 tests/suzuki-defense-browser.py`（防衛戦）（どれも画面のない Chromium、各数分）、作業F（救援無線・相談・KEI truck・見送り・山王の初遭遇・仲間に・旧セーブ・倒れたときのやり直し）は `python3 tests/story-f-browser.py`（`STORY_SHOTS=フォルダ` で場面を撮る。15分ほど）と `python3 tests/story-f-touch-browser.py`（iPhone の操作の再現）、KEI truck の運転の物理（慣性・遠心力・ハンドル）は `node tests/truck-physics.cjs`、KEI truck の正式モデル（修理前・修理後の GLB・切り替え・接地・ガラス・つづきから・読めないとき）は `python3 tests/kei-truck-glb-browser.py`（`KT_SHOTS=フォルダ` で画面を撮る）、KEI truck の仕組み（燃料・車体の傷み・横転・車両基地・改修・荷台・源さんの運搬・座る・ドア）と鱗の装備の違い・上志比の目標の距離・作業台と車両基地の画面・荷台の救急箱／保冷箱／投光器・田んぼ・拠点の配置は `python3 tests/kei-truck-systems-browser.py`（`KTS_SHOTS=フォルダ`。約15分）、画面の配置（手持ちバーは下・PC の操作表と重ならない・スマホのボタンと重ならない、PC 9種類・スマホとタブレット 7種類の大きさ）は `python3 tests/hud-layout-browser.py`（`HUD_SHOTS=フォルダ` で画面を撮る）。拠点本部（P3-B：シャッター・前庭のサル・入る・3か所の調査・拠点設立の会話の台詞・倉庫と総合作業場の修理・時間が進む・資材置き場・軽トラの解体・持ち物の重さ・時刻・つづきから・古いセーブ）は `python3 tests/p3b-hq-browser.py`（約8分）。住民と救助（P3-C の C-1：澄江のがれき・リオの工具棚と部品とコンプレッサー・§9・§10 の台詞・スズキがいないとき・本部の中の昼と夜・スズキの上志比の拠点・つづきから・古いセーブ）は `python3 tests/p3c-residents-browser.py`（約8分）。拠点の管理と工事（P3-C の C-2：管理画面の4つのタブ・納める順・担当と効率・勤務時間・光明寺でも進む・共同住居と布団・基本防衛・つづきから）は `python3 tests/p3c-manage-browser.py`（約5分）。復興依頼とレベルアップ（P3-C の C-3：依頼の受ける・手順・報告・光る印・必須の依頼・物置・農業倉庫・半鐘・Lv2・共同住居3・避難住民・用水路・倒木・整備工場跡の屋内・Lv2 の施設・農園と収集運搬の仕事・収穫箱・車両整備場・Lv3 の条件・つづきから・古いセーブ）は `python3 tests/p3c-requests-browser.py`（約8分）。九頭竜川の釣りと宗一（P3-D の D-1：釣り竿・投げる・待つ・アタリ・合わせる・早すぎる／逃げられる／届かない／歩くとやめる・図鑑・宗一の出会いと加入依頼・協力者・アラレガコ（すぐ川へ戻す・§15 の台詞・川守の釣り竿）・川底をのぞく・Lv2 で本部に住む・つづきから・古いセーブ）は `python3 tests/p3d-fishing-browser.py`（河原は画面のない Chromium では重いので10分ほど）。防衛戦の勝率は `tools/defense-sim.cjs`（`docs/p1-sim-baseline.md`。`--suzuki 1` でスズキを連れる）、変異したサルとの1対1は `tools/mutant-duel-sim.cjs`（`docs/mutant-monkey-ai.md`）。画面の確認は Playwright（SwiftShader）で起動と表示を見る。
- 報告では「コードに存在／コミット済み／公開済み／PCで確認／iPhoneで確認」を区別する。実機で確かめていないことを確認済みと書かない。
- 各フェーズで、変更履歴・使った3Dアセットと版・実装済み／未実装・テスト結果・未解決の不具合・セーブ互換・次の工程を `docs/` に残す。

## 文書
| ファイル | 内容 |
|---|---|
| `docs/save-and-flags.md` | セーブ項目・章フラグ・イベントID |
| `docs/asset-registry.md` | 3Dアセットの台帳と制作依頼の形式 |
| `docs/dialogue-changes.md` | 確定した台詞・呼び方を変えた記録（v0.79.3：住民はヌシを「化け猪」と呼ぶ・変えていない所の一覧） |
| `docs/character-classic-body.md` | プレイヤー・村人の体の決定と検証 |
| `docs/chapter2-progress.md` | 第2章の実装状況 |
| `docs/chapter2-map-plan.md` | 上志比マップの調査と計画 |
| `docs/phase-p1-status.md` | P1 の現状整理 |
| `docs/phase-p2-status.md` | P2 の現状整理（2026-11-14 更新：作業A〜F と追加分の実装状況・確定仕様・決めてほしい質問13個・依存関係・推奨順序） |
| `docs/phase-p3-status.md` | P3（上志比の拠点施設・復興）の現状整理（2026-11-18）：範囲の読み取り・P2 の締め・目標（案）・実装状況・確定仕様・決めてほしい質問14個・3Dモデル・依存関係・技術的な問題・推奨順序 |
| `docs/p3a-report.md` | P3-A の報告（2026-11-18 ユーザー承認・v0.80 で main へ）：コード調査・拠点本部の候補（bld[1]・OSM way 447692360）・4地点の試作（妻入りの農家など）と屋内の試案（スズキも入る）・改善前後の比較（`docs/p3a/`）・参考資料・性能・8施設の費用の案（暫定）・屑鉄は解体して持ち帰る（採用）・時刻は均等24時間・屋内のつなぎ方・セーブ・回帰テスト |
| `docs/p3b-plan.md` | P3-B（拠点本部と内部探索）の準備（2026-11-19）：指示書 §24 と v0.80 のコードの照合・使える仕組み・決めてほしいこと7つ・進め方の案 |
| `docs/p3b-report.md` | P3-B（拠点本部と内部探索）の報告（2026-11-19・作業ブランチ `p3b-hq`）：決めてもらったこと（06:55）・屋内（間取りの表・引き戸・手前の壁）・入れる時期と前庭・3か所の調査と拠点設立の会話（§3.3 のまま）・倉庫と総合作業場の修理（素材は暫定・工期）・新しい素材3つ・資材置き場・持ち物の重さ（暫定）・時刻・画面・性能・セーブ・テスト・影響・未実装。§17 承認（2026-11-19 10:12）・§18 v0.81.1 光明寺の獣を離れているときに描かない（屋内の三角形 約54万→約7.6万） |
| `docs/p3c-plan.md` | P3-C（住民・復興・運営）の準備（2026-11-19）：指示書 §24 と v0.81.1 の照合・住民3人の見た目の候補（`docs/p3c/`・`tools/p3c-npc-candidates.js`。澄江3案・リオ3案・宗一2案）・指示書どうしの食い違い（宗一の出会いは釣り＝P3-D など）・決めてほしいこと10個・4段階の進め方 |
| `docs/p3c-c1.md` | P3-C の C-1（住民と救助、2026-11-19・作業ブランチ `p3c1-residents`）：澄江（住宅地の家のがれき）・リオ（整備工場跡で工具棚・部品・コンプレッサー）・台詞（§9・§10 のまま＋Claude が書いた台詞の一覧）・本部の中の住民（昼と夜）・宗一の枠・スズキの上志比の拠点・場所（地図の建物の案）・セーブ `p3c`・テスト |
| `docs/p3c-c2.md` | P3-C の C-2（拠点の管理画面と工事、2026-11-19・作業ブランチ `p3c2-manage`）：4つのタブ・分けて納める（持ち物→本部の倉庫→本部のそばの荷台）・住民の担当と勤務時間・作業効率・止まっている理由・別の地域でも進む・共同住居（布団で休む）と基本防衛設備（素材は暫定）・セーブ `p3c.fac`・`p3c.job`・テスト |
| `docs/p3c-c3.md` | P3-C の C-3（復興依頼とレベルアップ、2026-11-19 承認・v0.83 で main へ）：依頼8件（必須2件）の場所・手順・報酬（暫定）・復興 Lv1→Lv2（2階の共同住居3）・Lv2→Lv3 の条件・Lv2 の施設（農園・車両整備場・収集運搬施設）と住民の仕事・避難住民（見た目は 2026-11-19 承認）・Claude が書いた台詞・セーブ `p3c.lv`・`req` など・テスト |
| `docs/p3d-plan.md` | P3-D（釣り・生態系・川の改修）の準備（2026-11-19）：今のコード（P3-A の河原と釣り場の目印・支流6本・時刻と天気・かまど）・進め方 D-1〜D-3 と C-4・釣りの操作の案・魚11種とアラレガコの出方（資料）・釣り竿3段階の性能の案・魚料理10品の案・宗一の出会いと加入依頼・決めてほしいこと5つ |
| `docs/p3d-d1.md` | P3-D の D-1（九頭竜川の釣りと宗一、2026-11-19・作業ブランチ `p3d-fishing`）：釣りの操作・釣り竿3段階（暫定）・魚11種の出方（釣り場の決め方）・アラレガコ（目撃・すぐ川へ戻す・§15 の報告・川守の釣り竿）・宗一（出会い・加入依頼・協力者・Lv2 で正式居住）・図鑑・Claude が書いた台詞・セーブ `p3d`・テスト |
| `docs/p2-region.md` | 地域の仕組み（光明寺は常駐・ほかは一時、座標のずらし、移動・失敗時の復旧・セーブ） |
| `docs/p2-kamishihi-map.md` | 上志比の地図（出典・利用条件・座標と縮尺・広さ・作り直し方・ゲーム内の作り・確認・未実装） |
| `docs/mutant-monkey-glb-check.md` | 変異したサル（Tripo の GLB）の検査・軽量化の試作・修正方針・確認事項。道具は `tools/models/` |
| `docs/mutant-monkey-rig.md` | 変異したサルの骨・重み・動き（rig 1）・ゲーム用データ・確認動画の作り方 |
| `docs/mutant-monkey-ai.md` | 変異したサルの AI（暫定の強さ・攻撃・初遭遇は逃げ去る・v0.62 の強敵化と「変異した鱗」・強さの測定結果）と試遊版 `previews/p2-mutant/` |
| `docs/mutant-scale-uses.md` | 変異した鱗の使い道（2026-11-13 決定）と v0.63〜v0.64 の実装：かまど・変換炉・蒼鱗／変異鱗の武器・鱗の飛去来器・蒼鱗／変異した鱗の防具・衝撃波・未定の事項 |
| `docs/kamado-cooking-plan.md` | かまどの料理と食材の種類（v0.66）：ユーザー決定・食材・料理の決まり方・未定の事項 |
| `docs/p2-kami-wild.md` | 上志比の獣・採集・伐採（v0.67、P2 指示の第1段階）：決まったこと・照合の食い違い・数（暫定）・作り・セーブ `kami`・試遊版のテストモード・未実装（第2・第3段階） |
| `docs/p2-kami-fort.md` | サルの占拠区域（v0.68、P2 指示の第2段階）：中心要塞・小拠点2か所の場所と形・侵入経路3つ・見張り台・物資置き場（本編では持ち出せない）・確認・報酬の数の案・未実装（第3段階） |
| `docs/p2-kami-watch.md` | 要塞・小拠点のサルと警戒 AI（v0.69、P2 指示の第3段階）：顔ぶれ・見張り（18m・視線・遮り）・巡回・通報と増援・見失った後の探索・倒された守りの戻り・遠くのサルの簡略化・物資の回収と再補充（60分）・確認 |
| `docs/p2-suzuki-ally-plan.md` | スズキの仲間 AI（作業E）の現状整理：目標・使える既存の処理・確定仕様（見た目は 2026-11-15 承認）・ChatGPT に決めてほしい質問14個・依存関係・技術的な問題・推奨順序 |
| `docs/p2-suzuki-ally.md` | スズキの仲間 AI（作業E）の実装記録：ChatGPT 指示書との照合（既存コード15項目・食い違い）・実装方針・未確定の数の提案・段階ごとの確認 |
| `docs/p2-story-f-plan.md` | 作業F（救援無線・出発・山王での初遭遇）の現状整理（2026-11-16）：目標・実装状況（使える既存の処理）・確定仕様・決めてほしい質問14個・依存関係・技術的な問題・推奨順序 |
| `docs/p2-story-f.md` | 作業F の実装記録（v0.77、2026-11-17 本編へ）：2026-11-17 ユーザー確定の5項目・指示書との照合・流れと仕組み・KEI truck（仮の値・操作・【3Dモデル制作依頼】）・台詞（2026-11-17 すべて承認）・セーブ（新しいキー・旧セーブ）・確認・決めてほしいこと |
| `docs/kei-truck-glb.md` | KEI truck の正式モデル（Tripo の GLB、修理前・修理後。v0.77）：main の確認・元データ・ゲーム用の作り方・フロントガラス（元に無いので足した）・車輪の分離（ドア・あおりは未）・大きさ・運転席・荷台・当たり・組み込み・軽量化・確認・指示書 §8 の実装の順 |
| `docs/kei-truck-systems.md` | KEI truck の仕組み（v0.78、2026-11-17 20:57 ユーザー決定。v0.79 で改修を段階5まで・荷台の施設6つ・車両基地を南東へ）：燃料（木炭で足す）・車体の傷み（激突・着地・獣・横転）・横転と起こす・車両基地（拠点の南東・画面のタブ）・改修（初期＋5段階）・荷台（丸太6本・広さ60・建設に直接使う・保冷箱で食べ物）・荷台の施設6つ（作業台・見張り台・炭焼き釜・救急箱・保冷箱・投光器）・源さんの運搬・照合・数（暫定）・セーブ・確認・決めてほしいこと |
| `docs/base-layout-plan.md` | 拠点（光明寺）の施設の配置の見直し（v0.79、2026-11-18 ユーザー決定の B案）：動かしたもの・車両基地の新しい形・田んぼの役目（田植え→稲刈り）・作業台と車両基地の画面（タブとカード・アイテムの絵）・確認 |
| `docs/p2-weapon-glb.md` | 武器13本と鉈の鞘の GLB（v0.75）：照合・対応表（アイテムID ← GLB）・ゲーム用の作り方（`tools/models/weapon_build.mjs`）・読み込みとフォールバック・光・確認・重さ・未確認 |
| `docs/scale-armor-v2.md` | 鱗の防具の作り直し（v0.76）：STEP 0 の調査・新しい作り（体を測って沿わせる板・立体の鱗・亀裂・縁金と爪）・8種類の形・演出・確認・重さ・未解決 |
| `docs/p2-investigation.md` | P2 統合指示書 v3.0 への初期調査（防具の原因・地理データ・スズキ・順序・確認事項） |
| `docs/p1-sim-baseline.md` | 防衛戦の勝率測定ツールと基準値 |
| `docs/p1-balance-report.md` | P1 の測定結果・調整（v0.55・v0.56 で反映）・未確認事項 |
| `docs/death-penalty.md` | 倒れたときの代償（v0.56） |
| `docs/combat-aim.md` | 攻撃の向きと当たり判定（v0.58） |
| `docs/hud-layout.md` | 画面の配置（v0.76.1）：手持ちバーはスマホでも下・PC の操作表と重ならない・指は離したときに選ぶ・確認 |

- 拠点を真上から撮った図（施設の名前つき）：`python3 tools/base-topdown.py 出力.png [中心x 中心z 幅m]`。
- KEI truck の GLB の確認画像：`python3 tools/kei-truck-studio.py 出力.png [broken|repaired|both] [views|parts|spin|person]`（6方向と上・車体と車輪を分けた姿・車輪を回した姿・人と並べた大きさ）。ゲーム用を作り直すときは `node tools/models/kei_truck_build.mjs`（設定 `tools/models/kei_truck.json`）。
- 武器の GLB の確認画像：`python3 tools/weapon-studio.py 出力.png lineup|hand|holster|perf 武器ID …`（前の形との比較・手に持つ姿・腰と背中・重さ）。ゲーム用の GLB を作り直すときは `node tools/models/weapon_build.mjs [ID …]`（設定 `tools/models/weapons.json`。`tools/models` で npm install が要る）。
- キャラクターの確認画像：`python3 tools/char-studio.py 出力.png player suzuki gen`（`player@forest` で防具の組を着せる。`STUDIO_POSE=1` で動きの姿勢。`STUDIO_HTML` で別の index.html。`STUDIO_CANDS=tools/p3c-npc-candidates.js` で P3-C の住民の候補 `sumieA`〜`soichiB` も並べられる）。鱗の防具（蒼鱗・変異した鱗）は `python3 tools/scale-armor-studio.py 出力.png`（全身）と `python3 tools/scale-armor-studio2.py 出力.png raw|blue fx|nofx|dark [pose]`（部位ごとの正面・横・背面・斜め／演出なし／暗い背景／ゲームの中の姿勢）。スズキの動き（待つ・歩く・走る・蹴り3種・倒れる・臭いの煙など、ゲームの中で）は `python3 tools/suzuki-pose-shots.py 出力.png [姿勢 …]`。動画は `python3 tools/suzuki-anim-video.py 出力.mp4`。スズキを連れたときの重さの目安は `python3 tools/suzuki-perf.py`。
- 試遊版の作り方：`python3 tools/build-p1-preview.py`（防衛戦。A／B／C ボタン。`previews/p1-balance/`）と `python3 tools/build-p2-mutant-preview.py`（変異したサル。`previews/p2-mutant/`）と `python3 tools/build-p2-kami-preview.py`（上志比の獣・採集・サルの要塞。開発用テストモードはここだけ。`previews/p2-kami/`）と `python3 tools/build-p2-suzuki-preview.py`（スズキの仲間 AI。スズキを呼ぶボタンはここだけ。`previews/p2-suzuki/`）と `python3 tools/build-p2-story-preview.py`（作業F。途中から始めるボタン・素材を足すボタンはここだけ。`previews/p2-story/`）。どちらも本編をコピーして試遊用の保存キーを足す。本編を変えたら作り直す。
