from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
from src.services.search import search_web
from src.services.scrape import extract_and_filter_texts
from src.services.analysis import build_report, render_markdown, render_html

app = FastAPI(title="ZhiYu.ai", version="0.1")

# 允许前端开发服务器（Vite 默认 5173）跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许任意来源，避免端口变化导致的跨域错误
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    query: str
    max_results: int = 500


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query不能为空")

    results, search_meta = await search_web(req.query, req.max_results)
    if not results:
        return JSONResponse({"query": req.query, "sources": [], "report": {}, "markdown": "# 无结果", "meta": {"search": search_meta}})

    docs, stats = await extract_and_filter_texts(results)
    if not docs:
        return JSONResponse({"query": req.query, "sources": [], "report": {}, "markdown": "# 无有效文档", "meta": {"filter": stats, "search": search_meta}})

    report = build_report(req.query, docs)
    md = render_markdown(report)
    html = render_html(report)
    return JSONResponse({"query": req.query, "sources": [{"title": d["title"], "url": d["url"]} for d in docs], "report": report, "markdown": md, "html": html, "meta": {"filter": stats, "search": search_meta}})


@app.get("/")
async def home():
    html = """
    <!doctype html>
    <html lang=\"zh-CN\">
    <head>
      <meta charset=\"utf-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
      <title>ZhiYu.ai</title>
      <style>
        :root { --bg:#f8fafc; --fg:#111827; --card:#ffffff; --muted:#6b7280; --accent:#2563eb; --border:#e5e7eb; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif; margin: 0; background: var(--bg); color: var(--fg); }
        header { padding: 20px 24px; background: var(--card); border-bottom: 1px solid var(--border); }
        .container { max-width: 900px; margin: 0 auto; }
        main { padding: 20px 24px; max-width: 900px; margin: 0 auto; }
        .bar { display:flex; gap:8px; align-items:center; }
        input { padding:10px 12px; font-size:14px; border:1px solid var(--border); border-radius:8px; width: clamp(240px, 50vw, 540px); }
        button { padding:10px 14px; font-size:14px; border:1px solid var(--accent); color:#fff; background: var(--accent); border-radius:8px; cursor:pointer; }
        .section { background: var(--card); border:1px solid var(--border); border-radius:12px; padding:16px; margin-top:16px; }
        #markdown { white-space: pre-wrap; }
        .src a { color: var(--accent); text-decoration:none; }
        .meta { font-size:13px; color: var(--muted); }
        .actions { display:flex; gap:8px; }
        @media (max-width: 640px) {
          header, main { padding: 16px; }
          .actions { flex-wrap: wrap; }
        }
        header h1 { background: linear-gradient(90deg, #1e3a8a, #2563eb, #60a5fa); -webkit-background-clip: text; color: transparent; }
        button:hover { filter: brightness(1.05); }
      </style>
    </head>
    <body>
      <header>
        <div class=\"container\">
          <h1>ZhiYu.ai</h1>
          <p class=\"meta\">输入中文话题 → 抓取国内公开网页 → 降噪 → 本地分析 → 输出报告。</p>
        </div>
      </header>
      <main>
        <div class=\"bar\">
          <input id=\"q\" placeholder=\"例如：武汉大学舆情\" />
          <button onclick=\"run()\">分析</button>
          <div class=\"actions\">
            <button onclick=\"downloadMD()\">下载Markdown</button>
            <button onclick=\"copyMD()\">复制报告</button>
          </div>
        </div>
        <div class=\"section\">
          <h2>报告</h2>
          <div id=\"markdown\">尚未生成</div>
        </div>
        <div class=\"section\">
          <h3>可视化概览</h3>
          <div style=\"display:flex; gap:16px; flex-wrap:wrap;\">
            <div style=\"flex:1; min-width:260px;\">
              <canvas id=\"donut\" height=\"180\"></canvas>
            </div>
            <div style=\"flex:1; min-width:260px;\">
              <canvas id=\"line\" height=\"180\"></canvas>
            </div>
            <div style=\"flex:1; min-width:260px;\">
              <canvas id=\"rating\" height=\"180\"></canvas>
            </div>
          </div>
        </div>
        <div class=\"section\">
          <h3>过滤统计</h3>
          <div id=\"stats\" class=\"meta\">暂无</div>
        </div>
        <div class=\"section\">
          <h3>参考来源</h3>
          <div id=\"sources\"></div>
        </div>
      </main>
      <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
      <script>
        let lastMD = '';
        const charts = { donut:null, line:null, rating:null };
        async function run(){
          const q = document.getElementById('q').value.trim();
          if(!q){ alert('请输入话题'); return; }
          document.getElementById('markdown').textContent = '正在分析，请稍候...';
          document.getElementById('sources').innerHTML = '';
          document.getElementById('stats').textContent = '运行中...';
          try {
            const resp = await fetch('/analyze', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({query:q, max_results:100})});
            const data = await resp.json();
            lastMD = data.markdown || '无结果';
            const html = data.html || '';
            if (html) { document.getElementById('markdown').innerHTML = html; }
            else { document.getElementById('markdown').textContent = lastMD; }
            // 隐藏独立的可视化模块（改为在报告中呈现）
            try {
              const donut = document.getElementById('donut');
              if (donut) {
                const sec = donut.closest('.section');
                if (sec) sec.style.display = 'none';
              }
            } catch(_){ }
            const srcDiv = document.getElementById('sources');
            (data.sources||[]).forEach(s=>{
              const a = document.createElement('a'); a.href = s.url; a.textContent = s.title || s.url; a.target = '_blank';
              const p = document.createElement('p'); p.className = 'src'; p.appendChild(a); srcDiv.appendChild(p);
            });
            const m = (data.meta||{});
            const filt = (m.filter||{});
            const f = (filt.filtered||{});
            const s = (m.search||{});
            const srcs = (s.attempted_sources||[]).join('、');
            document.getElementById('stats').textContent = `搜索源：${s.chosen_source||'无'}；尝试源：${srcs||'无'}；搜索结果数：${s.items_count||0}；筛选后保留：${filt.kept||0}；过滤：空页面${f.empty||0}、过短${f.too_short||0}、中文比例低${f.low_chinese_ratio||0}、广告关键词${f.ad_keywords||0}`;

            renderCharts(data);
          } catch(e){
            document.getElementById('markdown').textContent = '发生错误：' + e;
            document.getElementById('stats').textContent = '发生错误';
          }
        }

        function renderCharts(data){
          const report = data.report || {};
          const sources = report.sources_used || [];
          const senti = report.sentiment_summary || {pos:0,neg:0};
          const domainCounts = {};
          sources.forEach(s=>{ const d=(s.domain||'其它'); domainCounts[d]=(domainCounts[d]||0)+1; });
          const labels = Object.keys(domainCounts);
          const values = Object.values(domainCounts);
          const keyPoints = report.key_points || [];
          const lengths = keyPoints.map(k=>k.length);

          const donutCtx = document.getElementById('donut').getContext('2d');
          if (charts.donut) charts.donut.destroy();
          charts.donut = new Chart(donutCtx, { type:'doughnut', data:{ labels, datasets:[{ data: values, backgroundColor:['#3b82f6','#22c55e','#f59e0b','#ef4444','#6366f1','#14b8a6','#a78bfa'] }]}, options:{ plugins:{legend:{position:'bottom'}}, cutout:'60%'}});

          const lineCtx = document.getElementById('line').getContext('2d');
          if (charts.line) charts.line.destroy();
          charts.line = new Chart(lineCtx, { type:'line', data:{ labels: lengths.map((_,i)=>i+1), datasets:[{ label:'要点长度趋势', data:lengths, borderColor:'#3b82f6', tension:0.3 }]}, options:{ scales:{ y:{ beginAtZero:true }}}});

          const ratingCtx = document.getElementById('rating').getContext('2d');
          const pos = parseInt(senti.pos||0), neg = parseInt(senti.neg||0);
          const score = Math.max(0, Math.min(5, 3 + ((pos-neg)/(pos+neg+1))*2));
          if (charts.rating) charts.rating.destroy();
          charts.rating = new Chart(ratingCtx, { type:'bar', data:{ labels:['5星','4星','3星','2星','1星'], datasets:[{ label:`评分 ${score.toFixed(1)}`, data:[score*10, (5-score)*6, 10, 6, 4], backgroundColor:'#60a5fa' }]}, options:{ indexAxis:'y', scales:{ x:{ beginAtZero:true }}}});
      }
        function downloadMD(){
          const blob = new Blob([lastMD||''], {type:'text/markdown'});
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url; a.download = 'report.md'; a.click();
          URL.revokeObjectURL(url);
        }
        async function copyMD(){
          try { await navigator.clipboard.writeText(lastMD||''); alert('已复制'); } catch(e){ alert('复制失败'); }
        }
      </script>
    </body>
    </html>
    """
    return HTMLResponse(html)