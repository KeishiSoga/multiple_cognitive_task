# Multiple Cognitive Tasks

複数の認知課題を統合したFlaskアプリケーションです。

## 機能

以下の4つの認知課題を1つのアプリケーションから選択して実施できます：

- **Flanker Task** - フランカー課題（干渉制御機能の測定）
- **Go/NoGo Task** - Go/NoGo課題（反応抑制と衝動性の評価）
- **Stroop Task** - ストループ課題（選択的注意と認知制御能力の測定）
- **TMT (Trail Making Test)** - トレイルメイキング課題（視覚探索、処理速度、実行機能の測定）

## セットアップ

### 1. 仮想環境の作成と有効化

```bash
python -m venv flanker_env
source flanker_env/bin/activate  # macOS/Linux
# または
flanker_env\Scripts\activate  # Windows
```

### 2. 依存関係のインストール

```bash
pip install flask
```

### 3. アプリケーションの起動

```bash
python main_app.py
```

ブラウザで `http://localhost:5006` にアクセスしてください。

## 使用方法

1. メイン画面で実施したい認知課題を選択
2. 各課題の説明を確認
3. 「開始する」ボタンをクリックして課題を開始
4. 課題完了後、結果が表示されます

## ファイル構成

- `main_app.py` - メインアプリケーション（統合版）
- `flanker.py` - Flanker課題（個別版）
- `gonogo.py` - Go/NoGo課題（個別版）
- `stroop.py` - Stroop課題（個別版）
- `tmt.py` - トレイルメイキング課題（個別版）
- `templates/` - HTMLテンプレートファイル

## 注意事項

- ポート5006で起動します（ポート5000はmacOSのAirPlay Receiverで使用される可能性があります）
- 各課題はセッションを使用してデータを保存します

