---
name: sasaru-spread-payoff
description: "Apply when writing why a short gets watched, and only the payoff slice. Name the second the opening claim is paid off, what the viewer can now point at, and the anticipation, the hit, and the settle as three different beats. A label with no on-screen change fails. Write spread.payoff and label it an inference. Do not invent a view count, copy a source sentence, or add a CLI."
disable-model-invocation: true
---

# sasaru-spread-payoff

再生される理由の、回収の一切れ。冒頭の主張が、画面の上で果たされる瞬間だけを読む。冒頭の読み、コメント、共有、離脱、再生数は、このスキルの出力に書かない。

形は `../sasaru/SKILL.md` の「役の形」に従う。ルーターは四つの役を振り、このファイルは振らない。スキーマ、ルーター、テンプレート、他のスキル、設計ノートは変えない。新しいコマンドは足さない。

書く前に `../sasaru-principle-describe-the-form-not-the-work/SKILL.md` を全文読む。画面の字、せりふ、キャプション、題は、出力に写さない。

## Start

todo をこの順に開く。

1. 冒頭の主張が回収される秒
2. その秒に、見る人が指差せるようになったもの
3. 待ち、当たり、着地を三つの拍に分ける

三つの拍は、別々の画面の変化である。変化の無い秒に拍の名前だけを置いた出力は、不合格である。

渡された一覧のうち、ファイルが無い動画は名前だけを残す。その動画の読みは作らない。あるファイルだけを見る。

## Phase A: 回収の秒

最初の三秒が画面で渡した主張が、絵の変化で果たされる秒を一つ書く。主張の文は写さない。回収は、その主張がもう画面の上で見えていることである。その秒より前は、主張がまだ果たされていない。

作り方の説明が続いているだけの秒は、回収の秒にしない。後から足された別の到達も、この秒にしない。

## Phase B: 指させるもの

その秒のあと、見る人が画面の一点を指して示せるものを書く。その秒の前には、同じものを指せなかったものに限る。

字の役割、心の中の理解、再生の数は、指させるものではない。画面に新しい対象が現れていること。

## Phase C: 三つの拍

待ち、当たり、着地を、別の拍として書く。それぞれに、入る秒、出る秒、その拍で画面がどう変わるかを書く。

- 待ち。回収の前の変化で、主張がまだ果たされていないことが画面に出る。
- 当たり。主張が果たされる変化。Phase A の秒はこの拍の中にある。
- 着地。当たりのあと、別の変化で、指させるものが画面に残って止まる。当たりと同じ絵のまま、名前だけを着地にしない。

一つの拍に画面の変化が無いなら、その拍の名前は書かない。三つが書けない動画は、`spread.payoff` を合格として出さない。書けなかった拍の、画面の変化が無かったことだけを残す。三つの拍を同じ秒に重ねない。

## Outputs

`spread.payoff` だけを書く。出どころは推論である。`basis` は `inferred` と書く。再生数、再生回数、割合、いいねの数は書かない。参照の文は写さない。スクリプトもコマンドも足さない。動画ファイルは作らない。

- `paidOffAtSec`。主張が果たされた秒。
- `pointAt`。その秒に、見る人が指差せるようになったもの。
- `beats.anticipation`。待ち。`tIn`、`tOut`、`onScreen`。
- `beats.hit`。当たり。`tIn`、`tOut`、`onScreen`。`paidOffAtSec` はこの中。
- `beats.settle`。着地。`tIn`、`tOut`、`onScreen`。
- `basis`。`inferred`。

`onScreen` は、その拍の画面の変化である。変化が書けない `onScreen` は、失敗した出力である。
