---
name: sasaru-pick
description: "Choose one playbook from the library for the maker's content, constraints, and budget, with reasons, or return the missing information. Use only when the sasaru router routes a pick."
disable-model-invocation: true
---

# sasaru-pick

作る人のブリーフを受け取り、playbook ライブラリから型を 1 本、理由つきで選ぶ。選べないときは、足りない情報を返して止まる。

読むのは playbook のフロントマターだけ。本文、参照動画、`work/` は開かない。有料 API は呼ばない。

## Start

1. ルーター `../sasaru/SKILL.md` を読んでいなければ、全文読む。
2. 会話から次の欄を YAML に書き出す。分からない欄は書かない。推測で埋めない。

   ```yaml
   content:
     kind: 勉強法のコツ            # 載せる自分のコンテンツの種類。fitsContent と照らす
     message: 25分で区切ると続く    # 一本で伝えたいこと
   audience: 資格勉強中の社会人     # 誰に。playbook の audience と照らし、内容の一致が並んだときの順に使う
   playbook: some-format-id        # 型を名指しされたときだけ。その一本だけを照らす
   durationSec: 12                 # 数か {min, max}
   aspect: "9:16"                  # 9:16, 4:5, 1:1, 16:9
   assets: [own-footage]           # 用意できる素材と使える生成。routes[].needs の語
   budgetUsd: 0                    # 一本あたりの上限。省略は 0 として扱う
   voice: [none, tts-voiceover]    # 許す声。省略は none, tts-voiceover, own-voiceover の全部
   allowTalkingHead: false         # 人がカメラに喋る型とルート。名指しで頼まれたときだけ true
   tags: [study]                   # playbook の tags と同じ語なら少し加点
   ```

   `playbook` が無いときは、`content.kind` か `content.message` のどちらかが要る。
3. 「この動画みたいに作って」の流れで ingest から来たときは、いま取り込んだ playbook の id を `playbook` に書く。

## Phase 1: 絞る

ブリーフを作業フォルダの `sasaru/work/pick-brief.yaml`（`SASARU_HOME` があればその下の `work/`）に書き、スクリプトを回す。

```bash
uv run --script <このスキルの絶対パス>/scripts/pick.py --brief sasaru/work/pick-brief.yaml
```

ライブラリは `$SASARU_HOME/playbooks/`（無ければ `./sasaru/playbooks/`）、次にプラグインの `playbooks/` を読む。同じ id は先の方を使う。置き場所を変えるときは `--library <dir>` を重ねる。結果は JSON で標準出力に出る。終了コードは 0（結果あり）か 2（ブリーフが読めない）。

スクリプトが決めること。

- 参照が人がカメラに喋る型（`source.reference.speech: on-camera`）は外す。`allowTalkingHead: true` か、`playbook` で名指しされたときだけ照らす。喋る人のルート（`talkingHead: true`、`r2v-talking`）は `allowTalkingHead: true` のときだけ通す（**sasaru-principle-no-talking-head-by-default**）。
- ルートは既定ルートを先に試す。素材、予算、喋る人の条件で止まれば、同じ playbook の他のルートを、状態（tested、written、design-only の順）と費用の安い順に試す。
- 費用は `routes[].costUsdPerVideo.max` が `budgetUsd` 以下のルートだけ通す。数は playbook の欄から読み、足したり見積もったりしない。
- 並べる順は、内容の一致、audience の一致（playbook に `audience` が無ければ 0）、playbook の状態（produced、measured、draft の順）、ルートの状態、費用、希望の尺との近さ、測った欄の数。
- 内容の一致が 0.3 未満の型は選ばない（名指しのときを除く）。当て推量で選ぶより聞き返す。
- 各 playbook を候補にする前に、道具 `check-product-placement` の `check_placement` を読む。不合格の型は `skipped` に載せ、選ばない。選んだ型の `productPlacement` を結果に出す。`{"slot": false}` は置き場が無いことで、エンドカードも説明動画も足さない。役割と直接さが書いてあるときも、その言葉のとおりで、書いていないエンドカードは足さない。
- 同じ位置で、道具 `check-spread-psychology` の `check_spread` を読む。不合格の型は `skipped` に載せ、選ばない。選んだ型の `spreadPsychology` を結果に出す。`payoff` がある型で欄が無いもの、`null`、再生数の主張は選ばない。`{"watchToEnd": false}` は最後まで見ることが仕事ではない型で、再生数の主張ではない。
- ブリーフの `content.kind` か `content.message` の主題が商品の説明なら、型を選ばずに `refused` を返す。

