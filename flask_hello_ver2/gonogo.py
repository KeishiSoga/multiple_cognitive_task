from flask import Flask, render_template, request, jsonify, session
import random
import time
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = "gonogo_task_secret_key"
app.config['SESSION_TYPE'] = 'filesystem'

# Go/NoGo刺激の種類
# Go刺激：反応が必要（緑色の○）
# NoGo刺激：反応を抑制する必要がある（赤色の○）
STIMULI = {
    'go': 'go',      # Go刺激（反応が必要）
    'nogo': 'nogo'   # NoGo刺激（反応を抑制）
}

# 刺激の提示時間と刺激間隔時間（ミリ秒）
STIMULUS_DURATION = 500   # 0.5秒（刺激表示時間）
ISI_DURATION = 1500       # 1.5秒（刺激間隔時間、ブランク表示時間）
MAX_RESPONSE_TIME = STIMULUS_DURATION + ISI_DURATION  # 最大反応時間（2.0秒）

# 反応キーの設定
RESPONSE_KEY = 'space'  # スペースキーで反応

@app.route('/')
def index():
    # セッションを初期化
    session['trials'] = []
    session['current_trial'] = 0
    session['results'] = []
    session['start_time'] = None
    print("セッション初期化完了")  # デバッグ用
    return render_template('gonogoindex.html', template='index')

@app.route('/start', methods=['POST'])
def start():
    # 試行回数を設定（デフォルト：Go刺激20回、NoGo刺激10回、計30試行）
    go_trials = int(request.form.get('go_trials', 20))
    nogo_trials = int(request.form.get('nogo_trials', 10))
    print(f"開始: Go刺激 {go_trials} 回、NoGo刺激 {nogo_trials} 回")  # デバッグ用
    
    # 各刺激をランダムに配置した試行リストを作成
    trials = []
    # Go刺激を追加
    for _ in range(go_trials):
        trials.append({'type': 'go', 'stimulus': STIMULI['go']})
    # NoGo刺激を追加
    for _ in range(nogo_trials):
        trials.append({'type': 'nogo', 'stimulus': STIMULI['nogo']})
    
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
    
    print(f"刺激: {trial_data['stimulus']} ({trial_data['type']})")  # デバッグ用
    
    return jsonify({
        'status': 'next',
        'stimulus': trial_data['stimulus'],
        'trial_type': trial_data['type'],
        'trial_number': current_trial + 1,
        'total_trials': len(trials),
        'stimulus_duration': STIMULUS_DURATION,
        'isi_duration': ISI_DURATION,
        'max_response_time': MAX_RESPONSE_TIME,
        'response_key': RESPONSE_KEY
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
        trial_type = trial_data['type']  # 'go' または 'nogo'
        stimulus = trial_data['stimulus']  # 'go' または 'nogo'
        
        # 反応があったかどうか
        has_response = data.get('response') is not None
        
        # 正誤判定
        if trial_type == 'go':
            # Go刺激：反応があれば正解、なければエラー（ミス）
            is_correct = has_response
            error_type = 'miss' if not has_response else None
        else:  # nogo
            # NoGo刺激：反応がなければ正解、あればエラー（誤反応）
            is_correct = not has_response
            error_type = 'false_alarm' if has_response else None
        
        # 結果を記録
        result = {
            'trial': trial_idx + 1,
            'stimulus': stimulus,
            'trial_type': trial_type,
            'response': data.get('response'),
            'reaction_time': data.get('reaction_time'),
            'is_correct': is_correct,
            'error_type': error_type
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
            return render_template('gonogoindex.html', error='結果がありません', template='results')
        
        print(f"結果件数: {len(results)}")
        
        # 集計データを準備
        total_trials = len(results)
        correct_trials = sum(1 for r in results if r.get('is_correct', False))
        accuracy = correct_trials / total_trials * 100 if total_trials > 0 else 0
        
        # Go条件の集計
        go_results = [r for r in results if r.get('trial_type') == 'go']
        go_total = len(go_results)
        go_correct = sum(1 for r in go_results if r.get('is_correct', False))
        go_accuracy = go_correct / go_total * 100 if go_total > 0 else 0
        go_rts = [r.get('reaction_time', 0) for r in go_results if r.get('reaction_time') is not None]
        go_avg_rt = sum(go_rts) / len(go_rts) if go_rts else 0
        go_misses = sum(1 for r in go_results if r.get('error_type') == 'miss')
        
        # NoGo条件の集計
        nogo_results = [r for r in results if r.get('trial_type') == 'nogo']
        nogo_total = len(nogo_results)
        nogo_correct = sum(1 for r in nogo_results if r.get('is_correct', False))
        nogo_accuracy = nogo_correct / nogo_total * 100 if nogo_total > 0 else 0
        nogo_false_alarms = sum(1 for r in nogo_results if r.get('error_type') == 'false_alarm')
        
        summary = {
            'total_trials': total_trials,
            'accuracy': round(accuracy, 2),
            'go_total': go_total,
            'go_accuracy': round(go_accuracy, 2),
            'go_avg_rt': round(go_avg_rt, 2),
            'go_misses': go_misses,
            'nogo_total': nogo_total,
            'nogo_accuracy': round(nogo_accuracy, 2),
            'nogo_false_alarms': nogo_false_alarms
        }
        
        print(f"サマリー: {summary}")
        
        # 試行ごとのデータ
        trial_data = []
        for r in results:
            trial_data.append({
                'trial': r.get('trial', 0),
                'stimulus': r.get('stimulus', ''),
                'trial_type': r.get('trial_type', ''),
                'response': r.get('response'),
                'reaction_time': round(r.get('reaction_time', 0), 2) if r.get('reaction_time') else None,
                'is_correct': r.get('is_correct', False),
                'error_type': r.get('error_type', '')
            })
        
        return render_template('gonogoindex.html', summary=summary, trial_data=trial_data, template='results')
    except Exception as e:
        print(f"結果表示エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('gonogoindex.html', error=f'エラーが発生しました: {str(e)}', template='results')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)

