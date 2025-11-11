import { useState } from 'react'
import { analyze, health, API_BASE } from './api/client'
import { Doughnut, Bar } from 'react-chartjs-2'
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement } from 'chart.js'
ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement)

function Badge({children}:{children: any}){
  return <span className="inline-flex items-center rounded-md border px-2 py-1 text-sm">{children}</span>
}

export default function App(){
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState<string|null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const addLog = (s:string)=> setLogs(l=>[...l, `[${new Date().toLocaleTimeString()}] ${s}`])

  async function onAnalyze(){
    try{
      setLoading(true); setError(null); setLogs([])
      addLog(`准备分析：${q}`)
      const ok = await health()
      if(!ok){
        addLog(`后端不可用：${API_BASE}`)
        throw new Error('后端未响应，请确认 http://localhost:8000 已启动')
      }
      addLog('发送分析请求…')
      const res = await analyze(q, 500)
      addLog('收到分析响应')
      setData(res)
    }catch(e:any){
      setError(e.message || '请求失败')
      addLog(`错误：${e.message || '请求失败'}`)
    }finally{
      setLoading(false)
    }
  }

  const report = data?.report || {}
  const senti = report?.sentiment_summary || {}
  const meta = data?.meta || {}
  const sources = report?.sources_used || []

  // 构造图表数据
  const mediaCount = report?.domain_table?.reduce((acc:number, r:any)=>acc + (r[0]?.includes('gov.cn')?0:1), 0) || 0
  const govCount = report?.sources_used?.filter((s:any)=> (s.domain||'').endsWith('gov.cn')).length || 0
  const socialCount = report?.sources_used?.filter((s:any)=> {
    const d = (s.domain||'')
    return d.includes('weibo.com') || d.includes('weixin.qq.com') || d.includes('zhihu.com') || d.includes('bilibili.com')
  }).length || 0

  const donutData = {
    labels: ['媒体', '政务/机构', '社交/公众号'],
    datasets: [{ data: [mediaCount, govCount, socialCount], backgroundColor: ['#3b82f6','#10b981','#f59e0b'] }]
  }
  const barData = {
    labels: ['正面','负面'],
    datasets: [{ label: '词频', data: [senti.pos||0, senti.neg||0], backgroundColor: ['#10b981','#ef4444'] }]
  }

  return (
    <div className="min-h-screen">
      <div className="page space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="brand brand-gradient">ZhiYu.ai</h1>
        <span className="subtitle">API: {API_BASE}</span>
      </header>

      {/* 便当盒结构：查询卡片 */}
      <div className="card space-y-2">
        <div className="text-lg font-semibold">分析查询</div>
        <div className="flex gap-2">
          <input className="flex-1 input input-lg" placeholder="输入话题，例如：武汉大学 舆情" value={q} onChange={e=>setQ(e.target.value)} />
          <button className="btn" onClick={onAnalyze} disabled={loading}>{loading ? (<span className="flex items-center gap-2"><span className="spinner"/>分析中...</span>) : '分析'}</button>
        </div>
        <div className="flex gap-2 mt-2">
          {["武汉大学 舆情","山姆 会员店 舆情","RISC-V 产业"].map(s=> (
            <button key={s} className="chip" onClick={()=>setQ(s)}>{s}</button>
          ))}
        </div>
        {error && <div className="text-red-600">{error}</div>}
      </div>

      {/* 在“分析查询”下，横向排列两个框：研究报告 / 实时工作日志 */}
      <div className="grid-2">
        <div className="card space-y-2">
          <div className="text-lg font-semibold">研究报告</div>
          <div className="prose max-w-none" dangerouslySetInnerHTML={{__html: data?.html || '尚未生成'}} />
        </div>
        <div className="card space-y-2">
          <div className="text-lg font-semibold">实时工作日志</div>
          <div className="muted">用于定位分析失败或抓取不足的问题</div>
          <pre className="text-sm whitespace-pre-wrap">{logs.join('\n')}</pre>
        </div>
      </div>

      {data && (
        <>
          {/* 总览卡片放在下方 */}
          <div className="card space-y-2">
            <div className="text-lg font-semibold">结果总览</div>
            <div className="flex gap-2">
              <span className="chip">样本数：{meta?.search?.items_count ?? 0}</span>
              <span className="chip">保留数：{meta?.filter?.kept ?? 0}</span>
              <span className="chip">情绪：{senti?.overall ?? '中性'}</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
              <div className="border rounded-md p-2"><Doughnut data={donutData} /></div>
              <div className="border rounded-md p-2 md:col-span-2"><Bar data={barData} options={{ responsive:true, plugins:{legend:{display:false}} }} /></div>
            </div>
            <div className="muted">搜索源：{(meta?.search?.chosen_source||'无')}；尝试源：{(meta?.search?.attempted_sources||[]).join('、')||'无'}</div>
            <div className="muted">过滤统计：空页面{meta?.filter?.filtered?.empty||0}、过短{meta?.filter?.filtered?.too_short||0}、中文比例低{meta?.filter?.filtered?.low_chinese_ratio||0}、广告关键词{meta?.filter?.filtered?.ad_keywords||0}</div>
          </div>

          <div className="card space-y-2">
            <div className="text-lg font-semibold">参考来源（Top）</div>
            <ul className="list-disc pl-6">
              {sources.slice(0,20).map((s:any, i:number)=> (
                <li key={i}><a className="text-blue-600" href={s.url} target="_blank">[{s.domain}] {s.title}</a></li>
              ))}
            </ul>
          </div>
        </>
      )}
      </div>
    </div>
  )
}