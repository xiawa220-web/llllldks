import re
import math
import jieba


POS_WORDS = {
    "积极", "增长", "提升", "改善", "优化", "利好", "支持", "认可", "满意", "优秀", "成功", "稳定"
}
NEG_WORDS = {
    "消极", "下降", "质疑", "风险", "争议", "投诉", "不满", "负面", "危机", "失败", "不稳定", "网暴", "开盒"
}


def tokenize(text: str):
    return [t for t in jieba.lcut(text) if t.strip()]


def sentence_split(text: str):
    # 简易中文句子切分
    parts = re.split(r"[。！？；\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def build_keywords(docs: list[dict], topn: int = 20):
    freq = {}
    for d in docs:
        for tok in tokenize(d["content"][:5000]):
            if len(tok) <= 1:
                continue
            freq[tok] = freq.get(tok, 0) + 1
    items = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, c in items[:topn]]


def summarize_sentences(docs: list[dict], topn: int = 8):
    # 频次打分选句
    freq = {}
    for d in docs:
        for tok in tokenize(d["content"][:8000]):
            if len(tok) <= 1:
                continue
            freq[tok] = freq.get(tok, 0) + 1
    def score_sentence(s: str):
        score = 0
        for tok in tokenize(s):
            score += freq.get(tok, 0)
        # 句长惩罚
        L = len(s)
        if L > 200:
            score *= 0.7
        return score
    candidates = []
    for d in docs:
        for s in sentence_split(d["content"][:4000])[:50]:
            sc = score_sentence(s)
            if sc > 0:
                candidates.append((sc, s))
    candidates.sort(key=lambda x: x[0], reverse=True)
    # 去重
    seen = set()
    res = []
    for sc, s in candidates:
        key = s[:30]
        if key in seen:
            continue
        seen.add(key)
        res.append(s)
        if len(res) >= topn:
            break
    return res


def simple_sentiment(docs: list[dict]):
    pos = 0
    neg = 0
    for d in docs:
        text = d["content"][:8000]
        for w in POS_WORDS:
            pos += text.count(w)
        for w in NEG_WORDS:
            neg += text.count(w)
    if neg > pos * 1.2:
        overall = "消极"
        reason = f"负面词频较高（neg={neg}, pos={pos}）"
    elif pos > neg * 1.2:
        overall = "积极"
        reason = f"正面词频较高（pos={pos}, neg={neg}）"
    else:
        overall = "中性"
        reason = f"正负词频接近（pos={pos}, neg={neg}）"
    return {"overall": overall, "reason": reason, "pos": pos, "neg": neg}


def build_report(topic: str, docs: list[dict]) -> dict:
    key_sents = summarize_sentences(docs, topn=8)
    kws = build_keywords(docs, topn=12)
    senti = simple_sentiment(docs)
    sources = [{"title": d["title"], "url": d["url"], "domain": d.get("domain","")} for d in docs]
    # 统计来源分布
    domain_counts = {}
    for s in sources:
        dom = s.get("domain", "其它") or "其它"
        domain_counts[dom] = domain_counts.get(dom, 0) + 1
    total_src = max(len(sources), 1)
    domain_table = sorted([(dom, cnt, round(cnt*100/total_src, 1)) for dom, cnt in domain_counts.items()], key=lambda x: x[1], reverse=True)
    overview = f"围绕“{topic}”，系统抓取国内主流媒体公开网页并进行降噪与本地分析，以下为要点、情绪与风险的初步概览。"

    # 风险与机会（启发式）
    risk_terms = {"风险", "争议", "质疑", "投诉", "不满", "危机", "负面", "网暴"}
    oppo_templates = [
        "透明沟通：按阶段发布核实进展与依据，降低误解与传播噪声。",
        "流程优化：完善事件调查与申诉复核机制，提升公正与可预期性。",
        "网络文明：倡导理性表达与反网暴，强化证据意识与法治教育。",
        "心理支持：为涉事方提供心理与名誉修复渠道，减少二次伤害。",
        "第三方评估：引入校外/行业专家参与复核，提高结果可信度。"
    ]
    risk_sents = []
    for d in docs:
        for s in sentence_split(d["content"][:3000]):
            if any(rt in s for rt in risk_terms):
                risk_sents.append(s)
    risk_sents = risk_sents[:5] if risk_sents else ["公众对程序公正与信息透明提出质疑，存在声誉与信任风险。"]

    report = {
        "overview": overview,
        "key_points": key_sents,
        "keywords": kws,
        "sentiment_summary": senti,
        "risks": risk_sents,
        "opportunities": oppo_templates,
        "sources_used": sources,
        "domain_table": domain_table
    }
    return report


