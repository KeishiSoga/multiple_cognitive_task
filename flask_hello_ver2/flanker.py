from flask import Flask, render_template, request, jsonify, session
import random
import time
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = "flanker_task_secret_key"
app.config['SESSION_TYPE'] = 'filesystem'

# フランカー刺激の種類
STIMULI = [
    "<<<<<",  # 一致条件
    ">>>>>",  # 一致条件
    "<<><<",  # 不一致条件
    ">><>>"   # 不一致条件
]

# 刺激の提示時間とブランク時間（ミリ秒）
STIMULUS_DURATION = 300  # 0.3秒
BLANK_DURATION = 1500    # 1.5秒
MAX_RESPONSE_TIME = STIMULUS_DURATION + BLANK_DURATION  # 最大反応時間（1.8秒）

# 反応キーの設定
LEFT_KEY = 'c'  # 左方向の反応キー
RIGHT_KEY = 'm'  # 右方向の反応キー

# 刺激の表示スタイル設定
# HTMLでエスケープするために使用
STIMULUS_DISPLAY = {
    ">>>>>": "&gt;&gt;&gt;&gt;&gt;",
    "<<<<<": "&lt;&lt;&lt;&lt;&lt;",
    ">><>>": "&gt;&gt;&lt;&gt;&gt;",
    "<<><<": "&lt;&lt;&gt;&lt;&lt;"
}

@app.route('/')
def index():
    # セッションを初期化
    session['trials'] = []
    session['current_trial'] = 0
    session['results'] = []
    session['start_time'] = None
    print("セッション初期化完了")  # デバッグ用
    return render_template('flankerindex.html', template='index')

@app.route('/start', methods=['POST'])
def start():
    # 試行回数を設定（デフォルト：各刺激5回ずつ、計20試行）
    trials_per_stimulus = int(request.form.get('trials_per_stimulus', 5))
    print(f"開始: 各刺激 {trials_per_stimulus} 回")  # デバッグ用
    
    # 各刺激をランダムに配置した試行リストを作成
    trials = []
    for stimulus in STIMULI:
        for _ in range(trials_per_stimulus):
            trials.append(stimulus)
    
    random.shuffle(trials)
    print(f"試行リスト: {trials}")  # デバッグ用
    
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
    stimulus = trials[current_trial]
    session['current_trial'] = current_trial + 1
    
    print(f"刺激: {stimulus}")  # デバッグ用
    
    return jsonify({
        'status': 'next',
        'stimulus': stimulus,
        'stimulus_display': STIMULUS_DISPLAY.get(stimulus, stimulus),
        'trial_number': current_trial + 1,
        'total_trials': len(trials),
        'stimulus_duration': STIMULUS_DURATION,
        'blank_duration': BLANK_DURATION,
        'left_key': LEFT_KEY,
        'right_key': RIGHT_KEY
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
            
        stimulus = trials[trial_idx]
        
        # 反応が正しいかどうかを判定
        correct_response = 'left' if stimulus[2] == '<' else 'right'
        is_correct = data.get('response') == correct_response
        
        # 試行タイプを判定（一致・不一致）
        trial_type = 'congruent' if stimulus[0] == stimulus[2] else 'incongruent'
        
        # 結果を記録
        result = {
            'trial': trial_idx + 1,
            'stimulus': stimulus,
            'response': data.get('response'),
            'reaction_time': data.get('reaction_time'),
            'is_correct': is_correct,
            'trial_type': trial_type
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
            return render_template('flankerindex.html', error='結果がありません', template='results')
        
        print(f"結果件数: {len(results)}")
        
        # 集計データを準備
        total_trials = len(results)
        correct_trials = sum(1 for r in results if r.get('is_correct', False))
        accuracy = correct_trials / total_trials * 100 if total_trials > 0 else 0
        
        correct_rts = [r.get('reaction_time', 0) for r in results if r.get('is_correct', False)]
        avg_rt = sum(correct_rts) / len(correct_rts) if correct_rts else 0
        
        # 条件別の集計
        congruent_results = [r for r in results if r.get('trial_type') == 'congruent']
        incongruent_results = [r for r in results if r.get('trial_type') == 'incongruent']
        
        # 一致条件の集計
        congruent_correct = sum(1 for r in congruent_results if r.get('is_correct', False))
        congruent_accuracy = congruent_correct / len(congruent_results) * 100 if congruent_results else 0
        congruent_rts = [r.get('reaction_time', 0) for r in congruent_results if r.get('is_correct', False)]
        congruent_avg_rt = sum(congruent_rts) / len(congruent_rts) if congruent_rts else 0
        
        # 不一致条件の集計
        incongruent_correct = sum(1 for r in incongruent_results if r.get('is_correct', False))
        incongruent_accuracy = incongruent_correct / len(incongruent_results) * 100 if incongruent_results else 0
        incongruent_rts = [r.get('reaction_time', 0) for r in incongruent_results if r.get('is_correct', False)]
        incongruent_avg_rt = sum(incongruent_rts) / len(incongruent_rts) if incongruent_rts else 0
        
        # 干渉効果（不一致 - 一致）の計算
        interference_effect = incongruent_avg_rt - congruent_avg_rt
        
        summary = {
            'total_trials': total_trials,
            'accuracy': round(accuracy, 2),
            'avg_rt': round(avg_rt, 2),
            'congruent_accuracy': round(congruent_accuracy, 2),
            'congruent_avg_rt': round(congruent_avg_rt, 2),
            'incongruent_accuracy': round(incongruent_accuracy, 2),
            'incongruent_avg_rt': round(incongruent_avg_rt, 2),
            'interference_effect': round(interference_effect, 2)
        }
        
        print(f"サマリー: {summary}")
        
        # 試行ごとのデータ
        trial_data = []
        for r in results:
            trial_data.append({
                'trial': r.get('trial', 0),
                'stimulus': r.get('stimulus', ''),
                'response': r.get('response'),
                'reaction_time': round(r.get('reaction_time', 0), 2),
                'is_correct': r.get('is_correct', False),
                'trial_type': r.get('trial_type', '')
            })
        
        return render_template('flankerindex.html', summary=summary, trial_data=trial_data, template='results')
    except Exception as e:
        print(f"結果表示エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('flankerindex.html', error=f'エラーが発生しました: {str(e)}', template='results')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)