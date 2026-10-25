# 計測スクリプトの口

`ingest.py` が呼び、`draft_playbook.py` が読む形。四つの計測スクリプトは、この形の JSON を `<work_dir>` に書けば下書きに入る。スクリプトが無い、失敗した、欄が無いときは、対応する欄を仮置きにして `evidence.unmeasured` に名前を残す。

共通。PEP 723 のヘッダーで `uv run --script` で動く。位置引数は `<video> <work_dir>`。`--json` で同じものを標準出力に出し、人向けのログは標準エラーに出す。終了コードは 0 成功、2 入力の誤り。秒はすべて参照の尺の上の秒、座標と大きさは画面の幅と高さに対する比。文言は持たない（OCR だけが例外で、別ファイルに分ける）。

## caption_boxes.py → `captions.json`

```text
caption_boxes.py <video> <work_dir> --json
```

```json
{
  "threshold": 220,
  "roi": null,
  "heightMethod": "row-profile",
  "firstFrameHasText": false,
  "cards": [
    { "layer": "c1", "tIn": 0.48, "tOut": 1.74, "cx": 0.5, "cy": 0.265, "w": 0.85,
      "capHeightRatio": 0.056, "lines": 1, "change": "fade", "changeOut": "cut" }
  ],
  "noCaption": [[0.0, 0.48]],
  "color": "#FFFFFF",
  "stroke": { "color": "#000000", "px1080": 8 },
  "shadow": true,
  "plate": "none",
  "writingMode": "horizontal"
}
```

| JSON | playbook |
| --- | --- |
| `cards[]` が空 | `captions: []`、テロップ無しを測った |
| `cards[].layer`（無ければ `c1`） | 層の `id`。層ごとにまとめる |
| `capHeightRatio` の中央値 | `captions.<id>.capHeightRatio`。最大 / 中央値が 1.15 以上なら `emphasis.scale` |
| `cx`、`cy` の中央値 | `position.cx`、`cy`。cx が 0.5 から 0.05 以内なら `align: center` |
| `lines` の最大 | `linesMax` |
| `change` の最頻値（`cut`、`pop`、`fade`、`slide-up`、`typewriter`、`word-by-word`、`scale-in`、`other`） | `motionIn` |
| `changeOut` の最頻値（`cut`、`fade`、`slide`、`other`） | `motionOut` |
| カードの長さの最小 | `minHoldSec` |
| 隣のカードとの隙間の中央値が 0.1 秒以下 | `hide: next-card`、それより長ければ `phrase-end` |
| 層の最後のカードが最終フレームまで残る | `lastCard: hold-to-end` |
| 発話の始まり（`audio.json` の `speech`）とカードの出る秒の差の中央値 | `show`、`leadSec` |
| `firstFrameHasText` | `hook.firstFrameHasText` |
| `color`、`stroke`、`shadow`、`plate`、`writingMode`、`unit`、`font`、`charsPerCard` | 同名の欄。無ければテンプレートの値で未計測 |
| `heightMethod`、`threshold`、`roi` | 本文の「テロップ」に書く |

`cards[].tIn` はビートの区切りにも使う（最優先）。

OCR をするなら、文言は `captions.ocr.json` に分ける。`{"cards": [{"tIn": 0.48, "tOut": 1.74, "text": "…"}]}`。`draft_playbook.py` はこれを `source-text.json` に写すだけで、playbook には入れない。

## camera_motion.py → `camera.json`

```text
camera_motion.py <video> <work_dir> [--mask-captions <work_dir>/captions.json] --json
```

```json
{
  "zoomEvents": [{ "tStart": 1.0, "tEnd": 1.5, "scaleFrom": 1.0, "scaleTo": 1.2, "easing": "easeOut" }],
  "transitions": [{ "t": 3.0, "type": "hard-cut" }],
  "moves": [{ "tIn": 0.0, "tOut": 3.0, "move": "handheld" }],
  "shake": { "txStd": 0.003, "tyStd": 0.002 }
}
```

