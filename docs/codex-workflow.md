# Claude Code から Codex CLI に作業を任せる

Claude Code が仕様と指示を作り、差分とテスト結果をレビューして最終判定する。Codex は使い捨ての作業フォルダで実装と単体テストを担当する。ゲーム本体と `main` は触らない。GitHub への保存が必要なら、レビューのあとに別の承認を受け、Claude Code が別の操作として行う。このツールは commit・push を行わない。

## 新しいセッションの準備

Linux の `/proc` と、標準ライブラリの tar 抽出フィルターを備えた Python 3（3.12 以降を推奨）が必要。Codex CLI 0.172.0、Node.js、Git、ブラウザーテストを行う場合は Playwright と `/opt/pw-browsers` を確認する。

`check` は Node.js で `/opt/node-tools` の Playwright を解決できるかを確認する。Playwright またはブラウザーのディレクトリがなければ、環境の管理者に準備を依頼する。この環境では Playwright の再インストールや `playwright install` は行わない。

コマンドでできる準備は、必要なものだけを実施する。

- `npm install -g @openai/codex@0.172.0` で確認済みの CLI を入れる。
- リポジトリの外にある作業メモ用フォルダで `npm pack three@0.128.0` を実行する。取得した `three-0.128.0.tgz` を同じ場所で展開し、`export THREE_JS="/絶対パス/package/build/three.min.js"` を設定する。確認時に `--three` でそのファイルを指定してもよい。
- 必要なら人が許可したブランチを `git fetch origin <ブランチ>` で取り、取り出すコミットを確認する。

