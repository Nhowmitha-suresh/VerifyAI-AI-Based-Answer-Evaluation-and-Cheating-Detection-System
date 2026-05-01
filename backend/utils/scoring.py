"""Combine metrics into final interview report and scores.
Lightweight scoring functions intended to be called by existing backend flows.
"""
def compute_final_report(attention_score=100, voice_metrics=None, integrity_score=100):
    vm = voice_metrics or {}
    voice_score = int(round((vm.get('confidence_score', 0) * 100 + (1 - vm.get('filler_ratio', 0)) * 100) / 2))
    final = int(round((attention_score * 0.4) + (voice_score * 0.4) + (integrity_score * 0.2)))

    strengths = []
    weaknesses = []
    suggestions = []

    if attention_score > 80:
        strengths.append('Good sustained attention')
    else:
        weaknesses.append('Attention lapses')
        suggestions.append('Try to keep eyes on camera and minimize distractions')

    if vm.get('filler_ratio', 0) < 0.05:
        strengths.append('Clear speech')
    else:
        weaknesses.append('Frequent filler words')
        suggestions.append('Reduce filler words like "um", "uh", "like"')

    if vm.get('speaking_speed', 0) < 1.0:
        suggestions.append('Consider increasing speaking pace slightly')

    return {
        'final_score': final,
        'attention_score': attention_score,
        'voice_score': voice_score,
        'integrity_score': integrity_score,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'suggestions': suggestions
    }