| JSON | playbook |
| --- | --- |
| `zoomEvents[]`（`scaleTo` が無ければ `factor`。`easing` は `linear`、`easeIn`、`easeOut`、`easeInOut`、`punch` かスキーマの語） | `camera.zooms[]`。`at` は `tStart` を含むビートと、その頭からの秒 |
| `transitions[]`（`type` はスキーマの語だけ。他の語は捨てる） | `camera.transitions[]`。無ければ prep の確信の高いカットを `hard-cut` で入れる |
| `moves[]`（`move` はスキーマの語） | `camera.moves[]`。ビートごとに重なりの一番長い動き |
| `moves` が無く `shake` がある | 並進の標準偏差 / 画面幅が 0.004 を超えれば全ビート `handheld`、以下なら `static` |

## audio_events.py → `audio.json`

```text
audio_events.py <video> <work_dir> --json
```

```json
{
  "speech": [[0.43, 2.6], [3.09, 4.34]],
  "music": { "present": true, "tStart": 0.0, "bpm": 107.7, "bpmCandidates": [53.8, 107.7, 215.3],
             "ducksUnderSpeech": true, "levelDbUnderVoice": -14.0 },
  "sfxCandidates": [{ "t": 4.64, "labels": ["Whoosh"], "beatAligned": false }]
}
```

| JSON | playbook |
| --- | --- |
| `speech`（`[tIn, tOut]` か `{"tIn","tOut"}` の列） | テロップの `show` と `leadSec`。`transcribe.py --speech` が区間の外の文字起こしを捨てる |
| `music.present`、`tStart` | `audio.bgm.present`、`entersAt` |
| `music.bpm`、`bpmCandidates` | `audio.bgm.character` の言葉（推論の欄） |
| `music.ducksUnderSpeech`、`levelDbUnderVoice` | `audio.bgm.duckUnderVoice`、`levelDbUnderVoice` |
| `sfxCandidates[]` | `audio.sfx[]`。カードの出から 0.12 秒以内なら `cue: card-in`、カットなら `cut`、ズームなら `zoom`、`beatAligned` なら `beat-drop`、他は `other`。`type` は `labels[0]` |

音声ストリームが無い参照では呼ばない。

## people_voice.py → `people.json`

```text
people_voice.py <video> <work_dir> [--speech <work_dir>/audio.json] --json
```

```json
{ "onCamera": "face", "speech": "on-camera", "faceRate": 0.98 }
```

| JSON | playbook |
| --- | --- |
| `onCamera`（`none`、`hands`、`body-no-face`、`face`） | `source.reference.onCamera` |
| `speech`（`none`、`voiceover`、`on-camera`） | `source.reference.speech` |

参照の判定から、作るカットの欄を推論で決める。`face` は `format.onCamera: none`、声があれば `format.speech: voiceover` と `audio.voice: own-voiceover`。`source.reference.onCamera` が測れて `none` なら、既定ルートを `code-motion` にする。それ以外は `caption-over-footage`。

## 下書きが自分で使うもの

| ファイル | 書くスクリプト | 使い道 |
| --- | --- | --- |
| `manifest.json`、`shots.json`、`audio/onsets.json` | `prep.py` | 来歴、尺、fps、縦横比、カット、無音区間 |
| `transcript.json` | `transcribe.py` | `reliable` が真で区間が 2 つ以上なら、ビートの区切り（カードが無いとき）。`source-text.json` の `transcript` |
| `source-text.json` | `draft_playbook.py` | gate の文言検査。`captions` はシートの読み（`"from": "sheet"`）と OCR、`transcript` は文字起こし。読んでいない部分は `null` |

ビートの区切りは、カードの出る秒、文字起こしの区間の始まり、prep の無音区間の終わり、の順に最初に使えるものと、確信の高いカットを合わせて、0.6 秒より近い区切りを捨てて作る。
