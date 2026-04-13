// auth.js - 认证相关逻辑

/**
 * 获取 API 基础 URL
 * 固定指向 FastAPI 后端运行端口 (8000)
 */
function getApiBaseUrl() {
    // 始终使用 FastAPI 后端所在的端口 8000
    const protocol = 'http:';
    const host = '127.0.0.1:8000';
    const apiUrl = `${protocol}//${host}`;
    console.log('API URL:', apiUrl);
    console.log('当前页面 URL:', window.location.href);
    console.log('注意: API 请求将发送到 FastAPI 后端 (端口 8000)');
    return apiUrl;
}

const API_BASE_URL = getApiBaseUrl();
const TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

// 当前登录方式：password 或 code
let currentLoginType = 'password';
let countdownTimer = null;
let countdownSeconds = 0;

/**
 * Toast 提示
 */
function showToast(message, type = 'info', duration = 3000) {
    removeToast();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span class="toast-icon">${getToastIcon(type)}</span> ${message}`;
    document.body.appendChild(toast);

    setTimeout(() => {
        if (toast.parentNode) {
            document.body.removeChild(toast);
        }
    }, duration);
}

function getToastIcon(type) {
    const icons = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    };
    return icons[type] || 'ℹ️';
}

function removeToast() {
    const toasts = document.querySelectorAll('.toast');
    toasts.forEach(toast => {
        if (toast.parentNode) {
            document.body.removeChild(toast);
        }
    });
}

/**
 * 获取请求头（带 token）
 */
function getAuthHeaders() {
    const token = localStorage.getItem(TOKEN_KEY);
    const headers = {
        'Content-Type': 'application/json',
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

/**
 * 获取请求头（用于 refresh token）
 */
function getAuthHeadersWithRefresh() {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    const headers = {
        'Content-Type': 'application/json',
    };
    if (refreshToken) {
        headers['Authorization'] = `Bearer ${refreshToken}`;
    }
    return headers;
}

/**
 * 保存 token
 */
function saveToken(accessToken, refreshToken = null) {
    localStorage.setItem(TOKEN_KEY, accessToken);
    if (refreshToken) {
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
    console.log('Token 已保存');
}

/**
 * 清除 token
 */
function clearTokens() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    console.log('Token 已清除');
}

/**
 * 检查是否已登录
 */
function isLoggedIn() {
    return !!localStorage.getItem(TOKEN_KEY);
}

/**
 * 页面初始化
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('Auth 页面加载');

    initTabSwitching();
    initLoginTypeSwitch();
    initLoginForms();
    initRegisterForm();
    checkLoginStatus();
});

/**
 * 检查登录状态
 */
function checkLoginStatus() {
    if (isLoggedIn()) {
        // 如果已登录，可以重定向到首页
        window.location.href = '/ui/index.html';
    }
}

/**
 * 标签页切换
 */
function initTabSwitching() {
    const loginBtn = document.querySelector('[data-tab="login"]');
    const registerBtn = document.querySelector('[data-tab="register"]');

    if (loginBtn && registerBtn) {
        loginBtn.addEventListener('click', () => {
            switchTab('login');
        });

        registerBtn.addEventListener('click', () => {
            switchTab('register');
        });
    }
}

function switchTab(tab) {
    const loginBtn = document.querySelector('[data-tab="login"]');
    const registerBtn = document.querySelector('[data-tab="register"]');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    loginBtn.classList.remove('active');
    registerBtn.classList.remove('active');

    if (tab === 'login') {
        loginBtn.classList.add('active');
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
    } else {
        registerBtn.classList.add('active');
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
    }
}

/**
 * 登录方式切换
 */
function initLoginTypeSwitch() {
    const passwordSwitchBtn = document.getElementById('switch-password');
    const codeSwitchBtn = document.getElementById('switch-code');
    const passwordForm = document.getElementById('password-login-form');
    const codeForm = document.getElementById('code-login-form');

    if (passwordSwitchBtn && codeSwitchBtn) {
        passwordSwitchBtn.addEventListener('click', () => {
            currentLoginType = 'password';
            passwordSwitchBtn.classList.add('active');
            codeSwitchBtn.classList.remove('active');
            passwordForm.style.display = 'block';
            codeForm.style.display = 'none';
        });

        codeSwitchBtn.addEventListener('click', () => {
            currentLoginType = 'code';
            codeSwitchBtn.classList.add('active');
            passwordSwitchBtn.classList.remove('active');
            passwordForm.style.display = 'none';
            codeForm.style.display = 'block';
        });
    }

    // 默认选中密码登录
    passwordSwitchBtn.click();
}

/**
 * 密码登录表单
 */
function initLoginForms() {
    const passwordForm = document.getElementById('password-login-form');
    const codeForm = document.getElementById('code-login-form');
    const sendCodeBtn = document.getElementById('send-code-btn');
    const errorEl = document.getElementById('error-message');

    // 密码登录
    if (passwordForm) {
        passwordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await handlePasswordLogin();
        });
    }

    // 验证码登录
    if (codeForm) {
        codeForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await handleCodeLogin();
        });
    }

    // 发送验证码
    if (sendCodeBtn) {
        sendCodeBtn.addEventListener('click', async () => {
            await handleSendCode();
        });
    }
}

/**
 * 密码登录处理
 */
async function handlePasswordLogin() {
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;

    if (!email || !password) {
        showErrorMessage('请填写完整的登录信息');
        return;
    }

    if (!isValidEmail(email)) {
        showErrorMessage('请输入有效的邮箱地址');
        return;
    }

    const submitBtn = document.getElementById('login-submit-btn');
    setLoading(submitBtn, true);

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ email, password }),
        });

        const result = await response.json();

        if (result.code === 200 && result.data) {
            // 登录成功
            saveToken(result.data.access_token, result.data.refresh_token);
            showToast('登录成功', 'success');

            // 跳转到首页
            setTimeout(() => {
                window.location.href = '/ui/index.html';
            }, 1000);
        } else {
            showErrorMessage(result.message || '登录失败');
        }
    } catch (error) {
        console.error('登录失败:', error);
        showErrorMessage('登录失败，请稍后重试');
    } finally {
        setLoading(submitBtn, false);
    }
}

/**
 * 验证码登录处理
 */
async function handleCodeLogin() {
    const email = document.getElementById('login-code-email').value.trim();
    const code = document.getElementById('verification-code-input').value.trim();

    if (!email || !code) {
        showErrorMessage('请填写完整的登录信息');
        return;
    }

    if (!isValidEmail(email)) {
        showErrorMessage('请输入有效的邮箱地址');
        return;
    }

    if (code.length !== 6) {
        showErrorMessage('请输入6位验证码');
        return;
    }

    const submitBtn = document.getElementById('code-login-submit-btn');
    setLoading(submitBtn, true);

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/login/code`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ email, code }),
        });

        const result = await response.json();

        if (result.code === 200 && result.data) {
            // 登录成功
            saveToken(result.data.access_token, result.data.refresh_token);
            showToast('登录成功', 'success');

            // 清除验证码倒计时
            stopCountdown();

            // 跳转到首页
            setTimeout(() => {
                window.location.href = '/ui/index.html';
            }, 1000);
        } else {
            showErrorMessage(result.message || '登录失败');
        }
    } catch (error) {
        console.error('验证码登录失败:', error);
        showErrorMessage('登录失败，请稍后重试');
    } finally {
        setLoading(submitBtn, false);
    }
}

