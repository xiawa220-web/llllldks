# ZhiYu.ai — 舆情分析 PoC

一个基于 FastAPI 的后端与 React + Vite 的前端的舆情分析原型项目，支持：

- 中文话题分析（默认抓取目标 500）
- 跨源聚合搜索（Baidu News / Sogou News / SearxNG / Baidu / Bing / 微博/公众号/知乎/B站公开页）
- 文本抽取与降噪（广告/模板噪声过滤、中文占比动态阈值）
- 连续文章式报告（摘要与核心发现、声量与影响力、本周期关键事件回顾、品牌形象与用户认知、用户画像、风险与机遇、结论与建议、数据附录）
- 前端“便当盒”布局：查询卡片、研究报告、实时工作日志、结果总览、参考来源

## 开发

![CI](https://github.com/xiawa220-web/llllldks/actions/workflows/ci.yml/badge.svg)

### 后端
```bash
source .venv/bin/activate
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

### 前端
```bash
cd frontend
npm install
npm run dev # 默认 http://localhost:5173/ 若占用会切换端口
```

> 生产构建（本地）：
```bash
cd frontend
npm run build
```

## 目录结构
```
├── src/               # FastAPI 后端
├── frontend/          # React + Vite 前端
├── requirements.txt
├── .gitignore
└── README.md
```

## 许可证
内部 PoC，用于演示与评估。