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
| `inv` | 持ち物（木材・食料・獣素材・柵キット・罠キット・杭柵・落とし穴・餌場・おにぎり・弁当・焼き野菜・薬草粥・牙・藁・縄・石・竹・鉄・種・稲の種・`armor` など）。v0.62 で `mutScale`（変異した鱗、既定 0）を足した。旧セーブにこのキーがなくても 0 で読む。v0.63 で `procScale`（加工した鱗、既定 0）、v0.64 で `charcoal`（木炭、既定 0）を足した | `freshState()` |
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
| `kama` | v0.64：かまど（`conv` と同じ形） | 同上 |

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
