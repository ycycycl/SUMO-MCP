// 全局变量
let currentChatId = null;
let isProcessing = false;
let currentTodos = [];
let hiddenSections = new Set(); // 跟踪需要隐藏的section
let pendingSections = new Set(); // 跟踪待创建的section
let socket = null; // WebSocket连接

// DOM元素
const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 绑定事件
    sendBtn.addEventListener('click', handleSendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    
    // 自动调整输入框高度
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
    });
    
    // 配置marked
    if (typeof marked !== 'undefined') {
        marked.use({
            breaks: true,
            gfm: true
        });
    }
    
    showWelcomeMessage();
    
    // 初始化WebSocket连接
    initWebSocket();
});

// 显示欢迎消息
function showWelcomeMessage() {
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'welcome-message';
    welcomeDiv.innerHTML = `
        <div class="welcome-content">
            <h3><i class="bi bi-robot"></i> SUMO-MCP 交互助手</h3>
            <p>您好！我是SUMO-MCP助手，可以帮助您进行交通仿真相关的操作。</p>
            <div class="example-prompts">
                <div class="example-prompt" onclick="useExample(this)">
                    帮我下载山东省日照市的路网
                </div>
                <div class="example-prompt" onclick="useExample(this)">
                    生成一个简单的交通仿真场景
                </div>
                <div class="example-prompt" onclick="useExample(this)">
                    分析路网的交通流量数据
                </div>
            </div>
        </div>
    `;
    chatContainer.appendChild(welcomeDiv);
}

// 使用示例提示
function useExample(element) {
    userInput.value = element.textContent.trim();
    userInput.focus();
}

// 处理发送消息
async function handleSendMessage() {
    const message = userInput.value.trim();
    if (!message || isProcessing) return;
    
    // 如果是新对话，创建新的对话ID
    if (!currentChatId) {
        currentChatId = generateChatId();
    }
    
    // 清空相关集合，为新的对话做准备
    hiddenSections.clear();
    pendingSections.clear();
    
    // 显示用户消息
    appendUserMessage(message);
    
    // 清空输入框
    userInput.value = '';
    userInput.style.height = 'auto';
    
    isProcessing = true;
    
    try {
        await sendMessageStream(message);
    } catch (error) {
        console.error('流式API调用错误:', error);
        displayError(`连接错误: ${error.message}`);
    }
    
    isProcessing = false;
}

// 流式发送消息
async function sendMessageStream(message) {
    const url = 'http://localhost:5000/api/chat';
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            },
            body: JSON.stringify({ message: message })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // 创建助手消息容器
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message';
        chatContainer.appendChild(messageDiv);
        scrollToBottom();
        
        // 处理流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        handleStreamData(data, messageDiv);
                    } catch (e) {
                        console.error('解析流数据错误:', e);
                    }
                }
            }
        }
        
    } catch (error) {
        console.error('流式API调用错误:', error);
        displayError(`连接错误: ${error.message}`);
    }
}

// 动态创建section
function createSection(messageDiv, sectionType) {
    // 获取section配置
    const sectionConfig = getSectionConfig(sectionType);
    
    // 创建section HTML
    const sectionDiv = document.createElement('div');
    sectionDiv.className = `${sectionType}-section`;
    
    const isThinkSection = sectionType.startsWith('think');
    const defaultContentDisplay = isThinkSection ? 'none' : 'block';
    
    sectionDiv.innerHTML = `
        <div class="section-header" ${isThinkSection ? 'onclick="toggleSection(this)"' : ''}>
            <i class="bi bi-${sectionConfig.icon}"></i>
            <span>${sectionConfig.title}</span>
            ${isThinkSection ? '<i class="bi bi-chevron-down toggle-icon"></i>' : ''}
        </div>
        <div class="section-content" style="display: ${defaultContentDisplay};">
            <div class="loading">${sectionConfig.loadingText}</div>
        </div>
    `;
    
    messageDiv.appendChild(sectionDiv);
}

