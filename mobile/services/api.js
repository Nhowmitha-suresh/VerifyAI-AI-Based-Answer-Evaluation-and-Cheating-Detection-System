/**
 * Mock API service for VerifyAI
 * analyzeText returns a Promise that resolves after 2s with mock data
 */
export async function analyzeText(inputText){
  return new Promise((resolve) => {
    setTimeout(()=>{
      // very small mock highlight logic: mark words with 'always' or 'never' as suspicious
      const words = inputText.split(/\s+/).filter(Boolean)
      const highlights = words.map(w=>({ word: w, type: /always|never|all/i.test(w)? 'suspicious' : (Math.random()>0.85? 'suspicious' : Math.random()>0.7? 'unclear' : 'verified') }))
      resolve({
        score: 42,
        highlights,
        explanation: 'This might be misleading due to exaggeration and missing sources.'
      })
    }, 2000)
  })
}
