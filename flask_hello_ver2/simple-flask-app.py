# app.pyの先頭部分に追加するコード
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import numpy as np

# 日本語フォント設定
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']

app = Flask(__name__)
app.config['SECRET_KEY'] = 'simple_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///water_health.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# モデル定義
class WaterIntake(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)  # ml単位
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

class K6Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    q1 = db.Column(db.Integer, nullable=False)  # 神経過敏に感じましたか
    q2 = db.Column(db.Integer, nullable=False)  # 絶望的だと感じましたか
    q3 = db.Column(db.Integer, nullable=False)  # そわそわ、落ち着かなく感じましたか
    q4 = db.Column(db.Integer, nullable=False)  # 気分が沈み込んで、何が起こっても気が晴れないように感じましたか
    q5 = db.Column(db.Integer, nullable=False)  # 何をするのも骨折りだと感じましたか
    q6 = db.Column(db.Integer, nullable=False)  # 自分は価値のない人間だと感じましたか
    total_score = db.Column(db.Integer, nullable=False)  # 合計スコア
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ルート定義
@app.route('/')
def index():
    return render_template('index.html')

# 水摂取記録
@app.route('/water/log', methods=['GET', 'POST'])
def log_water():
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        notes = request.form.get('notes', '')
        date_str = request.form.get('date', '')
        time_str = request.form.get('time', '')
        
        if amount <= 0:
            flash('摂取量は0より大きい値を入力してください', 'danger')
        else:
            try:
                # 日付と時間を設定（入力がない場合は現在時刻を使用）
                if date_str and time_str:
                    timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                elif date_str:
                    timestamp = datetime.strptime(f"{date_str} {datetime.now().strftime('%H:%M')}", "%Y-%m-%d %H:%M")
                else:
                    timestamp = datetime.now()
                    
                water_intake = WaterIntake(amount=amount, notes=notes, timestamp=timestamp)
                db.session.add(water_intake)
                db.session.commit()
                flash('摂取記録を保存しました！', 'success')
                return redirect(url_for('log_water'))
            except Exception as e:
                flash(f'エラーが発生しました: {str(e)}', 'danger')
    
    # 日付フィルタリング - デフォルトは今日
    filter_date_str = request.args.get('filter_date', datetime.now().strftime('%Y-%m-%d'))
    try:
        filter_date = datetime.strptime(filter_date_str, '%Y-%m-%d').date()
    except:
        filter_date = datetime.now().date()
        filter_date_str = filter_date.strftime('%Y-%m-%d')
    
    # 指定された日付の摂取記録を取得
    day_start = datetime.combine(filter_date, datetime.min.time())
    day_end = datetime.combine(filter_date, datetime.max.time())
    
    filtered_intakes = WaterIntake.query.filter(
        WaterIntake.timestamp >= day_start,
        WaterIntake.timestamp <= day_end
    ).order_by(WaterIntake.timestamp.desc()).all()
    
    total_filtered = sum(intake.amount for intake in filtered_intakes)
    
    # 過去7日間の摂取データを取得
    past_week = datetime.now() - timedelta(days=7)
    intakes = WaterIntake.query.filter(
        WaterIntake.timestamp >= past_week
    ).all()
    
    # グラフ用のデータを準備
    dates = []
    amounts = []
    current_date = past_week.date()
    end_date = datetime.now().date()
    
    while current_date <= end_date:
        dates.append(current_date.strftime('%m/%d'))
        daily_amount = sum(intake.amount for intake in intakes if intake.timestamp.date() == current_date)
        amounts.append(daily_amount)
        current_date += timedelta(days=1)
    
    # グラフの生成
    plt.figure(figsize=(10, 6))
    plt.bar(dates, amounts, color='skyblue')
    plt.title('過去7日間の水摂取量')
    plt.xlabel('日付')
    plt.ylabel('摂取量 (ml)')
    plt.ylim(bottom=0)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    # 画像をBase64エンコード
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return render_template('water_log.html', 
                          intakes=filtered_intakes, 
                          total=total_filtered,
                          filter_date=filter_date_str,
                          img_data=img_str)

# 水摂取記録の編集
@app.route('/water/edit/<int:id>', methods=['GET', 'POST'])
def edit_water(id):
    intake = WaterIntake.query.get_or_404(id)
    
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        notes = request.form.get('notes', '')
        date_str = request.form.get('date', '')
        time_str = request.form.get('time', '')
        
        if amount <= 0:
            flash('摂取量は0より大きい値を入力してください', 'danger')
        else:
            try:
                # 日付と時間を設定
                if date_str and time_str:
                    timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                    intake.timestamp = timestamp
                
                intake.amount = amount
                intake.notes = notes
                db.session.commit()
                flash('摂取記録を更新しました！', 'success')
                return redirect(url_for('log_water'))
            except Exception as e:
                flash(f'エラーが発生しました: {str(e)}', 'danger')
    
    # 編集フォームの初期値を設定
    return render_template('edit_water.html', intake=intake)

