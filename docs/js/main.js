// 筛选、搜索、排序和懒加载功能
document.addEventListener('DOMContentLoaded', function() {
    console.log('JavaScript loaded');

    // 获取DOM元素
    const monthBtns = document.querySelectorAll('.month-btn');
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
        monthBtns: monthBtns.length,
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
    let currentMonth = 'all';  // 当前选中的月份
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
    let monthsCache = {};  // 缓存已加载的月份数据

    const field2task = {'Requirements & Design': ['Elicitation', 'Analysis', 'Specification &Validation', 'Management'],
        'Coding Assistant': ['Code Pre-Training', 'Code Instruction-Tuning', 'Code Alignment', 'Code Prompting', 'Code Completion', 'Code Summarization', 'Code Editing', 'Code Translation', 'Code Reasoning', 'Code Retrieval', 'Code Understanding', 'Code Performance Optimization', 'Code Representation Learning'],
        'Software Testing': ['Test Generation', 'Assertion generation', 'GUI test', 'Testing automation', 'Testing prediction', 'Testing Repair'],
        'AIOps': ['Log Statement Generation', 'Log Parsing'],
        'Maintenance': ['Code Review', 'Clone Detection', 'Refactoring'],
        'Quality Management': ['Defect Prediction', 'Bug Localization', 'Bug Repair', 'Vulnerability Detection', 'Vulnerability Repair'],
        'Version Control & Collaboration': ['Git VCS']}

    // 加载月份索引
    async function loadMonthsIndex() {
        try {
            const response = await fetch('data/index.json');
            const monthsIndex = await response.json();
            console.log('Months index loaded:', monthsIndex);

            // 默认加载最新月份的数据
            if (monthsIndex.length > 0) {
                await loadMonthData('all');
            }
        } catch (e) {
            console.error('Failed to load months index:', e);
        }
    }

    // 加载指定月份的数据
    async function loadMonthData(month) {
        if (month === 'all') {
            // 加载所有月份
            try {
                const response = await fetch('data/index.json');
                const monthsIndex = await response.json();

                // 加载所有月份数据
                allPapersData = [];
                for (const monthInfo of monthsIndex) {
                    if (!monthsCache[monthInfo.month]) {
                        const monthResponse = await fetch(`data/${monthInfo.month}.json`);
                        monthsCache[monthInfo.month] = await monthResponse.json();
                    }
                    allPapersData.push(...monthsCache[monthInfo.month]);
                }
                console.log(`Loaded all months, total ${allPapersData.length} papers`);
            } catch (e) {
                console.error('Failed to load all months data:', e);
            }
        } else {
            // 加载单个月份
            if (!monthsCache[month]) {
                try {
                    const response = await fetch(`data/${month}.json`);
                    monthsCache[month] = await response.json();
                    console.log(`Loaded month ${month}, ${monthsCache[month].length} papers`);
                } catch (e) {
                    console.error(`Failed to load month ${month}:`, e);
                    return;
                }
            }
            allPapersData = monthsCache[month];
            console.log(`Using cached data for ${month}, ${allPapersData.length} papers`);
        }
        
        // 渲染task按钮
        renderTaskButtons(currentField);

        // 数据加载完成后，触发筛选
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
    function updateFieldButtonCounts() {
        // 先筛选出符合当前状态的论文
        const statusFilteredPapers = allPapersData.filter(paper => {
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
    function updateCategoryButtonCounts() {
        // 先筛选出符合当前状态的论文
        const statusFilteredPapers = allPapersData.filter(paper => {
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
    function updateStatusButtonCounts() {

        // 计算各个领域的数量
        const statusCounts = {
            'all': allPapersData.length,
            'published': 0,
            'preprint': 0
        };

        allPapersData.forEach(paper => {
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

        // 筛选
        filteredPapers = allPapersData.filter(paper => {
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
        updateTaskButtonCounts();

        // 更新研究领域按钮的数量
        updateFieldButtonCounts();

        // 更新论文类型按钮的数量
        updateCategoryButtonCounts();

        // 更新发表状态按钮的数量
        updateStatusButtonCounts();

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
        if (isLoading || loadedCount >= filteredPapers.length) {
            console.log('Skip loading:', { isLoading, loadedCount, total: filteredPapers.length });
            return;
        }

        isLoading = true;

        // 第一次加载50个，后续每次10个
        const batchSize = loadedCount === 0 ? initialBatchSize : subsequentBatchSize;
        console.log(`Loading papers ${loadedCount} to ${loadedCount + batchSize} (batch size: ${batchSize})`);

        const endIndex = Math.min(loadedCount + batchSize, filteredPapers.length);
        const fragment = document.createDocumentFragment();

        for (let i = loadedCount; i < endIndex; i++) {
            const paperHTML = createPaperHTML(filteredPapers[i]);
            const temp = document.createElement('div');
            temp.innerHTML = paperHTML;
            fragment.appendChild(temp.firstElementChild);
        }

        // 移除旧的加载指示器
        const oldIndicator = document.getElementById('loading-indicator');
        if (oldIndicator) {
            oldIndicator.remove();
        }

        papersContainer.appendChild(fragment);
        loadedCount = endIndex;
        isLoading = false;

        console.log(`Loaded ${endIndex} papers total`);

        // 如果还有更多，设置加载触发器
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

    // 月份筛选
    monthBtns.forEach(btn => {
        btn.addEventListener('click', async function() {
            console.log('Month button clicked:', this.dataset.month);
            monthBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentMonth = this.dataset.month;

            // 显示加载提示
            if (resultsCount) {
                resultsCount.textContent = '加载中...';
            }
            if (papersContainer) {
                papersContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;">加载中...</div>';
            }

            // 加载月份数据
            await loadMonthData(currentMonth);
        });
    });

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
    loadMonthsIndex();
});
