# セーブ項目・章フラグ・イベントID 一覧 — v0.54.1（main `5a4b09a` 時点）

`index.html` の実コードから抜き出した一覧です。新しい機能を足すときは、ここに書いた **変えてはいけない項目** を守り、この文書も更新します。

## 1. ブラウザに保存しているもの（localStorage）

| キー | 中身 | 書く場所 |
|---|---|---|
| `eiheiji_vs_beasts_v010`（`SAVE_KEY`） | ゲームの進行（下の表） | `saveGame()` |
| `REWILDED_EIHEIJI_SETTINGS`（`SND_KEY`） | 音量などの設定 | 設定の切り替え時 |
| `eiheiji_aimMode` | 攻撃方向（カーソル／向き） | 攻撃方向の切り替え |
| `eiheiji_perf` | 性能の設定 | 設定の切り替え時 |
| `eiheiji_shadow` | 影の設定 | 設定の切り替え時 |
| `eiheiji_weatherEffects`（`WEATHER_PREF`） | 雨・霧の表示 | 設定の切り替え時 |
| `__t` | 保存できるかの確認用（すぐ消す） | 起動時 |

## 2. セーブデータ（`SAVE_KEY` の中身）

`saveGame()` が書き、`continueGame()` → `readSave()` → `applySave()` が読みます。形式の版は `v:1` です。