/**
 * 发送验证码处理（测试模式，直接显示验证码）
 */
async function handleSendCode() {
    const email = document.getElementById('login-code-email').value.trim();

    if (!isValidEmail(email)) {
        showErrorMessage('请输入有效的邮箱地址');
        return;
    }

    const sendCodeBtn = document.getElementById('send-code-btn');
    setLoading(sendCodeBtn, true);

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/send-code`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ email }),
        });

        const result = await response.json();

        if (result.code === 200 && result.data && result.data.verification_code) {
            // 直接显示验证码弹窗
            const code = result.data.verification_code;
            showVerificationCodePopup(code);
            startCountdown(60); // 60秒倒计时
        } else {
            showErrorMessage(result.message || '生成验证码失败');
        }
    } catch (error) {
        console.error('生成验证码失败:', error);
        showErrorMessage('生成验证码失败，请稍后重试');
    } finally {
        setLoading(sendCodeBtn, false);
    }
}

/**
 * 显示验证码弹窗
 */
function showVerificationCodePopup(code) {
    // 移除现有弹窗
    const existingPopup = document.getElementById('verification-code-popup');
    if (existingPopup) {
        document.body.removeChild(existingPopup);
    }

    // 创建弹窗
    const popup = document.createElement('div');
    popup.id = 'verification-code-popup';
    popup.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
        background: white;
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        text-align: center;
        max-width: 400px;
        width: 90%;
    `;

    const title = document.createElement('h3');
    title.textContent = '验证码';
    title.style.cssText = `
        margin: 0 0 20px 0;
        color: #4a6cf7;
        font-size: 24px;
    `;

    const codeDisplay = document.createElement('div');
    codeDisplay.textContent = code;
    codeDisplay.style.cssText = `
        font-size: 48px;
        font-weight: bold;
        letter-spacing: 12px;
        color: #4a6cf7;
        background: #f0f4ff;
        padding: 20px 40px;
        border-radius: 8px;
        margin: 20px 0;
        user-select: all;
        cursor: pointer;
    `;

    // 点击复制验证码
    codeDisplay.onclick = () => {
        navigator.clipboard.writeText(code).then(() => {
            showToast('验证码已复制', 'success');
        }).catch(() => {
            // 复制失败时提示
            showToast('复制失败，请手动输入', 'info');
        });
    };

    const hint = document.createElement('p');
    hint.textContent = '验证码有效期为 5 分钟，60 秒后可重新发送';
    hint.style.cssText = `
        margin: 0 0 20px 0;
        color: #666;
        font-size: 14px;
    `;

    const copyHint = document.createElement('p');
    copyHint.textContent = '点击验证码可复制';
    copyHint.style.cssText = `
        margin: 0 0 20px 0;
        color: #999;
        font-size: 12px;
    `;

    const closeButton = document.createElement('button');
    closeButton.textContent = '关闭';
    closeButton.style.cssText = `
        background: #4a6cf7;
        color: white;
        border: none;
        padding: 12px 30px;
        font-size: 16px;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.3s;
    `;
    closeButton.onmouseover = () => {
        closeButton.style.background = '#3a5ce8';
    };
    closeButton.onmouseout = () => {
        closeButton.style.background = '#4a6cf7';
    };
    closeButton.onclick = () => {
        document.body.removeChild(popup);
    };

    content.appendChild(title);
    content.appendChild(codeDisplay);
    content.appendChild(hint);
    content.appendChild(copyHint);
    content.appendChild(closeButton);
    popup.appendChild(content);
    document.body.appendChild(popup);

    // 60秒后自动关闭
    setTimeout(() => {
        if (document.body.contains(popup)) {
            document.body.removeChild(popup);
        }
    }, 60000);
}

