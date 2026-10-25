---
name: sasaru-gate
description: "Check a playbook file against the schema, the template, and the source wording, or check a finished cut against its playbook, and return pass, fail, or unmeasured per column. Use only when the sasaru router routes a gate."
disable-model-invocation: true
---

# sasaru-gate

gate は測って報告するだけで、直さない。欄ごとに合格、不合格、未計測のどれかを返す。未計測の欄が一つでも残れば、全体は合格にしない（**sasaru-principle-measure-or-label**）。

合否の線は playbook の欄から読む。ゲート全体で使う測り方の定義と許容幅は `lines.json` にあり、出典は同じファイルの `sources` に書いてある。一回だけ測った値を、そこに定数として足さない。許容幅を変えるのは、複数のファイルで測ったときだけで、理由を `sources` に書く。

スクリプトはこのファイルから見て `scripts/` にある。どれも PEP 723 のヘッダーを持ち、`uv run --script` で動く。ネットワークに出るのは、無料の検出モデルを初回に取りに行くときだけで、有料の API は呼ばない。モデルは `$SASARU_CACHE`（既定は `~/.cache/sasaru`）に置く。終了コードは 0 が合格、2 が入力の誤り、3 が不合格か未計測あり。

## Start

渡されたものを見て、検査を一つ選ぶ。

- playbook のファイル → playbook 検査。
- `sasaru/cuts/<cut-id>/`（書き出した動画と `cut.json`）→ カット検査。カット検査は最初に playbook 検査も走らせる。
- 動画だけで `cut.json` が無い → 止まる。make に `cut.json` を書かせてから来る。

## Phase 1: playbook 検査

```bash
uv run --script scripts/validate_playbook.py sasaru/playbooks/<id>.md --work sasaru/work/<id>
```

見るもの。

- フロントマターがスキーマに合格する。YAML の日付（`ingestedAt`、`asOf`）は文字列に直してから検証する。
- 本文の `##` 見出しがテンプレートと同じ順で全部ある。`## 制作ルート` の下の `###` が `routes` と同じ順。
- `id` とファイル名が一致する。ビートが重ならない。`at.beat`、`camera.moves[].beat`、層の `beats` が実在するビートを指す。
- `evidence` のパスが実在する（層は `captions.<層id>.<欄>`）。一つのパスを二つの組に入れない。`measured` の欄は null でない。null の `capHeightRatio`、`minHoldSec` は `unmeasured` に載っている。
- 文言検査。`source-text.json` の文字列と playbook のファイル全体（フロントマターの自由文字列も）を突き合わせる。CJK は 6 文字、ラテン文字は 3 語が続けて一致したら不合格。`source.kind: ingested` で `source-text.json` が無ければ不合格。`--work` が無いときは `playbooks/../work/<id>/` を探す。

## Phase 2: カット検査

```bash
uv run --script scripts/check_cut.py sasaru/cuts/<cut-id> [--reference-audio <ref.wav>] [--fetch-models] [--out sasaru/cuts/<cut-id>/gate.json]
```

playbook は `cut.json` の `playbookPath`、`$SASARU_HOME/playbooks/`、`sasaru/playbooks/`、同梱の `playbooks/` の順に探す。`--playbook` で直接渡してもよい。ビートの秒は、カットの尺を `format.durationSec.reference` で割った比で伸び縮みさせて読む。

測る欄。