# 水摂取記録の削除
@app.route('/water/delete/<int:id>', methods=['POST'])
def delete_water(id):
    intake = WaterIntake.query.get_or_404(id)
    
    try:
        db.session.delete(intake)
        db.session.commit()
        flash('摂取記録を削除しました！', 'success')
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
    
    return redirect(url_for('log_water'))

# K6アンケート関連部分の完全修正版
@app.route('/k6/survey', methods=['GET', 'POST'])
def k6_survey():
    if request.method == 'POST':
        try:
            # デバッグ用：リクエストフォームの全内容を表示
            print("フォームデータ:", request.form)
            
            # 文字列として取得してからintに変換
            q1_str = request.form.get('q1', '')
            q2_str = request.form.get('q2', '')
            q3_str = request.form.get('q3', '')
            q4_str = request.form.get('q4', '')
            q5_str = request.form.get('q5', '')
            q6_str = request.form.get('q6', '')
            
            # 受け取った値のデバッグ出力
            print(f"受け取った値: q1={q1_str}, q2={q2_str}, q3={q3_str}, q4={q4_str}, q5={q5_str}, q6={q6_str}")
            
            # 入力検証
            if not all([q1_str, q2_str, q3_str, q4_str, q5_str, q6_str]):
                flash('すべての質問に回答してください', 'danger')
                today = datetime.now().strftime('%Y-%m-%d')
                return render_template('k6_survey.html', today=today)
            
            # 整数に変換
            q1 = int(q1_str)
            q2 = int(q2_str)
            q3 = int(q3_str)
            q4 = int(q4_str)
            q5 = int(q5_str)
            q6 = int(q6_str)
            
            # 変換後の値を確認
            print(f"整数変換後: q1={q1}, q2={q2}, q3={q3}, q4={q4}, q5={q5}, q6={q6}")
            
            # 日付の取得（指定がなければ現在日時）
            date_str = request.form.get('date', '')
            if date_str:
                # 日付が指定されている場合はその日の日付で記録
                survey_date = datetime.strptime(date_str, "%Y-%m-%d")
            else:
                # 日付が指定されていない場合は現在日時
                survey_date = datetime.now()
            
            # スコア計算と検証
            total_score = q1 + q2 + q3 + q4 + q5 + q6
            print(f"K6合計スコア: {total_score}")
            
            if total_score < 0 or total_score > 24:  # K6スコアの有効範囲
                flash('無効なスコアです。各質問は0〜4点の範囲で回答してください', 'danger')
                today = datetime.now().strftime('%Y-%m-%d')
                return render_template('k6_survey.html', today=today)
            
            # データベースに保存
            survey = K6Survey(
                q1=q1, q2=q2, q3=q3, q4=q4, q5=q5, q6=q6,
                total_score=total_score,
                timestamp=survey_date
            )
            db.session.add(survey)
            db.session.commit()
            
            flash('K6アンケートの回答を保存しました！', 'success')
            return redirect(url_for('k6_result'))
        except ValueError as e:
            print(f"値エラー: {str(e)}")
            flash('入力値に問題があります。数値を正しく入力してください。', 'danger')
        except Exception as e:
            print(f"その他のエラー: {str(e)}")
            flash(f'エラーが発生しました: {str(e)}', 'danger')
    
    # デフォルトの日付を設定（今日）
    today = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('k6_survey.html', today=today)

# K6結果表示
@app.route('/k6/result')
def k6_result():
    # 過去のK6アンケート結果を取得
    surveys = K6Survey.query.order_by(K6Survey.timestamp.desc()).all()
    
    if not surveys:
        flash('まだK6アンケートの記録がありません', 'info')
        return redirect(url_for('k6_survey'))
    
    # 最新の結果
    latest = surveys[0]
    print(f"最新のK6結果: id={latest.id}, 合計={latest.total_score}, 回答=[{latest.q1},{latest.q2},{latest.q3},{latest.q4},{latest.q5},{latest.q6}]")
    
    # 過去のスコアの推移をグラフ化
    timestamps = []
    scores = []
    
    for survey in reversed(surveys):
        timestamps.append(survey.timestamp.strftime('%m/%d'))
        scores.append(survey.total_score)
    
    # グラフの生成
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, scores, marker='o', linestyle='-', color='#3498db')
    plt.title('K6スコアの推移', fontname='Hiragino Sans')
    plt.xlabel('日付', fontname='Hiragino Sans')
    plt.ylabel('総合スコア', fontname='Hiragino Sans')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    # 画像をBase64エンコード
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    # スコアの解釈
    interpretation = ""
    if latest.total_score <= 4:
        interpretation = "問題なし：精神的ストレスは低いレベルです。"
    elif latest.total_score <= 9:
        interpretation = "軽度：軽度の精神的苦痛の可能性があります。"
    elif latest.total_score <= 12:
        interpretation = "中等度：中等度の精神的苦痛の可能性があります。"
    else:
        interpretation = "重度：重度の精神的苦痛の可能性があります。専門家への相談をご検討ください。"
    
    return render_template('k6_results.html', 
                          surveys=surveys, 
                          latest=latest, 
                          interpretation=interpretation,
                          img_data=img_str)