| キー | 中身 | 初期値・読み込み |
|---|---|---|
| `v` | 形式の版。**1 のまま** | — |
| `chapter2` | 第2章の状態（第3節） | `chapter2State()` が不正な値を補正 |
| `inv` | 持ち物（木材・食料・獣素材・柵キット・罠キット・杭柵・落とし穴・餌場・おにぎり・弁当・焼き野菜・薬草粥・牙・藁・縄・石・竹・鉄・種・稲の種・`armor` など）。v0.62 で `mutScale`（変異した鱗、既定 0）を足した。旧セーブにこのキーがなくても 0 で読む。v0.63 で `procScale`（加工した鱗、既定 0）、v0.64 で `charcoal`（木炭、既定 0）、v0.66 で食べ物 `meat`・`veg`・`rice`・`katsudon`・`botan`・`gomadofu`・`koroni`・`kushi`（既定 0。鮮度の表 `f7` にも同じ名前で入る）を足した。v0.81（P3-B・作業ブランチ `p3b-hq`）で `oldParts`（古い機械部品）・`shelfKit`（棚の金具）・`toolSet`（作業場の工具一式）（既定 0） | `freshState()` |
| `weapon` / `dur` | 手に持つ武器と耐久 | — |
| `full` | 満腹 | — |
| `arms` | 武器ごとの耐久。v0.63 で蒼鱗の武器 `scNata`・`scAxe`・`scClub`・`scSpear`、v0.64 で変異鱗の武器 `rwNata`・`rwAxe`・`rwClub`・`rwSpear` と鱗の飛去来器 `boomer` が増えた（読み込みは `WEAPONS` にある名前だけ） | — |
| `prog` | 進行（下の表） | — |
| `fences` | 柵のすき間ごとの種類と耐久（`GAPS` の順） | — |
| `traps` | 罠（`saveTrap` / `restoreTrap`） | — |
| `stats` | 撃破数・死亡数・製作数・時間・パーフェクト・狩猟記録 `hunt` | `loadHuntRecords()` |
| `nodes` | 採集場所の残り（`NODES` の順） | — |
| `g4` | 掲示板・追跡・柵・畑・依頼の進み（`g4Fresh()`） | — |
| `f4` | 伐採・丸太・荷車（`f4Save()`） | — |
| `f5` | 探索・道具・岩・金属（`f5Save()`） | — |
| `f7` | 食料の手持ちと倉庫（`v:1`） | 旧形式は読み込み時に移行し、すぐ保存 |
| `f8` | 共同菜園・稲（`v:2`） | — |
| `f9` | 町民イベント（`intro`・`yone`・`yIntro`、`v:1`） | — |
| `f10` | 伏線 `lore`・時刻 `tod`（`v:1`） | — |
| `conv` | v0.63：変換炉（`built` 建てたか・`q` 待っている数・`t` 今の進み（秒）・`out` できた数、`v:1`）。`facSave('conv')`／`facLoad('conv',…)` | 項目がない旧セーブ・不正な値は未建設（`facFresh()`） |
| `kama` | v0.64：かまど。v0.66 で形を変えた：`built`・`q`（作業の並び。`'charcoal'` か料理の名前の配列）・`t`・`out`（できた物ごとの数）。`kamaSave()`／`kamaLoad()` | 項目がない旧セーブは未建設。v0.64 の形（`q`・`out` が数）も読む |
| `kami` | v0.67：上志比の採集・伐採・獣（`v:1`）。`n` 取った場所が戻る時刻（鍵 `s`石・`b`竹・`r`岩・`w`藁・`p`薪・`o`畑＋番号）・`r` 岩の残り・`sc` 探ったがれきの番号・`f` 切った木（`k区画_区画_番号`、新しい400本まで）・`sp` 獣が戻る時刻（`a`＋番号）・`g` 群れ（`g`＋番号：`d` 倒れた仲間3つ・`w` 全滅から戻る時刻）。時刻は遊んだ時間 `stats.time`。番号は地図データから決まる置き場所の順（`docs/p2-kami-wild.md`）。`kamiSave()`／`kamiLoad()` | 項目がない旧セーブ・不正な値は「何も取っていない」（`kamiFresh()`）。開発用テストの設定（`KW_TEST`）は保存しない。v0.68：`st` 物資置き場（`fort`・`outB`：`n` 持ち出した回数・`t` 最後に持ち出した時刻。v0.69 から60分で再補充）。v0.69：`fm` 倒された守りのサルが戻る時刻（`f0`〜`f9`・`a0`〜`a2`・`b0`〜`b2`）。項目がなければ空 |
| `paddy` | v0.79：拠点の田んぼ（`v:1`）。`st` 1=水だけ（田植えの前）・2=育っている・3=実った、`t` 育った秒（遊んだ時間）、`care` 草取りをしたか（0/1）。`paddySave()`／`paddyLoad()`（`docs/base-layout-plan.md` §3） | 項目がない旧セーブ・不正な値は「育っている途中（半分）・草取りなし」（`paddyFresh()`） |
| `suzuki` | v0.73：スズキの仲間（`v:1`）。`joined` 仲間か（作業F の初遭遇で立てる予定。今は試遊版の呼び出しだけ）・`order` 指示（`follow` ついて来る／`wait` ここで待つ／`base` 拠点で過ごす）・`region` いる地域・`x`,`z` 位置・`wx`,`wz` 待つ所・`hp` 体力（倒れていれば0）・`down` 倒れているか。仲間でないときは `{v:1,joined:false}`。**古いセーブ（キーがない）・形の違う値は「まだ仲間でない」**。ついて来ている・位置が分からないスズキは、読み込んだ後に主人公の近くへ出す。待つ所がなければいた所で待つ。拠点で過ごすのは光明寺だけ（v0.82：拠点設立のあと（`p3.hq.plan`）は上志比の拠点本部の前庭でも。`order:'base'`・`region:'kamishihi'`）。試遊版 `previews/p2-suzuki/` は別の保存キー（`eiheiji_vs_beasts_p2suzuki`） |
| `p3` | v0.81（P3-B・作業ブランチ `p3b-hq`）：上志比の拠点本部（`v:1`）。`hq`：`sv` 調べた3か所（0/1）・`talk` 拠点設立の会話を始めた・`plan` 会話を終えた（「上志比復興計画を開始」）・`beasts` 前庭のサルを出した・`visited` 入ったことがある。`rep`：`storage`・`workshop` 直した所（0/1 を3つずつ）。`got`：`gen` 発電機から部品を外した・`yardTruck` 前庭の軽トラを解体した・`yardHits` たたいた回数。`p3Save()`／`p3Load()`（`docs/p3b-report.md` §10） | 項目がない旧セーブ・`v` が違う値は「まだ何もない」（`p3Fresh()`）。`plan` があれば会話と調査は済み。会話の途中（`talk` だけ）で閉じたら会話をやり直す。倉庫が直っていないのに作業場が進んでいれば作業場を戻す |
| `stash` | v0.81（P3-B・作業ブランチ `p3b-hq`）：資材置き場（`v:1`）。`komyoji` 光明寺の丸太置き場・`kami` 拠点本部の倉庫。素材（`wood`・`stone`・`iron`・`rope`・`straw`・`bamboo`・`hide`・`charcoal`・`oldParts`）ごとの数。`stashSave()`／`stashLoad()` | 項目がない旧セーブ・`v` が違う値は空。知らない素材・0以下・数でない値は捨て、小数は切り捨て |
| `p3c` | v0.82（P3-C の C-1・作業ブランチ `p3c1-residents`）：住民（`v:1`）。`hint` 案内を出した。`sumie`：`met` 声をかけた・`hits` がれきをどかした回数（0〜3）・`done` 住民になった。`rio`：`met`・`shelf` 工具棚を動かした・`talk` 話を聞いた・`parts` 部品2つ（0/1）・`fixed` コンプレッサーを直した・`done`。`soichi`：`found`・`coop`・`joinDone`・`resident`・`job`（P3-D から使う枠）。`p3cSave()`／`p3cLoad()`（`docs/p3c-c1.md` §5） | 項目がない旧セーブ・`v` が違う値は「まだ誰もいない」（`p3cFresh()`）。後の段階が済んでいれば前の段階も済みにそろえる |

