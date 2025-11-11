export const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'

export async function health(){
  try{
    const r = await fetch(`${API_BASE}/`, { method:'GET' })
    return r.ok
  }catch{
    return false
  }
}

export async function analyze(query: string, maxResults = 500){
  const r = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, max_results: maxResults })
  })
  if(!r.ok){
    let txt = ''
    try{ txt = await r.text() }catch{}
    throw new Error(txt || `请求失败 (${r.status})`)
  }
  return r.json()
}