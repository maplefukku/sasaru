---
name: sasaru-scenario
description: "Write scenario.story only after verbalization and the spread slices are files in one directory. The story is a few plain sentences a person can retell, then each beat says what is on screen, what changed, and why the next second is wanted. The first paragraph uses no shot numbers and opens on an impossible completion that already names the end state. Do not copy a how-to opening. An English word list is a failed scenario. No source sentences. No new CLI. Making a video is not this skill."
disable-model-invocation: true
---

# sasaru-scenario

言語化と、伸びた理由の切れが、同じディレクトリのファイルとして揃ったあとにだけ動く。出力は、そのディレクトリの `scenario.story` だけである。映像を作る役ではない。新しいコマンドは足さない。ショット一覧は書かない。

形は `../sasaru/SKILL.md` の「役の形」に従う。ルーターは四つの役を振り、このファイルは振らない。ファイルが揃ったとき、このファイルを全文読んでから書く。スキーマ、ルーター、テンプレート、他のスキル、設計ノートは変えない。

書く前に `../sasaru-principle-describe-the-form-not-the-work/SKILL.md` を全文読む。画面の字、せりふ、キャプション、題、参照の文は、出力に写さない。

`docs/bridge-scenario-v2.md` は、この役の出力ではない。`account-pattern.md` と、開き以外の切れが揃う前に、その文書を作らない。

## Start

todo を Phase ごとに一つずつ開く。Phase A を通過する前に `scenario.story` を作らない。記憶にある動画から物語を書かない。動画ファイルは開かない。

1. 揃うまで待つ
2. 人が言い直せる話を書く
3. 拍ごとに、画面、変化、次の一秒を書く
4. 失敗した出力を残さない

## Phase A: 揃うまで待つ

呼び出し手は、アカウントの作業ディレクトリを一つ渡す。読むのはその直下のファイルだけ。

言語化。次の六つがすべてファイルであること。

- `picture.md`
- `edit.md`
- `words.md`
- `sound.md`
- `pull.md`
- `account-pattern.md`

伸びた理由の切れ。`open.md` に加え、次の仕事が、ファイル名か最初の見出しで分かる別ファイルとして、それぞれ一つあること。

- あり得ない制約
- 一段ごとの上げ
- 回収の拍
- コメントが返る地点
- 共有の把手
- 離脱する条件

`open.md` は開きの主張で、中身は `spread.open` である。切れは、言語化の六ファイルとは別のファイルである。`account-pattern.md` の節を、切れの代わりにしない。

次のどれかなら、`scenario.story` を作らない。足りないファイルか、足りない仕事の名前だけを返す。記憶で補わない。

- 言語化の六つのどれかが無い。
- `open.md` が無い。
- 上の六つの仕事のどれかに、対応する切れのファイルが無い。
- 言語化が指している動画が一本だけである。

`open.md` だけがある状態は、Phase A を通過しない。

## Phase B: 言い直せる話

六つの言語化と、切れのファイルだけを読む。`scenario.story` の最初の段落を、普通の話し言葉で数文書く。読んだ人が、その場で同じ話を言い直せる。専門語の定義を重ねない。秒の表にしない。

最初の段落に、ショット番号を置かない。ショット、Shot、カット番号、区間の秒は、最初の段落に書かない。

最初の段落は、あり得ない完成から始まる。その完成の名前は、最初の段落にすでに置かれている。参照の最初の数秒が手順（作り方、使い方、最初の一手）なら、その手順は開きに写さない。`open.md` で `howTo` が真の動画は、その主張をシナリオの開きにしない。

溝の上の一枚の板から始まる参照は、橋と名乗っていない。その手順を開きに写さない。シナリオの最初の段落は、あり得ない完成で、すでに橋と名乗る。

## Phase C: 拍

最初の段落のあとに、拍を起こった順に書く。見出しは、何が起きるかを普通の言葉で呼ぶ。ショット番号も、秒の区間も、見出しにしない。

各拍は三つの文。

- 画面。その拍で画面にあるもの。
- 変化。前の拍から変わったもの。最初の拍は、何が現れたか。
- 次の一秒。なぜ次の一秒を見たいか。最後の拍は、なぜその絵を残したいか。

最初の拍の画面は、すでに橋と名乗る完成である。溝の上の一枚の板を、最初の拍の手順にしない。

拍の数と中身は、ファイルが支えているものだけ。ファイルに無い拍は足さない。一本のリールのショット一覧にしない。

次の一秒の理由は、`pull.md` と、コメント、共有、離脱、回収の切れから取る。画面は `picture.md` と `account-pattern.md` から取る。変化は `edit.md` と、制約、上げ、回収の切れから取る。`words.md` からは語の役割だけを使い、語そのものは写さない。`sound.md` からは音の役割だけを使う。

これは推論である。再生数は書かない。ファイルが示していない接続は書かない。

## Outputs

書き込むファイルは、渡されたディレクトリの `scenario.story`。Phase A を通過する前に、このファイルを作らない。

```markdown
# scenario.story

## 拍の名

画面。

変化。

次の一秒。
```

`# scenario.story` の直後、最初の `##` より前が、最初の段落である。上の骨格の「拍の名」は、何が起きるかを普通の言葉で置き換える。説明の行は本文に残さない。

失敗した `scenario.story` は消す。失敗は次のとおり。

- 最初の段落にショット番号か秒の区間がある。
- 英語の単語を、斜線や読点でつないだだけの行である。人が文として言い直せない。
- 参照の文、または入力ファイルに残っていた画面の字を写している。
- 溝の上の一枚の板という手順から始まっている。橋の名前が最初の段落に無い。
- 一本のリールのショット一覧である。
- 動画ファイル、生成のプロンプト、編集の手順である。

ファイルが揃っているときの失敗は、消したあと、同じファイルだけから書き直す。ファイルが足りないときは、消して Phase A の止まりに戻る。

スクリプトも、新しいコマンドも、足さない。動画は作らない。
