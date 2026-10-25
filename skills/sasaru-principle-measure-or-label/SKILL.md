---
name: sasaru-principle-measure-or-label
description: "Apply when filling a playbook field or a gate column with a number. A number counts as measured only if a script measured it on a file. Any other number is allowed only when its path is listed under evidence.inferred. A field nobody measured or chose is null and listed under evidence.unmeasured."
disable-model-invocation: true
---

# Measure or Label

`evidence` の三つの欄が、playbook の数の出どころを決める。

- `measured` は、スクリプトがファイルで測った数。手順の名前を本文の「測ったことと推論」に書く。
- `inferred` は、目で見た印象、手書きの型の指定、別の文書から持ってきた値。数を書いてよいが、測った数として扱わない。
- `unmeasured` は、誰も測らず決めてもいない欄。値は `null`。

ゲートは `unmeasured` の欄を合格にしない。

一本の参照で測った数は、その playbook の値である。別の型の定数にしない。`measuredFiles` が増えたときだけ帯を広げる。
