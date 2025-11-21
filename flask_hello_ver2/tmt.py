from flask import Flask, render_template, request, jsonify, session
import random
import time
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = "tmt_task_secret_key"
app.config['SESSION_TYPE'] = 'filesystem'

# トレイルメイキングテストの設定
NUMBERS = list(range(1, 26))  # 1から25までの数字

@app.route('/')
def index():
    # セッションを初期化
    session['start_time'] = None
    session['completion_time'] = None
    session['errors'] = 0
    session['clicks'] = []
    print("セッション初期化完了")  # デバッグ用
    return render_template('tmtindex.html', template='index')

@app.route('/start', methods=['POST'])
def start():
    # テスト開始
    session['start_time'] = time.time()
    session['completion_time'] = None
    session['errors'] = 0
    session['clicks'] = []
    session['current_number'] = 1
    print("テスト開始")  # デバッグ用
    
    return jsonify({
        'status': 'success',
        'total_numbers': len(NUMBERS)
    })

@app.route('/record_click', methods=['POST'])
def record_click():
    try:
        data = request.get_json()
        clicked_number = int(data.get('number'))
        click_time = data.get('time')
        
        print(f"クリック記録: 数字 {clicked_number}, 時刻: {click_time}")  # デバッグ用
        
        # クリック情報を記録
        if 'clicks' not in session:
            session['clicks'] = []
        
        clicks = session.get('clicks', [])
        clicks.append({
            'number': clicked_number,
            'time': click_time,
            'timestamp': time.time()
        })
        session['clicks'] = clicks
        
        # 現在の数字を確認
        current_number = session.get('current_number', 1)
        
        # 正しい順序かどうかを判定
        is_correct = (clicked_number == current_number)
        
        if is_correct:
            # 正しい場合は次の数字へ
            session['current_number'] = current_number + 1
            
            # すべての数字をクリックしたか確認
            if current_number >= len(NUMBERS):
                session['completion_time'] = time.time()
                return jsonify({
                    'status': 'success',
                    'correct': True,
                    'completed': True,
                    'next_number': None
                })
            else:
                return jsonify({
                    'status': 'success',
                    'correct': True,
                    'completed': False,
                    'next_number': current_number + 1
                })
        else:
            # 間違った場合はエラーを記録
            errors = session.get('errors', 0)
            session['errors'] = errors + 1
            
            return jsonify({
                'status': 'success',
                'correct': False,
                'completed': False,
                'next_number': current_number,
                'error': True
            })
            
    except Exception as e:
        print(f"エラー発生: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/complete', methods=['POST'])
def complete():
    try:
        data = request.get_json()
        completion_time = data.get('completion_time')
        
        session['completion_time'] = time.time()
        
        # 結果を計算
        start_time = session.get('start_time')
        if start_time:
            total_time = time.time() - start_time
        else:
            total_time = 0
        
        errors = session.get('errors', 0)
        clicks = session.get('clicks', [])
        
        return jsonify({
            'status': 'success',
            'total_time': round(total_time, 2),
            'errors': errors,
            'total_clicks': len(clicks)
        })
    except Exception as e:
        print(f"エラー発生: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/results')
def show_results():
    try:
        start_time = session.get('start_time')
        completion_time = session.get('completion_time')
        errors = session.get('errors', 0)
        clicks = session.get('clicks', [])
        
        if not start_time or not completion_time:
            return render_template('tmtindex.html', error='結果がありません', template='results')
        
        # 所要時間を計算
        total_time = completion_time - start_time
        
        # クリックデータを整理
        click_data = []
        for i, click in enumerate(clicks):
            click_data.append({
                'sequence': i + 1,
                'number': click.get('number', 0),
                'time': round(click.get('time', 0), 2)
            })
        
        summary = {
            'total_time': round(total_time, 2),
            'errors': errors,
            'total_clicks': len(clicks),
            'numbers_completed': session.get('current_number', 1) - 1
        }
        
        print(f"サマリー: {summary}")
        
        return render_template('tmtindex.html', summary=summary, click_data=click_data, template='results')
    except Exception as e:
        print(f"結果表示エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('tmtindex.html', error=f'エラーが発生しました: {str(e)}', template='results')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)

