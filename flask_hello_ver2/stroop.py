from flask import Flask, render_template, request, jsonify, session
import random
import time
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = "stroop_task_secret_key"
app.config['SESSION_TYPE'] = 'filesystem'

# ストループ課題の文字と色
COLORS = {
    'red': {'name': 'あか', 'color': '#dc3545'},      # 赤
    'blue': {'name': 'あお', 'color': '#007bff'},     # 青
    'yellow': {'name': 'きいろ', 'color': '#ffc107'},  # 黄
    'black': {'name': 'くろ', 'color': '#000000'},     # 黒
    'green': {'name': 'みどり', 'color': '#28a745'}    # 緑
}

# 刺激の提示時間と刺激間隔時間（ミリ秒）
STIMULUS_DURATION = 500   # 0.5秒（刺激表示時間）
ISI_DURATION = 1500       # 1.5秒（刺激間隔時間、ブランク表示時間）
MAX_RESPONSE_TIME = STIMULUS_DURATION + ISI_DURATION  # 最大反応時間（2.0秒）

# 反応キーの設定（色に応じたキー）
RESPONSE_KEYS = {
    'red': '1',      # 赤色：1キー
    'blue': '2',     # 青色：2キー
    'yellow': '3',   # 黄色：3キー
    'black': '4',    # 黒色：4キー
    'green': '5'     # 緑色：5キー
}

@app.route('/')
def index():
    # セッションを初期化
    session['trials'] = []
    session['current_trial'] = 0
    session['results'] = []
    session['start_time'] = None
    print("セッション初期化完了")  # デバッグ用
    return render_template('stroopindex.html', template='index')

@app.route('/start', methods=['POST'])
def start():
    # 試行回数を設定（デフォルト：一致条件20回、不一致条件20回、計40試行）
    congruent_trials = int(request.form.get('congruent_trials', 20))
    incongruent_trials = int(request.form.get('incongruent_trials', 20))
    print(f"開始: 一致条件 {congruent_trials} 回、不一致条件 {incongruent_trials} 回")  # デバッグ用
    
    # 各刺激をランダムに配置した試行リストを作成
    trials = []
    
    # 一致条件の試行を作成（文字の意味と色が一致）
    color_list = list(COLORS.keys())
    for _ in range(congruent_trials):
        color = random.choice(color_list)
        trials.append({
            'type': 'congruent',
            'text': COLORS[color]['name'],
            'text_color': color,
            'display_color': color  # 一致条件では表示色も同じ
        })
    
    # 不一致条件の試行を作成（文字の意味と色が一致しない）
    for _ in range(incongruent_trials):
        text_color = random.choice(color_list)
        # 文字の意味とは異なる色を選択
        display_color_options = [c for c in color_list if c != text_color]
        display_color = random.choice(display_color_options)
        trials.append({
            'type': 'incongruent',
            'text': COLORS[text_color]['name'],
            'text_color': text_color,
            'display_color': display_color  # 不一致条件では表示色が異なる
        })
    
    random.shuffle(trials)
    print(f"試行リスト作成完了: {len(trials)} 試行")  # デバッグ用
    
    # セッションに試行リストを保存
    session['trials'] = trials
    session['current_trial'] = 0
    session['results'] = []
    session['start_time'] = time.time()
    
    return jsonify({
        'status': 'success',
        'total_trials': len(trials)
    })

@app.route('/next_trial')
def next_trial():
    trials = session.get('trials', [])
    current_trial = session.get('current_trial', 0)
    
    print(f"次の試行: {current_trial + 1}/{len(trials)}")  # デバッグ用
    
    # すべての試行が終了した場合
    if current_trial >= len(trials):
        print("すべての試行完了")  # デバッグ用
        return jsonify({
            'status': 'completed'
        })
    
    # 次の刺激を取得
    trial_data = trials[current_trial]
    session['current_trial'] = current_trial + 1
    
    # 表示色のコードを取得
    if trial_data['type'] == 'congruent':
        display_color_code = COLORS[trial_data['text_color']]['color']
    else:
        display_color_code = COLORS[trial_data['display_color']]['color']
    
    print(f"刺激: {trial_data['text']} (文字の意味: {trial_data['text_color']}, 表示色: {trial_data.get('display_color', trial_data['text_color'])})")  # デバッグ用
    
    return jsonify({
        'status': 'next',
        'text': trial_data['text'],
        'text_color': trial_data['text_color'],
        'display_color': trial_data.get('display_color', trial_data['text_color']),
        'display_color_code': display_color_code,
        'trial_type': trial_data['type'],
        'trial_number': current_trial + 1,
        'total_trials': len(trials),
        'stimulus_duration': STIMULUS_DURATION,
        'isi_duration': ISI_DURATION,
        'max_response_time': MAX_RESPONSE_TIME,
        'response_keys': RESPONSE_KEYS
    })