// 获取section配置
function getSectionConfig(sectionType) {
    if (sectionType.startsWith('think')) {
        return {
            icon: 'lightbulb',
            title: '思考过程',
            loadingText: '正在思考...'
        };
    } else if (sectionType.startsWith('tool-calls')) {
        return {
            icon: 'tools',
            title: '工具调用',
            loadingText: '正在调用工具...'
        };
    } else if (sectionType.startsWith('tool-responses')) {
        return {
            icon: 'gear',
            title: '工具响应',
            loadingText: '等待工具响应...'
        };
    } else if (sectionType.startsWith('answer')) {
        return {
            icon: 'chat-text',
            title: '回答',
            loadingText: '正在生成回答...'
        };
    } else {
        return {
            icon: 'question-circle',
            title: sectionType,
            loadingText: '处理中...'
        };
    }
}

// 处理流式数据
function handleStreamData(data, messageDiv) {
    const { type, section, content } = data;
    
    // 如果这个section已经被标记为隐藏，则忽略所有相关事件
    if (hiddenSections.has(section)) {
        return;
    }
    
    // 只对tool-calls和tool-responses section检查并隐藏TodoWrite相关内容
    if (content && content.includes('TodoWrite') && 
        (section.startsWith('tool-calls') || section.startsWith('tool-responses'))) {
        hiddenSections.add(section);
        // 如果section在待创建列表中，直接移除，避免创建DOM
        if (pendingSections.has(section)) {
            pendingSections.delete(section);
        }
        return; // 完全忽略TodoWrite相关的数据，不创建任何DOM
    }
    
    if (type === 'section_start') {
        // 先标记为待创建，等收到content时再决定是否真正创建
        pendingSections.add(section);
    } else if (type === 'content') {
        // 如果section在待创建列表中，现在创建它
        if (pendingSections.has(section)) {
            createSection(messageDiv, section);
            pendingSections.delete(section);
            scrollToBottom();
        }
        
        // 更新section内容
        updateSectionContent(messageDiv, section, content);
        
        // 如果是思考过程且有内容，自动展开显示
        if (section.startsWith('think') && content && content.trim()) {
            const sectionDiv = messageDiv.querySelector(`.${section}-section`);
            if (sectionDiv) {
                const contentDiv = sectionDiv.querySelector('.section-content');
                if (contentDiv && contentDiv.style.display === 'none') {
                    contentDiv.style.display = 'block';
                    // 同时更新箭头方向
                    const icon = sectionDiv.querySelector('.toggle-icon');
                    if (icon) {
                        icon.className = 'bi bi-chevron-up toggle-icon';
                    }
                }
            }
        }
    } else if (type === 'section_complete') {
        // section完成，如果是隐藏的section，从集合中移除
        if (hiddenSections.has(section)) {
            hiddenSections.delete(section);
            return;
        }
        
        // 如果section还在待创建列表中（比如没有收到content就结束了），创建它
        if (pendingSections.has(section)) {
            createSection(messageDiv, section);
            pendingSections.delete(section);
            scrollToBottom();
        }
        
        const sectionDiv = messageDiv.querySelector(`.${section}-section`);
        if (sectionDiv) {
            const loadingDiv = sectionDiv.querySelector('.loading');
            if (loadingDiv) {
                loadingDiv.remove();
            }
        }
    } else if (type === 'error') {
        displayError(data.message);
    }
}

