# Multiple Cognitive Tasks

複数の認知課題を統合したFlaskアプリケーションです。

## 機能

以下の3つの認知課題を1つのアプリケーションから選択して実施できます：

- **Flanker Task** - フランカー課題（干渉制御機能の測定）
- **Go/NoGo Task** - Go/NoGo課題（反応抑制と衝動性の評価）
- **Stroop Task** - ストループ課題（選択的注意と認知制御能力の測定）

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
- `templates/` - HTMLテンプレートファイル

## Renderでのデプロイ

このアプリケーションはRenderで簡単にデプロイできます。

### デプロイ手順

1. [Render](https://render.com)にアカウントを作成（GitHubアカウントでログイン可能）
2. 「New +」→「Web Service」を選択
3. GitHubリポジトリを接続
4. 以下の設定を入力：
   - **Name**: `multiple-cognitive-task`（任意）
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main_app:app`
5. 「Create Web Service」をクリック

デプロイが完了すると、自動的にURLが生成されます（例: `https://multiple-cognitive-task.onrender.com`）

## 注意事項

- ローカル環境ではポート5006で起動します（ポート5000はmacOSのAirPlay Receiverで使用される可能性があります）
- Renderでは環境変数`PORT`が自動的に設定されます
- 各課題はセッションを使用してデータを保存します

