// app.js - 主应用逻辑（重写版）

/**
 * 获取 API 基础 URL
 * 注意：API_BASE_URL 已在 auth.js 中声明，这里不再重复声明
 */

/**
 * 主应用类
 */
class App {
    constructor() {
        // DOM 元素引用
        this.queryInput = null;
        this.submitBtn = null;
        this.resultSection = null;
        this.resultContent = null;
        this.progressSection = null;
        this.progressContent = null;
        this.statusIndicator = null;
        this.connectionStatus = null;
        this.fileUploadArea = null;
        this.fileInput = null;
        this.selectedFiles = null;
        this.selectedFilesList = null;
        this.clearFilesBtn = null;


        // 状态
        this.threadId = null;
        this.wsManager = null;
        this.isLoading = false;
        this.currentQuery = '';
        this.selectedFileList = [];

        console.log('App 类初始化');
    }

    /**
     * 缓存 DOM 元素
     */
    cacheElements() {
        this.queryInput = document.getElementById('query-input');
        this.submitBtn = document.getElementById('submit-btn');
        this.resultSection = document.getElementById('result-section');
        this.resultContent = document.getElementById('result-content');
        this.progressSection = document.getElementById('progress-section');
        this.progressContent = document.getElementById('progress-content');
        this.statusIndicator = document.getElementById('status-indicator');
        this.connectionStatus = document.getElementById('connection-status');
        this.fileUploadArea = document.getElementById('file-upload-area');
        this.fileInput = document.getElementById('file-input');
        this.selectedFiles = document.getElementById('selected-files');
        this.selectedFilesList = document.getElementById('selected-files-list');
        this.clearFilesBtn = document.getElementById('clear-files-btn');
        console.log('DOM 元素缓存完成');
    }

