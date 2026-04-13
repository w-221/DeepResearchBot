// websocket.js - WebSocket 连接管理（重写版）

/**
 * 获取 WebSocket 基础 URL
 * 固定指向 FastAPI 后端运行端口 (8000)
 */
function getWebSocketBaseUrl() {
    // 始终使用 FastAPI 后端所在的端口 8000
    const protocol = 'ws:';
    const host = '127.0.0.1:8000';
    const wsUrl = `${protocol}//${host}/ws`;
    console.log('WebSocket URL:', wsUrl);
    console.log('注意: WebSocket 连接将发送到 FastAPI 后端 (端口 8000)');
    return wsUrl;
}

const WS_BASE_URL = getWebSocketBaseUrl();

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.threadId = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        this.reconnectTimer = null;
        this.messageQueue = [];
        this.isConnected = false;

        // 事件监听器
        this.listeners = {
            connected: [],
            message: [],
            error: [],
            disconnected: []
        };

        console.log('WebSocketManager 初始化');
    }

    /**
     * 连接到 WebSocket
     * @param {string} threadId - 会话ID
     */
    connect(threadId) {
        console.log('开始连接 WebSocket, thread_id:', threadId);

        // 如果已有连接，先关闭
        if (this.ws) {
            console.log('关闭现有连接');
            this.ws.close();
        }

        this.threadId = threadId;
        const url = `${WS_BASE_URL}/${threadId}`;
        console.log('连接到:', url);

        try {
            this.ws = new WebSocket(url);

            this.ws.onopen = (event) => {
                console.log('WebSocket 已连接:', event);
                this.reconnectAttempts = 0;
                this.isConnected = true;
                this.updateConnectionStatus('connected');
                this.emit('connected');

                // 发送队列中的消息
                this.flushMessageQueue();
            };

            this.ws.onmessage = (event) => {
                console.log('收到 WebSocket 消息:', event.data);
                try {
                    const data = JSON.parse(event.data);
                    this.emit('message', data);
                } catch (error) {
                    console.error('解析 WebSocket 消息失败:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket 错误:', error);
                this.isConnected = false;
                this.updateConnectionStatus('error');
                this.emit('error', error);
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket 已关闭:', event.code, event.reason);
                this.isConnected = false;
                this.updateConnectionStatus('disconnected');
                this.emit('disconnected', event);

                // 尝试重新连接
                this.tryReconnect();
            };

        } catch (error) {
            console.error('WebSocket 连接异常:', error);
            this.updateConnectionStatus('error');
            this.emit('error', error);
        }
    }

    /**
     * 更新连接状态显示
     */
    updateConnectionStatus(status) {
        const indicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('connection-status');

        if (!indicator || !statusText) return;

        // 移除所有状态类
        indicator.classList.remove('status-connected', 'status-disconnected', 'status-connecting');

        switch (status) {
            case 'connected':
                indicator.classList.add('status-connected');
                statusText.textContent = '已连接';
                break;
            case 'disconnected':
                indicator.classList.add('status-disconnected');
                statusText.textContent = '未连接';
                break;
            case 'connecting':
                indicator.classList.add('status-connecting');
                statusText.textContent = '连接中...';
                break;
            case 'error':
                indicator.classList.add('status-disconnected');
                statusText.textContent = '连接错误';
                break;
        }
    }

    /**
     * 尝试重新连接
     */
    tryReconnect() {
        // 如果正在尝试重连，取消之前的定时器
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }

        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 10000); // 指数退避，最多10秒
            console.log(`尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})，${this.reconnectDelay}ms 后`);

            this.updateConnectionStatus('connecting');

            this.reconnectTimer = setTimeout(() => {
                this.connect(this.threadId);
            }, this.reconnectDelay);
        } else {
            console.error('达到最大重连次数');
            this.updateConnectionStatus('error');
            this.emit('maxReconnectAttempts');
        }
    }

    /**
     * 发送消息
     * @param {object} message - 要发送的消息对象
     */
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify(message));
                console.log('发送 WebSocket 消息:', message);
            } catch (error) {
                console.error('发送 WebSocket 消息失败:', error);
            }
        } else {
            console.warn('WebSocket 未连接，消息加入队列');
            this.messageQueue.push(message);
        }
    }

    /**
     * 发送队列中的消息
     */
    flushMessageQueue() {
        while (this.messageQueue.length > 0 && this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = this.messageQueue.shift();
            this.send(message);
        }
    }

    /**
     * 断开连接
     */
    disconnect() {
        console.log('断开 WebSocket 连接');
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }

        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        this.isConnected = false;
        this.updateConnectionStatus('disconnected');
    }

    /**
     * 获取连接状态
     */
    getConnectionState() {
        if (!this.ws) return 'none';
        switch (this.ws.readyState) {
            case WebSocket.CONNECTING:
                return 'connecting';
            case WebSocket.OPEN:
                return 'connected';
            case WebSocket.CLOSING:
                return 'closing';
            case WebSocket.CLOSED:
                return 'closed';
            default:
                return 'unknown';
        }
    }

    /**
     * 注册事件监听器
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     */
    on(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event].push(callback);
            console.log(`注册事件监听器: ${event}`);
        } else {
            console.warn(`未知事件类型: ${event}`);
        }
    }

    /**
     * 移除事件监听器
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     */
    off(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
        }
    }

    /**
     * 触发事件
     * @param {string} event - 事件名称
     * @param {*} data - 事件数据
     */
    emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`事件回调错误 (${event}):`, error);
                }
            });
        }
    }

    /**
     * 清除所有监听器
     */
    removeAllListeners() {
        Object.keys(this.listeners).forEach(event => {
            this.listeners[event] = [];
        });
        console.log('清除所有事件监听器');
    }
}

// 导出单例
const wsManager = new WebSocketManager();

// 导出供其他模块使用
if (typeof window !== 'undefined') {
    window.WSManager = WebSocketManager;
    window.wsManager = wsManager;
    console.log('WebSocket 模块已加载');
}