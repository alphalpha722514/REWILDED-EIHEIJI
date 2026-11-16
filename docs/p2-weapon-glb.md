# 武器の GLB（Tripo で作った形）を入れる — v0.75

指示書：`REWILDED_EIHEIJI_Claude_Weapon_Implementation.md`（2026-11-16）と、武器13本と鉈の鞘の GLB 14個（`REWILDED_EIHEIJI_weapon_assets_14.zip`）。
基準のコード：`main` = 9aaef8d（v0.74）。v0.74.1（スズキの棍棒）の上に作った。

**中心の決まり**：武器の**見た目だけ**を GLB に替える。威力・当たり・間合い・耐久・レシピ・解放条件・アイテムID・名前・セーブ・主人公の体は変えない。

## 1. 受け取った物と照合

- 14個とも、台帳（`weapon_asset_manifest.json`）の SHA-256 と一致。見つからないファイルはない。
- どれも GLB 2.0・形1つ・材質1つ・2048² の絵3枚（色・金属と粗さ・凹凸）・骨と動きなし。三角形 5,466〜5,974。
- 向きはばらばら（横向き・縦向き・斜め。鉈は刃が長い軸のまわりに約50°ねじれている）。1本ずつ、握る位置・向き・大きさを合わせた（下の 3）。
- 台帳の飛去来器の ID は `weapon.special.throwing_scale`、指示書は `weapon.special.scale_boomerang`。**指示書の ID を使う**（置き場所は台帳のまま `special/throwing_scale/`）。

## 2. 今のコード（調べた結果）

| 調べた物 | 今の作り |
|---|---|
| 武器の形 | すべてコードで作る：`makeWeapon`（鉈・槍）・`makeArm`（斧・棍棒・竹槍）・`weaponFineDetail`（細部）・`scaleArmDeco`（鱗の武器＝元の武器＋鱗と光の板）・`boomerShape`（飛去来器） |
| GLB を読む仕組み | なかった（three.js r128 本体だけ。変異したサルは GLB を前もって JS のデータに変えて読む） |
| 手の武器 | `showWeapon` → 右手の `weaponPivot`。攻撃中は `placeRig` で振りの曲線どおりに置き直す。大きさは `f47WeaponScale` |
| 当たり | `WTIP`（武器の形の中の根元・先端）× 大きさ → `weaponWorld`。**形とは関係しない**ので、見た目を替えても当たりは同じ |
| 腰・背中 | `HOL`：鉈は腰（簡素な鞘の箱）、斧は背中。持っている中で一番良い物を、手に持っていないときだけ表示 |
| アイコン | 手持ちバー・持ち物の絵は、武器の形を一度描いて画像にする（`iconOf`） |
| 飛去来器 | `BOOM`（投げる・戻る・当たる・衝撃波）。見た目は `boomerMesh`（飛ぶ姿）と手に持つ姿 |
| セーブ | `weapon`・`dur`・`arms`（ID と耐久）。見た目とは関係しない |
| 落とす・拾う | 武器を地面に落とす・拾う仕組みはない（作業台で作る・鍛えるだけ）。新しく作らない |

**見つけた不具合（直した）**：やわらかい体（v0.54.1〜）では腰の骨が足もとにあるため、**腰の鞘と鉈が足もとに埋まって見えていなかった**。脚の付け根の高さへ上げた（`buildHolsters`、見た目だけ）。

## 3. 対応表（ゲームのアイテムID ← GLB）

| 論理ID | 元のファイル | ゲームのID | ゲーム用（`game/`） | 大きさ・向き |
|---|---|---|---|---|
| weapon.normal.nata | 鉈１.glb | `nata1`・`nata2`・`nata3`（2026-11-16 ユーザー：3段階とも同じ形） | nata_normal.glb | 先端 -1.30。Lv2 は 1.046 倍・Lv3 は 1.1 倍（前の形の長さにそろえる） |
| weapon.normal.axe | hand axe 3d model.glb | `axeIron`（鉄の斧） | axe_normal.glb | 先端 -1.15 |
| weapon.normal.club | wooden club 3d model.glb | `club` | club_normal.glb | 先端 -1.33 |
| weapon.normal.spear | spear 3d model(1).glb | `spear`（牙槍） | spear_normal.glb | 先端 -2.30 |
| weapon.azure.nata | fantasy knife 3d model.glb | `scNata` | nata_azure.glb | 先端 -1.43・青い鱗が光る |
| weapon.azure.axe | fantasy battle axe 3d model.glb | `scAxe` | axe_azure.glb | 先端 -1.15・光る |
| weapon.azure.club | fantasy staff 3d model.glb | `scClub` | club_azure.glb | 先端 -1.33・光る |
| weapon.azure.spear | fantasy staff 3d model 2.glb | `scSpear`（**2026-11-16 ユーザー採用**） | spear_azure.glb | 先端 -2.30・光る |
| weapon.mutant.nata | 変異　鉈.glb | `rwNata` | nata_mutant.glb | 先端 -1.43・紫の亀裂 |
| weapon.mutant.axe | 変異　斧.glb | `rwAxe` | axe_mutant.glb | 先端 -1.15・紫の亀裂 |
| weapon.mutant.club | 変異　棍棒.glb | `rwClub` | club_mutant.glb | 先端 -1.33・紫の亀裂 |
| weapon.mutant.spear | 変異　槍.glb | `rwSpear` | spear_mutant.glb | 先端 -2.30・紫の亀裂 |
| weapon.special.scale_boomerang | dragon-scale blade 3d model.glb | `boomer`（手に持つ姿・飛ぶ姿） | boomerang_scale.glb | 直径 0.8・紫の光 |
| accessory.normal.nata_sheath | leather knife sheath 3d model.glb | 腰の鞘（鉈。v0.76 から蒼鱗・変異の鉈も） | sheath_nata.glb | 長さ 0.70。腰で幅を 1.25 倍・厚みを 1.2 倍（鉈の刃が収まるように） |

