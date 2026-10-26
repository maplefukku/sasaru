---
name: sasaru-spread-open
description: "Apply when writing why a short gets watched, and only the opening slice. Say what the first three seconds claim, whether the end-state word is already on screen, and whether the opening is a how-to. A how-to opening fails this flow. Write spread.open and label it an inference. Do not invent a view count, copy a source sentence, or add a CLI."
disable-model-invocation: true
---

# sasaru-spread-open

再生される理由の、冒頭の一切れ。最初の三秒だけを読む。コメント、共有、再生数は、このスキルの出力に書かない。

## Start

todo をこの順に開く。

1. 最初の三秒が何を主張しているか
2. 終状態の語がすでに画面にあるか
3. 冒頭がハウツーか

終状態の語は、この動画が行き着くものの名前である。名前を決めるために結末を見てよい。書くのは、その語が最初の三秒の画面に既にあるかどうかである。画面に出ている文は写さない。

## Phase A: 最初の三秒の主張

最初の三秒が、見る人に何を渡しているかを言葉にする。型が先に置いた約束として書く。画面の文、ナレーションの文、タイトルの文は写さない。

## Phase B: 終状態の語

終状態の語が、最初の三秒の画面に既にあるかを書く。あるときは、それが到達点の名前であることを書く。語そのものは写さない。無いときは、到達点の名前が先に渡されていない、と書く。

## Phase C: ハウツーなら不合格

冒頭が手順の始め（何かをする順番、作り方、使い方）なら、この流れは不合格である。完成の名前を先に置く流れと、作り方から入る流れは別で、後者は `spread.open` を合格にしない。不合格でも読みは書き、`howTo` を真にする。

## Outputs

`spread.open` だけを書く。出どころは推論である。`basis` は `inferred` と書く。再生数、再生回数、割合、いいねの数は書かない。参照の文は写さない。スクリプトもコマンドも足さない。

- `claim`。最初の三秒が渡す主張。
- `endStateWordOnScreen`。終状態の語がすでに画面にあるか。
- `howTo`。冒頭がハウツーか。真ならこの流れは不合格。
- `basis`。`inferred`。
