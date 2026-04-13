// API.js - API 请求封装

const API_BASE_URL = 'http://127.0.0.1:8000';

/**
 * 发起搜索任务
 * @param {string} query - 搜索查询
 * @returns {Promise}
 */
export async function searchTask(query) {
    try {
        const token = localStorage.getItem('access_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const response = await fetch(`${API_BASE_URL}/api/task`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ query }),
        });

        if (!response.ok) {
            throw new Error(`请求失败: ${response.status}`);
        }

        const result = await response.json();
        return result;
    } catch (error) {
        console.error('搜索任务失败:', error);
        throw error;
    }
}

/**
 * 上传文件
 * @param {FileList} files - 文件列表
 * @param {string} threadId - 会话ID
 * @returns {Promise}
 */
export async function uploadFiles(files, threadId) {
    const formData = new FormData();
    files.forEach(file => {
        formData.append('files', file);
    });
    formData.append('thread_id', threadId);

    try {
        const response = await fetch(`${API_BASE_URL}/api/upload`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`上传失败: ${response.status}`);
        }

        const result = await response.json();
        return result;
    } catch (error) {
        console.error('文件上传失败:', error);
        throw error;
    }
}

/**
 * 下载文件
 * @param {string} path - 文件路径
 * @returns {Promise}
 */
export async function downloadFile(path) {
    const encodedPath = encodeURIComponent(path);
    const url = `${API_BASE_URL}/api/download?path=${encodedPath}`;

    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`下载失败: ${response.status}`);
        }

        // 创建下载链接
        const blob = await response.blob();
        const downloadUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = path.split('/').pop();
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(downloadUrl);
    } catch (error) {
        console.error('文件下载失败:', error);
        throw error;
    }
}

/**
 * 获取文件列表
 * @param {string} path - 目录路径
 * @returns {Promise}
 */
export async function listFiles(path) {
    const encodedPath = encodeURIComponent(path);
    const url = `${API_BASE_URL}/api/files?path=${encodedPath}`;

    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`获取文件列表失败: ${response.status}`);
        }

        const result = await response.json();
        return result;
    } catch (error) {
        console.error('获取文件列表失败:', error);
        throw error;
    }
}