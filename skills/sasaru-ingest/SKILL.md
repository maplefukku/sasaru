---
name: sasaru-ingest
description: "Read one local reference short and write one new playbook file that describes its format. Use only when the sasaru router routes an ingest."
disable-model-invocation: true
---

# sasaru-ingest

手元の動画ファイル一本から、型の playbook を一本書く。数はスクリプトが測り、判断はエージェントが書く。形は `../sasaru/SKILL.md` の「役の形」に従う。出力は `../../schema/playbook.schema.json` に合格し、`../../templates/playbook.md` の見出しを同じ順で全部持つ。

このファイルのあるディレクトリを `<skill>` と書く。スクリプトは `<skill>/scripts/` にあり、どれも `uv run --script` で自立して動く。システムには `uv`、`ffmpeg`、`ffprobe` が要る。

## Start

todo を Phase ごとに一つずつ開く。

1. 受け取る
2. 測る
3. 読む
4. 文言を残す
5. 埋める
6. 検査して置く

## Phase A: 受け取る

- 入力は利用者が手元に保存した動画ファイル一本と、権利 tier（A 自分の作品、B 許諾あり、C 第三者の公開物で解析だけ）。tier を言われなければ聞く。URL だけなら取得せず、保存したファイルを頼む。
- `id` を決める。型を言う kebab-case にする（例 `dark-room-command-cards`）。作者名、アカウント名、元の題、動画の ID を入れない。
- tier C は、外部のモデルやサービスへ送らない。ローカルの Whisper は送らないので使ってよい。

## Phase B: 測る

一行で下処理から下書きまで回る。

```bash
uv run --script <skill>/scripts/ingest.py <video> --id <id> --tier <A|B|C> [--platform instagram-reels|tiktok|youtube-shorts|other] [--language ja]
```

- 置き場所は `--home`、`$SASARU_HOME`、`./sasaru` の順。生成物はすべて `<home>/work/<id>/` に入る。`work/` はコミットしない。
- 順に `prep.py`（来歴、プローブ、カット、シート、キーフレーム、wav、オンセット、無音区間）、`caption_boxes.py`、`camera_motion.py`、`audio_events.py`、`people_voice.py`、`transcribe.py`、低確信のカットの `zoom.sh`、`draft_playbook.py`。最後に gate の `../sasaru-gate/scripts/validate_playbook.py` で下書きを検査する。
- 計測スクリプトがこのディレクトリに無ければ `missing`、失敗すれば `failed` と `ingest.json` に残し、その欄を仮置きにして進む。口の形は `<skill>/references/measurements.md`。
- 言語が分かっていれば `--language` を渡す。短い参照では自動判定が崩れることがある。`transcript.json` の `reliable` が偽なら、その文字起こしをビートにも声の判定にも使わない。

測った結果は `<home>/work/<id>/<id>.md`（下書き）、`ingest.json`（何が動いたか、`todo` に `未記入` の残る行の数）、`validate.json`（gate の検査の結果）。gate は `未記入` を見ないので、検査が通っても `todo` が 0 になるまでは下書きである。

## Phase C: 読む

- `sheets/sheet_NN.jpg` を全部見る。タイルの上の帯が元動画の秒。`keyframes/` は焼かない原本。
- 確信の低い秒だけ、一コマずつ読む。

```bash
bash <skill>/scripts/zoom.sh <home>/work/<id>/source.mp4 <start> <end> native <home>/work/<id>/zoom/<name>
```

- 焼かれる時刻は元動画の秒。テロップの出し方、トランジション、ズームの始まりをここで決める。
- 目で読んだ値は推論である。欄に入れたら、そのパスを `evidence.unmeasured` から `evidence.inferred` に移す（**sasaru-principle-measure-or-label**）。測った値を目の印象で上書きしない。

## Phase D: 文言を残す

