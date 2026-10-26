---
name: sasaru-spread-escalation
description: "Apply when writing why a short is watched, and only the escalation slice. Record spread.escalation as an ordered sequence of build steps. Each step says what got harder or clearer, and which beat would be flat if it repeated the previous step. Mark the reading as inferred. Do not write a view count, a source sentence, or a new command."
disable-model-invocation: true
---

# 一段ごとの上げ

見られる理由のうち、積みの上げだけを書く。再生・コメント・共有の心理、開きの主張、あり得ない制約、回収、コメントが返る地点、共有の把手、離脱は、このスキルの外である。

欄は `spread.escalation`。形容詞一つではない。作る順の列である。

各要素は次の言葉を持つ。

- `build`。この段で、前の段の上に何が積まれるか。
- `change`。直前の段より、何が難しくなったか、または何がはっきりしたか。難しくなった、だけでは閉じない。何がどう変わったかを一文で書く。最初の要素に直前は無い。何がはっきりしたかだけを書く。
- `flatIfRepeated`。この段が直前の段と同じ積みの繰り返しだったとき、平坦になるビート。playbook に id があればその id。無ければ、その拍の役割を短く書く。最初の要素にはこの鍵を書かない。`null` は書かない。
- `basis`。`inferred`。

`evidence.inferred` に `spread.escalation` を載せる。測った再生数として扱わない。

画面や声の文は写さない。見る人に積まれるものの形を書く。再生回数、割合、いいねは書かない。

この切片はコマンドを持たない。検査スクリプトは作らない。

## 手順

1. 映像を、積みの変わり目で切る。秒の等分では切らない。新しい障害、新しい到達、新しい明らかさ、が乗ったところだけを次の段にする。同じ状態のカメラ変更は段にしない。
2. 各段の `build` に、その段で足されたものだけを書く。前の段に既にあるものは繰り返さない。
3. `change` に、直前より難しくなったことか、直前よりはっきりしたことかを一つ書く。両方見えても、その段で注意を残しているほうを一つにする。
4. その段の積みを直前の段の繰り返しに置き換えたら、どの拍が次を待たなくなるかを `flatIfRepeated` に書く。平坦になるのは、上げが無いと役割が消える拍である。
5. 絵が別の作業へリセットしたら、列を分ける。リセットは上げではない。
6. 一段で終わる型は、最初の要素だけを書く。

## 形

```yaml
spread:
  escalation:
    - build: 届ける先の輪郭だけを置く
      change: 何を見届けるかが、最初の段ではっきりする
      basis: inferred
    - build: 同じ輪郭に、届かない障害を一つ足す
      change: 到達までの距離が、その障害の分だけ遠くなる
      flatIfRepeated: turn
      basis: inferred
    - build: 障害を越えた到達を、輪郭の内側に収める
      change: 先に見えた輪郭が、到達の形としてはっきりする
      flatIfRepeated: payoff
      basis: inferred
```

## 不合格

- `escalation: 激しい` のように、列でない一語で閉じる
- 隣り合う段の `build` が同じ文
- 再生回数、割合、いいね
- 参照のテロップ、声、キャプションの文
- この切片のための新しいコマンド
