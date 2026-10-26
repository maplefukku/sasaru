---
name: sasaru-spread-comment
description: "Apply when writing why people reply to a short. Name the beat that leaves a procedure unfinished or a claim arguable, and the kind of reply that invites. Do not invent comment counts. One slice only."
disable-model-invocation: true
---

# sasaru-spread-comment

人が返信する理由の一枚だけを書く。再生と共有は書かない。スキーマ、ルーター、テンプレート、他のスキルは触らない。新しいコマンドは足さない。

元の文は写さない。テロップ、セリフ、キャプション、固有名を一文として残さない（**sasaru-principle-describe-the-form-not-the-work**）。この切片は推論で、測ったコメント数ではない（**sasaru-principle-measure-or-label**）。

## Start

1. 渡された動画ファイルだけを見る。一覧にあってファイルが無いものは、ファイル名を書いて、その本の拍は作らない。
2. コメント数の取得結果がこの作業に渡されていなければ、数は空のままにする。見た印象の多さで埋めない。
3. 書く名前は `spread.comment` だけ。他の切片は書かない。

## Phase 1: 拍

動画ごとに、次のどちらかが残っている拍を一つ書く。

- 手順が途中で止まっている。次の一手が、画面の中で済んでいない。
- 主張がまだ争える。言い切りが、見る人の反例か同意を待っている。

秒が分かるときは、その拍の位置を添える。測った境界でなければ、見本だと書く。両方あるときは、返信を招いているほうを一つ選ぶ。どちらも無く、手順も主張も閉じているときは、閉じていると一行で書き、返信の種類は作らない。

拍は型の働きで書く。元の文は入れない。

## Phase 2: 招く返信

その拍が招く返信の種類を一つ書く。

- 未完の手順は、見る人が自分の次の一手を返す。
- 争える主張は、見る人が賛成か反対を一文で返す。

拍に無い種類は書かない。

## Phase 3: 数

コメント数を作らない。取得した数が渡されているときだけ、出どころと一緒に書く。渡されていなければ、「コメント数は取得していない」と書く。多い、少ない、は数の代わりにしない。

## Outputs

`spread.comment` を一つ。動画ごとに、拍、招く返信、数。冒頭で推論と明記する。