### `prog` の中身

| キー | 中身 |
|---|---|
| `stage` | 進行段階（第4節）。保存時は `checkpointStage()` で戦闘中の段階を準備段階に戻す |
| `unlockTrap` / `unlockBoss` | 罠・ボスの解放 |
| `clues` | 手がかり3つ |
| `bossDefeated` | ヌシ討伐。**第2章の解放条件** |
| `scoutTower` / `scoutWarned` / `scoutRaidWarned` | 見張り台と予告 |
| `townRequests` | 町の依頼（`active` と依頼主ごとの `cooldown`。最大180秒） |
| `level` / `exp` / `mastery` / `xph` | 育成（`f31SaveProg()`） |
| `gear` | 防具の所持 `owned` と装備 `equip`（頭・胸・脚・靴） |

## 3. 第2章の状態（`chapter2`）

`chapter2State(saved, bossCleared)` が毎回作り直します。

| キー | 決まり方 |
|---|---|
| `version` | 1 |
| `unlocked` | ヌシ討伐済みなら true |
| `currentRegion` | 最後にいた地域（`komyoji`／`kamishihi`）。**作りがあり（`REG.defs`）、第2章が開放済みのときだけ**復元し、それ以外（旧セーブ・未実装の地域）は `komyoji`（v0.60）。上志比で保存したら、つづきからは上志比の着く所から（位置は保存しない） |
| `currentChapter` | ヌシ討伐済みで、かつ `progress.openingStarted` が true なら 2。それ以外は 1 |
| `regions` | `komyoji` は常に解放。`kamishihi` はヌシ討伐で解放扱い（地図は未実装） |
| `progress` | 第2章の進み。中身はそのまま保存する（後の段階用） |

`progress` で使っている値：