- シートで読んだテロップの文を、`<home>/work/<id>/source-text.json` の `captions` に足す。一枚ずつ `{"tIn": 0.48, "tOut": 1.74, "text": "…", "from": "sheet"}`。`draft_playbook.py` を回し直しても `"from": "sheet"` の行は残る。
- テロップが無い参照なら `captions` を `[]` にする。gate の文言検査は、このファイルの中の文字列とだけ突き合わせる。読んでいないテロップは照合されない。
- 文字起こしは `transcribe.py` が `transcript` に入れる。声のある参照で `null` なら、`--language` を付けて `transcribe.py` を回す。

```bash
uv run --script <skill>/scripts/transcribe.py <home>/work/<id>/source.mp4 <home>/work/<id>/transcript.json --language <ja|en>
uv run --script <skill>/scripts/draft_playbook.py <home>/work/<id> --id <id>
```

- `source-text.json` と `transcript.json` は参照の文言である。playbook にも、コミットにも、返答にも写さない（**sasaru-principle-describe-the-form-not-the-work**）。

## Phase E: 埋める

下書きの `未記入` を全部書き換える。

- `name`、`summary`、`audience`（任意の欄。書けなければ消す）、`fitsContent`、`hook.type`、ビートの `role`、`purpose`、`swap`、本文の「なぜ伸びるか」「差し替える場所」。元の文言を言い換えて写さず、見る人にとっての役割で書く。「なぜ伸びるか」は推論と明記し、伸びない側に落ちない理由を分ける。判断は強いモデルに書かせる（ルーターの Subagents）。
- 仮置きの欄（`evidence.unmeasured` にあるもの）は、シートで読めたら推論として入れて `inferred` に移す。読めなければ値はそのまま、パスは `unmeasured` に残す。
- 喋る人の参照なら、`source.reference.onCamera: face`、`speech: on-camera` を書く（推論なら `inferred`）。作るカットの `format.onCamera` は `face` にせず、既定ルートは喋らないルートのままにする（**sasaru-principle-no-talking-head-by-default**）。失うもの（顔と口が作る視線の引き）を「なぜ伸びるか」に書く。
- テロップの大きさは測った値のまま書く。細い字でも引き上げない。引き上げは make が行う（**sasaru-principle-captions-read-as-headlines**）。
- ルートと費用を足すなら、有料のルートは `paidApi: true` と費用の帯と `asOf` を書く。金額は見積もりで確かめた値だけ（**sasaru-principle-quote-before-you-spend**）。
- 日付（`ingestedAt`、`asOf`）は引用符つきの文字列で書く。効果音のきっかけは `cue` で書く。

## Phase F: 検査して置く

playbook 検査は gate のスクリプトを使う。ingest は検査を持たない。

```bash
grep -n 未記入 <home>/work/<id>/<id>.md
uv run --script <skill>/../sasaru-gate/scripts/validate_playbook.py <home>/work/<id>/<id>.md --work <home>/work/<id>
```

- `grep` が何も出さず、検査の JSON が `"ok": true` になるまで Phase E に戻る。`warnings` も読み、直せるものは直す。直すのはエージェントで、検査は報告だけ。
- gate のスクリプトが無いときは、ingest を終えない。gate は未実装と返す。
- 合格したら `<home>/playbooks/<id>.md` に移す。移したあとも同じ検査が通る（`source-text.json` は `<home>/work/<id>/` から探す）。

```bash
mkdir -p <home>/playbooks && mv <home>/work/<id>/<id>.md <home>/playbooks/<id>.md
uv run --script <skill>/../sasaru-gate/scripts/validate_playbook.py <home>/playbooks/<id>.md
```

## Outputs

- `<home>/playbooks/<id>.md` 一本。フロントマターはスキーマに合格し、`status: measured`、`evidence` に測った、推論、未計測が分かれている。
- `<home>/work/<id>/` に下処理の生成物、`manifest.json`（tier、元ファイルの sha256、取り込み日、保持期限）、`source-text.json`。コミットしない。保持期限を過ぎたコピーは消す。
- 返答は、playbook のパス、検査の結果、`evidence.unmeasured` に残った欄、`ingest.json` で `missing` か `failed` だった計測。