| 欄 | 測り方 | 線 |
| --- | --- | --- |
| `format.*` | ffprobe と、全フレームの枚数 | 縦横比、fps、尺の帯 |
| `beats.boundaries` | テロップのカードの切り替わりとハードカット | 最短のビートの半分以内に、各ビートの終わりがある |
| `camera.transitions` | HSV のフレーム差 | 急な切り替えが書いた秒にだけある。フェードは見ない |
| `captions.<層>.capHeightRatio`、`headlineFloor` | 層の色と縁の色に合う画素の行の箱。各カードの安定したフレームを原寸で測る | playbook の値（`cut.json` の逸脱があればその値）。`headline` は 0.04 以上 |
| `captions.<層>.emphasis`、`position.*`、`safeArea`、`linesMax` | 同じ箱 | 倍率、cx、cy、揃え、`format.safeArea`、同時の段数 |
| `captions.<層>.show`、`hide`、`minHoldSec`、`lastCard` | カードの出た秒と消えた秒、声の頭と終わり | 層の規則。最後のカードは層の最後のビートの終わりまで残る |
| `captions.<層>.motionIn`、`motionOut`、`stroke`、`color` | 出入りのフレームの変化、箱の外側の暗い帯、芯の色 | 層の値。縁の外も暗い画は縁を区別できないので未計測 |
| `audio.voice`、`audio.midPhraseHoles`、`audio.closing` | 乾いた声（`cut.json` の voice、無ければミックス）の RMS | 声の有無。一枚のカードの中の 0.15 秒以上の穴は、その句に読点か空白があるときだけ許す。結びのモーラの窓が発話線を超え、声が終端の前に終わる |
| `audio.bgm.*` | ミックスの、発話から離れた間の音量 | 有無、声より下、`levelDbUnderVoice`、入りの秒 |
| `cut.audio.*` | `cut.json` の音源ファイルに時間で変わる利得をかけてミックスを再現した割合。参照の音との窓ごとの相関 | 音源のライセンスと `referenceAudioUsed: false`。再現が 0.9 以上。参照との相関が 0.3 以下 |
| `cut.route`、`cut.container`、`cut.costUsd`、`cut.deviation.*` | `cut.json` | 既定でないルートは `routeRequestedByMaker: true` のときだけ。費用は無料ルートで 0、有料ルートで上限以内。逸脱には理由 |
| `people.face` | YuNet の検出だけ。誰の顔かは見ない | `format.onCamera` は顔を取らないので、検出されない。喋る人のルートで作ったカットだけ、検出される |
| `people.mouth` | `talking_gate.py`（MediaPipe の唇の開きと声の相関） | 喋る人のルートのときだけ動く任意の欄。相関 0.30 以上、ずれ 100 ms 以内、探索の端でない、発話中の開きが間より大きい |

見ない欄は結果の `notChecked` に理由と一緒に出る。カメラの動きとズーム（取り込みの `camera_motion.py` が測る）、効果音、`duckUnderVoice`、字形から読めない書体の分類と太さ（`cut.json` に書けば突き合わせる）。

喋る人のルートの口の計測は、MediaPipe が `libEGL.so.1` を要る。無ければ `people.mouth` は未計測で返る。

## Phase 3: 自己テスト

スクリプトを直したら、合成のカットで合格と不合格の両方が出ることを確かめる。

```bash
uv run --script scripts/selftest.py
```

## Outputs

カット検査は JSON を一つ返す。`verdict`（`pass`、`fail`、`unmeasured`）、`summary`、`failed`、`unmeasured`、欄ごとの `columns`（`status`、`measured`、`target`、`targetFrom`、`method`）、`notChecked`。`--out` で `sasaru/cuts/<cut-id>/gate.json` に書く。映像と音はコミットしない。

`cut.json` は make が書く制作記録で、gate は次の鍵を読む。

```json
{
  "schema": "sasaru-cut/1",
  "playbook": "<id>",
  "playbookPath": "../../playbooks/<id>.md",
  "video": "cut.mp4",
  "route": "caption-over-footage",
  "routeRequestedByMaker": false,
  "container": "ffmpeg-ass",
  "stretch": 1.0,
  "costUsd": 0,
  "cards": [{ "layer": "c1", "start": 0.48, "end": 1.74, "text": "自分の句" }],
  "captionStyle": { "c1": { "fontFamily": "Noto Sans JP", "fontClass": "extra-bold-gothic", "weight": 900, "shadow": true, "plate": "none" } },
  "audio": {
    "sources": [{ "role": "voice", "path": "voice.wav", "license": "own", "atSec": 0, "inSec": 0 }],
    "referenceAudioUsed": false
  },
  "lastMora": { "tIn": 7.62, "tOut": 7.7 },
  "deviations": [{ "path": "captions.c1.capHeightRatio", "from": 0.02, "to": 0.057, "reason": "見出しの帯へ上げた" }]
}
```

返事は合否を先に書く。不合格の欄と未計測の欄を、測った値と線と一緒に並べる。結果ファイルのパスを付ける。