- **今のコードの形のまま**：`axeStone`（石の手斧）・`bamboo`（竹槍）（2026-11-16 ユーザー：「よい。余裕があれば後から作ります」）。
- 「先端」は武器の形の単位（`f47WeaponScale` を掛ける前）で、前のコードの形の先端の位置にそろえた。握る所は柄の真ん中あたり。
- 蒼鱗・変異の鉈の腰の鞘も、通常の鉈と同じ GLB の鞘を使う（2026-11-16 ユーザー「蒼鱗、変異鱗の鉈は通常鉈と同じglbの鞘を使用してください」。v0.76 で反映。テスト `tests/weapon-glb-browser.py` で確認）。

## 4. 置き場所と作り方

- 元の GLB：`assets/models/weapons/<normal|azure|mutant|special|accessory>/<種類>/src/`（受け取ったまま。SHA-256 一致）。台帳：`assets/models/weapons/weapon_asset_manifest.json`・`.csv`。
- ゲーム用：同じ場所の `game/`。作り方：`node tools/models/weapon_build.mjs [ID …]`（設定は `tools/models/weapons.json`、結果は `assets/models/weapons/game-build.json`）。
  1. 向き：握る所が原点・先端が -y・刃が +z（コードの武器と同じ）。鉈・変異の斧は、刃の広がる向きを自動でそろえる（`twist: auto`、必要なら `flip`）。変異の槍は先に 26.5° 回す（`preRotY`）。
  2. 大きさ：先端が前のコードの形の先端の位置に来るように。
  3. 絵：色の絵だけを **512²** の JPEG に。金属と粗さ・凹凸の絵は外した（ゲームはトゥーンの陰影なので使わない）。
     - 1024² と 512² を近くで比べ（`tools/weapon-studio.py` と同じ光）、512² は少しやわらかいがゲームの距離では差がほぼない。iPhone のメモリを考えて 512² にした（色の絵1枚：1024² は約5.6MB、512² は約1.4MB）。
  4. 光る所の絵（白黒 512²）：蒼鱗は色の絵の「青い鱗」を色で選ぶ（7〜28%）。変異鱗の4本は、絵に紫がないので、細い枝分かれの亀裂を描いた（2〜3%。決まった乱数）。飛去来器は絵の中の紫（1%）。
  5. 拡張（KHR_materials_volume）を外した。
- 三角形は減らしていない（5,466〜5,974。6,000 以下の目標どおり）。
- 合計：元 56.2MiB → ゲーム用 14個で **約3.8MB**（1個 230〜350KB）。

## 5. ゲームの中の作り（`index.html`）

- `WGLB_FILE`（形のファイル）・`WGLB`（武器ID → 形と微調整 `s`・`p`・`r`・`glow`）・`WGLB_X`（鞘・飛ぶ飛去来器）。
- 読み込み：three.js r128 の GLTFLoader を `vendor/three-r128/GLTFLoader.js`（MIT、`LICENSE` 同梱）に置き、初めて要るときだけ読む（失敗したら jsDelivr の同じ版）。GLB は1本ずつ別のファイル（`index.html` に埋め込まない）。本編と試遊版（`previews/…/`）の両方の置き場所を試す。
- **持っている武器の形だけを読む**（`wglbPrefetch`：持ち物が変わったとき・武器を持ち替えたとき）。鉈（通常・蒼鱗・変異）を持っていれば鞘も（v0.76）。形と絵は種類ごとに1つを使い回す（手・腰・背中・アイコン）。
- 読めるまで・読めないときは、**今のコードの形のまま**（フォールバック）。読めたら、手・腰・背中の形をその場で入れ替え、アイコンは次に表示するとき描き直す。
- 材質：トゥーンの陰影（ほかのキャラクターと同じ）。絵は変換しない（画面が線形のため）。
- `makeWeapon` は、コードの形を作る `makeWeaponCode` を呼んでから GLB に替える。鱗の武器の仮の飾り（`scaleArmDeco`）は、GLB に替わると外れる（二重にならない）。
- 当たり（`WTIP`・`weaponWorld`）・大きさ（`f47WeaponScale`）・振りの曲線・攻撃の動き・持ち替え・耐久・作業台は変えていない。

