---
name: sasaru-verbalize-words
description: "Apply when reading each on-screen word in a reference short. Record when the word appears and leaves, its role (end-state name, step, punch, or none), its size and place relative to the frame, and whether it names a category (such as 橋) or a proper name. Write verbalization.words. Do not copy source wording into the playbook. No new command."
disable-model-invocation: true
---

# sasaru-verbalize-words

画面に出る語を、一語ずつ読む細かい流れ。出力は `verbalization.words` だけである。新しいコマンドは足さない。動画は作らない。他の断面（絵、編集、音、引き、アカウントの型、シナリオ）は書かない。

形は `../sasaru/SKILL.md` の「役の形」に従う。ルーターは四つの役を振り、このファイルは振らない。スキーマ、ルーター、テンプレート、他のスキル、設計ノートは変えない。

書く前に `../sasaru-principle-describe-the-form-not-the-work/SKILL.md` と `../sasaru-principle-measure-or-label/SKILL.md` を全文読む。画面の字、せりふ、キャプション、題は、playbook に写さない。`verbalization.words` にも写さない。

## Start

todo を Phase ごとに一つずつ開く。

1. 各語が出て消えるとき
2. 役
3. 画面に対する大きさと位置
4. カテゴリか固有名か

呼び出し手は、言語化ディレクトリと、読む動画の置き場を渡す。一覧に名前があってファイルが無い動画は、名前だけを残し、その動画の語は書かない。記憶で補わない。

一本の絵のショット一覧は、この出力ではない。語の区間だけを書く。

## Phase A: 出て消えるとき

画面に一語が出てから、その語が消えるまでを一区間にする。前の語が残ったまま次の語が出るなら、重なっている区間を別々に書く。同じ語が消えずに残るあいだは、区間を割らない。いったん消えてまた出たら、別の区間にする。

秒は参照の尺の上の秒。字の無い秒は区間にしない。出る秒と消える秒を決めていない区間は書かない。

## Phase B: 役

各区間に役を一つだけ付ける。

- 終状態の名前。この動画が行き着くものの名前。完成した物を指す語。
- 手順。そこへ至る一手。部品、動作、工程を指す語。
- 喝。着地の一語。終状態の名前でも手順でもなく、拍を閉じる語。
- なし。上のどれでもない。

文の中の位置だけで決めない。その語が画面でしている仕事で決める。役は推論である。測った箱ではない。

## Phase C: 画面に対する大きさと位置

各区間について、画面の幅と高さに対する比を書く。

- 大きさは、一行の芯の高さ / 画面高。
- 位置は、芯の箱の中心。横は左を 0、右を 1。縦は上を 0、下を 1。

同じ画面に語が二つあるときは、語ごとに比を書く。測った比と、目で見た比を一つの数に混ぜない。測っていなければ未計測と書き、定数で埋めない。

## Phase D: カテゴリか固有名か

各区間を、次のどれか一つで書く。

- カテゴリ。種類の名前。橋のように、物の種類を指し、固有の一本を指さない。
- 固有名。その一つの名前。
- どちらでもない。種類も、その一つの名前も指さない。

カテゴリの説明に、参照の綴りを使わない。固有名の綴りも書かない。

## Outputs

書き込むファイルは、言語化ディレクトリの `words.md`。このファイルが `verbalization.words` である。

中身は次の見出しだけ。この順。

```markdown
# verbalization.words

## 欠ける動画

## 語
```

欠ける動画が無ければ、その見出しの下に「なし」と書く。

`## 語` の下は、動画の区別が付く呼び名ごとに、区間の表だけ。列は、その動画の中の順、出る秒、消える秒、役、芯の高さ / 画面高、中心の横、中心の縦、カテゴリか固有名か。元の字の列は置かない。

playbook には `verbalization.words` を写さない。playbook に元の文言を足さない。元の字が `work/<id>/source-text.json` にあっても、ここへは持ってこない。

スクリプトも、新しいコマンドも、足さない。読むのも書くのも、この手順だけである。
