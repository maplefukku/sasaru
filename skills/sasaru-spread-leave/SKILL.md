---
name: sasaru-spread-leave
description: "Apply when writing why a viewer leaves, and only that slice. Walk four steps: the first second the promise stalls, a repeated step, a word that does not name what is on screen, and an ending that does not match the opening claim. Write spread.leave and label it an inference. Do not invent a view count, copy a source sentence, or add a CLI."
disable-model-invocation: true
---

# sasaru-spread-leave

見る人が離れる理由の、一切れ。四つの時点だけを読む。再生、コメント、共有、再生数は、このスキルの出力に書かない。

## Start

todo をこの順に開く。

1. 最初の一秒で、約束が止まるか
2. 同じ手順が繰り返されるか
3. 言葉が、画面にあるものを名指ししないか
4. 終わりが、最初の主張と合わないか

画面の文、ナレーションの文、タイトルの文は写さない。読むのは、約束が止まったか、手順が同じ役割のままか、語が画面の物を指していないか、終わりが開きの主張と違うかである。

一覧にあってファイルが無い動画は、名前だけを残し、四つの時点は書かない。記憶でその動画を補わない。

## Phase A: 最初の一秒で約束が止まる

最初の一秒が、この先に何があるかを置いているかを見る。置く前に同じ絵が続く、または約束より前に説明が来るとき、約束は止まっている。止まっていれば、離れる機構を一文、引き金を一文。止まっていなければ、その時点では離れない、と書く。

## Phase B: 繰り返される手順

次の一歩が、前の一歩と同じ役割で、新しい差を足さない箇所を探す。同じ役割の繰り返しが、見る人を離すなら、その機構と引き金を書く。差が毎回足されるなら、その時点では離れない、と書く。

## Phase C: 画面を名指ししない語

読める語が、いま見えている物の名前でも役割でもない箇所を探す。語そのものは写さない。ずれを、語が指す役割と、画面にある物の役割の差として書く。ずれが無ければ、その時点では離れない、と書く。

## Phase D: 終わりが最初の主張と合わない

開きで置いた約束を、最後の絵が別の物として閉じていないかを見る。別の物なら、機構と引き金を書く。同じ約束を閉じているなら、その時点では離れない、と書く。

## Outputs

`spread.leave` だけを書く。出どころは推論である。`basis` は `inferred` と書く。再生数、再生回数、割合、いいねの数は書かない。参照の文は写さない。スクリプトもコマンドも足さない。

渡された動画が複数なら、動画ごとにこの四つを書く。

- `firstSecond`。最初の一秒で約束が止まるか。`stalls` と、機構と引き金。
- `repeatedStep`。同じ手順が繰り返されて離れるか。`repeats` と、機構と引き金。
- `unnamedWord`。語が画面の物を名指ししないか。`misses` と、機構と引き金。語は写さない。
- `ending`。終わりが最初の主張と合わないか。`mismatches` と、機構と引き金。
- `basis`。`inferred`。
