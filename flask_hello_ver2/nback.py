from flask import Flask, render_template, request, jsonify, session
import random
import time
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = "nback_task_secret_key"
app.config['SESSION_TYPE'] = 'filesystem'

# 1-back課題の刺激（位置や文字など）
# 今回は位置（9つの位置）を使った1-back課題を作成
POSITIONS = [
    {'id': 1, 'name': '左上', 'grid': 'grid-1'},
    {'id': 2, 'name': '上', 'grid': 'grid-2'},
    {'id': 3, 'name': '右上', 'grid': 'grid-3'},
    {'id': 4, 'name': '左', 'grid': 'grid-4'},
    {'id': 5, 'name': '中央', 'grid': 'grid-5'},
    {'id': 6, 'name': '右', 'grid': 'grid-6'},
    {'id': 7, 'name': '左下', 'grid': 'grid-7'},
    {'id': 8, 'name': '下', 'grid': 'grid-8'},
    {'id': 9, 'name': '右下', 'grid': 'grid-9'}
]

# 刺激の提示時間と刺激間隔時間（ミリ秒）
STIMULUS_DURATION = 500   # 0.5秒（刺激表示時間）
ISI_DURATION = 2500       # 2.5秒（刺激間隔時間、ブランク表示時間）
MAX_RESPONSE_TIME = STIMULUS_DURATION + ISI_DURATION  # 最大反応時間（3.0秒）

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
    return render_template('nbackindex.html', template='index')

@app.route('/start', methods=['POST'])
def start():
    # 試行回数を設定（デフォルト：30試行、そのうち約30%が1-back一致）
    total_trials = int(request.form.get('total_trials', 30))
    print(f"開始: 総試行数 {total_trials} 回")  # デバッグ用
    
    # 試行リストを作成
    trials = []
    
    # 1-back一致の試行数を計算（約30%）
    nback_trials = int(total_trials * 0.3)
    
    # 最初の試行は必ず非一致（1-back比較ができないため）
    previous_position = None
    
    # 1-back一致の試行を配置
    nback_count = 0
    for i in range(total_trials):
        if i == 0:
            # 最初の試行はランダム
            position = random.choice(POSITIONS)
            trials.append({
                'trial_number': i + 1,
                'position': position,
                'is_nback': False  # 最初の試行は1-back比較不可
            })
            previous_position = position
        else:
            # 1-back一致の試行を配置するかどうか
            if nback_count < nback_trials and random.random() < 0.4:  # 40%の確率で1-back一致
                # 直前の位置と同じ位置を選択
                position = previous_position
                trials.append({
                    'trial_number': i + 1,
                    'position': position,
                    'is_nback': True
                })
                nback_count += 1
            else:
                # 直前の位置とは異なる位置を選択
                available_positions = [p for p in POSITIONS if p['id'] != previous_position['id']]
                position = random.choice(available_positions)
                trials.append({
                    'trial_number': i + 1,
                    'position': position,
                    'is_nback': False
                })
            previous_position = position
    
    print(f"試行リスト作成完了: {len(trials)} 試行（1-back一致: {nback_count}回）")  # デバッグ用
    
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
    
    print(f"刺激: 位置 {trial_data['position']['name']} (1-back一致: {trial_data['is_nback']})")  # デバッグ用
    
    return jsonify({
        'status': 'next',
        'position': trial_data['position'],
        'is_nback': trial_data['is_nback'],
        'trial_number': trial_data['trial_number'],
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
        is_nback = trial_data['is_nback']  # 1-back一致かどうか
        
        # 反応があったかどうか
        has_response = data.get('response') is not None
        
        # 正誤判定
        # 1-back一致の場合：反応があれば正解、なければエラー（ミス）
        # 1-back不一致の場合：反応がなければ正解、あればエラー（誤反応）
        if is_nback:
            is_correct = has_response
            error_type = 'miss' if not has_response else None
        else:
            is_correct = not has_response
            error_type = 'false_alarm' if has_response else None
        
        # 結果を記録
        result = {
            'trial': trial_data['trial_number'],
            'position': trial_data['position']['name'],
            'position_id': trial_data['position']['id'],
            'is_nback': is_nback,
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
            return render_template('nbackindex.html', error='結果がありません', template='results')
        
        print(f"結果件数: {len(results)}")
        
        # 集計データを準備
        total_trials = len(results)
        correct_trials = sum(1 for r in results if r.get('is_correct', False))
        accuracy = correct_trials / total_trials * 100 if total_trials > 0 else 0
        
        # 条件別の集計
        nback_results = [r for r in results if r.get('is_nback', False)]
        non_nback_results = [r for r in results if not r.get('is_nback', False)]
        
        # 1-back一致条件の集計
        nback_total = len(nback_results)
        nback_correct = sum(1 for r in nback_results if r.get('is_correct', False))
        nback_accuracy = nback_correct / nback_total * 100 if nback_total > 0 else 0
        nback_rts = [r.get('reaction_time', 0) for r in nback_results if r.get('reaction_time') is not None and r.get('is_correct', False)]
        nback_avg_rt = sum(nback_rts) / len(nback_rts) if nback_rts else 0
        nback_misses = sum(1 for r in nback_results if r.get('error_type') == 'miss')
        
        # 1-back不一致条件の集計
        non_nback_total = len(non_nback_results)
        non_nback_correct = sum(1 for r in non_nback_results if r.get('is_correct', False))
        non_nback_accuracy = non_nback_correct / non_nback_total * 100 if non_nback_total > 0 else 0
        non_nback_false_alarms = sum(1 for r in non_nback_results if r.get('error_type') == 'false_alarm')
        
        summary = {
            'total_trials': total_trials,
            'accuracy': round(accuracy, 2),
            'nback_total': nback_total,
            'nback_accuracy': round(nback_accuracy, 2),
            'nback_avg_rt': round(nback_avg_rt, 2),
            'nback_misses': nback_misses,
            'non_nback_total': non_nback_total,
            'non_nback_accuracy': round(non_nback_accuracy, 2),
            'non_nback_false_alarms': non_nback_false_alarms
        }
        
        print(f"サマリー: {summary}")
        
        # 試行ごとのデータ
        trial_data = []
        for r in results:
            trial_data.append({
                'trial': r.get('trial', 0),
                'position': r.get('position', ''),
                'is_nback': r.get('is_nback', False),
                'response': r.get('response'),
                'reaction_time': round(r.get('reaction_time', 0), 2) if r.get('reaction_time') else None,
                'is_correct': r.get('is_correct', False),
                'error_type': r.get('error_type', '')
            })
        
        return render_template('nbackindex.html', summary=summary, trial_data=trial_data, template='results')
    except Exception as e:
        print(f"結果表示エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('nbackindex.html', error=f'エラーが発生しました: {str(e)}', template='results')

if __name__ == '__main__':
    app.run(debug=True, port=5004)

