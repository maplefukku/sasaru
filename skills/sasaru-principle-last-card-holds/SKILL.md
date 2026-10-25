---
name: sasaru-principle-last-card-holds
description: "Apply when setting caption out-times. The last caption card stays on screen until the last frame. Do not close it when the voice or beat ends."
disable-model-invocation: true
---

# Last Card Holds

最後の一枚の終了秒は、絵の終了秒と同じにする。言い切った句が画面に残ってから終わる。

それ以外の一枚を、次の一枚の頭まで残すか、句の終わりで消すかは playbook の層ごとの `captions[].hide` と `minHoldSec` に従う。字の無い秒がある型は `phrase-end` と書く。