/**
 * 倒计时
 */
function startCountdown(seconds) {
    stopCountdown();
    countdownSeconds = seconds;

    const countdownEl = document.getElementById('countdown');
    updateCountdownDisplay();

    countdownTimer = setInterval(() => {
        countdownSeconds--;
        updateCountdownDisplay();

        if (countdownSeconds <= 0) {
            stopCountdown();
        }
    }, 1000);
}

function stopCountdown() {
    if (countdownTimer) {
        clearInterval(countdownTimer);
        countdownTimer = null;
        countdownSeconds = 0;
        const countdownEl = document.getElementById('countdown');
        if (countdownEl) {
            countdownEl.textContent = '';
        }
    }
}

function updateCountdownDisplay() {
    const countdownEl = document.getElementById('countdown');
    if (countdownEl && countdownSeconds > 0) {
        countdownEl.textContent = `${countdownSeconds}秒后可重新发送`;
    }
}

/**
 * 注册表单
 */
function initRegisterForm() {
    const registerForm = document.getElementById('register-form-element');
    const errorEl = document.getElementById('error-message');

    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await handleRegister();
        });
    }
}

/**
 * 注册处理
 */
async function handleRegister() {
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;
    const name = document.getElementById('register-name').value.trim();
    const department = document.getElementById('register-department').value.trim();
    const phone = document.getElementById('register-phone').value.trim();
    const employeeId = document.getElementById('register-employee-id').value.trim();

    // 验证必填字段
    if (!email || !password) {
        showErrorMessage('请填写邮箱和密码');
        return;
    }

    if (!isValidEmail(email)) {
        showErrorMessage('请输入有效的邮箱地址');
        return;
    }

    if (password !== confirmPassword) {
        showErrorMessage('两次输入的密码不一致');
        return;
    }

    if (password.length < 6) {
        showErrorMessage('密码长度不能少于6位');
        return;
    }

    const submitBtn = document.getElementById('register-submit-btn');
    setLoading(submitBtn, true);

    try {
        const requestBody = {
            email,
            password,
        };

        // 添加可选字段
        if (name) requestBody.name = name;
        if (department) requestBody.department = department;
        if (phone) requestBody.phone = phone;
        if (employeeId) requestBody.employee_id = employeeId;

        const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(requestBody),
        });

        const result = await response.json();

        if (result.code === 200) {
            showToast('注册成功，请登录', 'success');

            // 清空表单
            const registerForm = document.getElementById('register-form-element');
            if (registerForm) {
                registerForm.reset();
            }

            // 先恢复按钮状态，再切换标签页
            setLoading(submitBtn, false);

            // 切换到登录标签
            switchTab('login');
        } else {
            showErrorMessage(result.message || '注册失败');
            setLoading(submitBtn, false);
        }
    } catch (error) {
        console.error('注册失败:', error);
        showErrorMessage('注册失败，请稍后重试');
        setLoading(submitBtn, false);
    }
}

/**
 * 显示错误消息
 */
function showErrorMessage(message) {
    const errorEl = document.getElementById('error-message');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.add('show');

        // 3秒后自动消失
        setTimeout(() => {
            errorEl.classList.remove('show');
        }, 3000);
    }
}

/**
 * 邮箱格式验证
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * 设置按钮加载状态
 */
function setLoading(button, loading) {
    if (button) {
        button.disabled = loading;

        if (loading) {
            // 保存原始文本（如果还没有保存过）
            if (!button.dataset.originalText) {
                button.dataset.originalText = button.textContent;
            }
            button.textContent = '处理中...';
        } else {
            // 恢复原始文本
            button.textContent = button.dataset.originalText || '注册';
            button.disabled = false;
        }
    }
}

/**
 * 退出登录
 */
function logout() {
    clearTokens();
    showToast('已退出登录', 'info');
    window.location.href = '/ui/auth.html';
}

// 导出到全局，供其他模块使用
window.authUtils = {
    isLoggedIn,
    getAuthHeaders,
    saveToken,
    clearTokens,
    logout
};