認証は人が行う。`codex login --device-auth` を実行し、表示されたコードをデバイス認証ページで入力する。ChatGPT の設定で Codex のデバイスコード認証を有効にする必要がある場合がある。認証の保存方法は変えず、認証ファイルを JOB にコピーしない。[Codex デバイス認証](https://auth.openai.com/codex/device)

## ふだんの流れ

以下はリポジトリのルートから実行する例。既存のリポジトリ外の親フォルダを選び、まだ存在しない JOB を指定する。`REF` にはレビュー対象として定めたコミット、プロンプトには仕様・作業範囲・実行する単体テストを書く。

```sh
JOB=/絶対パス/作業メモ/job-001
REF='対象コミットのハッシュ'
PROMPT=/絶対パス/作業メモ/task.md

python3 tools/codex-delegate.py check --repo .
python3 tools/codex-delegate.py prepare --repo . --ref "$REF" --job "$JOB"
python3 tools/codex-delegate.py sandbox-check --job "$JOB" --mode rw
python3 tools/codex-delegate.py run --job "$JOB" --mode rw --prompt "$PROMPT"
python3 tools/codex-delegate.py test --job "$JOB" --name unit --sandbox -- python3 tests/codex-delegate-unit.py
python3 tools/codex-delegate.py report --job "$JOB"
python3 tools/codex-delegate.py diff --job "$JOB"
```

1. `check` は前提条件を表示する。`--branch <ブランチ>` を指定した場合に限り、`--repo` の `origin` に `git ls-remote` で問い合わせる。
2. `prepare` は指定コミットを `git archive` で `JOB/work` と比較用の `JOB/base` に展開し、初期ハッシュを `files.json` に記録する。既存 JOB は再利用せず、新しい JOB 名を指定する。
3. `sandbox-check` では作業領域の読み書き、作業領域外と認証ファイルの不可視性、通信の遮断、秘密環境変数の除外を確かめる。試験ファイルがホスト側の JOB 直下や元リポジトリに残った場合は削除して失敗とする。`JOB/watch` の内容、mtime、atime に変化があった場合も失敗とする。砂場の中だけで消えた書き込みは JSON の `sandbox_only_writes` に記録する。成功後に `run` へ進む。
4. `run` は毎回同じ事前確認を行う。`ro` は調査用、`rw` は編集用。必要に応じて `--model`（既定値 `gpt-6.2-sol`）、`--max-runs`（既定値 4）、`--timeout`（既定値 600 秒）を指定する。事前確認で中止した回も試行回数に含む。
5. `test` は `JOB/work` で実行する。`--sandbox` では作業フォルダを読み書きできる。砂場の外で実行するのはレビュー済みのコードだけとする。テストにも `--timeout` を指定できる。
6. `report` で成否、安全確認、変更、使用量を確認する。全件の集計は `JOB/report.json`、各実行の詳細は `JOB/runs/<番号>/` と `JOB/tests/` にある。`diff --file <相対パス>` で確認するファイルを絞れる。Claude Code が差分と記録をレビューし、最終判定したあと、GitHub への保存には別の承認を得る。

## 運用の決まり（2026-11-25 ユーザー決定）

1. 実装の委任は、1つの作業につき最大4回とする。ツールの既定値は `--max-runs 4`。
2. 読み取り専用の調査（`--mode ro`）は、運用上の実装回数に含めない。
3. 調査は原則3回程度を目安に、実装とは別の JOB で行う。ツールは JOB ごとに `ro` と `rw` を合算するため、同じ JOB で調査すると実装に使える回数が減る。1つの作業の実装は1つの JOB で数え、回数の上限を逃れるために JOB を作り直さない。新しい実装用 JOB は、ユーザーが新しい作業として認めたときだけ作る。
4. 同じ原因で2回続けて失敗したら止めて、原因・結果・必要な対応をユーザーに報告する。権限を緩めたり、実行回数を足して続けたりしない。
5. 小さなコード修正も、原則として Codex に任せる。
6. Claude Code は作業の選定、仕様と設計、作業の分割、Codex への指示、差分レビュー、ブラウザーのテスト、画面と音の確認、セーブ互換の確認、ユーザーが承認した GitHub 操作、最終判断と報告を担当する。スクリプトの実行、テストの開始、git 操作、確認済みの成果物の保存など、手順が決まっている作業も Claude Code が行う。
7. 4回は上限とし、作業が完了したら追加で実行しない。
8. アイテム・報酬・台詞・物語などの未確定の仕様は、Codex が推測で作らず、Claude Code がユーザーに決めてもらう。

## 安全の決まり

- JOB はリポジトリ外に置く。Codex には GitHub の操作をさせず、作業は `JOB/work` に限定する。実行は `--ephemeral --ignore-user-config --skip-git-repo-check` と一時権限設定を使い、承認は `never`、シェル環境の継承は `core` とする。`--sandbox` を `codex exec` に重ねない。
- 基本の読み取り範囲は `:minimal`、Codex の vendor ディレクトリ、`/opt/node22` と作業フォルダ。`--read` は必要な場所だけ指定する。パスは実体に解決し、認証領域やその親、元リポジトリや JOB と重なる許可は拒否する。`/proc`、`/sys`、`/dev` への追加許可も拒否する。`~/.codex` と `/root/.codex` は拒否する。
- 環境変数は名前を大文字小文字の区別なく検査する。`token|key|secret|pass|askpass|aws_|cloudsdk_auth|_auth` に当たる値は取得せず、起動環境から外す。許可名は `MAX_THINKING_TOKENS`、`BUN_TLS_EXTRA_DISTRUSTED_KEYS`、`CCR_AUTO_MODE_USER_ENV_KEYS_FACT`、`AWS_CA_BUNDLE`。砂場のコマンドに渡す値は `--env NODE_PATH=/絶対パス` のように指定する。秘密を示す名前や `sk-`、`ghp_`、`github_pat_`、`eyJ`、`AKIA` などで始まる値は拒否する。プロンプトやテスト引数にも秘密を入れない。
- Codex の回答は `JOB/runs/<番号>/.answer.raw`（所有者だけが読み書きできる通常のファイル。フォルダも所有者だけ）に書かせる。シンボリックリンクをたどらずに読み、通常のファイルで別名（ハードリンク）が無いことを確かめ、秘密らしい文字列を伏せて `answer.txt` に残した後、成功・失敗にかかわらず `.answer.raw` を消す。実行の記録（JSON の出来事の記録・標準エラー）は伏せた後の形だけを所有者限定のファイルに残す。未加工の回答や記録は、チャット・GitHub・公開する成果物に含めない。
- `/proc` から子プロセスを定期観測し、マウント名前空間、秘密に当たる環境変数の名前の個数、伏せ字を施したコマンドを記録する。実行後は `JOB/watch` の atime が 2020-01-01 のままか調べ、回答・記録・差分で検出したダミーと秘密らしい文字列を数えて伏せる。検出は既知の形式が対象で、短命のプロセスを取りこぼす可能性がある。`codex-code-mode-host`、`lsb_release`、最初のシェルの準備など、砂場の外で動く処理は観測できても内部動作までは確かめられない。
- 事前確認や実行後の安全確認が失敗したら、記録をレビューして原因を調べる。

## 運用上の注意

- 実行中・実行後の JOB フォルダ全体を `grep -r` などで一括検索しない。ホスト側から読んでも `JOB/watch` の atime が変わり、安全確認が FAIL になる。2026-11-25 には Claude Code のホスト側での一括検索が原因で実際に発生した。調査には `report`・`diff` を使うか、`JOB/work`・`JOB/runs` だけを指定して読む。安全確認の条件は維持する。
- 2026-11-25 には、Codex が `index.html` の末尾に元のファイルに無い改行を付ける事例が3つの作業で発生した。`index.html` を変更する指示には「最後は `</body></html>` で、その後に改行は無い。末尾に改行を足さない」と毎回書き、レビューで `tail -c 14 index.html` を確認する。
- Codex の砂場内では Chromium を起動できないことがある（「Chromium と Playwright」参照）。Claude Code がレビュー後に砂場の外でブラウザーのテストを実行し、失敗した行や測定値を次の指示で Codex に伝える。

## Chromium と Playwright

2026-11-24 の確認では、Codex の砂場内で Chromium を起動できなかった。`content/browser/sandbox_host_linux.cc:41` の `shutdown()` が `Operation not permitted` となり、`--no-sandbox`、`--no-zygote`、`--single-process` でも解消しなかった。ブラウザーテストは Claude Code がコードをレビューしたあと、`test` に `--sandbox` を付けずに実行する。

## 使用量の測り方

Codex 分は `report` のトークン合計を記録する。内訳は各 Run の `report.json` にあり、`exec.jsonl` の `turn.completed` に含まれる usage を集計している。Claude Code 分は作業の前後に Claude Code の `/cost` または使用量画面を記録し、差を取る。

同じ種類・規模の仕事を「Claude Code だけ」と「Codex と併用」で行う。両方の使用量と `JOB/report.md` の文字数（UTF-8 ロケールの `wc -m`）を同じ表に控える。

| 作業・条件 | Claude Code 作業前 | Claude Code 作業後 | Claude Code 差分 | Codex 入力／キャッシュ済み入力／出力 | report 文字数 |
| --- | --- | --- | --- | --- | --- |
| 作業 A・Claude Code だけ | | | | — | — |
| 作業 A と同種・Codex と併用 | | | | | |
