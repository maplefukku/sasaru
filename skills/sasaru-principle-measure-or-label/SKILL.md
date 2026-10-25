---
name: sasaru-principle-measure-or-label
description: "Apply when filling a playbook field or a gate column with a number. A number goes in only if a script measured it on a file; otherwise the field is null and its path is listed under evidence.unmeasured. Inferred values are listed under evidence.inferred."
disable-model-invocation: true
---

# Measure or Label

数は、スクリプトがファイルで測ったものだけを入れる。目で見た印象は `inferred` に、測っていない欄は `null` にして `unmeasured` に名前を残す。未計測の欄を合格にしない。

一本の参照で測った数は、その playbook の値である。別の型の定数にしない。`measuredFiles` が増えたときだけ帯を広げる。