// 更新section内容
function updateSectionContent(messageDiv, section, content) {
    const sectionDiv = messageDiv.querySelector(`.${section}-section`);
    if (!sectionDiv) return;
    
    const contentDiv = sectionDiv.querySelector('.section-content');
    if (!contentDiv) return;
    
    // 移除loading
    const loadingDiv = contentDiv.querySelector('.loading');
    if (loadingDiv) {
        loadingDiv.remove();
    }
    
    // 根据section类型处理内容
    let html = '';
    if (section.startsWith('think')) {
        html = `<div class="think-content">${escapeHtml(content)}</div>`;
    } else if (section.startsWith('tool-calls') || section.startsWith('tool-responses')) {
        // 尝试解析为JSON并高亮（TodoWrite相关的内容已在handleStreamData中过滤）
        try {
            const parsed = JSON.parse(content);
            html = `<pre><code class="language-json">${escapeHtml(JSON.stringify(parsed, null, 2))}</code></pre>`;
        } catch {
            html = `<pre><code>${escapeHtml(content)}</code></pre>`;
        }
    } else if (section === 'answer') {
        // 使用marked解析Markdown
        if (typeof marked !== 'undefined') {
            html = marked.parse(content);
        } else {
            html = `<div>${escapeHtml(content).replace(/\n/g, '<br>')}</div>`;
        }
    }
    
    contentDiv.innerHTML = html;
    
    // 应用代码高亮
    if (window.hljs) {
        try {
            contentDiv.querySelectorAll('pre code').forEach((block) => {
                window.hljs.highlightElement(block);
            });
        } catch (e) {
            console.warn('代码高亮失败:', e);
        }
    }
    
    scrollToBottom();
}

// 显示用户消息
function appendUserMessage(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-text">${escapeHtml(message)}</div>
        </div>
    `;
    chatContainer.appendChild(messageDiv);
    scrollToBottom();
}

// 显示错误消息
function displayError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `
        <i class="bi bi-exclamation-triangle"></i>
        <span>${escapeHtml(message)}</span>
    `;
    chatContainer.appendChild(errorDiv);
    scrollToBottom();
}

// 滚动到底部
function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 生成对话ID
function generateChatId() {
    return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// 切换section显示/隐藏
function toggleSection(header) {
    const section = header.parentElement;
    const content = section.querySelector('.section-content');
    const icon = header.querySelector('.toggle-icon');
    
    if (content.style.display === 'none' || content.style.display === '') {
        content.style.display = 'block';
        icon.className = 'bi bi-chevron-up toggle-icon';
    } else {
        content.style.display = 'none';
        icon.className = 'bi bi-chevron-down toggle-icon';
    }
}

// 全局函数
window.toggleSection = toggleSection;
window.useExample = useExample; 

// 显示图片
function displayImage(imageInfo) {
    const chatContainer = document.getElementById('chat-container');
    
    // 创建图片消息容器
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message';
    
    // 创建图片section
    const imageSection = document.createElement('div');
    imageSection.className = 'image-section';
    
    // 创建图片标题
    const titleDiv = document.createElement('div');
    titleDiv.className = 'image-title';
    titleDiv.innerHTML = `<i class="fas fa-image"></i> ${imageInfo.title}`;
    
    // 创建图片内容容器
    const contentDiv = document.createElement('div');
    contentDiv.className = 'image-content';
    
    // 创建图片元素
    const img = document.createElement('img');
    
    // 处理图片路径，转换为可访问的URL
    let imageUrl;
    if (imageInfo.image_path.startsWith('http')) {
        // 如果是完整URL，直接使用
        imageUrl = imageInfo.image_path;
    } else {
        // 如果是本地路径，通过后端API访问
        // 将Windows路径转换为URL路径
        const urlPath = encodeURIComponent(imageInfo.image_path);
        imageUrl = `http://localhost:5000/api/image/${urlPath}`;
    }
    
    img.src = imageUrl;
    img.alt = imageInfo.title;
    img.className = 'display-image';
    
    // 图片加载错误处理
    img.onerror = function() {
        this.style.display = 'none';
        const errorDiv = document.createElement('div');
        errorDiv.className = 'image-error';
        errorDiv.textContent = '图片加载失败';
        contentDiv.appendChild(errorDiv);
    };
    
    // 添加图片描述（如果有）
    if (imageInfo.description) {
        const descDiv = document.createElement('div');
        descDiv.className = 'image-description';
        descDiv.textContent = imageInfo.description;
        contentDiv.appendChild(descDiv);
    }
    
    contentDiv.appendChild(img);
    
    imageSection.appendChild(titleDiv);
    imageSection.appendChild(contentDiv);
    messageDiv.appendChild(imageSection);
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// 初始化WebSocket连接
function initWebSocket() {
    try {
        socket = io('http://localhost:5000');
        
        socket.on('connect', function() {
            console.log('WebSocket连接成功');
        });
        
        socket.on('disconnect', function() {
            console.log('WebSocket连接断开');
        });
        
        socket.on('new_image', function(imageInfo) {
            console.log('收到新图片推送:', imageInfo);
            displayImage(imageInfo);
        });
        
        socket.on('todos_updated', function(data) {
            console.log('收到todolist更新推送:', data);
            updateTodoList(data.todos);
        });
        
        socket.on('connect_error', function(error) {
            console.error('WebSocket连接错误:', error);
            console.log('WebSocket连接失败，实时推送功能可能不可用');
        });
        
    } catch (error) {
        console.error('初始化WebSocket失败:', error);
        console.log('WebSocket初始化失败，实时推送功能可能不可用');
    }
}

