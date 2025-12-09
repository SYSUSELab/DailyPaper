import arxiv
from search_paper import *


def scan_paper_jsonl(paper_search):
    """扫描papers_metadata.jsonl文件是否有手动添加的论文"""
    print("--- 正在扫描论文列表 ---")
    paper_manual_jsonl = "paper_manual.jsonl"
    paper_jsonl = paper_search.config['papers_metadata_path']

    try:
        # 读取原文件
        with open(paper_manual_jsonl, 'r', encoding='utf-8') as f, open(paper_jsonl, 'a', encoding='utf-8') as file:

            for line in f:

                data = json.loads(line)
                if "id" in data:
                    id = data['id']
                    client = arxiv.Client()
                    search_engine = arxiv.Search(
                        query=id,
                        sort_by=arxiv.SortCriterion.Relevance,
                        max_results=1
                    )
                    # 遍历搜索结果中的每一篇论文
                    for result in client.results(search_engine):

                        try:
                            # 判断是否有重复论文
                            paper_id = result.get_short_id()
                            ver_pos = paper_id.find('v')
                            paper_key = paper_id[0:ver_pos] if ver_pos != -1 else paper_id
                            if paper_key in paper_search.paper:
                                print("论文已存在")
                                break

                            # 判断论文是否为LLM4SE
                            paper_title = result.title
                            print(paper_title)
                            paper_abstract = result.summary
                            content = paper_title + '\n' + paper_abstract
                            print(result.journal_ref)
                            if result.journal_ref:
                                content += '\n' + "journal_ref: " + result.journal_ref
                            if result.comment:
                                content += '\n' + "comment: " + result.comment
                            resp = paper_search.filter_paper(content)
                            print(resp)
                            if resp['isLLM4SE']:
                                # 下载PDF文件
                                pdf_path = paper_search.download_paper_pdf(result, paper_search.config['download_papers_path'])

                                # 保存元数据到jsonl
                                # 提取论文的基本信息
                                paper_title = result.title
                                paper_url = f"https://arxiv.org/abs/{paper_key}"
                                paper_abstract = result.summary.replace("\n", " ")
                                paper_authors = [author.name for author in result.authors]
                                paper_first_author = paper_search.get_authors(result.authors, first_author=True)
                                # primary_category = result.primary_category
                                publish_time = result.published.date()
                                update_time = result.updated.date()

                                conference = resp['venue']
                                if resp['venue'] and resp['year']:
                                    conference = resp['venue'] + ' ' + str(resp['year'])
                                conference = paper_search.extract_venue_from_journal_ref(conference) or paper_search.extract_venue_from_comment(conference)

                                text = paper_search.get_3_page_paper(pdf_path)
                                resp = paper_search.build_paper_analyse_prompt(text)

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
                                    "task": resp['task'],
                                    "tags": resp['tags'],
                                    "summary": resp['summary'],
                                    "quality": resp['quality'],
                                    "conference": conference,  # 会议/期刊
                                    'pdf_url': result.pdf_url,  # PDF路径
                                    'published': str(publish_time),  # 发布日期
                                    'update_time': str(update_time),  # 更新日期
                                    'download_time': download_time,  # 下载时间
                                }

                                file.write(json.dumps(paper_metadata, ensure_ascii=False) + '\n')
                                file.flush()
                                paper_search.paper.add(paper_key)

                        except Exception as e:
                            print(f"处理{result.get_short_id()}论文时出错: {e}")

        # 清空文件
        with open(paper_manual_jsonl, 'w', encoding='utf-8') as f:
            f.write('')

    except Exception as e:
        print(f"处理文件时出错: {e}")

    print("--- 扫描结束 ---")


if __name__ == "__main__":
    config_path = "config.yaml"
    search = PaperSearch(config_path)
    scan_paper_jsonl(search)