# K6調査の編集機能
@app.route('/k6/edit/<int:id>', methods=['GET', 'POST'])
def edit_k6(id):
    survey = K6Survey.query.get_or_404(id)
    print(f"編集対象K6: id={survey.id}, 合計={survey.total_score}, 回答=[{survey.q1},{survey.q2},{survey.q3},{survey.q4},{survey.q5},{survey.q6}]")
    
    if request.method == 'POST':
        try:
            # デバッグ用：リクエストフォームの全内容を表示
            print("フォームデータ:", request.form)
            
            # 文字列として取得
            q1_str = request.form.get('q1', '')
            q2_str = request.form.get('q2', '')
            q3_str = request.form.get('q3', '')
            q4_str = request.form.get('q4', '')
            q5_str = request.form.get('q5', '')
            q6_str = request.form.get('q6', '')
            
            # 受け取った値のデバッグ出力
            print(f"受け取った値: q1={q1_str}, q2={q2_str}, q3={q3_str}, q4={q4_str}, q5={q5_str}, q6={q6_str}")
            
            # 入力検証
            if not all([q1_str, q2_str, q3_str, q4_str, q5_str, q6_str]):
                flash('すべての質問に回答してください', 'danger')
                return render_template('edit_k6.html', survey=survey)
            
            # 整数に変換
            q1 = int(q1_str)
            q2 = int(q2_str)
            q3 = int(q3_str)
            q4 = int(q4_str)
            q5 = int(q5_str)
            q6 = int(q6_str)
            
            # 変換後の値を確認
            print(f"整数変換後: q1={q1}, q2={q2}, q3={q3}, q4={q4}, q5={q5}, q6={q6}")
            
            # 日付の取得
            date_str = request.form.get('date', '')
            if date_str:
                survey_date = datetime.strptime(date_str, "%Y-%m-%d")
                survey.timestamp = survey_date
            
            # スコア計算と検証
            total_score = q1 + q2 + q3 + q4 + q5 + q6
            print(f"K6合計スコア: {total_score}")
            
            if total_score < 0 or total_score > 24:  # K6スコアの有効範囲
                flash('無効なスコアです。各質問は0〜4点の範囲で回答してください', 'danger')
                return render_template('edit_k6.html', survey=survey)
            
            # 値を更新
            survey.q1 = q1
            survey.q2 = q2
            survey.q3 = q3
            survey.q4 = q4
            survey.q5 = q5
            survey.q6 = q6
            survey.total_score = total_score
            
            db.session.commit()
            print(f"更新後K6: id={survey.id}, 合計={survey.total_score}, 回答=[{survey.q1},{survey.q2},{survey.q3},{survey.q4},{survey.q5},{survey.q6}]")
            
            flash('K6アンケートの回答を更新しました！', 'success')
            return redirect(url_for('k6_result'))
        except ValueError as e:
            print(f"値エラー: {str(e)}")
            flash('入力値に問題があります。数値を正しく入力してください。', 'danger')
        except Exception as e:
            print(f"その他のエラー: {str(e)}")
            flash(f'エラーが発生しました: {str(e)}', 'danger')
    
    return render_template('edit_k6.html', survey=survey)

# K6の選択した記録を削除する機能

@app.route('/k6/delete_selected', methods=['POST'])
def delete_selected_k6():
    try:
        # 選択されたIDのリストを取得
        selected_ids = request.form.getlist('selected_records')
        
        if not selected_ids:
            flash('削除する記録が選択されていません', 'warning')
            return redirect(url_for('k6_result'))
        
        # 選択された記録を削除
        deleted_count = 0
        for record_id in selected_ids:
            survey = K6Survey.query.get(record_id)
            if survey:
                db.session.delete(survey)
                deleted_count += 1
        
        db.session.commit()
        flash(f'選択した{deleted_count}件の記録を削除しました', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'エラーが発生しました: {str(e)}', 'danger')
    
    return redirect(url_for('k6_result'))

@app.route('/k6/delete/<int:id>', methods=['POST'])
def delete_k6(id):
    try:
        survey = K6Survey.query.get_or_404(id)
        db.session.delete(survey)
        db.session.commit()
        flash('K6調査記録を削除しました！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'エラーが発生しました: {str(e)}', 'danger')
    
    return redirect(url_for('k6_result'))

# データベースの初期化コマンド
@app.cli.command("init-db")
def init_db():
    db.create_all()
    print('データベースを初期化しました')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # アプリ起動時にデータベースを作成
    app.run(debug=True)