@app.route('/record_response', methods=['POST'])
def record_response():
    try:
        data = request.get_json()
        print(f"受信したデータ: {data}")  # デバッグ用
        
        # 前の試行のインデックス
        trial_idx = session.get('current_trial', 0) - 1
        if trial_idx < 0:
            print("試行が開始されていません")  # デバッグ用
            return jsonify({'status': 'error', 'message': '試行が開始されていません'})
        
        trials = session.get('trials', [])
        if not trials or trial_idx >= len(trials):
            print(f"試行インデックスエラー: {trial_idx}, 試行数: {len(trials) if trials else 0}")
            return jsonify({'status': 'error', 'message': '試行インデックスエラー'})
            
        trial_data = trials[trial_idx]
        trial_type = trial_data['type']  # 'congruent' または 'incongruent'
        
        # 表示色を取得（文字の色に応じて反応する）
        display_color = trial_data.get('display_color', trial_data['text_color'])
        correct_key = RESPONSE_KEYS[display_color]
        
        # 反応があったかどうか
        has_response = data.get('response') is not None
        response_key = data.get('response')
        
        # 正誤判定（表示色に応じたキーが押されたか）
        is_correct = (response_key == correct_key) if has_response else False
        
        # 結果を記録
        result = {
            'trial': trial_idx + 1,
            'text': trial_data['text'],
            'text_color': trial_data['text_color'],
            'display_color': display_color,
            'trial_type': trial_type,
            'response': response_key,
            'correct_key': correct_key,
            'reaction_time': data.get('reaction_time'),
            'is_correct': is_correct
        }
        
        print(f"記録する結果: {result}")  # デバッグ用
        
        # セッションから結果リストを取得（なければ新規作成）
        if 'results' not in session:
            session['results'] = []
        
        results = session.get('results', [])
        results.append(result)
        session['results'] = results
        
        return jsonify({'status': 'success', 'recorded': True})
    except Exception as e:
        print(f"エラー発生: {str(e)}")
        import traceback
        traceback.print_exc()  # より詳細なエラー情報
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/results')
def show_results():
    try:
        results = session.get('results', [])
        
        if not results:
            print("結果がありません")
            return render_template('stroopindex.html', error='結果がありません', template='results')
        
        print(f"結果件数: {len(results)}")
        
        # 集計データを準備
        total_trials = len(results)
        correct_trials = sum(1 for r in results if r.get('is_correct', False))
        accuracy = correct_trials / total_trials * 100 if total_trials > 0 else 0
        
        # 条件別の集計
        congruent_results = [r for r in results if r.get('trial_type') == 'congruent']
        incongruent_results = [r for r in results if r.get('trial_type') == 'incongruent']
        
        # 一致条件の集計
        congruent_total = len(congruent_results)
        congruent_correct = sum(1 for r in congruent_results if r.get('is_correct', False))
        congruent_accuracy = congruent_correct / congruent_total * 100 if congruent_total > 0 else 0
        congruent_rts = [r.get('reaction_time', 0) for r in congruent_results if r.get('reaction_time') is not None and r.get('is_correct', False)]
        congruent_avg_rt = sum(congruent_rts) / len(congruent_rts) if congruent_rts else 0
        
        # 不一致条件の集計
        incongruent_total = len(incongruent_results)
        incongruent_correct = sum(1 for r in incongruent_results if r.get('is_correct', False))
        incongruent_accuracy = incongruent_correct / incongruent_total * 100 if incongruent_total > 0 else 0
        incongruent_rts = [r.get('reaction_time', 0) for r in incongruent_results if r.get('reaction_time') is not None and r.get('is_correct', False)]
        incongruent_avg_rt = sum(incongruent_rts) / len(incongruent_rts) if incongruent_rts else 0
        
        # ストループ効果（不一致 - 一致の反応時間差）の計算
        stroop_effect = incongruent_avg_rt - congruent_avg_rt
        
        summary = {
            'total_trials': total_trials,
            'accuracy': round(accuracy, 2),
            'congruent_total': congruent_total,
            'congruent_accuracy': round(congruent_accuracy, 2),
            'congruent_avg_rt': round(congruent_avg_rt, 2),
            'incongruent_total': incongruent_total,
            'incongruent_accuracy': round(incongruent_accuracy, 2),
            'incongruent_avg_rt': round(incongruent_avg_rt, 2),
            'stroop_effect': round(stroop_effect, 2)
        }
        
        print(f"サマリー: {summary}")
        
        # 試行ごとのデータ
        trial_data = []
        for r in results:
            trial_data.append({
                'trial': r.get('trial', 0),
                'text': r.get('text', ''),
                'text_color': r.get('text_color', ''),
                'display_color': r.get('display_color', ''),
                'trial_type': r.get('trial_type', ''),
                'response': r.get('response'),
                'correct_key': r.get('correct_key', ''),
                'reaction_time': round(r.get('reaction_time', 0), 2) if r.get('reaction_time') else None,
                'is_correct': r.get('is_correct', False)
            })
        
        return render_template('stroopindex.html', summary=summary, trial_data=trial_data, template='results')
    except Exception as e:
        print(f"結果表示エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('stroopindex.html', error=f'エラーが発生しました: {str(e)}', template='results')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)

