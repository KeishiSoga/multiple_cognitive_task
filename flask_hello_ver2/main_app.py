from flask import Flask, render_template, request, jsonify, session
import random
import time
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = "main_task_secret_key"
app.config['SESSION_TYPE'] = 'filesystem'

# ===== メイン画面 =====
@app.route('/')
def index():
    """課題選択画面"""
    return render_template('task_selection.html')

# ===== Flanker課題 =====
# フランカー刺激の種類
STIMULI_FLANKER = [
    "<<<<<",  # 一致条件
    ">>>>>",  # 一致条件
    "<<><<",  # 不一致条件
    ">><>>"   # 不一致条件
]

STIMULUS_DURATION_FLANKER = 300  # 0.3秒
BLANK_DURATION_FLANKER = 1500    # 1.5秒
LEFT_KEY = 'c'  # 左方向の反応キー
RIGHT_KEY = 'm'  # 右方向の反応キー

STIMULUS_DISPLAY = {
    ">>>>>": "&gt;&gt;&gt;&gt;&gt;",
    "<<<<<": "&lt;&lt;&lt;&lt;&lt;",
    ">><>>": "&gt;&gt;&lt;&gt;&gt;",
    "<<><<": "&lt;&lt;&gt;&lt;&lt;"
}

@app.route('/flanker')
def flanker_index():
    session['trials'] = []
    session['current_trial'] = 0
    session['results'] = []
    session['start_time'] = None
    return render_template('flankerindex.html', template='index')

@app.route('/flanker/start', methods=['POST'])
def flanker_start():
    trials_per_stimulus = int(request.form.get('trials_per_stimulus', 5))
    trials = []
    for stimulus in STIMULI_FLANKER:
        for _ in range(trials_per_stimulus):
            trials.append(stimulus)
    random.shuffle(trials)
    session['trials'] = trials
    session['current_trial'] = 0
    session['results'] = []
    session['start_time'] = time.time()
    return jsonify({'status': 'success', 'total_trials': len(trials)})

@app.route('/flanker/next_trial')
def flanker_next_trial():
    trials = session.get('trials', [])
    current_trial = session.get('current_trial', 0)
    if current_trial >= len(trials):
        return jsonify({'status': 'completed'})
    stimulus = trials[current_trial]
    session['current_trial'] = current_trial + 1
    return jsonify({
        'status': 'next',
        'stimulus': stimulus,
        'stimulus_display': STIMULUS_DISPLAY.get(stimulus, stimulus),
        'trial_number': current_trial + 1,
        'total_trials': len(trials),
        'stimulus_duration': STIMULUS_DURATION_FLANKER,
        'blank_duration': BLANK_DURATION_FLANKER,
        'left_key': LEFT_KEY,
        'right_key': RIGHT_KEY
    })

@app.route('/flanker/record_response', methods=['POST'])
def flanker_record_response():
    try:
        data = request.get_json()
        trial_idx = session.get('current_trial', 0) - 1
        if trial_idx < 0:
            return jsonify({'status': 'error', 'message': '試行が開始されていません'})
        trials = session.get('trials', [])
        if not trials or trial_idx >= len(trials):
            return jsonify({'status': 'error', 'message': '試行インデックスエラー'})
        stimulus = trials[trial_idx]
        correct_response = 'left' if stimulus[2] == '<' else 'right'
        is_correct = data.get('response') == correct_response
        trial_type = 'congruent' if stimulus[0] == stimulus[2] else 'incongruent'
        result = {
            'trial': trial_idx + 1,
            'stimulus': stimulus,
            'response': data.get('response'),
            'reaction_time': data.get('reaction_time'),
            'is_correct': is_correct,
            'trial_type': trial_type
        }
        if 'results' not in session:
            session['results'] = []
        results = session.get('results', [])
        results.append(result)
        session['results'] = results
        return jsonify({'status': 'success', 'recorded': True})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/flanker/results')