| キー | 意味 |
|---|---|
| `openingStarted` | 光明寺防衛戦を始めた |
| `defenseComplete` | 光明寺防衛戦を完了した（章クリアとは別。失わない） |
| `defenseRewarded` | 初回クリアの報酬を受け取った（v0.55）。これがない勝利で1回だけ報酬が出る |
| `mutantMet` | 変異したサルと初遭遇した（v0.67 で予約）。**v0.77（作業F・作業ブランチ）**：山王の初遭遇のあと、スズキとの会話を終えて仲間になったとき（`suzuki.joined` と同時）に立つ。立つと、上志比の町の群れに変異したサルが加わる（`kamiMutantOK()`） |
| `radioHeard` | **v0.77（作業ブランチ）**：救援無線を聞いた。防衛戦の勝利で `false` が付き、聞くと `true`。**キーが無い＝作業F の記録が無い**（v0.76 以前・試験の開放）＝今までどおり |
| `departureDecision` | v0.77：出発の相談をした |
| `truck` | v0.77：KEI truck `{found,repaired,fueled,fuel,parts,trips,region,x,z,a}`（見つけた・直した・燃料を入れた・持っている燃料・拾った部品 ID・上志比へ運転して行った回数・置いてある地域と場所と向き）。不正な値は `trk()` が直す |
| `truck`（v0.78 で足した項目） | `gas`（燃料 0〜100%。無い旧セーブは燃料を入れていれば100）・`hp`（車体。無い旧セーブは満タン）・`lv`（改修の段階 0〜3）・`bed:{logs:[丸太の太さ 't'/'m'/'k'…6本まで],mats:{素材:数}}`（荷台）・`fac:{bench,kiln,tower}`（荷台の施設 0/1。段階が足りないものは0に直す）・`kiln:{q,t}`（荷台の炭焼き釜の待ち・経過秒）・`tip`（横転の向き 0/1/-1）。不正な値は `trkSys()` が直す（`docs/kei-truck-systems.md`） |
| `truck`（v0.79 で足した項目） | `lv` は 0〜5 に（段階4・5を足した）。`fac` に `aid`（荷台の救急箱）・`cool`（荷台の保冷箱）・`light`（荷台の投光器）を足した（無ければ0。作ってある施設は段階に関係なく残す）。`bed.foods = {食べ物の名前:[[数,経過秒],…]}`（保冷箱の中。無ければ空） |
| `depot` | v0.78：車両基地 `{built:0/1}`（作業台で建てる）。v0.79 で場所を拠点の南東へ移した（保存するのは建てたかだけなので旧セーブもそのまま南東に出る） |
| `departureComplete` | v0.77：直した報告と見送りが済んだ（このあと KEI truck で上志比へ） |
| `legacyKamishihiAccess` | v0.77：旧セーブの移動権。防衛戦は済み・`radioHeard` が無い保存を読み込むと `true`（ほかに `radioHeard:false` など）。歩いて上志比へ行けるまま、無線が1回鳴る。新しい保存には付かない（`stfNormalize()`、`docs/p2-story-f.md`） |

v0.77 の初遭遇（山王のカット・戦い）の途中は保存しない（`stfNoSave()`）。

## 4. 進行段階（`prog.stage`）

| 値 | 意味 | 保存時 |
|---|---|---|
| `talk` | 開始直後（区長に話す） | そのまま |
| `gather` | 素材集め | そのまま |
| `buildFence` | 柵の準備 | そのまま |
| `raid` | 襲撃中 | `buildFence` に戻す |
| `explore` | 探索 | そのまま |
| `invasionPrep` | 大規模侵攻の準備 | そのまま |
| `invasion` | 大規模侵攻中 | `invasionPrep` に戻す |
| `toBoss` | ヌシへ向かう | そのまま |
| `boss` | ヌシ戦中 | `toBoss` に戻す |
| `cleared` | 第1章クリア | そのまま |

## 5. イベントの種類（`ev.kind`）

| 値 | 内容 |
|---|---|
| `raid` | 第1章の襲撃（`startEvent('raid')`） |
| `invasion` | 第1章の大規模侵攻 |
| `chapter2` | 第2章冒頭の光明寺防衛戦（`C2_DEFENSE`） |

## 6. 変えてはいけない項目

- `SAVE_KEY` の文字列と `v:1`。
- 既存のキー名（`inv`・`prog`・`chapter2`・`f4`〜`f10`・`g4` など）と、その中の既存のキー名。
- `chapter2State()` の補正（不正な値・旧セーブでも壊れない）。
- 戦闘中の段階を保存しない仕組み（`checkpointStage()`）。
- 新しいデータは、**既定値つきの新しいキー**として足す。読み込み側は、そのキーがない旧セーブでも動くようにする。
- 第2章の進みは `chapter2.progress` の中に足す。`currentRegion` は遊べる地域だけを復元する（`docs/p2-region.md`）。

## 7. 確かめ方

- `node tests/chapter2-save.cjs`：旧セーブ・不正な値・保存の往復・キーと版の維持。
- `node tests/chapter2-defense.cjs`：防衛戦の開始・波・完了記録・再挑戦。
- `node tests/classic-body.cjs`：プレイヤー・村人の体。