    /**
     * 绑定 DOM 事件
     */
    bindEvents() {
        console.log('绑定 DOM 事件');

        // 提交按钮
        if (this.submitBtn) {
            this.submitBtn.addEventListener('click', () => this.handleSubmit());
        }

        // 输入框快捷键（Ctrl+Enter）
        if (this.queryInput) {
            this.queryInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                    e.preventDefault();
                    this.handleSubmit();
                }
            });
        }

        // 文件上传相关事件
        this.bindFileUploadEvents();

        console.log('DOM 事件绑定完成');
    }

    /**
     * 绑定文件上传事件
     */
    bindFileUploadEvents() {
        if (!this.fileInput) {
            console.error('fileInput 元素未找到，无法绑定文件上传事件');
            return;
        }

        console.log('开始绑定文件上传事件');

        // 文件选择事件
        this.fileInput.addEventListener('change', (e) => {
            console.log('========================================');
            console.log('文件选择事件触发');
            console.log('选择的文件数量:', e.target.files.length);
            console.log('文件详情:', Array.from(e.target.files).map(f => ({ name: f.name, size: f.size, type: f.type })));

            this.handleFileSelect(e.target.files);

            // 清空 input，允许重复选择同一文件
            e.target.value = '';
            console.log('已清空 file input');
            console.log('========================================');
        });

        // 拖拽事件
        if (this.fileUploadArea) {
            console.log('fileUploadArea 元素已找到，绑定拖拽事件');

            this.fileUploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.fileUploadArea.classList.add('dragover');
                console.log('dragover 事件触发');
            });

            this.fileUploadArea.addEventListener('dragleave', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.fileUploadArea.classList.remove('dragover');
                console.log('dragleave 事件触发');
            });

            this.fileUploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.fileUploadArea.classList.remove('dragover');

                console.log('========================================');
                console.log('drop 事件触发');
                console.log('拖拽的文件数量:', e.dataTransfer.files.length);
                console.log('文件详情:', Array.from(e.dataTransfer.files).map(f => ({ name: f.name, size: f.size, type: f.type })));

                this.handleFileSelect(e.dataTransfer.files);
                console.log('========================================');
            });

            // 点击上传区域触发文件选择
            this.fileUploadArea.addEventListener('click', (e) => {
                // 防止点击 input 元素或移除按钮时重复触发
                if (e.target === this.fileInput || e.target.closest('.file-item-remove')) {
                    return;
                }
                console.log('点击上传区域，触发文件选择对话框');
                this.fileInput.click();
            });
        } else {
            console.error('fileUploadArea 元素未找到');
        }

        // 清空文件按钮
        if (this.clearFilesBtn) {
            this.clearFilesBtn.addEventListener('click', () => {
                console.log('点击清空文件按钮');
                this.clearSelectedFiles();
            });
        } else {
            console.error('clearFilesBtn 元素未找到');
        }

        console.log('文件上传事件绑定完成');
    }

    /**
     * 处理文件选择
     * @param {FileList} files - 选择的文件列表
     */
    handleFileSelect(files) {
        if (!files || files.length === 0) {
            console.log('没有选择文件');
            return;
        }

        console.log('处理文件选择，文件数量:', files.length);

        const maxFileSize = 50 * 1024 * 1024; // 50MB

        Array.from(files).forEach(file => {
            console.log('处理文件:', file.name, '大小:', file.size);
            // 检查文件大小
            if (file.size > maxFileSize) {
                this.showToast(`文件 ${file.name} 超过50MB限制`, 'warning');
                return;
            }

            // 检查是否已存在
            const exists = this.selectedFileList.some(f => f.name === file.name && f.size === file.size);
            if (!exists) {
                console.log('添加新文件:', file.name);
                this.selectedFileList.push(file);
            } else {
                console.log('文件已存在，跳过:', file.name);
            }
        });

        console.log('当前已选文件总数:', this.selectedFileList.length);
        this.renderSelectedFiles();
    }

        /**
     * 渲染已选文件列表
     */
    renderSelectedFiles() {
        if (!this.selectedFiles || !this.selectedFilesList) {
            console.error('selectedFiles 或 selectedFilesList 元素未找到');
            return;
        }

        console.log('[渲染] 渲染已选文件列表，文件数量:', this.selectedFileList.length);

        if (this.selectedFileList.length === 0) {
            this.selectedFiles.style.display = 'none';
            this.selectedFilesList.innerHTML = '';
            console.log('[渲染] 隐藏已选文件列表');
            return;
        }

        this.selectedFiles.style.display = 'block';
        console.log('[渲染] 显示已选文件列表');

        // 保存 this 引用，避免在 map 中 this 指向错误
        const self = this;

        // 生成 HTML 字符串
        const filesHtml = this.selectedFileList.map((file, index) => {
            return `<div class="file-item">
                <div class="file-item-info">
                    <span class="file-item-icon">${self.getFileIcon(file.name)}</span>
                    <span class="file-item-name" title="${self.escapeHtml(file.name)}">${self.escapeHtml(file.name)}</span>
                    <span class="file-item-size">${self.formatFileSize(file.size)}</span>
                </div>
                <button class="file-item-remove" data-index="${index}" title="移除文件">×</button>
            </div>`;
        }).join('');

        console.log('[渲染] 生成的 HTML 长度:', filesHtml.length);

        // 设置 HTML 内容
        this.selectedFilesList.innerHTML = filesHtml;
        console.log('[渲染] HTML 内容已设置到 DOM');

        // 验证 DOM 是否已更新
        const fileItems = this.selectedFilesList.querySelectorAll('.file-item');
        console.log('[渲染] DOM 中实际的 .file-item 数量:', fileItems.length);

        if (fileItems.length === 0) {
            console.error('[渲染] 错误: DOM 中没有找到 .file-item 元素');
            return;
        }

        // 为每个移除按钮直接绑定点击事件（不使用事件委托）
        const removeButtons = this.selectedFilesList.querySelectorAll('.file-item-remove');
        console.log('[渲染] 找到', removeButtons.length, '个移除按钮');

        removeButtons.forEach((btn, idx) => {
            console.log('[渲染] 为按钮', idx, '绑定点击事件，data-index:', btn.dataset.index);

            // 移除之前的所有点击事件监听器
            btn.replaceWith(btn.cloneNode(true));
        });

        // 重新获取按钮并绑定事件
        const newButtons = this.selectedFilesList.querySelectorAll('.file-item-remove');
        newButtons.forEach((btn) => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();

                const index = parseInt(btn.dataset.index);
                console.log('[移除] 点击移除按钮，文件索引:', index);
                console.log('[移除] 移除前文件列表:', this.selectedFileList.map(f => f.name));

                if (!isNaN(index) && index >= 0 && index < this.selectedFileList.length) {
                    this.removeFile(index);
                } else {
                    console.error('[移除] 错误: 无效的索引', index);
                }
            });

            console.log('[渲染] 按钮事件绑定完成');
        });

        console.log('[渲染] 文件列表渲染完成 ✓');
    }

    /**
     * 移除文件
     * @param {number} index - 文件索引
     */
    removeFile(index) {
        console.log('[移除] removeFile 被调用，索引:', index);
        console.log('[移除] 移除前文件数量:', this.selectedFileList.length);

        if (index < 0 || index >= this.selectedFileList.length) {
            console.error('[移除] 错误: 索引越界', index);
            return;
        }

        const removedFile = this.selectedFileList[index];
        console.log('[移除] 正在移除文件:', removedFile.name);

        this.selectedFileList.splice(index, 1);
        console.log('[移除] 移除后文件数量:', this.selectedFileList.length);
        console.log('[移除] 剩余文件:', this.selectedFileList.map(f => f.name));

        this.renderSelectedFiles();
        console.log('[移除] 文件移除完成 ✓');
    }


    /**
     * 清空已选文件
     */
    clearSelectedFiles() {
        this.selectedFileList = [];
        this.renderSelectedFiles();
    }

    /**
     * 获取文件图标
     * @param {string} filename - 文件名
     * @returns {string} - 图标
     */
    getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const icons = {
            'pdf': '📄',
            'doc': '📝',
            'docx': '📝',
            'txt': '📃',
            'jpg': '🖼️',
            'jpeg': '🖼️',
            'png': '🖼️',
            'gif': '🖼️',
            'xls': '📊',
            'xlsx': '📊',
            'csv': '📊',
            'zip': '📦',
            'rar': '📦'
        };
        return icons[ext] || '📎';
    }

    /**
     * 格式化文件大小
     * @param {number} bytes - 字节数
     * @returns {string} - 格式化后的大小
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * 处理搜索提交
     */
    async handleSubmit() {
        const query = this.queryInput.value.trim();

        if (!query) {
            this.showToast('请输入搜索内容', 'warning');
            return;
        }

        if (this.isLoading) {
            console.log('正在加载中，忽略重复提交');
            return;
        }

        this.currentQuery = query;
        await this.executeSearch(query);
    }

    /**
     * 执行搜索
     * @param {string} query - 搜索查询
     */
    async executeSearch(query) {
        console.log('========================================');
        console.log('executeSearch 被调用');
        console.log('查询内容:', query);

        this.isLoading = true;
        this.setLoading(true);

        // 清空之前的结果
        this.clearResults();

        // 立即显示进度区域
        this.progressSection.style.display = 'block';

        // 添加初始进度项
        this.addProgressItem('start', '🚀', `开始搜索: ${query.substring(0, 50)}${query.length > 50 ? '...' : ''}`);

        // 如果有文件，先上传文件
        let threadId = null;
        if (this.selectedFileList.length > 0) {
            try {
                this.addProgressItem('info', '📤', `正在上传 ${this.selectedFileList.length} 个文件...`);
                this.showToast('正在上传文件...', 'info');

                threadId = await this.uploadFiles();

                if (threadId) {
                    this.addProgressItem('success', '✅', '文件上传成功');
                    this.showToast('文件上传成功', 'success');
                }
            } catch (error) {
                console.error('文件上传失败:', error);
                this.addProgressItem('error', '❌', `文件上传失败: ${error.message}`);
                this.showToast(`文件上传失败: ${error.message}`, 'error');
                this.isLoading = false;
                this.setLoading(false);
                return;
            }
        }

        const apiUrl = `${API_BASE_URL}/api/task`;
        console.log('完整 API URL:', apiUrl);

        try {
            console.log('准备发送 fetch 请求...');

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    query,
                    thread_id: threadId || this.threadId
                }),
                credentials: 'include',
            });

            console.log('fetch 响应状态:', response.status);

            if (!response.ok) {
                console.error('fetch 请求失败');
                const errorText = await response.text();
                console.error('错误响应内容:', errorText);
                throw new Error(`请求失败: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();
            console.log('API 响应:', result);

            if (result.thread_id) {
                this.threadId = result.thread_id;
                this.addProgressItem('session', '📁', '会话已创建');

                // 立即连接 WebSocket
                if (this.wsManager) {
                    console.log('准备连接 WebSocket, thread_id:', result.thread_id);
                    this.wsManager.connect(result.thread_id);
                } else {
                    console.error('WebSocket 管理器未初始化');
                }
            }

            // 保存历史
            this.saveHistory(query);

            // 清空已选文件
            this.clearSelectedFiles();

        } catch (error) {
            console.error('搜索失败, 异常详情:', error);
            console.error('错误堆栈:', error.stack);
            this.addProgressItem('error', '❌', `搜索失败: ${error.message}`);
            this.showToast(`搜索失败: ${error.message}`, 'error');
        } finally {
            this.isLoading = false;
            this.setLoading(false);
            console.log('========================================');
        }
    }

    /**
     * 上传文件
     * @returns {Promise<string>} - 返回 thread_id
     */
    async uploadFiles() {
        if (this.selectedFileList.length === 0) {
            throw new Error('没有选择文件');
        }

        // 生成或获取 thread_id
        const threadId = this.threadId || crypto.randomUUID();

        const formData = new FormData();
        this.selectedFileList.forEach(file => {
            formData.append('files', file);
        });
        formData.append('thread_id', threadId);

        const uploadUrl = `${API_BASE_URL}/api/upload`;
        console.log('上传文件到:', uploadUrl);

        const response = await fetch(uploadUrl, {
            method: 'POST',
            body: formData,
            credentials: 'include',
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`上传失败: ${response.status} ${errorText}`);
        }

        const result = await response.json();
        console.log('上传结果:', result);

        // 保存 thread_id
        this.threadId = threadId;

        return threadId;
    }


    /**
     * 初始化应用
     */
    init() {
        console.log('========================================');
        console.log('DeepSearchAgent 应用初始化');
        console.log('API_BASE_URL:', API_BASE_URL);
        console.log('当前页面 URL:', window.location.href);
        console.log('========================================');

        // 获取 DOM 元素
        this.cacheElements();

        // 如果元素不存在，说明 DOM 还没完全加载
        if (!this.queryInput) {
            console.error('DOM 元素未找到，等待 DOMContentLoaded');
            return;
        }

        // 等待 WebSocket 模块加载
        this.waitForWebSocketManager(() => {
            this.initWebSocketListeners();
            this.bindEvents();
            this.checkServerStatus();
        });
    }


    /**
     * 等待 WebSocket 管理器加载
     */
    waitForWebSocketManager(callback, maxAttempts = 50, interval = 100) {
        let attempts = 0;

        const checkManager = () => {
            attempts++;
            if (window.wsManager) {
                console.log('WebSocket 管理器已就绪');
                this.wsManager = window.wsManager;
                callback();
            } else if (attempts >= maxAttempts) {
                console.error('WebSocket 管理器加载超时');
                this.showToast('WebSocket 模块加载失败', 'error');
            } else {
                setTimeout(checkManager, interval);
            }
        };

        checkManager();
    }

    /**
     * 初始化 WebSocket 监听器
     */
    initWebSocketListeners() {
        console.log('初始化 WebSocket 监听器');

        if (!this.wsManager) {
            console.error('WebSocket 管理器未初始化');
            return;
        }

        // 连接事件
        this.wsManager.on('connected', () => {
            console.log('WebSocket 连接成功事件');
        });

        // 消息事件
        this.wsManager.on('message', (data) => {
            console.log('收到 WebSocket 消息:', data);
            this.handleWebSocketMessage(data);
        });

        // 错误事件
        this.wsManager.on('error', (error) => {
            console.error('WebSocket 错误事件:', error);
            this.showToast('连接错误，请检查后端服务', 'error');
        });

        // 断开事件
        this.wsManager.on('disconnected', (event) => {
            console.log('WebSocket 断开事件:', event);
        });
    }

    /**
     * 处理 WebSocket 消息
     * @param {Object} data - 消息数据
     */
    handleWebSocketMessage(data) {
        console.log('处理 WebSocket 消息:', data);

        // 处理 monitor_event 格式
        if (data.type === 'monitor_event') {
            const eventType = data.event;
            const message = data.message || '';
            const eventData = data.data || {};

            console.log(`Monitor 事件: ${eventType}`, eventData);

            switch (eventType) {
                case 'session_created':
                    this.threadId = eventData.thread_id || this.threadId;
                    this.addProgressItem('session', '📁', message || '会话已创建');
                    break;

                case 'assistant_call':
                    const assistantName = eventData.assistant_name || '未知助手';
                    this.addProgressItem('assistant', '🤖', `调用助手: ${assistantName}`);
                    this.showToast(`正在调用: ${assistantName}`, 'info');
                    break;

                case 'tool_start':
                    const toolName = eventData.tool_name || '未知工具';
                    this.addProgressItem('tool', '🔧', `执行工具: ${toolName}`);
                    this.showToast(`执行工具: ${toolName}`, 'info');
                    break;

                case 'task_result':
                    this.addProgressItem('result', '✅', message || '任务执行完成', true);
                    const result = eventData.result || data.result;
                    console.log('任务结果:', result);
                    this.showResult(result);
                    break;

                default:
                    console.log('未知事件类型:', eventType);
                    this.addProgressItem('info', 'ℹ️', message || eventType);
            }
            return;
        }

        // 处理其他消息类型（向后兼容）
        switch (data.type) {
            case 'session_created':
                this.threadId = data.thread_id;
                this.addProgressItem('session', '📁', '会话已创建');
                break;

            case 'assistant_call':
                this.addProgressItem('assistant', '🤖', `调用助手: ${data.assistant}`);
                this.showToast(`正在调用: ${data.assistant}`, 'info');
                break;

            case 'tool_start':
                this.addProgressItem('tool', '🔧', `执行工具: ${data.tool}`);
                this.showToast(`执行工具: ${data.tool}`, 'info');
                break;

            case 'task_result':
                this.addProgressItem('result', '✅', '任务执行完成', true);
                console.log('任务结果:', data.result);
                this.showResult(data.result || data);
                break;

            case 'error':
                this.addProgressItem('error', '❌', data.message || '发生错误');
                console.error('错误:', data.message);
                this.showToast(`错误: ${data.message}`, 'error');
                break;

            case 'pong':
                console.log('收到心跳');
                break;

            default:
                console.log('未知消息类型:', data.type);
                this.addProgressItem('unknown', '❓', JSON.stringify(data));
        }
    }

    /**
     * 添加进度项
     * @param {string} type - 类型
     * @param {string} icon - 图标
     * @param {string} message - 消息
     * @param {boolean} isLast - 是否是最后一项
     */
    addProgressItem(type, icon, message, isLast = false) {
        if (!this.progressContent) return;

        const item = document.createElement('div');
        item.className = `progress-item progress-item-${type} ${isLast ? 'progress-item-last' : ''}`;
        item.innerHTML = `
            <span class="progress-icon">${icon}</span>
            <span class="progress-message">${this.escapeHtml(message)}</span>
            <span class="progress-time">${new Date().toLocaleTimeString()}</span>
        `;
        this.progressContent.appendChild(item);

        console.log(`添加进度项 [${type}]:`, message);

        // 自动滚动到最新进度
        setTimeout(() => {
            item.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }, 100);
    }

    /**
     * 显示搜索结果
     * @param {string|object} result - 结果内容
     */
    showResult(result) {
        if (!this.resultSection || !this.resultContent) return;

        console.log('显示结果:', result);
        this.resultSection.style.display = 'block';

        // 格式化结果
        const formattedResult = this.formatResult(result);
        this.resultContent.innerHTML = formattedResult;

        // 滚动到结果区域
        setTimeout(() => {
            this.resultSection.scrollIntoView({ behavior: 'smooth' });
        }, 100);
    }

    /**
     * 格式化结果
     * @param {string|object} result - 原始结果
     * @returns {string} - 格式化后的结果
     */
    formatResult(result) {
        console.log('formatResult 输入:', result);

        if (typeof result === 'string') {
            // 纯文本结果
            return this.formatText(result);
        } else if (typeof result === 'object' && result !== null) {
            // 结构化结果
            return this.formatObject(result);
        }

        return `<p>${this.escapeHtml(String(result))}</p>`;
    }

    /**
     * 格式化文本
     * @param {string} text - 文本
     * @returns {string} - 格式化后的 HTML
     */
    formatText(text) {
        // 使用占位符策略：先用占位符替换文件路径，Markdown 处理完后再恢复
        // 这样可以防止 Markdown 正则（加粗/斜体/代码）破坏已生成的 <a> 标签
        const placeholders = [];
        let html = this.extractFilePaths(text, placeholders);

        // Markdown 基本格式转换
        // 加粗: **text**
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        // 代码: `text`
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // 处理换行
        html = html.split('\n').map(line => {
            line = line.trim();
            return line ? `<p>${line}</p>` : '';
        }).join('');

        // 恢复占位符为下载链接
        placeholders.forEach(({placeholder, link}) => {
            html = html.replace(placeholder, link);
        });

        return html;
    }

    /**
     * 提取文件路径并替换为占位符（防止 Markdown 正则污染链接）
     * @param {string} text - 包含文件路径的文本
     * @param {Array} placeholders - 占位符收集数组
     * @returns {string} - 替换后的文本（路径变为占位符）
     */
    extractFilePaths(text, placeholders) {
        const fileExts = 'pdf|md|doc|docx|txt|jpg|jpeg|png|gif|xls|xlsx|csv|zip|rar';

        // 1. 匹配 Windows 绝对路径 (如 D:\...\updated\session_xxx\output\file.pdf)
        const windowsPathRegex = new RegExp(
            `([A-Za-z]:\\\\(?:[^\\\\/:*?"<>|\\r\\n]+\\\\)*[^\\\\/:*?"<>|\\r\\n]+\\.(?:${fileExts}))`,
            'gi'
        );

        // 2. 匹配 updated/ 开头的相对路径 (如 updated/session_xxx/output/file.pdf)
        const updatedRelativeRegex = new RegExp(
            `(updated[\\\\/](?:session_[\\w-]+[\\\\/])?(?:[^\\s]+[\\\\/])*[^\\s]+\\.(?:${fileExts}))`,
            'gi'
        );

        // 3. 匹配 output/ 开头的相对路径 (如 output/file.pdf 或 output/report.md)
        const outputRelativeRegex = new RegExp(
            `(output[\\\\/](?:[^\\s]+[\\\\/])*[^\\s]+\\.(?:${fileExts}))`,
            'gi'
        );

        // 替换函数：生成占位符和下载链接
        const replaceWithPath = (match) => {
            const normalizedPath = match.replace(/\\/g, '/');
            const fileName = normalizedPath.split('/').pop();
            const downloadUrl = `${API_BASE_URL}/api/download?path=${encodeURIComponent(normalizedPath)}`;
            const link = `<a href="${downloadUrl}" target="_blank" class="file-download-link" title="点击下载文件：${fileName}">\u{1F4E5} ${fileName}</a>`;
            const placeholder = `__FILE_LINK_${placeholders.length}__`;
            console.log('[下载链接] 路径转换:', match, '->', normalizedPath);
            placeholders.push({ placeholder, link });
            return placeholder;
        };

        // 先替换 Windows 绝对路径（优先级最高，路径最长最确定）
        text = text.replace(windowsPathRegex, replaceWithPath);

        // 再替换 updated/ 开头的相对路径
        text = text.replace(updatedRelativeRegex, replaceWithPath);

        // 最后替换 output/ 开头的相对路径
        // 注意：output/ 路径需要转为 updated/ 前缀，因为后端 download 接口基于 updated 目录解析
        text = text.replace(outputRelativeRegex, (match) => {
            const normalizedPath = match.replace(/\\/g, '/');
            // output/xxx -> updated/xxx（后端 download 接口基于 updated 目录解析相对路径）
            const correctedPath = normalizedPath.replace(/^output\//, 'updated/');
            const fileName = correctedPath.split('/').pop();
            const downloadUrl = `${API_BASE_URL}/api/download?path=${encodeURIComponent(correctedPath)}`;
            const link = `<a href="${downloadUrl}" target="_blank" class="file-download-link" title="点击下载文件：${fileName}">\u{1F4E5} ${fileName}</a>`;
            const placeholder = `__FILE_LINK_${placeholders.length}__`;
            console.log('[下载链接] output相对路径转换:', match, '->', correctedPath);
            placeholders.push({ placeholder, link });
            return placeholder;
        });

        return text;
    }

    /**
     * 根据文件扩展名提供文件大小提示
     * @param {string} filename - 文件名
     * @returns {string} - 文件大小提示（可选）
     */
    getFileSizeInfo(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const sizeHints = {
            'pdf': 'PDF文档',
            'doc': 'Word文档',
            'docx': 'Word文档',
            'md': 'Markdown文档',
            'txt': '文本文件'
        };
        return sizeHints[ext] || '';
    }


    /**
     * 格式化对象
     * @param {object} obj - 对象
     * @returns {string} - 格式化后的 HTML
     */
    formatObject(obj) {
        let html = '';

        // 尝试多种可能的搜索结果位置
        const searchResults = obj.search_results || obj.result?.search_results || obj.items || obj.results;

        if (searchResults && Array.isArray(searchResults) && searchResults.length > 0) {
            html += '<div class="search-results"><h3>🔍 搜索结果</h3><ul>';
            searchResults.forEach((item, index) => {
                const title = item.title || item.name || `结果 ${index + 1}`;
                const content = item.content || item.snippet || item.description || item.body || '无内容';
                const url = item.url || item.link || item.href;
                html += `
                    <li class="result-item">
                        <h4>${this.escapeHtml(title)}</h4>
                        <p>${this.escapeHtml(content)}</p>
                        ${url ? `<a href="${url}" target="_blank" class="result-link">📎 查看详情</a>` : ''}
                    </li>
                `;
            });
            html += '</ul></div>';
        }

        // 尝试多种可能的答案位置
        const answer = obj.answer || obj.result?.answer || obj.content || obj.output || obj.message || obj.text;

        if (answer && typeof answer === 'string') {
            html += `<div class="ai-summary"><h3>🤖 AI 回答</h3>${this.formatText(answer)}</div>`;
        }

        // 如果没有内容，显示原始结果
        if (html === '' || obj.error) {
            html += '<div class="raw-result"><h3>📋 原始结果</h3><pre>' +
                this.escapeHtml(JSON.stringify(obj, null, 2)) + '</pre></div>';
        }

        return html;
    }

    /**
     * 转义 HTML
     * @param {string} text - 要转义的文本
     * @returns {string} - 转义后的文本
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 清空结果
     */
    clearResults() {
        if (this.progressContent) {
            this.progressContent.innerHTML = '';
        }
        if (this.resultContent) {
            this.resultContent.innerHTML = '';
        }
        if (this.progressSection) {
            this.progressSection.style.display = 'none';
        }
        if (this.resultSection) {
            this.resultSection.style.display = 'none';
        }
    }

    /**
     * 设置加载状态
     * @param {boolean} loading - 是否加载中
     */
    setLoading(loading) {
        if (this.submitBtn) {
            this.submitBtn.disabled = loading;
            this.submitBtn.textContent = loading ? '搜索中...' : '搜索';
        }
    }

    /**
     * 显示 Toast 提示
     * @param {string} message - 消息内容
     * @param {string} type - 类型
     * @param {number} duration - 持续时间（毫秒）
     */
    showToast(message, type = 'info', duration = 3000) {
        this.removeToast();

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `<span class="toast-icon">${this.getToastIcon(type)}</span> ${message}`;
        document.body.appendChild(toast);

        // 自动移除
        setTimeout(() => {
            if (toast.parentNode) {
                document.body.removeChild(toast);
            }
        }, duration);
    }

    /**
     * 获取 Toast 图标
     * @param {string} type - 类型
     * @returns {string} - 图标
     */
    getToastIcon(type) {
        const icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        };
        return icons[type] || 'ℹ️';
    }

    /**
     * 移除 Toast
     */
    removeToast() {
        const toasts = document.querySelectorAll('.toast');
        toasts.forEach(toast => {
            if (toast.parentNode) {
                document.body.removeChild(toast);
            }
        });
    }

    /**
     * 检查服务器状态
     */
    async checkServerStatus() {
        try {
            console.log('检查服务器状态...');
            const response = await fetch(`${API_BASE_URL}/api/task`, {
                method: 'OPTIONS',
            });

            if (response.ok) {
                console.log('服务器正常运行');
                // 如果 wsManager 存在，更新状态
                if (this.statusIndicator && this.connectionStatus) {
                    this.statusIndicator.classList.remove('status-disconnected');
                    this.statusIndicator.classList.add('status-connected');
                    this.connectionStatus.textContent = '服务器在线';
                }
            }
        } catch (error) {
            console.warn('服务器状态检查失败:', error);
        }
    }

    /**
     * 保存历史记录
     * @param {string} query - 搜索查询
     */
    saveHistory(query) {
        try {
            const historyKey = 'deepsearch_history';
            let history = localStorage.getItem(historyKey);
            const queries = history ? JSON.parse(history) : [];

            // 移除重复，保留最近 20 条
            const uniqueQueries = [...new Set([query, ...queries])].slice(0, 20);

            localStorage.setItem(historyKey, JSON.stringify(uniqueQueries));
            console.log('历史记录已保存，共', uniqueQueries.length, '条');
        } catch (e) {
            console.error('保存历史失败:', e);
        }
    }

    /**
     * 加载历史记录
     */
    loadHistory() {
        try {
            const historyKey = 'deepsearch_history';
            const history = localStorage.getItem(historyKey);
            if (history) {
                const queries = JSON.parse(history);
                console.log('历史记录:', queries);
                // 这里可以添加历史记录显示功能
            }
        } catch (e) {
            console.error('加载历史失败:', e);
        }
    }
}

/**
 * 检查登录状态
 */
function checkAuth() {
    const TOKEN_KEY = 'access_token';
    const token = localStorage.getItem(TOKEN_KEY);

    console.log('=== checkAuth 开始 ===');
    console.log('当前页面:', window.location.pathname);
    console.log('token 状态:', token ? '存在' : '不存在');

    if (!token) {
        console.log('未登录，重定向到 auth.html');
        window.location.href = 'auth.html';
        return false;
    }

    console.log('=== checkAuth 通过 ===');
    return true;
}

// 也监听 window.onload 确保所有资源加载完成
window.addEventListener('load', () => {
    console.log('所有资源已加载完成');
});

/**
 * 检查登录状态
 */
function checkLoginStatus() {
    if (!window.authUtils || !window.authUtils.isLoggedIn()) {
        window.location.href = '/ui/auth.html';
    } else {
        loadUserInfo();
    }
}

/**
 * 加载用户信息
 */
async function loadUserInfo() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
            method: 'GET',
            headers: getAuthHeaders(),
        });

        if (response.ok) {
            const userInfo = await response.json();
             updateUserInfo(userInfo);
        } else {
            console.error('获取用户信息失败');
            logout();
        }
    } catch (error) {
        console.error('加载用户信息失败:', error);
    }
}

/**
 * 更新用户信息显示
 */
function updateUserInfo(userInfo) {
    // 更新侧边栏用户信息
    const sidebarUserName = document.getElementById('sidebar-user-name');
    const sidebarUserEmail = document.getElementById('sidebar-user-email');
    const sidebarUserAvatar = document.getElementById('sidebar-user-avatar');

    if (sidebarUserName) {
        sidebarUserName.textContent = userInfo.name || '未设置姓名';
    }
    if (sidebarUserEmail) {
        sidebarUserEmail.textContent = userInfo.email || '';
    }
    if (sidebarUserAvatar && userInfo.avatar) {
        sidebarUserAvatar.src = userInfo.avatar;
    }

    // 更新个人资料页面信息
    const profileName = document.getElementById('profile-name');
    const profileEmail = document.getElementById('profile-email');
    const profileEmployeeId = document.getElementById('profile-employee-id');
    const profileDepartment = document.getElementById('profile-department');
    const profilePhone = document.getElementById('profile-phone');
    const profileStatus = document.getElementById('profile-status');
    const profileLastLogin = document.getElementById('profile-last-login');
    const profileRoleBadge = document.getElementById('profile-role-badge');
    const profileAvatar = document.getElementById('profile-avatar');

    if (profileName) {
        profileName.textContent = userInfo.name || '未设置姓名';
    }
    if (profileEmail) {
        profileEmail.textContent = userInfo.email || '-';
    }
    if (profileEmployeeId) {
        profileEmployeeId.textContent = userInfo.employee_id || '-';
    }
    if (profileDepartment) {
        profileDepartment.textContent = userInfo.department || '-';
    }
    if (profilePhone) {
        profilePhone.textContent = userInfo.phone || '-';
    }
    if (profileStatus) {
        profileStatus.textContent = getStatusText(userInfo.status);
        profileStatus.className = `status-badge ${userInfo.status}`;
    }
    if (profileLastLogin) {
        profileLastLogin.textContent = formatDateTime(userInfo.last_login_at);
    }
    if (profileRoleBadge) {
        profileRoleBadge.textContent = userInfo.is_admin ? '管理员' : '普通用户';
    }
    if (profileAvatar && userInfo.avatar) {
        profileAvatar.src = userInfo.avatar;
    }
}

/**
 * 获取状态文本
 */
function getStatusText(status) {
    const statusMap = {
        'active': '正常',
        'locked': '已锁定',
        'disabled': '已禁用',
        'deleted': '已删除'
    };
    return statusMap[status] || status;
}

/**
 * 格式化日期时间
 */
function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return '-';
    try {
        const date = new Date(dateTimeStr);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateTimeStr;
    }
}

/**
 * 初始化侧边栏
 */
function initSidebar() {
    console.log('========================================');
    console.log('初始化侧边栏...');
    console.log('========================================');

    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const userProfileTrigger = document.getElementById('user-profile-trigger');
    const navItems = document.querySelectorAll('.sidebar-nav-item');
    const backToHomeBtn = document.getElementById('back-to-home');
    const logoutBtn = document.getElementById('logout-btn');

    console.log('侧边栏元素:', sidebar);
    console.log('切换按钮:', sidebarToggle);
    console.log('导航项数量:', navItems.length);
    console.log('用户卡片触发器:', userProfileTrigger);
    console.log('返回主页按钮:', backToHomeBtn);
    console.log('退出登录按钮:', logoutBtn);

    // 侧边栏切换
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('点击侧边栏切换按钮');

            sidebar.classList.toggle('collapsed');
            const isCollapsed = sidebar.classList.contains('collapsed');
            sidebarToggle.textContent = isCollapsed ? '▶' : '◀';

            console.log('侧边栏状态:', isCollapsed ? '已收起' : '已展开');
        });

        console.log('侧边栏切换事件已绑定');
    } else {
        console.error('侧边栏或切换按钮未找到！');
    }

    // 导航项点击
    console.log('开始绑定导航项点击事件...');
    navItems.forEach((item, index) => {
        console.log(`绑定导航项 ${index}:`, item, 'data-page:', item.dataset.page);
        item.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const page = item.dataset.page;
            console.log(`导航项被点击，page=${page}`);
            console.log(`点击的元素:`, e.target);
            console.log(`当前元素:`, item);

            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            console.log('准备调用 switchPage...');
            try {
                switchPage(page);
                console.log('switchPage 调用成功');
            } catch (error) {
                console.error('switchPage 调用失败:', error);
            }
        });
        console.log(`导航项 ${index} 事件监听器已添加`);
    });
    console.log(`共绑定了 ${navItems.length} 个导航项`);
    console.log('导航项点击事件绑定完成');

    // 用户卡片点击
    if (userProfileTrigger) {
        userProfileTrigger.addEventListener('click', () => {
            console.log('用户卡片被点击');
            switchPage('profile');
            navItems.forEach(nav => {
                nav.classList.remove('active');
                if (nav.dataset.page === 'profile') {
                    nav.classList.add('active');
                }
            });
        });
        console.log('用户卡片点击事件已绑定');
    } else {
        console.error('用户卡片触发器未找到！');
    }

    // 返回主页
    if (backToHomeBtn) {
        backToHomeBtn.addEventListener('click', () => {
            console.log('返回主页按钮被点击');
            switchPage('home');
            navItems.forEach(nav => {
                nav.classList.remove('active');
                if (nav.dataset.page === 'home') {
                    nav.classList.add('active');
                }
            });
        });
        console.log('返回主页按钮事件已绑定');
    } else {
        console.error('返回主页按钮未找到！');
    }

    // 退出登录
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            if (confirm('确定要退出登录吗？')) {
                await handleLogout();
            }
        });
        console.log('退出登录按钮事件已绑定');
    } else {
        console.error('退出登录按钮未找到！');
    }

    console.log('========================================');
    console.log('侧边栏初始化完成');
    console.log('========================================');
}

/**
 * 切换页面
 */
function switchPage(page) {
    console.log('========================================');
    console.log('switchPage 被调用，page=', page);
    console.log('========================================');

    const homePage = document.getElementById('home-page');
    const profilePage = document.getElementById('profile-page');

    console.log('homePage:', homePage);
    console.log('profilePage:', profilePage);

    if (!homePage) {
        console.error('homePage 元素未找到！');
        return;
    }
    if (!profilePage) {
        console.error('profilePage 元素未找到！');
        return;
    }

    if (page === 'home') {
        console.log('切换到主页');
        homePage.style.display = 'block';
        profilePage.style.display = 'none';
    } else if (page === 'profile') {
        console.log('切换到个人信息页面');
        homePage.style.display = 'none';
        profilePage.style.display = 'block';
        // 重新加载用户信息
        console.log('开始加载用户信息...');
        loadUserInfo();
    } else {
        console.error('未知的页面:', page);
    }

    console.log('========================================');
    console.log('switchPage 完成');
    console.log('========================================');
}

/**
 * 处理退出登录
 */
async function handleLogout() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
            method: 'POST',
            headers: getAuthHeaders(),
        });

        if (response.ok) {
            // 使用 auth.js 的 showToast
            if (typeof showToast === 'function') {
                showToast('退出成功', 'success');
            }
            clearTokens();
            setTimeout(() => {
                window.location.href = '/ui/auth.html';
            }, 1000);
        } else {
            if (typeof showToast === 'function') {
                showToast('退出失败', 'error');
            }
        }
    } catch (error) {
        console.error('退出登录失败:', error);
        if (typeof showToast === 'function') {
            showToast('退出失败', 'error');
        }
    }
}

/**
 * 退出登录
 */
function logout() {
    clearTokens();
    window.location.href = '/ui/auth.html';
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    console.log('========================================');
    console.log('DeepSearchAgent 应用初始化');
    console.log('API_BASE_URL:', API_BASE_URL);
    console.log('当前页面 URL:', window.location.href);
    console.log('========================================');

    // 检查登录状态
    if (!window.authUtils || !window.authUtils.isLoggedIn()) {
        console.log('未登录，跳转到登录页面');
        window.location.href = '/ui/auth.html';
        return;
    }

    console.log('用户已登录，初始化应用...');

    // 初始化侧边栏
    initSidebar();

    // 加载用户信息
    loadUserInfo();

    // 初始化主应用
    const app = new App();
    app.init();
});

