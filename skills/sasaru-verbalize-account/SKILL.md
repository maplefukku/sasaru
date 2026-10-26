---
name: sasaru-verbalize-account
description: "Write verbalization.accountPattern only after several videos from the same account are already verbalized into picture.md, edit.md, words.md, sound.md, and pull.md. Record what repeats in the opening, the impossible constraint, the escalation, and the payoff, what does not repeat, and the story machine in plain language a person can retell. A shot list of one reel is a failed output. No source sentences. No new command."
disable-model-invocation: true
---

# sasaru-verbalize-account

同じアカウントの動画が複数本、言語化されたあとにだけ動く。出力は `verbalization.accountPattern` だけである。新しいコマンドは足さない。動画は作らない。

形は `../sasaru/SKILL.md` の「役の形」に従う。ルーターは四つの役を振り、このファイルは振らない。五つのファイルが揃ったとき、このファイルを全文読んでから書く。スキーマ、ルーター、テンプレート、他のスキル、設計ノートは変えない。

書く前に `../sasaru-principle-describe-the-form-not-the-work/SKILL.md` を全文読む。画面の字、せりふ、キャプション、題は、出力に写さない。

## Start

todo を Phase ごとに一つずつ開く。Phase A を通過するまで、あとの Phase は開かない。

1. 揃うまで待つ
2. 繰り返すところを読む
3. 繰り返さないところを分ける
4. 物語の機械を書く

## Phase A: 揃うまで待つ

呼び出し手は、アカウントの言語化ディレクトリを一つ渡す。読むのは、その直下の次の五つだけ。

- `picture.md`
- `edit.md`
- `words.md`
- `sound.md`
- `pull.md`

この五つは、同じアカウントの複数本を、絵、編集、言葉、音、引きで言語化したもの。この役は一本のリールを言語化しない。五つのファイルを書き換えない。

次のどれかなら、`account-pattern.md` を作らない。記憶で型を補わない。別のアカウントの言語化も使わない。動画ファイルは作らない。

- 五つが揃っていない。
- 五つが指している動画が一本だけである。
- どれかが、一本のリールのショット一覧である。

返すのは、止まっている理由だけ。足りないファイルの名前か、動画が一本であること。

複数本とは、五つのファイルの中で区別できる動画が二本以上あること。区別は、ファイルが付けている呼び名で数える。元の文では数えない。

## Phase B: 繰り返すところ

五つのファイルだけを読む。ファイルに無い繰り返しは書かない。一本にしか無いことは、ここに書かない。

次の四つに分ける。見出しの意味はスロットの定義で、中身はファイルから取る。

1. 冒頭。複数本で、始まりに同じ役割で置かれるもの。
2. 不可能な制約。見る人にとって、冒頭の到達がそのままで達成できないように見える条件。複数本で同じ条件だけ。
3. エスカレーション。同じ制約のまま、次の一手が前より難しくなること。複数本で同じ進み方だけ。
4. 回収。制約がほどける着地。複数本で同じ着地の役割だけ。

## Phase C: 繰り返さないところ

本ごとに変わるものを、機械から外して書く。変わらないものに混ぜない。ここに書くのも、五つのファイルにある違いだけ。

## Phase D: 物語の機械

人がその場で話し直せる言葉で、機械を一つ書く。冒頭、不可能な制約、エスカレーション、回収が、その順でどう繋がるか。専門語の定義を重ねない。秒の表にしない。ショットの一覧にしない。

これは推論である。測った再生数ではない。ファイルが示していない接続は書かない。

## Outputs

書き込むファイルは、五つのファイルと同じディレクトリの `account-pattern.md`。このファイルが `verbalization.accountPattern` である。Phase A を通過する前に、このファイルを作らない。

中身は次の見出しだけ。この順。

```markdown
# verbalization.accountPattern

## 繰り返すところ

### 冒頭

### 不可能な制約

### エスカレーション

### 回収

## 繰り返さないところ

## 物語の機械
```

各見出しの本文は、五つのファイルから読んだ役割の言葉だけ。元の文が五つのファイルに残っていても、ここへは写さない。

失敗した出力は、一本のリールのショット一覧である。秒とショットの表、一本のカット割り、元の文の写し、記憶で埋めた型、動画ファイルは、`verbalization.accountPattern` ではない。この役がそう書いてしまったら、その `account-pattern.md` だけを消して、Phase A の止まりに戻る。

スクリプトも、新しいコマンドも、足さない。読むのも書くのも、この手順だけである。
