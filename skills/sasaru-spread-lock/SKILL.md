---
name: sasaru-spread-lock
description: "Apply when writing why a short gets watched, and only the impossible-lock slice. Say what normal method is blocked, the second that block appears, and why a straight what-if that starts with the first ordinary step fails this flow. Write spread.lock and label it an inference. Do not invent a view count, copy a source sentence, or add a CLI."
disable-model-invocation: true
---

# sasaru-spread-lock

再生される理由の、不可能なロックの一切れ。通常の手順が止められているところだけを読む。冒頭の主張、コメント、共有、再生数は、このスキルの出力に書かない。

## Start

todo をこの順に開く。

1. 通常の手順の、何が止められているか
2. その止まりが画面に出る秒
3. 最初の普通の一手から始まる直線の what-if が、この流れでは失敗する理由

通常の手順は、その物を作るとき最初に取る当たり前の一手である。画面の文は写さない。読むのは、その一手が始められないことと、それが画面に出た秒である。

## Phase A: 止められた通常の手順

通常の手順のうち、何が止められているかを書く。見る人が「普通はこう始める」と知っている一手が、画面の状態では始められない、と書く。画面の文、ナレーションの文、タイトルの文は写さない。

## Phase B: 止まりの秒

その止まりが、最初に画面へ出る秒を書く。秒は見た時刻である。測った再生数ではない。止まりより前の完成の主張や、止まりのあとの手順は、ここに書かない。

## Phase C: 直線の what-if は失敗する

最初の普通の一手から始まる直線の what-if（空の状態と、その最初の手順）は、この流れでは失敗する。その理由を書く。普通の一手を先に成功させて見せると、止まりが起きず、不可能なロックが立たない。この流れが成立するのは、通常の手順が止められた秒が先に見えるときである。

## Outputs

`spread.lock` だけを書く。出どころは推論である。`basis` は `inferred` と書く。再生数、再生回数、割合、いいねの数は書かない。参照の文は写さない。スクリプトもコマンドも足さない。

- `blockedMethod`。止められている通常の手順。
- `blockSecond`。その止まりが画面に出る秒。
- `straightWhatIfFails`。最初の普通の一手から始まる直線の what-if が、この流れでは失敗する理由。
- `basis`。`inferred`。
