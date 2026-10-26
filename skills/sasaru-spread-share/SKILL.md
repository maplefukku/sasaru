---
name: sasaru-spread-share
description: "Apply when writing why a viewer sends a short, and only the share slice. Name the object or sentence a sender can point at, who they would send it to, and why a middle step with no name fails as a share. Write spread.share and label it an inference. Do not invent a share count, copy a source sentence, or add a CLI."
disable-model-invocation: true
---

# sasaru-spread-share

人が動画を送る理由の、共有の一切れ。指させる物、送る相手、名前の無い途中だけを読む。再生とコメントは、このスキルの出力に書かない。

ルーターは四つの役を振る。このファイルは振らない。スキーマ、ルーター、テンプレート、他のスキルは変えない。

## Start

todo をこの順に開く。

1. 送る人が指させる物か文
2. 誰に送るか
3. 名前の無い途中が共有にならない理由

指させる文は、役割で書く。画面の文、ナレーションの文、タイトルの文は写さない。数は測っていない。出どころは推論で、`basis` は `inferred` である。

## Phase A: 指させる物

送る人が相手に「これ」と渡せる物、またはその文の役割を一つ書く。それは、変化のあとで像になる到達である。途中の部品の名前は、到達の名前ではない。参照の文そのものは書かない。指させるものが無ければ、共有としては書けない。数で埋め合わせない。

## Phase B: 誰に送るか

その到達を、まだ持っていない誰に送るかを書く。属性で書く。アカウント名や作者名は書かない。送る人は、その到達を相手より先に持っている。

## Phase C: 名前の無い途中

途中の段階に名前が無いとき、それが共有にならない理由を書く。到達がまだ像になっていないので、相手に渡せるものがない。指させる物が無い段階は、送る文にならない。

## Outputs

`spread.share` だけを書く。出どころは推論である。`basis` は `inferred` と書く。シェアした回数、割合、再生数は書かない。参照の文は写さない。スクリプトもコマンドも足さない。

- `pointAt`。送る人が指させる物、または文の役割。
- `recipient`。誰に送るか。
- `unnamedMiddle`。名前の無い途中が共有にならない理由。
- `basis`。`inferred`。
