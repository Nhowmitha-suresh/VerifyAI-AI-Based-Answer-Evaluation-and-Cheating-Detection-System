// Simple attention tracking helpers for frontend
// assessFacePredictions(predictions, lastSeenTimestamp)
// predictions: array of objects {class: 'person', bbox: [x,y,w,h], score}

export function assessFacePredictions(predictions = [], lastSeenAt = 0) {
  const now = Date.now()
  const timeAwaySeconds = lastSeenAt ? Math.max(0, Math.floor((now - lastSeenAt) / 1000)) : 0

  const personPreds = (predictions || []).filter(p => {
    const cls = (p.class || p.className || p.label || '').toLowerCase()
    return cls === 'person' || cls === 'face'
  })

  const faceCount = personPreds.length
  const alerts = []
  if (faceCount === 0 && timeAwaySeconds >= 2) alerts.push('no_face')
  if (faceCount > 1) alerts.push('multiple_faces')

  // basic position detection using bbox center
  let position = 'center'
  if (personPreds[0] && personPreds[0].bbox) {
    const b = personPreds[0].bbox
    const cx = b[0] + (b[2] / 2)
    // assume video width ~640; normalize
    const rel = cx / 640
    if (rel < 0.35) position = 'left'
    else if (rel > 0.65) position = 'right'
  }

  // attention score heuristic: penalize no face, multiple faces, time away
  let attention = 100
  if (alerts.includes('no_face')) attention -= Math.min(80, timeAwaySeconds * 15)
  if (alerts.includes('multiple_faces')) attention -= 40
  if (position !== 'center') attention -= 10
  attention = Math.max(0, Math.min(100, Math.round(attention)))

  return {
    attention_score: attention,
    face_count: faceCount,
    position,
    time_away_seconds: timeAwaySeconds,
    alerts
  }
}

export default { assessFacePredictions }