// TodoList相关功能
function toggleTodoList() {
    const todoContainer = document.getElementById('todolist-container');
    const mainContent = document.querySelector('.main-content');
    
    if (todoContainer.style.display === 'none' || !todoContainer.style.display) {
        todoContainer.style.display = 'block';
        mainContent.classList.add('with-todolist');
    } else {
        todoContainer.style.display = 'none';
        mainContent.classList.remove('with-todolist');
    }
}

function updateTodoList(todos) {
    // 检查是否有变化
    if (JSON.stringify(todos) === JSON.stringify(currentTodos)) {
        return;
    }
    
    currentTodos = todos;
    renderTodoList(todos);
    
    // 如果有todolist且容器是隐藏的，自动显示
    if (todos.length > 0) {
        const todoContainer = document.getElementById('todolist-container');
        if (todoContainer.style.display === 'none' || !todoContainer.style.display) {
            toggleTodoList();
        }
    }
}

function renderTodoList(todos) {
    const todoContent = document.getElementById('todolist-content');
    
    if (!todoContent) {
        console.error('❌ 找不到todolist-content元素');
        return;
    }
    
    if (!todos || todos.length === 0) {
        todoContent.innerHTML = '<div class="empty-todos">暂无任务</div>';
        return;
    }
    
    const todosHtml = todos.map(todo => {
        const statusIcon = getStatusIcon(todo.status);
        const statusText = getStatusText(todo.status);
        
        return `
            <div class="todo-item ${todo.status}" data-todo-id="${todo.id}">
                <div class="todo-status">
                    <div class="status-icon">${statusIcon}</div>
                    <span class="status-text">${statusText}</span>
                </div>
                <div class="todo-content">${escapeHtml(todo.content)}</div>
            </div>
        `;
    }).join('');
    
    todoContent.innerHTML = todosHtml;
}

function getStatusIcon(status) {
    switch (status) {
        case 'pending':
            return '○';
        case 'in_progress':
            return '◐';
        case 'completed':
            return '✓';
        default:
            return '○';
    }
}

function getStatusText(status) {
    switch (status) {
        case 'pending':
            return '待处理';
        case 'in_progress':
            return '进行中';
        case 'completed':
            return '已完成';
        default:
            return '未知';
    }
}

// 清理WebSocket连接
function cleanupWebSocket() {
    if (socket) {
        socket.disconnect();
        socket = null;
    }
}

// 页面卸载时清理连接
window.addEventListener('beforeunload', function() {
    cleanupWebSocket();
});

// 全局函数
window.toggleTodoList = toggleTodoList;
window.initWebSocket = initWebSocket;
window.cleanupWebSocket = cleanupWebSocket; 