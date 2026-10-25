---
name: sasaru-pick
description: "Choose one playbook from the library for the maker's content, constraints, and budget, with reasons, or return the missing information. Use only when the sasaru router routes a pick."
disable-model-invocation: true
---

# sasaru-pick

作る人のブリーフを受け取り、playbook ライブラリから型を 1 本、理由つきで選ぶ。選べないときは、足りない情報を返して止まる。

形は `../sasaru/SKILL.md` の「役の形」に従う。読むのは playbook のフロントマターだけ。本文、参照動画、作業フォルダは開かない。有料 API は呼ばない。

## ブリーフ

会話から次の欄を YAML に書き出す。分からない欄は書かない。推測で埋めない。

```yaml
content:
  kind: 勉強法のコツ            # 載せる自分のコンテンツの種類。fitsContent と照らす
  message: 25分で区切ると続く    # 一本で伝えたいこと
audience: 資格勉強中の社会人     # 誰に。理由の文に使う。絞り込みには使わない
durationSec: 12                 # 数か {min, max}
aspect: "9:16"                  # 9:16, 4:5, 1:1, 16:9
assets: [own-footage]           # 用意できる素材と使える生成。routes[].needs の語
budgetUsd: 0                    # 一本あたりの上限。省略は 0 として扱う
voice: [none, tts-voiceover]    # 許す声。省略は on-camera 以外の全部
allowTalkingHead: false         # 人がカメラに喋る型とルート。名指しで頼まれたときだけ true
allowFace: false                # 顔が映る型（format.onCamera: face）
tags: [study]                   # playbook の tags と同じ語なら少し加点
```

`content.kind` と `content.message` のどちらかは要る。

## 手順

1. ブリーフを一時ファイルに書く（作業フォルダの `sasaru/work/pick-brief.yaml` など。コミットしない）。
2. スクリプトを回す。ライブラリの既定は `./sasaru/playbooks/`、次にプラグインの `playbooks/`。同じ id は先の方を使う。

   ```bash
   uv run <このスキルの絶対パス>/scripts/pick.py --brief sasaru/work/pick-brief.yaml
   ```

   置き場所を変えるときは `--library <dir>` を重ねる。結果は JSON で標準出力に出る。
3. `status` で返し方を分ける（次節）。
4. `picked` なら、`candidates` の上位 3 本の `name` と `matchedFitsContent` を見て、内容の合い方を確かめる。文字の重なりで測った一致なので、意味がずれていれば次点に替えてよい。替えたら、替えた理由を一文で添える。

## 返し方

| status | 返すもの |
| --- | --- |
| `picked` | 選んだ型の id とファイル、制作ルート（id、器、要るもの、一本の費用と根拠）、`reasons` を日本語の短い文で。`unspecified` の欄は「決めると絞り直せる」と添える。`betterIfAnswered` があれば、答えるともっと合う型が開くことを一文で聞く |
| `need-info` | `missing` の欄を問いにして聞く。`unlocks` から、答えるとどの型のどのルートが開くかを添える |
| `no-fit` | 条件に合う型の `fitsContent` を見せ、内容をその言葉で言い直すか、合う参照動画を sasaru-ingest で取り込むかを聞く |
| `no-match` | `excluded` の止まった理由を型ごとに一行で見せ、どの条件を緩めれば開くかを聞く |
| `empty-library` | playbook が無いことと、sasaru-ingest で一本取り込む道を返す |
| `bad-brief` | ブリーフのどの欄が読めなかったかを返し、聞き直す |

`skipped` に載った playbook は、スキーマに通らなかったので選んでいない。数が 1 以上なら、sasaru-gate で直す道を一行添える。

## スクリプトが決めること

- 人がカメラに喋る型（`format.speech` か `audio.voice` が `on-camera`）と、顔が映る型は、既定で外す。喋る人のルート（`r2v-talking`、`talkingHead: true`）は、`allowTalkingHead: true` のときだけ、既定ルートが止まった場合の代わりとして選ばれうる。`../sasaru-principle-no-talking-head-by-default/SKILL.md`。
- ルートは playbook の既定ルートを先に試す。素材、予算、喋る人の条件で止まれば、同じ playbook の他のルートを、状態（tested、written、design-only の順）と費用の安い順に試す。代わりのルートを選んだら、理由にそう書く。
- 費用は `routes[].costUsdPerVideo.max` が `budgetUsd` 以下のルートだけ通す。数は playbook の欄から読み、足したり見積もったりしない。有料のルートを選んだら、作る前に `../sasaru-principle-quote-before-you-spend/SKILL.md` に従う。
- 並べる順は、内容の一致、playbook の状態（produced、measured、draft の順）、ルートの状態、費用、希望の尺との近さ、測った欄の数。
- 内容の一致が 0.3 未満の型は選ばない。当て推量で選ぶより聞き返す。

## 試す

```bash
uv run skills/sasaru-pick/tests/test_pick.py
```

`tests/fixtures/` の playbook はテスト用で、ライブラリではない。