## Phase 2: 確かめる

`status` が `picked` なら、`candidates`（最大 3 本）の `name` と `matchedFitsContent` を見て、内容の合い方を確かめる。一致は文字の重なりで測っているので、意味がずれていれば次点に替えてよい。替えたら、替えた理由を一文で添える。名指しのときは替えない。

選んだルートが有料（`paidApi: true`）なら、作る前に **sasaru-principle-quote-before-you-spend** に従うと添える。費用の時点 `asOf` も見せる。

## Tools

### check-product-placement

ルーターの Tools と同じ道具。pick は選ぶ前に必ず読む。

- 名前: `check-product-placement`
- いつ: ライブラリの各 playbook を候補にする前。ブリーフの主題を読むとき。
- 引数:
  - `playbook`: その型のフロントマター
  - `content`: 渡さない。主題はブリーフの `content.kind` と `content.message`
- 入口: `../sasaru-gate/scripts/check_placement.py` の `check_placement`。`scripts/pick.py` が呼ぶ
- 戻り: `productPlacement`。置き場が無い型は `{"slot": false}`。説明動画と、書いていないエンドカードにはしない

### check-spread-psychology

ルーターの Tools と同じ道具。pick は選ぶ前に必ず読む。

- 名前: `check-spread-psychology`
- いつ: ライブラリの各 playbook を候補にする前。`check-product-placement` の直後。
- 引数:
  - `playbook`: その型のフロントマター
- 入口: `../sasaru-gate/scripts/check_spread.py` の `check_spread`。`scripts/pick.py` が呼ぶ
- 戻り: `spreadPsychology`。`payoff` が無い型で欄を省いたときは `{"watchToEnd": false}`。再生、コメント、共有は別の心理で、推論であり、再生数ではない

## Outputs

`status` ごとに返す。

| status | 返すもの |
| --- | --- |
| `picked` | 選んだ型の id とファイル、ルート（id、既定か、器、要るもの、一本の費用と根拠と時点）、`reasons` を短い文で。`unspecified` の欄は「決めると絞り直せる」と添える。`betterIfAnswered` があれば、答えるともっと合う型が開くことを一文で聞く |
| `need-info` | `missing` の欄を問いにして聞く。`unlocks` があれば、答えるとどの型のどのルートが開くかを添える |
| `no-fit` | 条件に合う型の `fitsContent` を見せ、内容をその言葉で言い直すか、合う参照動画を sasaru-ingest で取り込むかを聞く |
| `no-match` | `excluded` の止まった理由を型ごとに一行で見せ、どの条件を緩めれば開くかを聞く |
| `empty-library` | playbook が無いことと、sasaru-ingest で一本取り込む道を返す |
| `bad-brief` | ブリーフのどの欄が読めなかったかを返し、聞き直す |
| `refused` | ブリーフの主題が商品の説明だった。世界の出来事に言い直すよう聞く。型は選ばない |

`skipped` に載った playbook は、スキーマか商品の置き場に通らなかったので選んでいない。1 本以上あれば、sasaru-gate で確かめる道を一行添える。

make に渡すのは、選んだ playbook のファイルパス、ルートの id、読んだ `productPlacement`。

テストは `uv run --script skills/sasaru-pick/tests/test_pick.py`。`tests/fixtures/` の playbook はテスト用で、ライブラリではない。
