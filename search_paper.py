import os
import json
import arxiv
import yaml
import logging
import argparse
from datetime import datetime
from gpt import call_chatgpt
from utils import save_last_position, load_last_position
import requests
import fitz

logging.basicConfig(format='[%(asctime)s %(levelname)s] %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)


class PaperSearch:
    def __init__(self, config_path):
        self.config = self.load_config(config_path)
        logging.info(self.config)
        self.paper = set()
        self.get_recent_paper(self.config['papers_metadata_path'])

    # def load_config(config_file: str) -> dict:
    #     """
    #     config_file: input config file path
    #     return: a dict of configuration
    #     """
    #
    #     def pretty_filters(**config) -> dict:
    #         keywords = dict()
    #         OR = ' OR '
    #         AND = ' AND '
    #
    #         def parse_filters(filters: list) -> str:
    #             ret = []
    #             for filter_item in filters:
    #                 # 如果filter_item是列表，则用OR连接每个术语，并将包含空格的术语用双引号括起来
    #                 if isinstance(filter_item, list):
    #                     terms = []
    #                     for term in filter_item:
    #                         if ' ' in term:
    #                             terms.append(f'"{term}"')
    #                         else:
    #                             terms.append(term)
    #                     ret.append('(' + OR.join(terms) + ')')
    #                 # 如果filter_item是字符串，则直接使用
    #                 else:
    #                     ret.append(filter_item)
    #             return AND.join(ret)
    #
    #         for k, v in config['keywords'].items():
    #             keywords[k] = parse_filters(v['filters'])
    #         return keywords
    #
    #     with open(config_file, 'r') as f:
    #         config = yaml.load(f, Loader=yaml.FullLoader)
    #         config['kv'] = pretty_filters(**config)
    #         logging.info(f'config = {config}')
    #     return config

    def load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.error(f"读取文件 {config_path} 失败: {e}")

    def get_recent_paper(self, file_path):
        try:
            if not os.path.exists(file_path):
                return
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        item = json.loads(line.strip())
                        self.paper.add(item['id'])
                    except json.JSONDecodeError:
                        print(f"警告：无法解析JSON行: {line}")
                        continue
        except Exception as e:
            logging.error(f"读取文件 {file_path} 失败: {e}")

    # def get_recent_paper(self, file_path):
    #     """读取papers_metadata.jsonl文件从头到指定位置的内容"""
    #     last_position = load_last_position()
    #     current_position = 0
    #
    #     with open(file_path, 'r', encoding='utf-8') as f:
    #         while current_position < last_position:
    #             line = f.readline().strip()
    #             if not line:  # 文件结束
    #                 break
    #
    #             current_position = f.tell()  # 获取当前文件位置
    #
    #             # 如果读取这行后超过目标位置，说明这行不完整
    #             if current_position > last_position:
    #                 break
    #
    #             try:
    #                 item = json.loads(line.strip())
    #                 self.paper.append(item['id'])
    #             except json.JSONDecodeError:
    #                 print(f"警告：无法解析JSON行: {line}")
    #                 continue

    def get_authors(self, authors, first_author=False):
        output = str()
        if not first_author:
            output = ", ".join(str(author) for author in authors)
            return output
        else:
            # 返回第一作者，确保是字符串
            first_author_obj = authors[0]
            if hasattr(first_author_obj, 'name'):
                return first_author_obj.name
            else:
                return str(first_author_obj)

    def download_paper_pdf(self, result, download_dir="./papers"):
        """
        下载论文的PDF文件

        @param result: arxiv.Result - arXiv论文结果对象
        @param download_dir: str - PDF下载目录路径
        @return: pdf_path: str - PDF文件路径
        """
        try:
            # 获取论文ID（移除版本后缀）
            paper_id = result.get_short_id()
            if isinstance(paper_id, bytes):
                paper_id = paper_id.decode("utf-8", errors="ignore")
            ver_pos = paper_id.find('v')
            paper_key = paper_id[0:ver_pos] if ver_pos != -1 else paper_id

            # 创建下载目录（如果不存在）
            os.makedirs(download_dir, exist_ok=True)

            # 构建PDF文件路径
            pdf_filename = f"{paper_key}.pdf"
            pdf_path = os.path.join(str(download_dir), str(pdf_filename))

            # 检查PDF是否已存在
            if paper_key in self.paper:
                logging.info(f"PDF已存在: {pdf_filename}")
                return None

            try:
                # 使用 arxiv 库的 download_pdf 方法下载 PDF
                result.download_pdf(dirpath=download_dir, filename=pdf_filename)
                logging.info(f"下载PDF: {pdf_filename}")
                return str(pdf_path)
            except Exception as e:
                logging.error(f"使用 arxiv API 下载 {result.get_short_id()} PDF 失败: {e}")

            # 尝试直接 HTTP 下载
            pdf_url = getattr(result, "pdf_url", None)
            if pdf_url is None:
                pdf_url = f"https://arxiv.org/pdf/{paper_key}.pdf"

            if isinstance(pdf_url, bytes):
                try:
                    pdf_url = pdf_url.decode('utf-8', errors='ignore')
                except Exception:
                    pdf_url = str(pdf_url)

            r = requests.get(pdf_url, timeout=30)
            r.raise_for_status()

            # 使用普通写文件方式
            with open(pdf_path, "wb") as f:
                f.write(r.content)

            logging.info(f"HTTP 下载成功: {pdf_path}")
            return str(pdf_path)

        except Exception as e:
            logging.error(f"下载 {result.get_short_id()} PDF 失败: {e}")
            return None

    def get_3_page_paper(self, pdf_path):
        try:
            doc = fitz.open(pdf_path)
            all_text = []
            max_page = min(3, doc.page_count)
            for page_num in range(max_page):
                page = doc.load_page(page_num)
                all_text.append(page.get_text("text"))

            doc.close()

            final_text = "\n\n".join(all_text)

            return final_text

        except Exception as e:
            logging.error(f"获取论文前三页失败: {e}")
            try:
                doc.close()
            except:
                pass

    def save_paper_metadata(self, result, resp, pdf_path=None, jsonl_file="papers_metadata.jsonl"):
        """
        保存论文元数据到JSONL文件

        @param result: arxiv.Result - arXiv论文结果对象
        @param topic: str - 论文主题/类别
        @param pdf_path: str - PDF文件路径
        @param jsonl_file: str - JSONL元数据文件路径
        """
        try:
            # 提取论文的基本信息
            paper_id = result.get_short_id()
            ver_pos = paper_id.find('v')
            paper_key = paper_id[0:ver_pos] if ver_pos != -1 else paper_id

            paper_title = result.title
            paper_url = f"https://arxiv.org/abs/{paper_key}"
            paper_abstract = result.summary.replace("\n", " ")
            paper_authors = [author.name for author in result.authors]
            paper_first_author = self.get_authors(result.authors, first_author=True)
            # primary_category = result.primary_category
            publish_time = result.published.date()
            update_time = result.updated.date()
            # comment = result.comment if result.comment else None
            # journal_ref = result.journal_ref if hasattr(result, 'journal_ref') and result.journal_ref else None
            # journal_ref = self.extract_venue_by_llm(journal_ref).strip()
            # conference = self.extract_venue_from_journal_ref(journal_ref)
            # if conference is None:
            #     comment = self.extract_venue_by_llm(comment).strip()
            #     conference = self.extract_venue_from_comment(comment)
            conference = resp['venue']
            if resp['venue'] and resp['year']:
                conference = resp['venue'] + ' ' + str(resp['year'])
            conference = self.extract_venue_from_journal_ref(conference) or self.extract_venue_from_comment(conference)

            text = self.get_3_page_paper(pdf_path)
            resp = self.build_paper_analyse_prompt(text)


            # 获取当前时间作为下载时间
            download_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 构建论文元数据字典
            paper_metadata = {
                'id': paper_key,  # 论文ID
                'title': paper_title,  # 标题
                'abstract': paper_abstract,  # 摘要
                'arxiv_url': paper_url,  # 论文URL
                'authors': paper_authors,  # 所有作者
                'first_author': paper_first_author,  # 第一作者
                # 'primary_category': primary_category,  # 主要分类
                "category": resp['category'],
                "field": resp['field'],
                "tag": resp['task'],
                "summary": resp['summary'],
                "quality": resp['quality'],
                "conference": conference,  # 会议/期刊
                'pdf_url': result.pdf_url,  # PDF路径
                'published': str(publish_time),  # 发布日期
                'update_time': str(update_time),  # 更新日期
                'download_time': download_time,  # 下载时间
            }

            # 以追加模式写入JSONL文件
            with open(jsonl_file, 'a', encoding='utf-8') as f:
                # 将字典转换为JSON字符串并写入文件，末尾添加换行符
                f.write(json.dumps(paper_metadata, ensure_ascii=False) + '\n')
                # current_position = f.tell()
                # save_last_position(current_position)

            logging.info(f"保存元数据: {paper_key} - {paper_title}")

        except Exception as e:
            logging.error(f"保存元数据失败: {e}")

    def get_daily_papers(self, query, max_results=2, download_dir="./papers", jsonl_file="papers_metadata.jsonl"):
        """
        根据query检索论文
        """

        success = 0
        client = arxiv.Client()
        search_engine = arxiv.Search(
            query=f"cat:{query}",
            sort_by=arxiv.SortCriterion.SubmittedDate
            # sort_by=arxiv.SortCriterion.Relevance
        )

        # 遍历搜索结果中的每一篇论文
        for result in client.results(search_engine):

            try:
                paper_title = result.title
                paper_abstract = result.summary
                content = paper_title + '\n' + paper_abstract
                if result.journal_ref:
                    content += '\n' + "journal_ref: " + result.journal_ref
                if result.comment:
                    content += '\n' + "comment: " + result.comment
                resp = self.filter_paper(content)

                if resp['isLLM4SE']:
                    # 下载PDF文件
                    pdf_path = self.download_paper_pdf(result, download_dir)

                    # 保存元数据到jsonl
                    if pdf_path is not None:
                        self.save_paper_metadata(result, resp, pdf_path, jsonl_file)
                        success += 1
                        if success >= max_results:
                            break

            except Exception as e:
                logging.error(f"处理{result.get_short_id()}论文时出错: {e}")

        return success

    def build_paper_analyse_prompt(self, text_content) -> tuple[str, str]:
        """
        构建一个精确的提示，指导大模型对论文文本分类的 *详细* 信息。
        """
        system_prompt = """You are an expert researcher in Large Language Models for Software Engineering (LLM4SE).
        Your task is to classify and summarize academic papers with high accuracy.
        """

        user_prompt = f"""Classify the following LLM4SE paper according to four criteria. Follow the instructions exactly and output only the JSON.

        1. Paper Category
        
            Assign one or more of the following categories (multiple allowed):
            
            (1) Survey / Review — synthesizes, summarizes, or organizes existing research or tools.
            (2) Experience / Empirical — analyzes existing phenomena in LLM4SE (e.g., evaluating current LLMs on tasks, understanding behavior, measuring performance); does not introduce a new method or dataset.
            (3) Technical / Method — proposes a new method, model, algorithm, or tool for an SE task using LLMs.
            (4) Benchmark / Dataset —  introduces a brand‑new benchmark, dataset, or evaluation suite for LLM4SE.
                  - What does NOT qualify as “Benchmark / Dataset” :
                      1. Using an existing, publicly available benchmark or dataset for experiments or evaluation.
                      2. Presenting only evaluation results on a pre‑existing benchmark without providing any new data or evaluation framework. 
            
            Note: If a paper possesses multiple type features (e.g., proposing a new method + publishing a new dataset), multiple categories can be returned, for example: ["Technical", "Benchmark"]
        
        2. Field & Task Classification
        
            You will be provided with a field->task mapping relationship in JSON format. Your goal is to match the paper's content to the most specific `field` and `task` from this taxonomy.
            Output the **field** name (the top-level key) and the **task** name (the specific string from the list) that best describe the paper's main focus.
            If the paper's focus does not clearly match any provided `field` or `task`, summarize a new `field` or `task`.
            **Provided Taxonomy:** `{self.config['topic']}`
        
        3. One-Sentence Summary
        
            Summarize the paper in one concise sentence in Chinese.
        
        4. Quality Assessment
        
            Rate the overall quality as exactly one of:
            
                - High: Well-written, clearly motivated, methodologically sound (or promising), and presents a significant contribution. Worth following closely.
                - Middle: Clearly written with a reasonable contribution, but may have limitations in scope, evaluation, or novelty. Worth skimming.
                - Low: Poorly structured, weakly motivated, or contributes minimally. Low priority.
            
            Quality considers writing clarity, rigor, novelty/insight, and value for LLM4SE.
        
        Output Format (must match exactly)
        {{
          "category": [],
          "field": "",
          "task": "",
          "summary": "",
          "quality": ""
        }}
        
        Please analyze the following paper text and extract relevant information about the paper.:**\n---\n{text_content}\n---
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        resp = call_chatgpt(messages)

        return resp

    def filter_paper(self, text_content):

        system_prompt = """
        You are an expert researcher in Large Language Models for Software Engineering (LLM4SE).
        Your task is to analyze the provided academic paper's title and abstract to determine if it is related to LLM4SE. 
        
        If the paper is NOT related to LLM4SE, set the value for `isLLM4SE` to false, `venue` and `year` to null.
        
        If the paper is related to LLM4SE, identify the venue (conference or journal) where the paper was formally published and its publication year.
        If the paper is a preprint, set the values for both 'venue' and 'year' to null.
        
        Return output strictly in the specified JSON format, only return the JSON object, without any explanations.

        **Required JSON structure:**
        {
          "isLLM4SE": (true if the paper is related to LLM4SE, otherwise false),
          "venue": (Name of the conference or journal. Null if preprint/unpublished),
          "year": (Four-digit publication year. Null if preprint/unpublished)
        }
        """

        user_prompt = f"""
        Please analyze the following text of paper and extract relevant information about the paper:
        {text_content}
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        resp = call_chatgpt(messages)

        return resp

    def extract_venue_from_journal_ref(self, journal_ref: str) -> str:
        """从 journal_ref 字段提取会议/期刊信息
        例如: "The International Conference on Pattern Recognition (ICPR),2024"
        """
        if not journal_ref:
            return None

        journal_ref = journal_ref.strip()

        import re

        # 常见会议列表
        conferences = [
            'CVPR', 'ICCV', 'ECCV', 'NeurIPS', 'ICML', 'ICLR',
            'ACL', 'EMNLP', 'NAACL', 'AAAI', 'IJCAI', 'KDD',
            'ICRA', 'IROS', 'CoRL', 'RSS', 'ICPR',
            'SIGIR', 'WWW', 'WSDM', 'RecSys',
            'SIGMOD', 'VLDB', 'ICDE',
            'SIGGRAPH', 'ICASSP', 'INTERSPEECH', 'ISMB',
            'ISSTA', 'ICPC', 'FSE', 'ICSE', 'ASE', 'ICSME', 'COLM'
        ]

        # 模式1: 提取括号中的会议缩写及周围信息
        # 例如: "The International Conference on Pattern Recognition (ICPR),2024"
        pattern_with_acronym = r'([^()]*)\s*\(([A-Z]{2,})\s*(?:\d+)?\)\s*,?\s*(\d{4})?'
        match = re.search(pattern_with_acronym, journal_ref)
        if match:
            full_name = match.group(1).strip()  # "The International Conference on Pattern Recognition"
            acronym = match.group(2)  # "ICPR"
            year = match.group(3)  # "2024"

            # 检查是否是已知的会议
            if acronym.upper() in conferences:
                # 构建返回值
                if year:
                    result = f"{full_name} ({acronym} {year})"
                else:
                    result = f"{full_name} ({acronym})"

                # 限制长度
                if len(result) <= 200:
                    return result

        # 模式2: 如果没找到括号，就直接返回整个journal_ref
        # 但只有在看起来像期刊/会议名称时才返回
        if len(journal_ref) > 3 and len(journal_ref) <= 200:
            # 检查是否包含常见的关键词
            if any(keyword.lower() in journal_ref.lower() for keyword in
                   ['conference', 'journal', 'proceedings', 'transactions', 'letters',
                    'review', 'symposium', 'workshop']):
                return journal_ref

        return None

    def extract_venue_from_comment(self, comment: str) -> str:
        """从 comment 字段提取会议/期刊信息，优先返回原始完整描述"""
        if not comment:
            return None

        comment = comment.strip()

        # 预处理：移除页数、图表、链接等冗余信息
        import re
        # 移除 "X pages, Y figures, Z tables" 等信息
        comment = re.sub(r'\d+\s*pages?[,;]?\s*', '', comment, flags=re.IGNORECASE)
        comment = re.sub(r'\d+\s*figures?[,;]?\s*', '', comment, flags=re.IGNORECASE)
        comment = re.sub(r'\d+\s*tables?[,;]?\s*', '', comment, flags=re.IGNORECASE)
        comment = re.sub(r'\d+\s*appendices[,;]?\s*', '', comment, flags=re.IGNORECASE)
        # 移除 URL 链接
        comment = re.sub(r'https?://[^\s,;]+', '', comment, flags=re.IGNORECASE)
        # 移除 GitHub 链接描述
        comment = re.sub(r'GitHub\s+link:?\s*', '', comment, flags=re.IGNORECASE)
        comment = ' '.join(comment.split())  # 清理多余空格

        # 如果是 preprint，返回 None
        if 'preprint' in comment.lower() and 'accepted' not in comment.lower():
            return None

        # 常见会议列表
        conferences = [
            'CVPR', 'ICCV', 'ECCV', 'NeurIPS', 'ICML', 'ICLR',
            'ACL', 'EMNLP', 'NAACL', 'AAAI', 'IJCAI', 'KDD',
            'ICRA', 'IROS', 'CoRL', 'RSS',
            'SIGIR', 'WWW', 'WSDM', 'RecSys',
            'SIGMOD', 'VLDB', 'ICDE',
            'SIGGRAPH', 'ICASSP', 'INTERSPEECH', 'ISMB',
            'ISSTA', 'ICPC', 'FSE', 'ICSE', 'ASE', 'ICSME', 'COLM'
        ]

        # 常见期刊列表
        journals = [
            'Nature', 'Science', 'PAMI', 'TPAMI', 'JMLR', 'IJCV',
            'IEEE', 'ACM', 'Transactions', 'Journal', 'TMLR',
            'TSE', 'ESE'
        ]

        # 尝试匹配常见模式并提取完整描述
        # 模式1: "Accepted at/to CVPR 2025" 或 "Published in ICCV 2025" 或 "Published with Journal Name (Acronym)"
        # 支持更多变体：at the, by the, for, in the, with 等
        # 特别处理期刊名称，可能包含括号中的缩写
        # 使用 .+? 贪婪匹配到逗号、句号、分号或字符串结尾（\Z）
        # pattern1 = r'(?:accepted?\s+(?:at\s+(?:the\s+)?|to\s+(?:the\s+)?|by\s+(?:the\s+)?|for\s+(?:the\s+)?)|published\s+(?:in\s+(?:the\s+)?|at\s+(?:the\s+)?|with\s+)|to\s+appear\s+(?:in\s+(?:the\s+)?|at\s+(?:the\s+)?))\s*(.+?)(?:[.,;]|\Z)'
        pattern1 = r'(?:accepted?\s+(?:at\s+(?:the\s+)?|to\s+(?:the\s+)?|by\s+(?:the\s+)?|for\s+(?:the\s+)?)|published\s+(?:in\s+(?:the\s+)?|at\s+(?:the\s+)?|with\s+)|to\s+appear\s+(?:in\s+(?:the\s+)?|at\s+(?:the\s+)?))\s*([^.,;]*?(?:\'?\d{2,4})?)(?:[.,;]|\Z)'
        match = re.search(pattern1, comment, re.IGNORECASE)
        if match:
            venue_text = match.group(1).strip()
            # 清理多余空格、换行符
            venue_text = ' '.join(venue_text.split())
            # 移除尾部的位置信息（如 ", Washington, DC, USA"），但保留括号内容如 (IJETT)
            venue_text = re.sub(r',\s*[A-Z][a-zA-Z\s,]+,\s*[A-Z]{2,}(?:\s*,\s*[A-Z]{2,4})?$', '', venue_text)
            # 放宽长度限制，支持完整的期刊名称
            if 5 < len(venue_text) <= 200:
                return venue_text

        # 模式2: 直接以会议名开头，如 "CVPR 2025, Main Conference"
        for conf in conferences:
            pattern = rf'\b({conf}\s+\d{{4}}(?:\s*[,\-]\s*[\w\s]+)?)'
            match = re.search(pattern, comment, re.IGNORECASE)
            if match:
                venue_text = match.group(1).strip()
                # 限制长度
                if ',' in venue_text or '-' in venue_text:
                    # 只取会议名和年份部分
                    venue_text = re.match(rf'{conf}\s+\d{{4}}', venue_text, re.IGNORECASE).group(0)
                return venue_text

        # 模式3: 只有会议名和年份
        for conf in conferences:
            pattern = rf'\b{conf}\s*[:\']?\s*(\d{{4}})\b'
            match = re.search(pattern, comment, re.IGNORECASE)
            if match:
                year = match.group(1)
                return f"{conf} {year}"

        # 模式4: 只有会议名
        for conf in conferences:
            pattern = rf'\b{conf}\b'
            if re.search(pattern, comment, re.IGNORECASE):
                return conf

        # 检查期刊 - 尽量返回完整描述
        for journal in journals:
            if journal.lower() in comment.lower():
                # 取第一句或前80个字符
                first_sentence = comment.split('.')[0].strip()
                if len(first_sentence) <= 80:
                    return first_sentence
                return comment[:80].strip() + '...'

        return None

    def search(self):
        categories = self.config['categories']
        max_results = self.config['max_results']
        download_papers_path = self.config['download_papers_path']
        papers_metadata_path = self.config['papers_metadata_path']

        logging.info(f"GET daily papers begin")
        for cate in categories:
            logging.info(f"Keyword: {cate}")
            success_download = self.get_daily_papers(query=cate, max_results=max_results,
                                                     download_dir=download_papers_path, jsonl_file=papers_metadata_path)
            logging.info(f"Download {success_download} new papers")

        # 保存新的文件位置
        # new_position = os.path.getsize(papers_metadata_path)
        # save_last_position(new_position)

        logging.info(f"GET daily papers end")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_path', type=str, default='config.yaml',
                        help='configuration file path')
    args = parser.parse_args()

    search = PaperSearch(args.config_path)
    search.search()
