import { useState } from 'react'
import { analyze, health, API_BASE } from './api/client'
import { Doughnut, Bar, Line } from 'react-chartjs-2'
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, PointElement, LineElement } from 'chart.js'
ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, PointElement, LineElement)
import { Button } from './components/ui/button'
import { Badge } from './components/ui/badge'
import { Card, CardHeader, CardTitle, CardContent } from './components/ui/card'


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

      {/* 查询区：去掉外层卡片，仅保留输入与按钮 */}
      <div className="space-y-2">
        <div className="flex gap-2">
          <input className="flex-1 input input-lg" placeholder="输入话题，例如：武汉大学 舆情" value={q} onChange={e=>setQ(e.target.value)} />
          <Button onClick={onAnalyze} disabled={loading}>{loading ? (<span className="flex items-center gap-2"><span className="spinner"/>分析中...</span>) : '分析'}</Button>
        </div>
        <div className="flex gap-2 mt-2">
          {["武汉大学 舆情","山姆 会员店 舆情","RISC-V 产业"].map(s=> (
            <Badge key={s} className="cursor-pointer">
              <span onClick={()=>setQ(s)}>{s}</span>
            </Badge>
          ))}
        </div>
        {error && <div className="text-red-600">{error}</div>}
      </div>

      {/* 在“分析查询”下，横向排列两个框：研究报告 / 实时工作日志 */}
      <div className="grid-2">
        <Card className="space-y-2 card-tall">
          <CardHeader>
            <CardTitle>研究报告</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2 mb-2">
              <Button variant="outline" onClick={()=>{ navigator.clipboard.writeText(data?.markdown||'') }}>复制报告</Button>
              <Button variant="outline" onClick={()=>{ const blob = new Blob([data?.markdown||''], {type:'text/markdown'}); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href=url; a.download='report.md'; a.click(); URL.revokeObjectURL(url); }}>下载Markdown</Button>
              <Button variant="outline" onClick={()=>{ const blob = new Blob([data?.html||''], {type:'text/html'}); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href=url; a.download='report.html'; a.click(); URL.revokeObjectURL(url); }}>下载HTML</Button>
            </div>
            <div className="prose max-w-none" dangerouslySetInnerHTML={{__html: data?.html || '尚未生成'}} />
          </CardContent>
        </Card>
        <Card className="space-y-2 card-tall">
          <CardHeader>
            <CardTitle>实时工作日志</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="muted">用于定位分析失败或抓取不足的问题</div>
            <pre className="text-sm whitespace-pre-wrap">{logs.join('\n')}</pre>
          </CardContent>
        </Card>
      </div>

      {data && (
        <>
          {/* 总览卡片放在下方 */}
          <Card className="space-y-2">
            <CardHeader>
              <CardTitle>结果总览</CardTitle>
            </CardHeader>
            <div className="flex gap-2">
              <Badge>样本数：{meta?.search?.items_count ?? 0}</Badge>
              <Badge>保留数：{meta?.filter?.kept ?? 0}</Badge>
              <Badge>情绪：{senti?.overall ?? '中性'}</Badge>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
              <div className="border rounded-md p-2"><Doughnut data={donutData} /></div>
              <div className="border rounded-md p-2 md:col-span-2"><Bar data={barData} options={{ responsive:true, plugins:{legend:{display:false}} }} /></div>
            </div>
            <div className="muted">搜索源：{(meta?.search?.chosen_source||'无')}；尝试源：{(meta?.search?.attempted_sources||[]).join('、')||'无'}</div>
            <div className="muted">过滤统计：空页面{meta?.filter?.filtered?.empty||0}、过短{meta?.filter?.filtered?.too_short||0}、中文比例低{meta?.filter?.filtered?.low_chinese_ratio||0}、广告关键词{meta?.filter?.filtered?.ad_keywords||0}</div>
          </Card>

          <Card className="space-y-2">
            <CardHeader><CardTitle>参考来源（Top）</CardTitle></CardHeader>
            <ul className="list-disc pl-6">
              {sources.slice(0,20).map((s:any, i:number)=> (
                <li key={i}><a className="text-blue-600" href={s.url} target="_blank">[{s.domain}] {s.title}</a></li>
              ))}
            </ul>
          </Card>
          {/* 声量趋势折线图 */}
          {report?.trend_points && report?.trend_points.length>0 && (
            <Card className="space-y-2">
              <CardHeader><CardTitle>声量趋势</CardTitle></CardHeader>
              <CardContent>
                <Line data={{
                  labels: report.trend_points.map((p:any)=>p.date),
                  datasets:[{ label:'样本数', data: report.trend_points.map((p:any)=>p.count), borderColor:'#2563eb', backgroundColor:'rgba(37,99,235,.2)' }]
                }} options={{ responsive:true, plugins:{legend:{display:false}} }} />
              </CardContent>
            </Card>
          )}
        </>
      )}
      </div>
    </div>
  )
}