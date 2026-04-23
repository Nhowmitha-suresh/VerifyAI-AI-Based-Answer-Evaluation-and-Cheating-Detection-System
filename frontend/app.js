document.addEventListener('DOMContentLoaded',()=>{
  // Tabs (reuse existing tab buttons to switch panes)
  const tabs=document.querySelectorAll('.tab');
  const panes=document.querySelectorAll('.pane');
  tabs.forEach((t,i)=>t.addEventListener('click',()=>{
    tabs.forEach(x=>x.classList.remove('active'))
    panes.forEach(p=>p.style.display='none')
    t.classList.add('active')
    panes[i].style.display='block'
  }))

  // Orb & mic interactions
  const micBtn = document.getElementById('micBtn')
  const orb = document.getElementById('orb')
  const status = document.getElementById('status')
  const analyzeText = document.getElementById('analyzeText')
  const truthScoreEl = document.getElementById('truthScore')
  const tagsEl = document.getElementById('tags')
  const historyList = document.getElementById('historyList')

  let history = []

  function setPane(name){
    document.querySelectorAll('.pane').forEach(p=>p.style.display='none')
    const map = { home:'.home-pane', analysis:'.analysis-pane', result:'.result-pane', history:'.history-pane' }
    const sel = document.querySelector(map[name])
    if(sel) sel.style.display='block'
  }

  function simulateAnalysis(inputText){
    setPane('analysis')
    document.getElementById('sourceType').textContent = 'Voice'
    status.textContent = 'Analyzing…'
    orb.classList.remove('listening')
    orb.classList.add('analyzing')

    // fake async analysis
    setTimeout(()=>{
      const tokens = mockTokenize(inputText)
      renderAnalysis(tokens)
      const score = Math.max(12, Math.round(100 - tokens.filter(t=>t.label==='red').length * 12))
      truthScoreEl.textContent = score + '%'
      // tags
      const tags = deriveTags(tokens)
      tagsEl.innerHTML = ''
      tags.forEach(t=>{const el=document.createElement('div');el.className='tag';el.textContent=t;tagsEl.appendChild(el)})

      // push history
      const entry = {score, text:inputText, tags, time: new Date().toLocaleString() }
      history.unshift(entry)
      renderHistory()

      // show result pane after a short delay
      setTimeout(()=>{
        setPane('result')
        document.getElementById('resultScore').textContent = score + '%'
        const resultTags = document.getElementById('resultTags')
        resultTags.innerHTML = ''
        tags.forEach(t=>{const s=document.createElement('div');s.className='tag';s.textContent=t;resultTags.appendChild(s)})
        document.getElementById('evidence').innerHTML = '<div class="card">AI: This might be misleading because the claim lacks primary sources.</div>'
        orb.classList.remove('analyzing')
        status.textContent = 'Analysis complete'
      },700)
    },1200)
  }

  function mockTokenize(text){
    // naive split and randomly assign labels for demo
    const parts = text.split(/(\s+)/).filter(Boolean)
    return parts.map(p=>{
      const r = Math.random()
      const label = r>0.85? 'red' : r>0.6? 'yellow' : 'green'
      return {text:p, label}
    })
  }

  function deriveTags(tokens){
    const reds = tokens.filter(t=>t.label==='red').length
    const yellows = tokens.filter(t=>t.label==='yellow').length
    const tags = []
    if(reds>2) tags.push('Emotionally biased')
    if(yellows>3) tags.push('Missing context')
    if(reds===0 && yellows<2) tags.push('Verified')
    return tags.length?tags:['Unclear']
  }

  function renderAnalysis(tokens){
    analyzeText.innerHTML = ''
    tokens.forEach(t=>{
      const span = document.createElement('span')
      span.className = 'token ' + (t.label==='red'? 'red' : t.label==='yellow'?'yellow':'green')
      span.textContent = t.text
      span.addEventListener('click', ()=> showExplain(t))
      analyzeText.appendChild(span)
    })
  }

  function showExplain(token){
    const ex = document.getElementById('explain')
    ex.textContent = `${token.text} — ${token.label==='red'?'High suspicion':'Requires more context'}`
  }

  function renderHistory(){
    historyList.innerHTML = ''
    history.forEach(h=>{
      const item = document.createElement('div')
      item.className = 'history-item'
      item.innerHTML = `<div class="mini-orb"></div><div style="flex:1"><div style="font-weight:700">${h.score}%</div><div style="color:var(--muted);font-size:13px">${h.time}</div></div><div class="tags">${h.tags.map(t=>`<div class=\"tag\">${t}</div>`).join('')}</div>`
      item.addEventListener('click', ()=>{
        setPane('analysis')
        analyzeText.textContent = h.text
        truthScoreEl.textContent = h.score + '%'
      })
      historyList.appendChild(item)
    })
  }

  // Mic button behavior
  if(micBtn){
    micBtn.addEventListener('click', ()=>{
      // start listening animation
      orb.classList.add('listening')
      status.textContent = 'Listening…'
      // simulate 2s of listening then analyze
      setTimeout(()=>{
        const sample = 'Recent studies show that drinking five cups of coffee cures chronic fatigue in all cases.'
        simulateAnalysis(sample)
      },2000)
    })
  }

  // initial render
  renderHistory()
})