def flanker_results():
    try:
        results = session.get('results', [])
        if not results:
            return render_template('flankerindex.html', error='結果がありません', template='results')
        total_trials = len(results)
        correct_trials = sum(1 for r in results if r.get('is_correct', False))
        accuracy = correct_trials / total_trials * 100 if total_trials > 0 else 0
        correct_rts = [r.get('reaction_time', 0) for r in results if r.get('is_correct', False)]
        avg_rt = sum(correct_rts) / len(correct_rts) if correct_rts else 0
        congruent_results = [r for r in results if r.get('trial_type') == 'congruent']
        incongruent_results = [r for r in results if r.get('trial_type') == 'incongruent']
        congruent_correct = sum(1 for r in congruent_results if r.get('is_correct', False))
        congruent_accuracy = congruent_correct / len(congruent_results) * 100 if congruent_results else 0
        congruent_rts = [r.get('reaction_time', 0) for r in congruent_results if r.get('is_correct', False)]
        congruent_avg_rt = sum(congruent_rts) / len(congruent_rts) if congruent_rts else 0
        incongruent_correct = sum(1 for r in incongruent_results if r.get('is_correct', False))
        incongruent_accuracy = incongruent_correct / len(incongruent_results) * 100 if incongruent_results else 0
        incongruent_rts = [r.get('reaction_time', 0) for r in incongruent_results if r.get('is_correct', False)]
        incongruent_avg_rt = sum(incongruent_rts) / len(incongruent_rts) if incongruent_rts else 0
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
        return render_template('flankerindex.html', error=f'エラーが発生しました: {str(e)}', template='results')

# ===== Go/NoGo課題 =====
STIMULI_GONOGO = {'go': 'go', 'nogo': 'nogo'}
STIMULUS_DURATION_GONOGO = 500
ISI_DURATION_GONOGO = 1500
RESPONSE_KEY_GONOGO = 'space'

@app.route('/gonogo')
def gonogo_index():
    session['trials'] = []
    session['current_trial'] = 0
    session['results'] = []
    session['start_time'] = None
    return render_template('gonogoindex.html', template='index')

@app.route('/gonogo/start', methods=['POST'])
def gonogo_start():
    go_trials = int(request.form.get('go_trials', 20))
    nogo_trials = int(request.form.get('nogo_trials', 10))
    trials = []
    for _ in range(go_trials):
        trials.append({'type': 'go', 'stimulus': STIMULI_GONOGO['go']})
    for _ in range(nogo_trials):
        trials.append({'type': 'nogo', 'stimulus': STIMULI_GONOGO['nogo']})
    random.shuffle(trials)
    session['trials'] = trials
    session['current_trial'] = 0
    session['results'] = []
    session['start_time'] = time.time()
    return jsonify({'status': 'success', 'total_trials': len(trials)})

@app.route('/gonogo/next_trial')
def gonogo_next_trial():
    trials = session.get('trials', [])
    current_trial = session.get('current_trial', 0)
    if current_trial >= len(trials):
        return jsonify({'status': 'completed'})
    trial_data = trials[current_trial]
    session['current_trial'] = current_trial + 1
    return jsonify({
        'status': 'next',
        'stimulus': trial_data['stimulus'],
        'trial_type': trial_data['type'],
        'trial_number': current_trial + 1,
        'total_trials': len(trials),
        'stimulus_duration': STIMULUS_DURATION_GONOGO,
        'isi_duration': ISI_DURATION_GONOGO,
        'max_response_time': STIMULUS_DURATION_GONOGO + ISI_DURATION_GONOGO,
        'response_key': RESPONSE_KEY_GONOGO
    })

