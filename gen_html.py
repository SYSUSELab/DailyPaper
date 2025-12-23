#!/usr/bin/env python3
"""
生成静态网页脚本
将论文数据生成为 HTML 页面
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HTMLGenerator:
    """HTML 生成器"""
    def __init__(self, data_path: str = "data/papers.json",
                 output_dir: str = "docs"):
        self.data_path = Path(data_path)
        self.output_dir = Path(output_dir)
        self.papers = []
        self.papers_by_month = {}  # 按月份分组的论文

    def load_papers(self):
        """加载论文数据"""
        if not self.data_path.exists():
            logger.warning(f"数据文件不存在: {self.data_path}")
            return

        with open(self.data_path, 'r', encoding='utf-8') as f:
            for line in f:
                self.papers.append(json.loads(line))

        logger.info(f"加载了 {len(self.papers)} 篇论文")

        # 按月份分组
        for paper in self.papers:
            # 从 published 字段提取年月 (格式: 2025-10-31)
            published = paper.get('published', '')
            if published:
                year_month = published[:7]  # 提取 "2025-10"
                if year_month not in self.papers_by_month:
                    self.papers_by_month[year_month] = []
                self.papers_by_month[year_month].append(paper)

        logger.info(
            f"论文分布: {', '.join([f'{k}: {len(v)}篇' for k, v in sorted(self.papers_by_month.items(), reverse=True)])}")

    def generate_monthly_data_files(self):
        """生成按月份分离的数据文件"""
        data_dir = self.output_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        # 为每个月份生成独立的 JSON 文件
        for year_month, papers in self.papers_by_month.items():
            file_path = data_dir / f"{year_month}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(papers, f, ensure_ascii=False, indent=2)
            logger.info(f"生成月度数据文件: {file_path} ({len(papers)} 篇)")

        # 生成索引文件，包含所有月份的元数据
        months_index = []
        for year_month in sorted(self.papers_by_month.keys(), reverse=True):
            papers = self.papers_by_month[year_month]
            months_index.append({
                'month': year_month,
                'count': len(papers),
                'published_count': sum(1 for p in papers if p.get('conference')),
                'preprint_count': sum(1 for p in papers if not p.get('conference'))
            })

        with open(data_dir / "index.json", 'w', encoding='utf-8') as f:
            json.dump(months_index, f, ensure_ascii=False, indent=2)

        logger.info(f"生成月份索引文件: {data_dir / 'index.json'}")

    def generate_month_buttons(self):
        """生成月份筛选按钮"""
        buttons = []
        for year_month in sorted(self.papers_by_month.keys(), reverse=True):
            count = len(self.papers_by_month[year_month])
            buttons.append(
                f'<button class="filter-btn month-btn" data-month="{year_month}">{year_month} ({count})</button>')
        return '\n                    '.join(buttons)

    def generate_index_html(self):
        """生成主页 HTML"""

        # 计算各分类数量
        published_count = sum(1 for p in self.papers if p.get('conference'))
        preprint_count = sum(1 for p in self.papers if not p.get('conference'))
        survey_count = sum(1 for p in self.papers if 'Survey' in p.get('category', []))
        empirical_count = sum(1 for p in self.papers if 'Empirical' in p.get('category', []))
        benchmark_count = sum(1 for p in self.papers if 'Benchmark' in p.get('category', []))
        technical_count = sum(1 for p in self.papers if 'Technical' in p.get('category', []))
        require_count = sum(1 for p in self.papers if 'Requirements & Design' in p.get('field'))
        code_count = sum(1 for p in self.papers if 'Coding Assistant' in p.get('field'))
        test_count = sum(1 for p in self.papers if 'Software Testing' in p.get('field'))
        ops_count = sum(1 for p in self.papers if 'AIOps' in p.get('field'))
        maintenance_count = sum(1 for p in self.papers if 'Maintenance' in p.get('field'))
        quality_count = sum(1 for p in self.papers if 'Quality Management' in p.get('field'))
        version_count = sum(1 for p in self.papers if 'Version Control & Collaboration' in p.get('field'))

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <!-- 设置内容安全策略 (CSP) 以解决 unsafe-eval 报错 -->
    <meta http-equiv="Content-Security-Policy" content="
        default-src 'self' https://www.googletagmanager.com https://www.google-analytics.com;
        script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com https://www.google-analytics.com;
        style-src 'self' 'unsafe-inline';
        img-src 'self' data: https:;
        connect-src 'self' https://www.google-analytics.com https://analytics.google.com;
    ">

    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-1VP8RP72FC"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());

      gtag('config', 'G-1VP8RP72FC');
    </script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM4SEPaper - LLM4SE 最新论文</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>📚 LLM4SEPaper</h1>
            <p class="subtitle">每日自动更新 LLM4SE 领域最新论文</p>
            <p class="update-time">最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
        </div>
    </header>

    <nav class="container">
        <div class="filter-section">
            <div class="filter-group">
                <label class="filter-label">📅 时间范围：</label>
                <div class="date-range-filter">
                    <input type="date" id="startDate" class="date-input">
                    <span class="date-separator">至</span>
                    <input type="date" id="endDate" class="date-input">
                    <button id="resetDateBtn" class="filter-btn" style="margin-left: 10px; padding: 0.4rem 0.8rem;">重置</button>
                </div>
            </div>
            <div class="filter-group">
                <label class="filter-label">📌 发表状态：</label>
                <div class="filters status-filters">
                    <button class="filter-btn status-btn active" data-status="all">全部 ({len(self.papers)})</button>
                    <button class="filter-btn status-btn" data-status="published">已发表 ({published_count})</button>
                    <button class="filter-btn status-btn" data-status="preprint">预印本 ({preprint_count})</button>
                </div>
            </div>
            <div class="filter-group">
                <label class="filter-label">📑 论文类型：</label>
                <div class="filters category-filters">
                    <button class="filter-btn category-btn active" data-category="all">全部 ({len(self.papers)})</button>
                    <button class="filter-btn category-btn" data-category="Survey">Survey ({survey_count})</button>
                    <button class="filter-btn category-btn" data-category="Empirical">Empirical ({empirical_count})</button>
                    <button class="filter-btn category-btn" data-category="Technical">Technical ({technical_count})</button>
                    <button class="filter-btn category-btn" data-category="Benchmark">Benchmark ({benchmark_count})</button>
                </div>
            </div>
            <div class="filter-group">
                <label class="filter-label">🏷️ 研究领域：</label>
                <div class="filters field-filters">
                    <button class="filter-btn field-btn active" data-field="all">全部 ({len(self.papers)})</button>
                    <button class="filter-btn field-btn" data-field="Requirements & Design">Requirements & Design ({require_count})</button>
                    <button class="filter-btn field-btn" data-field="Coding Assistant">Coding Assistant ({code_count})</button>
                    <button class="filter-btn field-btn" data-field="Software Testing">Software Testing ({test_count})</button>
                    <button class="filter-btn field-btn" data-field="AIOps">AIOps ({ops_count})</button>
                    <button class="filter-btn field-btn" data-field="Maintenance">Maintenance ({maintenance_count})</button>
                    <button class="filter-btn field-btn" data-field="Quality Management">Quality Management ({quality_count})</button>
                    <button class="filter-btn field-btn" data-field="Version Control & Collaboration">Version Control & Collaboration ({version_count})</button>
                </div>
            </div>
            <div class="filter-group">
                <label class="filter-label">🎯 Task：</label>
                <div class="filters sort-filters">
                    <button class="filter-btn task-btn active" data-task="all">全部 ({len(self.papers)})</button>
                </div>
            </div>
            <div class="filter-group">
                <label class="filter-label">🔄 排序方式：</label>
                <div class="filters sort-filters">
                    <button class="filter-btn sort-btn active" data-sort="date-desc">最新优先</button>
                    <button class="filter-btn sort-btn" data-sort="date-asc">最早优先</button>
                </div>
            </div>
        </div>
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="🔍 搜索论文标题、作者、摘要...">
        </div>
        <div class="results-info">
            <span id="resultsCount">加载中...</span>
            <div class="export-controls">
                <button class="select-btn" id="selectAllBtn">✓ 全选</button>
                <button class="select-btn" id="clearAllBtn">✗ 清空</button>
                <button class="export-btn" id="exportBtn">📥 导出选中 (<span id="selectedCount">0</span>)</button>
            </div>
        </div>
    </nav>

    <main class="container">
        <div id="papers-container">
            <!-- Papers will be loaded by JavaScript -->
        </div>
    </main>

    <footer>
        <div class="container">
            <p>© 2025 LLM4SEPaper | 数据来源: ArXiv | <a href="https://github.com/SYSUSELab/DailyLLM4SEPaper" target="_blank">GitHub</a></p>
        </div>
    </footer>

    <script src="js/main.js"></script>
</body>
</html>
"""

        output_file = self.output_dir / "index.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"生成主页: {output_file}")

    def get_category_name(self, category: str) -> str:
        """将 ArXiv 类别代码转换为友好的名称"""
        category_map = {
            'cs.SE': 'Software Engineering',
            'cs.AI': 'Artificial Intelligence',
            'cs.CV': 'Computer Vision',
            'cs.CL': 'Computational Linguistics (NLP)',
            'cs.LG': 'Machine Learning',
            'cs.IR': 'Information Retrieval',
            'cs.RO': 'Robotics',
            'cs.NE': 'Neural and Evolutionary Computing',
            'cs.CR': 'Cryptography and Security',
            'cs.HC': 'Human-Computer Interaction',
            'cs.MM': 'Multimedia',
            'stat.ML': 'Machine Learning (Statistics)',
        }
        return category_map.get(category, category)

    def extract_code_links(self, abstract: str) -> Dict[str, str]:
        """从摘要中提取代码和项目链接"""
        import re
        links = {}

        # 提取 Code: 链接
        code_pattern = r'[Cc]ode[:\s]+(?:available at\s+)?(\S+)'
        code_match = re.search(code_pattern, abstract)
        if code_match:
            links['code'] = code_match.group(1).rstrip('.,;')

        # 提取 Project: 链接
        project_pattern = r'[Pp]roject[:\s]+(?:page\s+)?(\S+)'
        project_match = re.search(project_pattern, abstract)
        if project_match:
            links['project'] = project_match.group(1).rstrip('.,;')

        # 提取 GitHub 链接
        github_pattern = r'(https?://(?:www\.)?github\.com/[\w\-]+/[\w\-]+)'
        github_match = re.search(github_pattern, abstract)
        if github_match and 'code' not in links:
            links['code'] = github_match.group(1)

        return links

    def get_venue_badge(self, conference: str) -> tuple:
        """获取会议徽章的样式类和显示文本"""
        if not conference:
            return ('preprint', 'Preprint')

        # 顶级会议配色
        venue_styles = {
            'NeurIPS': ('venue-neurips', 'NeurIPS'),
            'CVPR': ('venue-cvpr', 'CVPR'),
            'ICCV': ('venue-iccv', 'ICCV'),
            'ECCV': ('venue-eccv', 'ECCV'),
            'ICML': ('venue-icml', 'ICML'),
            'ICLR': ('venue-iclr', 'ICLR'),
            'ACL': ('venue-acl', 'ACL'),
            'EMNLP': ('venue-emnlp', 'EMNLP'),
            'AAAI': ('venue-aaai', 'AAAI'),
            'IJCAI': ('venue-ijcai', 'IJCAI'),
            'ISSTA': ('venue-issta', 'ISSTA'),
            'ICPC': ('venue-icpc', 'ICPC'),
            'FSE': ('venue-fse', 'FSE'),
            'ICSE': ('venue-icse', 'ICSE'),
            'ASE': ('venue-ase', 'ASE'),
            'ICSME': ('venue-icsme', 'ICSME'),
            'COLM': ('venue-colm', 'COLM'),
        }

        # 检查会议名称
        for venue_name, (style, display) in venue_styles.items():
            if venue_name in conference:
                return (style, conference)

        return ('venue-other', conference)

    def generate_papers_html(self) -> str:
        """生成论文列表 HTML（兼容 paper['task'] 为 string 或 list）"""
        if not self.papers:
            return '<p class="no-results">暂无论文数据</p>'

        html_parts = []
        for paper in self.papers:
            # 兼容 task 为 string 或 list。若是 string，支持单个标签或逗号分隔多个标签。
            # raw_task = paper.get('tags', '')
            # if isinstance(raw_task, list):
            #     task_list = [t for t in raw_task if isinstance(t, str) and t.strip()]
            # elif isinstance(raw_task, str):
            #     if ',' in raw_task:
            #         task_list = [t.strip() for t in raw_task.split(',') if t.strip()]
            #     else:
            #         task_list = [raw_task.strip()] if raw_task.strip() else []
            # else:
            #     task_list = []

            # task_html = ''.join([f'<span class="task">{task}</span>' for task in task_list])
            # data_task_attr = ','.join(task_list)  # 用于 data-task 属性
            tags_html = ''.join([f'<span class="tag">{tag}</span>' for tag in paper.get('tags', [])])

            authors = paper.get('authors', [])
            authors_html = ', '.join(authors[:5])
            if len(authors) > 5:
                authors_html += ' et al.'

            # 获取友好的类别名称
            primary_category = paper.get('category')
            category_name = self.get_category_name(primary_category)

            # 获取会议信息和徽章样式
            conference = paper.get('conference')
            venue_class, venue_display = self.get_venue_badge(conference)

            # 确定发表状态
            is_published = 'published' if conference else 'preprint'

            # 提取代码链接
            code_links = self.extract_code_links(paper.get('abstract', ''))
            code_links_html = ''
            if code_links.get('code'):
                code_links_html += f'<a href="{code_links["code"]}" target="_blank" class="btn-link btn-code">💻 Code</a>'
            if code_links.get('project'):
                code_links_html += f'<a href="{code_links["project"]}" target="_blank" class="btn-link btn-project">🌐 Project</a>'

            paper_html = f"""
            <article class="paper-card" data-tags="{','.join(paper.get('tags', []))}" data-status="{is_published}" data-date="{paper.get('published', '')}">
                <div class="venue-badge {venue_class}">{venue_display}</div>
                <h2 class="paper-title">
                    <a href="{paper.get('arxiv_url', '')}" target="_blank">{paper.get('title', '')}</a>
                </h2>
                <div class="paper-meta">
                    <span class="meta-item">📅 {paper.get('published', '')}</span>
                    <span class="meta-item">📖 ArXiv {category_name}</span>
                </div>
                <div class="paper-authors">
                    👥 {authors_html}
                </div>
                <div class="paper-tags">
                    {tags_html}
                </div>
                <div class="paper-abstract">
                    <details>
                        <summary>查看摘要</summary>
                        <p>{paper.get('abstract', '')}</p>
                    </details>
                </div>
                <div class="paper-links">
                    <a href="{paper.get('pdf_url', '')}" target="_blank" class="btn-link">📄 PDF</a>
                    <a href="{paper.get('arxiv_url', '')}" target="_blank" class="btn-link">🔗 ArXiv</a>
                    {code_links_html}
                </div>
            </article>
            """
            html_parts.append(paper_html)

        return '\n'.join(html_parts)

    def generate_css(self):
        """生成 CSS 样式"""
        css = """/* 全局样式 */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f5f5f5;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* 头部样式 */
header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem 0;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

header h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}

.subtitle {
    font-size: 1.1rem;
    opacity: 0.9;
}

.update-time {
    font-size: 0.9rem;
    opacity: 0.8;
    margin-top: 0.5rem;
}

/* 导航和筛选 */
nav {
    background: white;
    padding: 1.5rem 20px;
    margin: 2rem auto;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.filter-section {
    margin-bottom: 1rem;
}

.filter-group {
    margin-bottom: 1rem;
}

.filter-label {
    display: inline-block;
    font-weight: 600;
    color: #333;
    margin-bottom: 0.5rem;
    font-size: 0.95rem;
}

.filters {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.filter-btn {
    padding: 0.5rem 1rem;
    border: 2px solid #667eea;
    background: white;
    color: #667eea;
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.3s;
    font-size: 0.9rem;
}

.filter-btn:hover {
    background: #f0f0f0;
}

.filter-btn.active {
    background: #667eea;
    color: white;
}

.date-range-filter {
    display: flex;
    align-items: center;
    gap: 10px;
}

.date-input {
    padding: 6px 12px;
    border: 2px solid #667eea;
    border-radius: 6px;
    font-size: 0.9rem;
    color: #333;
    outline: none;
}

.date-input:focus {
    border-color: #764ba2;
    box-shadow: 0 0 5px rgba(102, 126, 234, 0.3);
}

.date-separator {
    font-weight: bold;
    color: #666;
}

.search-box {
    margin-top: 1.5rem;
}

.search-box input {
    width: 100%;
    padding: 0.8rem;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-size: 1rem;
    transition: border-color 0.3s;
}

.search-box input:focus {
    outline: none;
    border-color: #667eea;
}

/* 主内容区域 */
main {
    margin-top: 0;
}

#papers-container {
    margin-top: 1rem;
}

/* 结果信息栏 */
.results-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
    padding: 0.8rem;
    background: #f8f9fa;
    border-radius: 8px;
}

#resultsCount {
    font-size: 0.9rem;
    color: #666;
    font-weight: 500;
}

.export-btn {
    padding: 0.5rem 1rem;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: background 0.3s;
}

.export-btn:hover {
    background: #5568d3;
}

/* 论文卡片 */
.paper-card {
    position: relative;
    background: white;
    padding: 1.5rem;
    padding-top: 2.5rem;
    padding-left: 4rem;
    margin-bottom: 1rem;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    transition: transform 0.3s, box-shadow 0.3s;
    display: flex;
    align-items: flex-start;
}

.paper-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}

/* 复选框样式 */
.paper-select {
    position: absolute;
    left: 1.2rem;
    top: 1.5rem;
}

.paper-checkbox {
    width: 20px;
    height: 20px;
    cursor: pointer;
    accent-color: #667eea;
}

.paper-content {
    flex: 1;
}

/* 导出控制按钮 */
.export-controls {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}

.select-btn {
    padding: 0.5rem 1rem;
    background: white;
    border: 2px solid #667eea;
    color: #667eea;
    border-radius: 5px;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 600;
    transition: all 0.3s;
}

.select-btn:hover {
    background: #667eea;
    color: white;
}

/* Venue 徽章 - 增强对比度和可见性 */
.venue-badge {
    display: inline-block;
    padding: 0.4rem 0.9rem;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: none;
    letter-spacing: 0.3px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    margin-left: 0.5rem;
    max-width: 600px;
    white-space: normal;
    word-wrap: break-word;
    line-height: 1.4;
}

.badge-neurips {
    background: #6B46C1;
    color: white;
}

.badge-cvpr, .badge-iccv, .badge-eccv {
    background: #E53E3E;
    color: white;
}

.badge-icml, .badge-iclr {
    background: #3182CE;
    color: white;
}

.badge-acl, .badge-emnlp, .badge-naacl {
    background: #38A169;
    color: white;
}

.badge-aaai, .badge-ijcai {
    background: #D69E2E;
    color: white;
}

.badge-published {
    background: #4A5568;
    color: white;
}

.preprint {
    background: #f5f5f5;
    color: #757575;
}

.paper-title {
    font-size: 1.3rem;
    margin-bottom: 0.8rem;
}

.paper-title a {
    color: #333;
    text-decoration: none;
    transition: color 0.3s;
}

.paper-title a:hover {
    color: #667eea;
}

.paper-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 0.8rem;
    font-size: 0.9rem;
    color: #666;
}

.meta-item.venue-conference {
    color: #2e7d32;
    font-weight: 600;
    background: #e8f5e9;
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
}

.meta-item.venue-preprint {
    color: #666;
}

.paper-authors {
    margin-bottom: 0.8rem;
    color: #555;
    font-size: 0.95rem;
}

.paper-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 1rem;
}

.tag {
    display: inline-block;
    padding: 0.3rem 0.8rem;
    background: #e3f2fd;
    color: #1976d2;
    border-radius: 15px;
    font-size: 0.85rem;
}

.paper-abstract {
    margin-bottom: 1rem;
}

.paper-abstract details summary {
    cursor: pointer;
    color: #667eea;
    font-weight: 500;
    user-select: none;
}

.paper-abstract details[open] summary {
    margin-bottom: 0.5rem;
}

.paper-abstract p {
    color: #555;
    line-height: 1.8;
    text-align: justify;
}

.paper-links {
    display: flex;
    gap: 1rem;
}

.btn-link {
    padding: 0.5rem 1rem;
    background: #667eea;
    color: white;
    text-decoration: none;
    border-radius: 5px;
    font-size: 0.9rem;
    transition: background 0.3s;
    display: inline-block;
}

.btn-link:hover {
    background: #5568d3;
}

.btn-code {
    background: #28a745;
}

.btn-code:hover {
    background: #218838;
}

.btn-project {
    background: #17a2b8;
}

.btn-project:hover {
    background: #138496;
}

/* 底部 */
footer {
    background: #333;
    color: white;
    text-align: center;
    padding: 2rem 0;
    margin-top: 3rem;
}

footer a {
    color: #667eea;
    text-decoration: none;
}

/* 无结果提示 */
.no-results {
    text-align: center;
    padding: 3rem;
    color: #999;
    font-size: 1.1rem;
}

/* 加载指示器 */
.loading-indicator {
    text-align: center;
    padding: 2rem;
    color: #667eea;
    font-size: 1rem;
    font-weight: 500;
}

.loading-indicator::after {
    content: '';
    display: inline-block;
    width: 20px;
    height: 20px;
    margin-left: 10px;
    border: 3px solid #667eea;
    border-radius: 50%;
    border-top-color: transparent;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* 响应式设计 */
@media (max-width: 768px) {
    header h1 {
        font-size: 2rem;
    }

    .filters {
        justify-content: center;
    }

    .paper-meta {
        flex-direction: column;
        gap: 0.3rem;
    }
}
"""

        css_dir = self.output_dir / "css"
        css_dir.mkdir(parents=True, exist_ok=True)

        with open(css_dir / "style.css", 'w', encoding='utf-8') as f:
            f.write(css)

        logger.info("生成 CSS 样式文件")

    def generate_js(self):
        """生成 JavaScript 文件"""
        js = """// 筛选、搜索、排序和懒加载功能
document.addEventListener('DOMContentLoaded', function() {
    console.log('JavaScript loaded');

    // 获取DOM元素
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const resetDateBtn = document.getElementById('resetDateBtn');
    
    const statusBtns = document.querySelectorAll('.status-btn');
    const categoryBtns = document.querySelectorAll('.category-btn');
    const fieldBtns = document.querySelectorAll('.field-btn');
    let taskBtns = document.querySelectorAll('.task-btn');
    const sortBtns = document.querySelectorAll('.sort-btn');
    const searchInput = document.getElementById('searchInput');
    
    const exportBtn = document.getElementById('exportBtn');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const clearAllBtn = document.getElementById('clearAllBtn');
    const selectedCount = document.getElementById('selectedCount');
    const resultsCount = document.getElementById('resultsCount');
    const papersContainer = document.getElementById('papers-container');

    console.log('DOM elements:', {
        statusBtns: statusBtns.length,
        categoryBtns: categoryBtns.length,
        fieldBtns: fieldBtns.length,
        taskBtns: taskBtns.length,
        sortBtns: sortBtns.length,
        searchInput: !!searchInput,
        exportBtn: !!exportBtn,
        selectAllBtn: !!selectAllBtn,
        clearAllBtn: !!clearAllBtn,
        resultsCount: !!resultsCount,
        papersContainer: !!papersContainer
    });

    // 状态变量
    let allPapersData = [];  // 所有论文数据
    let monthsIndex = [];        // 从 index.json 获取的所有月份列表
    let monthsCache = {};  // 缓存已加载的月份数据
    
    let currentStatus = 'all';
    let currentCategory = 'all';
    let currentField = 'all';
    let currentTask = 'all';
    let currentSort = 'date-desc';
    let searchTerm = '';
    
    let filteredPapers = [];
    let loadedCount = 0;
    const initialBatchSize = 20;  // 第一次加载20个
    const subsequentBatchSize = 10;  // 后续每次加载10个
    let isLoading = false;
    let observer = null;
    

    const field2task = {'Requirements & Design': ['Elicitation', 'Analysis', 'Specification &Validation', 'Management'],
        'Coding Assistant': ['Code Pre-Training', 'Code Instruction-Tuning', 'Code Alignment', 'Code Prompting', 'Code Completion', 'Code Summarization', 'Code Editing', 'Code Translation', 'Code Reasoning', 'Code Retrieval', 'Code Understanding', 'Code Performance Optimization', 'Code Representation Learning'],
        'Software Testing': ['Test Generation', 'Assertion generation', 'GUI test', 'Testing automation', 'Testing prediction', 'Testing Repair'],
        'AIOps': ['Log Statement Generation', 'Log Parsing'],
        'Maintenance': ['Code Review', 'Clone Detection', 'Refactoring'],
        'Quality Management': ['Defect Prediction', 'Bug Localization', 'Bug Repair', 'Vulnerability Detection', 'Vulnerability Repair'],
        'Version Control & Collaboration': ['Git VCS']}

    // 初始化加载
    async function init() {
        try {
            // 首先加载月份索引
            const response = await fetch('data/index.json');
            monthsIndex = await response.json(); // 格式: [{month: "2025-10", count: 10}, ...]
            
            if (monthsIndex.length > 0) {
                // 设置日期选择器的可选范围
                const sortedMonths = monthsIndex.map(m => m.month).sort();
                const minMonth = sortedMonths[0];
                const maxMonth = sortedMonths[sortedMonths.length - 1];
                startDateInput.min = `${minMonth}-01`;
                endDateInput.max = `${maxMonth}-31`;

                // 默认策略：只加载最新一个月的数据
                const latestMonth = monthsIndex[0].month;
                console.log("初始化：加载最新月数据 " + latestMonth);
                await loadMonthData(latestMonth);
            }
        } catch (e) {
            console.error('初始化失败:', e);
            resultsCount.textContent = "数据加载失败，请检查网络";
        }
    }

    // 加载单个或多个月份的数据
    async function loadMonthData(monthStr) {
        if (!monthsCache[monthStr]) {
            try {
                const response = await fetch(`data/${monthStr}.json`);
                const data = await response.json();
                monthsCache[monthStr] = data;
                // 合并到总池子
                allPapersData = allPapersData.concat(data);
            } catch (e) {
                console.error(`加载月份 ${monthStr} 失败:`, e);
            }
        }
        renderTaskButtons(currentField);
        filterAndSortPapers();
    }

    // 根据日期范围动态补全加载
    async function ensureDataRange(startStr, endStr) {
        if (!startStr || !endStr) return;
        
        const startMonth = startStr.substring(0, 7);
        const endMonth = endStr.substring(0, 7);

        // 找出索引中在该范围内但尚未缓存的月份
        const neededMonths = monthsIndex
            .map(m => m.month)
            .filter(m => m >= startMonth && m <= endMonth && !monthsCache[m]);

        if (neededMonths.length > 0) {
            resultsCount.textContent = `正在获取 ${neededMonths.length} 个月的数据...`;
            await Promise.all(neededMonths.map(m => loadMonthData(m)));
        }
        filterAndSortPapers();
    }

    // 生成论文HTML
    function createPaperHTML(paper) {
        // const task = paper.task ? `<span class="task">${paper.task}</span>` : '';
        const tags = paper.tags ? paper.tags.map(tag => `<span class="tag">${tag}</span>`).join('') : '';

        // 提取代码链接
        let codeLink = '';
        if (paper.code_link) {
            codeLink = `<a href="${paper.code_link}" target="_blank" class="code-link">📄 Code/Project</a>`;
        }

        // 获取会议徽章
        let venueBadge = '';
        if (paper.conference) {
            const badgeInfo = getVenueBadge(paper.conference);
            if (badgeInfo) {
                venueBadge = `<span class="venue-badge ${badgeInfo.class}">${badgeInfo.text}</span>`;
            }
        }

        const status = paper.conference ? 'published' : 'preprint';
        const firstCategory = paper.primary_category;

        return `
            <article class="paper-card" data-date="${paper.published}" data-status="${status}" data-tags="${paper.tags ? paper.tags.join(',') : ''}" data-paper-id="${paper.id}">
                <div class="paper-select">
                    <input type="checkbox" class="paper-checkbox" id="check-${paper.id}" data-paper-id="${paper.id}">
                    <label for="check-${paper.id}"></label>
                </div>
                <div class="paper-content">
                    <h2 class="paper-title">
                        <a href="https://arxiv.org/abs/${paper.id}" target="_blank">${paper.title}</a>
                    </h2>
                    <div class="paper-meta">
                        <span class="meta-item">📅 ${paper.published}</span>
                        ${venueBadge}
                        ${codeLink}
                    </div>
                    <div class="paper-authors">
                        👥 ${paper.authors}
                    </div>
                    <div class="paper-summary">
                        🤖 ${paper.summary}
                    </div>
                    <div class="paper-tags">
                        ${tags}
                    </div>
                    <div class="paper-abstract">
                        <details>
                            <summary>查看摘要</summary>
                            <p>${paper.abstract}</p>
                        </details>
                    </div>
                </div>
            </article>
        `;
    }

    // 获取会议徽章信息
    function getVenueBadge(conference) {
        if (!conference) return null;

        // 根据会议名称中包含的关键词决定徽章样式
        const conferenceUpper = conference.toUpperCase();
        let badgeClass = 'badge-published';  // 默认样式

        // 顶级会议匹配
        if (conferenceUpper.includes('NEURIPS')) {
            badgeClass = 'badge-neurips';
        } else if (conferenceUpper.includes('ICLR')) {
            badgeClass = 'badge-iclr';
        } else if (conferenceUpper.includes('ICML')) {
            badgeClass = 'badge-icml';
        } else if (conferenceUpper.includes('CVPR')) {
            badgeClass = 'badge-cvpr';
        } else if (conferenceUpper.includes('ICCV')) {
            badgeClass = 'badge-iccv';
        } else if (conferenceUpper.includes('ECCV')) {
            badgeClass = 'badge-eccv';
        } else if (conferenceUpper.includes('ACL')) {
            badgeClass = 'badge-acl';
        } else if (conferenceUpper.includes('EMNLP')) {
            badgeClass = 'badge-emnlp';
        } else if (conferenceUpper.includes('NAACL')) {
            badgeClass = 'badge-naacl';
        } else if (conferenceUpper.includes('AAAI')) {
            badgeClass = 'badge-aaai';
        } else if (conferenceUpper.includes('IJCAI')) {
            badgeClass = 'badge-ijcai';
        }

        // 直接使用从 ArXiv comments 提取的完整会议名称
        return { class: badgeClass, text: conference };
    }
    
    // 更新task按钮的数量
    function updateTaskButtonCounts() {
        try {
            // 筛选符合当前状态和分类的论文（但不按 task 筛选）
            const statusFilteredPapers = allPapersData.filter(paper => {
                const status = paper.conference ? 'published' : 'preprint';
                const category = paper.category || [];
                const field = paper.field;

                const matchStatus = currentStatus === 'all' || status === currentStatus;
                const matchCategory = currentCategory === 'all' || category.includes(currentCategory);
                const matchField = currentField === 'all' || field === currentField;

                return matchStatus && matchCategory && matchField;
            });

            // 如果 currentField === 'all'，我们只展示 "all" 按钮，其他按钮隐藏
            if (currentField === 'all') {
                // 统计总数，并只显示全部按钮（其余按钮隐藏）
                const total = statusFilteredPapers.length;
                taskBtns.forEach(btn => {
                    const task = btn.dataset.task;
                    if (task === 'all') {
                        btn.style.display = ''; // 显示
                        btn.textContent = `全部 (${total})`;
                    } else {
                        btn.style.display = 'none'; // 隐藏其他 task 按钮
                    }
                });
                return;
            }

            // 如果是具体的 field，展示该 field 对应的 tasks（先从 field2task 找到任务列表）
            const tasksForField = field2task[currentField] || [];

            // 初始化计数映射（包含 all）
            const taskCounts = { 'all': statusFilteredPapers.length };
            tasksForField.forEach(t => { taskCounts[t] = 0; });

            // 统计
            statusFilteredPapers.forEach(paper => {
                const task = paper.task || '';
                if (!task) return;
                if (taskCounts.hasOwnProperty(task)) {
                    taskCounts[task]++;
                } else {
                    // 若 task 不在预定义 tasksForField 中，也把它计入
                    taskCounts[task] = (taskCounts[task] || 0) + 1;
                }
            });

            // 更新按钮：只显示 'all' 和 tasksForField；其他按钮隐藏
            taskBtns.forEach(btn => {
                const task = btn.dataset.task;
                if (task === 'all') {
                    btn.style.display = '';
                    btn.textContent = `全部 (${taskCounts['all'] || 0})`;
                } else if (tasksForField.includes(task)) {
                    btn.style.display = '';
                    btn.textContent = `${task} (${taskCounts[task] || 0})`;
                } else {
                    // 隐藏不属于当前 field 的 task 按钮
                    btn.style.display = 'none';
                }
            });
        } catch (err) {
            console.error('updateTaskButtonCounts error:', err);
        }
    }

    // 渲染 task 按钮（基于 field2task）
    function renderTaskButtons(field) {
        // 1) 找到容器 —— 优先使用页面中已有 .task-btn 的父节点
        const anyTaskBtn = document.querySelector('.task-btn');
        const container = anyTaskBtn ? anyTaskBtn.parentElement : (document.querySelector('#task-buttons') || document.querySelector('.task-buttons'));
    
        if (!container) {
            console.warn('未找到 task 按钮容器：请确保页面存在 .task-btn 或 #task-buttons/.task-buttons 容器。');
            return;
        }
    
        // 2) 找到一个可用的样板按钮（优先 container 内的第一个 .task-btn）
        const prototypeBtn = container.querySelector('.task-btn') || document.querySelector('.task-btn');
    
        // 3) 清空容器
        container.innerHTML = '';
    
        // helper: 根据 prototype 克隆或回退创建按钮
        function makeTaskButton(taskKey, isActive = false) {
            let btn;
            if (prototypeBtn) {
                btn = prototypeBtn.cloneNode(true); // 深拷贝，保留所有类名/结构
                btn.classList.remove('active');     // 初始状态不带 active，按 isActive 决定
            } else {
                // 回退：创建一个和 HTML 匹配的按钮结构
                btn = document.createElement('button');
                btn.className = 'filter-btn task-btn';
                // 把文本放在按钮内
                btn.type = 'button';
            }
    
            // 设置 dataset、active 状态、并更新文本内容（若内部有文本节点/子元素，尽量保留原结构）
            btn.dataset.task = taskKey;
            if (isActive) btn.classList.add('active'); else btn.classList.remove('active');
    
            // 如果样板中有一个子元素用于文本（例如直接文本或 <span>），尝试更新它优先
            const labelSpan = btn.querySelector('.label') || btn.querySelector('span');
            const text = (taskKey === 'all') ? `全部 (0)` : `${taskKey} (0)`;
            if (labelSpan) {
                labelSpan.textContent = text;
                // 如果原样板含图标等，克隆会保留它们
            } else {
                // 若没有合适的子元素，直接设置按钮的文本
                btn.textContent = text;
            }
    
            // 确保是按钮类型
            if (btn.tagName.toLowerCase() === 'button') btn.type = 'button';
            else if (!btn.hasAttribute('role')) btn.setAttribute('role', 'button');
    
            // 绑定点击事件 —— 设置 currentTask 并触发筛选
            btn.addEventListener('click', function () {
                // 取消其它按钮的 active
                container.querySelectorAll('.task-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                currentTask = this.dataset.task;
                filterAndSortPapers(); // 由 filterAndSortPapers() 内部更新计数
            });
    
            return btn;
        }
    
        // Always add 'all' first
        container.appendChild(makeTaskButton('all', currentTask === 'all'));
    
        if (field !== 'all') {
            const tasks = field2task[field] || [];
            tasks.forEach(t => {
                container.appendChild(makeTaskButton(t, currentTask === t));
            });
        }
    
        // 更新全局 taskBtns 节点集合引用
        taskBtns = document.querySelectorAll('.task-btn');
        
        // 渲染task按钮后，设置all为active
        currentTask = 'all';
        taskBtns.forEach(b => b.classList.remove('active'));
        const allBtn = document.querySelector('.task-btn[data-task="all"]');
        if (allBtn) allBtn.classList.add('active');
    }

    // 更新研究领域按钮的数量
    function updateFieldButtonCounts(DatePapers) {
        // 先筛选出符合当前状态的论文
        const statusFilteredPapers = DatePapers.filter(paper => {
            const status = paper.conference ? 'published' : 'preprint';
            const category = paper.category || [];

            const matchStatus = currentStatus === 'all' || status === currentStatus;
            const matchCategory = currentCategory === 'all' || category.includes(currentCategory);

            return matchStatus && matchCategory;
        });

        // 计算各个领域的数量
        const fieldCounts = {
            'all': statusFilteredPapers.length,
            'Requirements & Design': 0,
            'Coding Assistant': 0,
            'Software Testing': 0,
            'AIOps': 0,
            'Maintenance': 0,
            'Quality Management': 0,
            'Version Control & Collaboration': 0
        };

        statusFilteredPapers.forEach(paper => {
            const field = paper.field;
            fieldCounts[field]++;
        });

        // 更新按钮文本
        fieldBtns.forEach(btn => {
            const field = btn.dataset.field;
            const displayName = field === 'all' ? '全部' : field;
                               // category === 'Natural Language Processing' ? 'NLP' : category;
            const count = fieldCounts[field] || 0;
            btn.textContent = `${displayName} (${count})`;
        });
    }

    // 更新论文类型按钮的数量
    function updateCategoryButtonCounts(DatePapers) {
        // 先筛选出符合当前状态的论文
        const statusFilteredPapers = DatePapers.filter(paper => {
            const status = paper.conference ? 'published' : 'preprint';
            return  currentStatus === 'all' || status === currentStatus;
        });

        // 计算各个领域的数量
        const categoryCounts = {
            'all': statusFilteredPapers.length,
            'Empirical': 0,
            'Survey': 0,
            'Benchmark': 0,
            'Technical': 0
        };

        statusFilteredPapers.forEach(paper => {
            const categories = paper.category || [];
            categories.forEach(cat => {
                if (categoryCounts.hasOwnProperty(cat)) {
                    categoryCounts[cat]++;
                }
            });
        });

        // 更新按钮文本
        categoryBtns.forEach(btn => {
            const category = btn.dataset.category;
            const displayName = category === 'all' ? '全部' : category;
            const count = categoryCounts[category] || 0;
            btn.textContent = `${displayName} (${count})`;
        });
    }

    // 更新发表状态按钮的数量
    function updateStatusButtonCounts(DatePapers) {

        // 计算各个领域的数量
        const statusCounts = {
            'all': allPapersData.length,
            'published': 0,
            'preprint': 0
        };

        DatePapers.forEach(paper => {
            if (paper.conference) {
                statusCounts['published']++;
            }
            else {
                statusCounts['preprint']++;
            }
        });

        // 更新按钮文本
        statusBtns.forEach(btn => {
            const status = btn.dataset.status;
            const displayName = status === 'all' ? '全部' :
                               status === 'published' ? '已发表' : '预印本';
            const count = statusCounts[status] || 0;
            btn.textContent = `${displayName} (${count})`;
        });
    }

    // 筛选和排序论文
    function filterAndSortPapers() {
        console.log('Filtering papers:', { currentStatus, currentCategory, currentField, currentTask, searchTerm, currentSort });
        
        const startVal = startDateInput.value;
        const endVal = endDateInput.value;
        DatePapers = allPapersData.filter(paper => {
            const pDate = paper.published;
            return (!startVal || pDate >= startVal) && (!endVal || pDate <= endVal);
        });
        
        // 筛选
        filteredPapers = DatePapers.filter(paper => {
            const status = paper.conference ? 'published' : 'preprint';
            const category = paper.category || [];
            const field = paper.field;
            const task =paper.task;
            const text = `${paper.title} ${paper.authors} ${paper.abstract}`.toLowerCase();

            const matchStatus = currentStatus === 'all' || status === currentStatus;
            const matchCategory = currentCategory === 'all' || category.includes(currentCategory);
            const matchField = currentField === 'all' || field === currentField;
            const matchTask = currentTask === 'all' || task === currentTask;
            const matchSearch = searchTerm === '' || text.includes(searchTerm);

            return matchStatus && matchCategory && matchField && matchTask && matchSearch;
        });

        console.log(`Filtered to ${filteredPapers.length} papers`);

        // 排序
        filteredPapers.sort((a, b) => {
            const dateA = new Date(a.published);
            const dateB = new Date(b.published);

            if (currentSort === 'date-desc') {
                return dateB - dateA;
            } else {
                return dateA - dateB;
            }
        });

        // 更新task按钮的数量
        updateTaskButtonCounts(DatePapers);

        // 更新研究领域按钮的数量
        updateFieldButtonCounts(DatePapers);

        // 更新论文类型按钮的数量
        updateCategoryButtonCounts(DatePapers);

        // 更新发表状态按钮的数量
        updateStatusButtonCounts(DatePapers);

        // 更新显示
        if (resultsCount) {
            resultsCount.textContent = `显示 ${filteredPapers.length} 篇论文`;
        }

        // 重置懒加载
        loadedCount = 0;
        if (papersContainer) {
            papersContainer.innerHTML = '';
        }

        // 移除旧的 observer
        if (observer) {
            observer.disconnect();
        }

        // 加载第一批
        loadMorePapers();
    }

    // 加载更多论文
    function loadMorePapers() {
        if (isLoading || loadedCount >= filteredPapers.length) return;
        isLoading = true;

        const batchSize = loadedCount === 0 ? initialBatchSize : subsequentBatchSize;
        const endIndex = Math.min(loadedCount + batchSize, filteredPapers.length);
        
        for (let i = loadedCount; i < endIndex; i++) {
            const paper = filteredPapers[i];
            const div = document.createElement('div');
            div.innerHTML = createPaperHTML(paper);
            papersContainer.appendChild(div.firstElementChild);
        }

        loadedCount = endIndex;
        isLoading = false;

        if (loadedCount < filteredPapers.length) {
            setupLoadTrigger();
        }
    }

    // 设置加载触发器
    function setupLoadTrigger() {
        let indicator = document.getElementById('loading-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'loading-indicator';
            indicator.className = 'loading-indicator';
            indicator.style.height = '100px';
            indicator.style.margin = '20px 0';
            indicator.style.textAlign = 'center';
            indicator.style.color = '#666';
            indicator.textContent = '加载更多...';
            papersContainer.appendChild(indicator);
        }

        // 创建新的 observer
        if (observer) {
            observer.disconnect();
        }

        observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    console.log('Loading more papers (intersection detected)');
                    loadMorePapers();
                }
            });
        }, {
            rootMargin: '200px'
        });

        observer.observe(indicator);
    }

    // 时间筛选
    startDateInput.onchange = () => {
        // 如果存在结束时间，且开始时间晚于结束时间
        if (endDateInput.value && startDateInput.value > endDateInput.value) {
            // 自动将结束时间设为和开始时间一样
            endDateInput.value = startDateInput.value;
        }
        ensureDataRange(startDateInput.value, endDateInput.value || startDateInput.value);
    };

    endDateInput.onchange = () => {
        // 如果存在开始时间，且结束时间早于开始时间
        if (startDateInput.value && endDateInput.value < startDateInput.value) {
            // 自动将开始时间设为和结束时间一样
            startDateInput.value = endDateInput.value;
        }
        ensureDataRange(startDateInput.value || endDateInput.value, endDateInput.value);
    };
    
    resetDateBtn.onclick = () => {
        // 获取当前本地日期
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0'); // 月份从0开始，需要+1
        const day = String(now.getDate()).padStart(2, '0');
        const todayStr = `${year}-${month}-${day}`;

        // 设置开始和结束时间都为今天
        startDateInput.value = todayStr;
        endDateInput.value = todayStr;

        // 触发数据加载和筛选
        ensureDataRange(todayStr, todayStr);
    };

    // 发表状态筛选
    statusBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            console.log('Status button clicked:', this.dataset.status);
            statusBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentStatus = this.dataset.status;
            filterAndSortPapers();
        });
    });

    // 论文类型筛选
    categoryBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            console.log('Category button clicked:', this.dataset.category);
            categoryBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentCategory = this.dataset.category;
            filterAndSortPapers();
        });
    });
    
    // field筛选
    fieldBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            console.log('Field button clicked:', this.dataset.field);
            fieldBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentField = this.dataset.field;

            // 先渲染对应的 task 按钮（如果 currentField === 'all' 则只渲染 'all'）
            renderTaskButtons(currentField);

            // 再进行筛选与统计（渲染后 updateTaskButtonCounts 会立即更新计数）
            filterAndSortPapers();
        });
    });


    // task筛选
    taskBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            console.log('Task button clicked:', this.dataset.task);
            taskBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentTask = this.dataset.task;
            filterAndSortPapers();
        });
    });

    // 排序按钮
    sortBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            console.log('Sort button clicked:', this.dataset.sort);
            e.preventDefault();
            sortBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentSort = this.dataset.sort;
            filterAndSortPapers();
        });
    });

    // 搜索输入
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            searchTerm = this.value.toLowerCase();
            console.log('Search term:', searchTerm);
            filterAndSortPapers();
        });
    }

    // 更新选中数量
    function updateSelectedCount() {
        const count = document.querySelectorAll('.paper-checkbox:checked').length;
        if (selectedCount) {
            selectedCount.textContent = count;
        }
    }

    // 监听复选框变化（使用事件委托）
    if (papersContainer) {
        papersContainer.addEventListener('change', function(e) {
            if (e.target.classList.contains('paper-checkbox')) {
                updateSelectedCount();
            }
        });
    }

    // 全选功能
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function() {
            const checkboxes = document.querySelectorAll('.paper-checkbox');
            checkboxes.forEach(cb => cb.checked = true);
            updateSelectedCount();
            console.log('All papers selected');
        });
    }

    // 清空选择
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', function() {
            const checkboxes = document.querySelectorAll('.paper-checkbox');
            checkboxes.forEach(cb => cb.checked = false);
            updateSelectedCount();
            console.log('All selections cleared');
        });
    }

    // 导出功能
    if (exportBtn) {
        exportBtn.addEventListener('click', function(e) {
            console.log('Export button clicked');
            e.preventDefault();
            exportToBibTeX();
        });
    }

    // 导出为 BibTeX
    function exportToBibTeX() {
        // 获取所有选中的复选框
        const checkboxes = document.querySelectorAll('.paper-checkbox:checked');

        if (checkboxes.length === 0) {
            alert('请至少选择一篇论文导出！');
            return;
        }

        // 获取选中的论文ID
        const selectedIds = Array.from(checkboxes).map(cb => cb.dataset.paperId);

        // 从所有论文数据中找到对应的论文
        const selectedPapers = allPapersData.filter(paper => selectedIds.includes(paper.id));

        let bibtex = '';
        selectedPapers.forEach((paper, index) => {
            const arxivId = paper.id;
            const year = paper.published.split('-')[0];

            bibtex += `@article{${arxivId.replace('.', '_')},
`;
            bibtex += `  title={${paper.title}},
`;
            bibtex += `  author={${paper.authors}},
`;
            bibtex += `  year={${year}},
`;
            bibtex += `  journal={arXiv preprint arXiv:${arxivId}}`;
            if (paper.conference) {
                bibtex += `,
  note={${paper.conference}}`;
            }
            bibtex += `
}

`;
        });

        console.log(`Exporting ${selectedPapers.length} selected papers`);
        downloadFile(bibtex, 'papers.bib', 'text/plain');
    }

    // 下载文件
    function downloadFile(content, filename, contentType) {
        const blob = new Blob([content], { type: contentType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        console.log('File download triggered:', filename);
    }

    // 初始化 - 加载数据
    console.log('Initializing...');
    init();
});
"""

        js_dir = self.output_dir / "js"
        js_dir.mkdir(parents=True, exist_ok=True)

        with open(js_dir / "main.js", 'w', encoding='utf-8') as f:
            f.write(js)

        logger.info("生成 JavaScript 文件")

    def run(self):
        """运行生成流程"""
        logger.info("开始生成静态网页...")

        self.load_papers()
        self.generate_monthly_data_files()  # 生成月度数据文件
        self.generate_css()
        self.generate_js()
        self.generate_index_html()

        logger.info(f"网页生成完成! 输出目录: {self.output_dir}")


def main(paper_path):
    generator = HTMLGenerator(paper_path)
    generator.run()


if __name__ == "__main__":
    paper_path = "papers_metadata.jsonl"
    main(paper_path)
