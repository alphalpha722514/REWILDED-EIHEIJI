# 古い農家（E3-1）の検収用試遊版

2026-11-26：v0.89 の正式公開の後も残す（ユーザーの指示）。作り方の元（REF）は次の回で v0.89 のコミットに変える。

上志比の家屋 `house26` から古い農家に入り、間取り、歩ける範囲、スズキの同行、時刻による明るさを確かめるための試遊版です。入口と屋内は本編 E3-1 のものを使います。農家でのアイテム入手、調べる機能、書き置き、新しい物語は追加していません。

- 元のコミットは `d2cf2f4f3d1c7a92b89da44cc9387ee99ca5862f`（v0.88.1 に E3-1 を入れたもの）です。
- 元の `index.html` の blob は `603f7ce7421bef937bc12f998b049b19386f650c` です。
- セーブは `eiheiji_vs_beasts_p3e3farm`、音の設定は `REWILDED_EIHEIJI_SETTINGS_p3e3farm`、ほかの設定は `eiheiji_p3e3f_` で始まるキーに保存します。ページの先頭でも本編のキー7つへの読み書きと削除を止めます。

## 遊び方

タイトル右上の「テスト：古い農家の前で始める」を押すと、作業Fと拠点本部の設立まで済んだ状態で始まります。KEI truck は修理済みで、スズキがついて来ます。朝9時の晴れで始まり、農家のそばでは獣を遠ざけます。「古い農家に入る」「外へ出る」の案内が出たら、PC では E キー、iPhone では行動ボタンを使います。

左上の「試遊メニュー」に場所、時刻、スズキの状態が出ます。メニュー名をもう一度押すと閉じます。

| ボタン | 動作 |
|---|---|
| 古い農家の前へ | 農家の入口の前に移動する。屋内では外へ出てから移動する |
| スズキ | 「ついて来る」と「ここで待つ」を切り替える |
| 時刻 | 朝9時、夕方17時、夜23時を順に切り替える。選択直後のゲーム内1時間は、その時間帯に対応した明かりで見比べられる |
| 描く細かさ | 標準と軽量を切り替える |

## 作り直しと確認

指定コミットを含むローカルの履歴がある環境では、`python3 tools/build-p3e3-farm-preview.py` で生成できます。元のファイルの写しが手元にある場合は、次のコマンドを使います。どちらも元の blob を照合してから `previews/p3e3-farm/index.html` に出力します。`--out` で別の出力先を指定できます。

```sh
python3 tools/build-p3e3-farm-preview.py --src index.html
node tests/p3e3-preview-build.cjs
node tests/chapter2-save.cjs
THREE_JS=/path/to/three.min.js node tests/p3e3-farm-preview.cjs
```

作り直しのテストは、保存済みの試遊版と生成結果をバイト単位で照合し、ページ内の JavaScript の構文も確認します。照合用の元ファイルは `PREVIEW_BUILD_SRC` で指定できます。試遊テストは Node の Playwright、Chromium、ローカルの three.js r128 を使います。Chromium の実行ファイルを指定する場合は `CHROMIUM_BIN` を使います。PC（1280×720）と iPhone（390×844）の画面と操作を再現し、ゲーム用のファイルは手元から読みます。

## 公開のしかた

公開するときは、試遊版の HTML と、同じコミットの `assets/`、`data/`、`vendor/` を参照できる状態にします。`<commit>` には試遊版の HTML を含む公開対象のコミット ID を入れます。three.js はページを開いたブラウザが CDN から読み込みます。

```text
https://rawcdn.githack.com/alphalpha722514/REWILDED-EIHEIJI/<commit>/previews/p3e3-farm/index.html
```
