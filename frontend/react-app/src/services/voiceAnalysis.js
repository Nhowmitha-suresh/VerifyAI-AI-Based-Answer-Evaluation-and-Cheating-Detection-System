// Lightweight client-side voice analysis with optional backend fallback
// Exports analyzeTranscript(transcript, durationSeconds)

export async function analyzeTranscript(transcript = '', durationSeconds = 0) {
  // Basic local analysis: count filler words and compute speaking speed
  const fillers = ['um', 'uh', 'like', 'you know', 'so', 'actually']
  const text = (transcript || '').toLowerCase()
  const words = text.trim().split(/\s+/).filter(Boolean)
  const wordCount = words.length

  let fillerCount = 0
  for (const f of fillers) {
    const re = new RegExp('\\b' + f.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&') + '\\b', 'g')
    const m = text.match(re)
    if (m) fillerCount += m.length
  }

  const speakingSpeed = durationSeconds > 0 ? (wordCount / Math.max(0.1, durationSeconds)) : 0
  const fillerRatio = wordCount > 0 ? (fillerCount / wordCount) : 0

  // confidence_score is heuristic: based on length and filler ratio
  const confidenceScore = Math.max(0, 100 * Math.min(1, (1 - fillerRatio) * Math.min(1, wordCount / 50)))

  return {
    filler_ratio: Number(fillerRatio.toFixed(3)),
    speaking_speed: Number(speakingSpeed.toFixed(3)),
    confidence_score: Number(confidenceScore.toFixed(1))
  }
}

export default { analyzeTranscript }