@app.route('/gonogo/record_response', methods=['POST'])
def gonogo_record_response():
    try:
        data = request.get_json()
        trial_idx = session.get('current_trial', 0) - 1
        if trial_idx < 0:
            return jsonify({'status': 'error', 'message': '試行が開始されていません'})
        trials = session.get('trials', [])
        if not trials or trial_idx >= len(trials):
            return jsonify({'status': 'error', 'message': '試行インデックスエラー'})
        trial_data = trials[trial_idx]
        trial_type = trial_data['type']
        has_response = data.get('response') is not None
        if trial_type == 'go':
            is_correct = has_response
            error_type = 'miss' if not has_response else None
        else:
            is_correct = not has_response
            error_type = 'false_alarm' if has_response else None
        result = {
            'trial': trial_idx + 1,
            'stimulus': trial_data['stimulus'],
            'trial_type': trial_type,
            'response': data.get('response'),
            'reaction_time': data.get('reaction_time'),
            'is_correct': is_correct,
            'error_type': error_type
        }
        if 'results' not in session:
            session['results'] = []
        results = session.get('results', [])
        results.append(result)
        session['results'] = results
        return jsonify({'status': 'success', 'recorded': True})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/gonogo/results')
def gonogo_results():
    try:
        results = session.get('results', [])
        if not results:
            return render_template('gonogoindex.html', error='結果がありません', template='results')
        total_trials = len(results)
        correct_trials = sum(1 for r in results if r.get('is_correct', False))
        accuracy = correct_trials / total_trials * 100 if total_trials > 0 else 0
        go_results = [r for r in results if r.get('trial_type') == 'go']
        go_total = len(go_results)
        go_correct = sum(1 for r in go_results if r.get('is_correct', False))
        go_accuracy = go_correct / go_total * 100 if go_total > 0 else 0
        go_rts = [r.get('reaction_time', 0) for r in go_results if r.get('reaction_time') is not None]
        go_avg_rt = sum(go_rts) / len(go_rts) if go_rts else 0
        go_misses = sum(1 for r in go_results if r.get('error_type') == 'miss')
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
        return render_template('gonogoindex.html', error=f'エラーが発生しました: {str(e)}', template='results')

# ===== Stroop課題 =====
COLORS_STROOP = {
    'red': {'name': 'あか', 'color': '#dc3545'},
    'blue': {'name': 'あお', 'color': '#007bff'},
    'yellow': {'name': 'きいろ', 'color': '#ffc107'},
    'green': {'name': 'みどり', 'color': '#28a745'}
}
STIMULUS_DURATION_STROOP = 500
ISI_DURATION_STROOP = 1500
RESPONSE_KEYS_STROOP = {
    'red': '1', 'blue': '2', 'yellow': '3', 'green': '4'
}

@app.route('/stroop')
def stroop_index():
    session['trials'] = []
    session['current_trial'] = 0
    session['results'] = []
    session['start_time'] = None
    return render_template('stroopindex.html', template='index')

@app.route('/stroop/start', methods=['POST'])
def stroop_start():
    congruent_trials = int(request.form.get('congruent_trials', 20))
    incongruent_trials = int(request.form.get('incongruent_trials', 20))
    trials = []
    color_list = list(COLORS_STROOP.keys())
    for _ in range(congruent_trials):
        color = random.choice(color_list)
        trials.append({
            'type': 'congruent',
            'text': COLORS_STROOP[color]['name'],
            'text_color': color,
            'display_color': color
        })
    for _ in range(incongruent_trials):
        text_color = random.choice(color_list)
        display_color_options = [c for c in color_list if c != text_color]
        display_color = random.choice(display_color_options)
        trials.append({
            'type': 'incongruent',
            'text': COLORS_STROOP[text_color]['name'],
            'text_color': text_color,
            'display_color': display_color
        })
    random.shuffle(trials)
    session['trials'] = trials
    session['current_trial'] = 0
    session['results'] = []
    session['start_time'] = time.time()
    return jsonify({'status': 'success', 'total_trials': len(trials)})

