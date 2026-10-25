---
name: sasaru-principle-describe-the-form-not-the-work
description: "Apply when writing or committing a playbook, an example, or any file under the plugin. Record the format as counts, ratios, timings, and classes. Never store the reference's caption wording, audio, frames, track title, or creator identity."
disable-model-invocation: true
---

# Describe the Form, Not the Work

playbook は他人の動画の型を言葉と数で持つ。作品そのものは持たない。スキーマは `captions` に文言の欄を持たず、`audio.referenceAudioUsed` は `false` だけを許す。欄が無いことを、本文に文言を書いてよい理由にしない。

失敗の例。ビートの `purpose` に元のテロップをそのまま書く。直すと「三つ目の否定で見る人に次を待たせる」になる。

取り込みで読んだテロップの文字と、声の文字起こしは、`work/<id>/source-text.json` に書く。ゲートはこのファイルと playbook 全体（フロントマターの自由文字列を含む）を突き合わせる。このファイルが無い取り込みの playbook は、ゲートを通らない。

取り込みの作業ディレクトリ（シート、キーフレーム、音声、白画素の記録、source-text.json）は、ライブラリの `work/` に置き、コミットしない。言い換えはスキーマでもゲートでも止められない。止めるのはこの原則である。