def render_markdown(report: dict) -> str:
    lines = []
    lines.append(f"# 舆情分析报告")
    lines.append("")
    lines.append("## 概览")
    lines.append(report.get("overview", ""))
    lines.append("")
    lines.append("## 关键要点")
    for kp in report.get("key_points", [])[:8]:
        lines.append(f"- {kp}")
    if report.get("keywords"):
        lines.append("")
        lines.append("## 关键词")
        lines.append(", ".join(report["keywords"]))
    lines.append("")
    lines.append("## 情绪与走向")
    s = report.get("sentiment_summary", {})
    lines.append(f"- 总体：{s.get('overall','中性')}")
    if s.get('reason'):
        lines.append(f"- 理由：{s.get('reason')}")
    # 简单可视化条形图
    pos = int(s.get('pos', 0))
    neg = int(s.get('neg', 0))
    total = max(pos + neg, 1)
    pos_bar = '█' * max(1, int(20 * pos / total))
    neg_bar = '█' * max(1, int(20 * neg / total))
    lines.append("")
    lines.append(f"- 正面词频：{pos} | {pos_bar}")
    lines.append(f"- 负面词频：{neg} | {neg_bar}")
    lines.append("")
    lines.append("## 风险与争议")
    for r in report.get("risks", [])[:5]:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("## 机会与建议")
    for o in report.get("opportunities", [])[:5]:
        lines.append(f"- {o}")
    lines.append("")
    # 来源分布
    lines.append("## 来源分布（Top）")
    lines.append("")
    lines.append("| 媒体 | 数量 | 占比% |")
    lines.append("| --- | ---: | ---: |")
    for dom, cnt, pct in report.get("domain_table", [])[:10]:
        lines.append(f"| {dom} | {cnt} | {pct} |")
    lines.append("")
    lines.append("## 参考来源（优先国内媒体）")
    lines.append("")
    lines.append("| 媒体 | 标题 | 链接 |")
    lines.append("| --- | --- | --- |")
    for src in report.get("sources_used", [])[:10]:
        title = (src.get("title", "(无标题)").replace('|',' '))
        url = src.get("url", "")
        dom = src.get("domain", "")
        lines.append(f"| {dom} | {title} | {url} |")
    return "\n".join(lines)


def render_html(report: dict) -> str:
    s = report.get("sentiment_summary", {})
    pos = int(s.get("pos", 0)); neg = int(s.get("neg", 0))
    total = max(pos+neg, 1)
    pos_pct = int(100 * pos / total)
    neg_pct = 100 - pos_pct
    def esc(x: str) -> str:
        return (x or "").replace("<","&lt;").replace(">","&gt;")

    kp_html = "".join([f"<li>{esc(p)}</li>" for p in report.get("key_points", [])])
    kw_html = ", ".join([esc(k) for k in report.get("keywords", [])])
    dom_rows = "".join([f"<tr><td>{esc(dom)}</td><td class='num'>{cnt}</td><td class='num'>{pct}%</td></tr>" for dom,cnt,pct in report.get("domain_table", [])[:10]])
    src_rows = "".join([
        f"<tr><td>{esc(src.get('domain',''))}</td><td>{esc(src.get('title','(无标题)'))}</td><td><a href='{esc(src.get('url',''))}' target='_blank'>{esc(src.get('url',''))}</a></td></tr>"
        for src in report.get("sources_used", [])[:20]
    ])

    # 简单来源类型统计
    srcs = report.get("sources_used", [])
    gov = sum(1 for s2 in srcs if (s2.get('domain','').endswith('gov.cn')))
    social = sum(1 for s2 in srcs if ('weixin.qq.com' in s2.get('domain','') or 'weibo.com' in s2.get('domain','')))
    media = max(len(srcs) - gov - social, 0)

    html = f"""
    <style>
      .article{ line-height:1.75; }
      h1,h2,h3{ font-weight:600; }
      .muted{ color:#6b7280; font-size:13px; }
      ul{ padding-left:18px; }
      .barbox{ display:flex; gap:8px; align-items:center; margin:8px 0; }
      .bar{ height:12px; border-radius:6px; }
      .pos{ background:#10b981; width:{pos_pct}%; }
      .neg{ background:#ef4444; width:{neg_pct}%; }
      table{ width:100%; border-collapse:collapse; }
      th,td{ border:1px solid #e5e7eb; padding:8px; text-align:left; font-size:14px; }
      .num{ text-align:right; }
    </style>
    <article class='article'>
      <h1>舆情分析报告</h1>
      <h2>摘要与核心发现</h2>
      <p>{esc(report.get('overview',''))}</p>
      <ul>{kp_html}</ul>

      <h2>声量与影响力分析</h2>
      <p class='muted'>样本条目数：{len(srcs)}；媒体来源：{media}；政务/机构：{gov}；社交/公众号：{social}</p>
      <h3>来源分布（Top）</h3>
      <table>
        <thead><tr><th>媒体域名</th><th>数量</th><th>占比%</th></tr></thead>
        <tbody>{dom_rows}</tbody>
      </table>
      <h3>情绪与走向</h3>
      <p>总体：{esc(s.get('overall','中性'))}</p>
      <div class='barbox' aria-label='情绪条'>
        <div class='bar pos' title='正面'></div>
        <div class='bar neg' title='负面'></div>
      </div>
      <p class='muted'>{esc(s.get('reason',''))}</p>

      <h2>本周期关键事件回顾</h2>
      <ul>{kp_html}</ul>

      <h2>品牌形象与用户认知</h2>
      <p>关键词：{kw_html}</p>

      <h2>用户画像分析</h2>
      <p>基于来源类型粗略估计：新闻媒体受众偏大众；政务/机构偏正式与政策传播；社交/公众号更倾向意见表达与互动。</p>

      <h2>声誉风险与机遇洞察</h2>
      <ul>{"".join([f"<li>{esc(r)}</li>" for r in report.get('risks',[])[:5]])}</ul>
      <h3>机遇与建议</h3>
      <ul>{"".join([f"<li>{esc(o)}</li>" for o in report.get('opportunities',[])[:5]])}</ul>

      <h2>结论与战略建议</h2>
      <p>结合情绪与来源结构，建议加强正向叙事与事实澄清，在社交/公众号渠道进行回应与互动，并保持对关键事件的透明信息发布。</p>

      <h2>数据附录</h2>
      <table>
        <thead><tr><th>媒体</th><th>标题</th><th>链接</th></tr></thead>
        <tbody>{src_rows}</tbody>
      </table>
    </article>
    """
    return html