@app.route('/stroop/next_trial')
def stroop_next_trial():
    trials = session.get('trials', [])
    current_trial = session.get('current_trial', 0)
    if current_trial >= len(trials):
        return jsonify({'status': 'completed'})
    trial_data = trials[current_trial]
    session['current_trial'] = current_trial + 1
    if trial_data['type'] == 'congruent':
        display_color_code = COLORS_STROOP[trial_data['text_color']]['color']
    else:
        display_color_code = COLORS_STROOP[trial_data['display_color']]['color']
    return jsonify({
        'status': 'next',
        'text': trial_data['text'],
        'text_color': trial_data['text_color'],
        'display_color': trial_data.get('display_color', trial_data['text_color']),
        'display_color_code': display_color_code,
        'trial_type': trial_data['type'],
        'trial_number': current_trial + 1,
        'total_trials': len(trials),
        'stimulus_duration': STIMULUS_DURATION_STROOP,
        'isi_duration': ISI_DURATION_STROOP,
        'max_response_time': STIMULUS_DURATION_STROOP + ISI_DURATION_STROOP,
        'response_keys': RESPONSE_KEYS_STROOP
    })

@app.route('/stroop/record_response', methods=['POST'])
def stroop_record_response():
    try:
        data = request.get_json()
        trial_idx = session.get('current_trial', 0) - 1
        if trial_idx < 0:
            return jsonify({'status': 'error', 'message': '試行が開始されていません'})
        trials = session.get('trials', [])
        if not trials or trial_idx >= len(trials):
            return jsonify({'status': 'error', 'message': '試行インデックスエラー'})
        trial_data = trials[trial_idx]
        display_color = trial_data.get('display_color', trial_data['text_color'])
        correct_key = RESPONSE_KEYS_STROOP[display_color]
        has_response = data.get('response') is not None
        response_key = data.get('response')
        is_correct = (response_key == correct_key) if has_response else False
        result = {
            'trial': trial_idx + 1,
            'text': trial_data['text'],
            'text_color': trial_data['text_color'],
            'display_color': display_color,
            'trial_type': trial_data['type'],
            'response': response_key,
            'correct_key': correct_key,
            'reaction_time': data.get('reaction_time'),
            'is_correct': is_correct
        }
        if 'results' not in session:
            session['results'] = []
        results = session.get('results', [])
        results.append(result)
        session['results'] = results
        return jsonify({'status': 'success', 'recorded': True})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/stroop/results')
def stroop_results():
    try:
        results = session.get('results', [])
        if not results:
            return render_template('stroopindex.html', error='結果がありません', template='results')
        total_trials = len(results)
        correct_trials = sum(1 for r in results if r.get('is_correct', False))
        accuracy = correct_trials / total_trials * 100 if total_trials > 0 else 0
        congruent_results = [r for r in results if r.get('trial_type') == 'congruent']
        incongruent_results = [r for r in results if r.get('trial_type') == 'incongruent']
        congruent_total = len(congruent_results)
        congruent_correct = sum(1 for r in congruent_results if r.get('is_correct', False))
        congruent_accuracy = congruent_correct / congruent_total * 100 if congruent_total > 0 else 0
        congruent_rts = [r.get('reaction_time', 0) for r in congruent_results if r.get('reaction_time') is not None and r.get('is_correct', False)]
        congruent_avg_rt = sum(congruent_rts) / len(congruent_rts) if congruent_rts else 0
        incongruent_total = len(incongruent_results)
        incongruent_correct = sum(1 for r in incongruent_results if r.get('is_correct', False))
        incongruent_accuracy = incongruent_correct / incongruent_total * 100 if incongruent_total > 0 else 0
        incongruent_rts = [r.get('reaction_time', 0) for r in incongruent_results if r.get('reaction_time') is not None and r.get('is_correct', False)]
        incongruent_avg_rt = sum(incongruent_rts) / len(incongruent_rts) if incongruent_rts else 0
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
        return render_template('stroopindex.html', error=f'エラーが発生しました: {str(e)}', template='results')

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5006))
    app.run(debug=False, host='0.0.0.0', port=port)