### 光（効果は変えない。見た目だけ）

| 種類 | 光り方（強さは暫定） |
|---|---|
| 通常 | 光らない |
| 蒼鱗 | 青い鱗が光る（色 0x5cc8ff・強さ 0.85）。ゆっくり脈打つ。手に持って攻撃している間は 1.35 倍。前からの青い光の粒（`scaleFxUpdate`）はそのまま |
| 変異鱗 | 紫の亀裂が光る（色 0xa040ff・強さ 0.95）。不規則にちらつく（いくつかの波を重ねる）。攻撃中は 1.4 倍。前からの暗い紫のもやはそのまま |
| 飛去来器 | 紫の光（変異鱗と同じ）。飛んでいる間は 1.4 倍。回り方（毎秒24ラジアン）・飛び方・当たり・戻り・衝撃波は前のまま |

全体にかける光のにじみ（ブルーム）は使っていない（iPhone の負荷のため）。

## 6. 確認（2026-11-16、画面のない Chromium・SwiftShader）

**`python3 tests/weapon-glb-browser.py`（新しいテスト）**：通過。
- 新しく始めると、持っている鉈と鞘の GLB だけを読む（持っていない武器は読まない）。
- 作業台で、鉈 Lv2・Lv3・木の棍棒・石の手斧→鉄の斧・牙槍・蒼鱗4本・変異鱗4本・飛去来器を作れる（レシピ・材料・解放条件は前のまま）。
- 13本とも、手に持つと GLB の形。手の武器の大きさ（`f47WeaponScale`）は前と同じ。
- 当たりの点（根元・先端）は、GLB でもコードの形でも同じ値。武器の数値（`WEAPONS` 全体）は変わらない。
- GLB の武器（蒼鱗の棍棒・変異鱗の槍・業物の鉈）で通常攻撃が出て、獣に当たる。
- 飛去来器：投げる→飛ぶ姿は GLB→戻って手に戻る（2回続けて）。
- アイコンは GLB を読んだあと描き直される。
- 上志比へ移っても手の武器は GLB のまま。光明寺へ戻れる。
- セーブ→読み直し→続きから：持ち物（13本）・手の武器・GLB の形が戻る。保存の版は `v:1`、キーは `weapon`・`dur`・`arms` のまま。
- エラーなし。

**`WGT_NOGLB=1 python3 tests/weapon-glb-browser.py`（GLB を 404 にする）**：通過。読めないときはコードの形のまま、作る・持ち替え・攻撃・飛去来器・地域の移動・セーブがエラーなしで動く。

**見た目**：`tools/weapon-studio.py`
- `lineup`：前のコードの形と GLB を、刃の面・刃の側・背・斜めで並べ、当たりの点（赤・緑）と握る所（黄）を重ねた。向き・握り・長さをそろえた。
- `hand`：ゲームの中で、立つ・通常攻撃の当たる瞬間・強攻撃の当たる瞬間（13本）。逆さ・浮く・地面に刺さる・手から離れるは見当たらない。
- `holster`：腰の鞘（鉈の刃が鞘に収まり、柄が上に出る）と背中の斧。

**ほかのテスト**：テスト5本・`scale-gear-browser`・`wardrobe-browser`・`region-browser` は通過。

**重さ（`tools/weapon-studio.py … perf`、画面のない Chromium）**

| | 前（コードの形） | GLB |
|---|---|---|
| 手の武器1本の部品（描く回数） | 2〜22（鱗の武器は光の板が多い） | **1** |
| 三角形 | 840〜6,100 | 5,470〜5,970 |
| 色の絵 | なし | 512² 1枚（光る武器は光の絵 512² をもう1枚） |
| ファイル | — | 1本 230〜350KB（初めて持つときだけ読む） |

- 手の武器の描く回数は減り、三角形は増える（1本あたり最大 +約5,000）。腰・背中にも1本ずつ見えるので、3本で +約15,000 三角形が目安。
- GPU のメモリ（目安）：色の絵1枚 約1.4MB、光の絵1枚 約1.4MB。14個すべてを読んでも 約40MB 以下。
- 読み込みの時間：手元（同じ機械の中）で1本 約25〜370ms。**GitHub Pages・スマホの回線では未計測。**
- 輪郭線（墨の線）は付けない（2026-11-16 ユーザー「武器のGLBに墨の輪郭線は必要ないです」）。

## 7. 未確認・決めてほしいこと

- PC・iPhone の実機（GitHub Pages での読み込み・表示・速さ）：**未確認**。画面のない Chromium（SwiftShader）でだけ確かめた。
- 速さ（FPS）：実機で測っていない（**未計測**）。
