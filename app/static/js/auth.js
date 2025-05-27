// 认证页面JavaScript - 支持AJAX登录/注册和弹窗通知

document.addEventListener('DOMContentLoaded', function() {
    // 登录表单处理
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // 注册表单处理
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
        
        // 密码强度检查
        const passwordInput = document.getElementById('password');
        if (passwordInput) {
            passwordInput.addEventListener('input', checkPasswordStrength);
        }
        
        // 确认密码检查
        const confirmPasswordInput = document.getElementById('confirmPassword');
        if (confirmPasswordInput) {
            confirmPasswordInput.addEventListener('input', checkPasswordMatch);
        }
    }
    
    // 添加输入框焦点效果
    addInputFocusEffects();
});

function setupRegisterValidation(form) {
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    const submitButton = form.querySelector('button[type="submit"]');
    
    function validatePasswords() {
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        
        // 清除之前的错误样式
        confirmPasswordInput.classList.remove('error');
        
        if (confirmPassword && password !== confirmPassword) {
            confirmPasswordInput.classList.add('error');
            showPasswordError('密码不匹配');
            return false;
        } else {
            hidePasswordError();
            return true;
        }
    }
    
    function validatePasswordStrength() {
        const password = passwordInput.value;
        
        if (password.length < 6) {
            showPasswordError('密码至少需要6个字符');
            return false;
        }
        
        hidePasswordError();
        return true;
    }
    
    function showPasswordError(message) {
        let errorDiv = document.querySelector('.password-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'password-error';
            errorDiv.style.cssText = `
                color: #dc3545;
                font-size: 0.875rem;
                margin-top: 0.25rem;
                display: flex;
                align-items: center;
                gap: 0.25rem;
            `;
            confirmPasswordInput.parentNode.appendChild(errorDiv);
        }
        errorDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
    }
    
    function hidePasswordError() {
        const errorDiv = document.querySelector('.password-error');
        if (errorDiv) {
            errorDiv.remove();
        }
    }
    
    // 实时验证
    passwordInput.addEventListener('input', validatePasswordStrength);
    confirmPasswordInput.addEventListener('input', validatePasswords);
    
    // 表单提交验证
    form.addEventListener('submit', function(e) {
        const isPasswordValid = validatePasswordStrength();
        const isConfirmValid = validatePasswords();
        
        if (!isPasswordValid || !isConfirmValid) {
            e.preventDefault();
            return false;
        }
    });
}

function setupLoginEnhancements(form) {
    const inputs = form.querySelectorAll('input');
    
    // 回车键快速提交
    inputs.forEach(input => {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                form.submit();
            }
        });
    });
    
    // 记住用户名功能
    const usernameInput = document.getElementById('username');
    if (usernameInput) {
        // 加载保存的用户名
        const savedUsername = localStorage.getItem('fl_username');
        if (savedUsername) {
            usernameInput.value = savedUsername;
        }
        
        // 保存用户名
        form.addEventListener('submit', function() {
            if (usernameInput.value.trim()) {
                localStorage.setItem('fl_username', usernameInput.value.trim());
            }
        });
    }
}

function setupFormEnhancements() {
    // 输入框聚焦效果
    const inputs = document.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentNode.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentNode.classList.remove('focused');
        });
    });
    
    // 表单提交加载状态
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                const originalText = submitButton.innerHTML;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...';
                submitButton.disabled = true;
                
                // 如果5秒内没有响应，恢复按钮状态
                setTimeout(() => {
                    submitButton.innerHTML = originalText;
                    submitButton.disabled = false;
                }, 5000);
            }
        });
    });
    
    // 账户类型选择增强
    const accountTypeSelect = document.getElementById('account_type');
    if (accountTypeSelect) {
        accountTypeSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const description = selectedOption.getAttribute('data-description');
            
            // 显示账户类型说明
            showAccountTypeDescription(selectedOption.text, description);
        });
    }
}

function showAccountTypeDescription(type, description) {
    let descDiv = document.querySelector('.account-type-description');
    
    if (!descDiv) {
        descDiv = document.createElement('div');
        descDiv.className = 'account-type-description';
        descDiv.style.cssText = `
            background: #e3f2fd;
            border: 1px solid #90caf9;
            border-radius: 6px;
            padding: 0.75rem;
            margin-top: 0.5rem;
            font-size: 0.875rem;
            color: #1565c0;
        `;
        document.getElementById('account_type').parentNode.appendChild(descDiv);
    }
    
    if (type && type !== '请选择账户类型') {
        descDiv.innerHTML = `
            <i class="fas fa-info-circle"></i>
            <strong>${type}:</strong> 
            ${getAccountTypeDescription(type)}
        `;
        descDiv.style.display = 'block';
    } else {
        descDiv.style.display = 'none';
    }
}

function getAccountTypeDescription(type) {
    const descriptions = {
        '服务器端 (管理和协调训练)': '作为联邦学习的协调者，管理训练过程，聚合模型参数，监控整个训练网络的状态。',
        '客户端 (参与训练和数据上传)': '参与联邦学习训练，上传本地数据进行模型训练，接收和更新全局模型参数。'
    };
    
    return descriptions[type] || '选择您的账户类型以查看详细说明。';
}

// 添加AJAX登录、注册处理函数和通知系统
function handleLogin(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    const username = formData.get('username');
    const password = formData.get('password');
    
    // 基本验证
    if (!username || !password) {
        showNotification('请填写用户名和密码', 'error');
        return;
    }
    
    // 显示加载状态
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 登录中...';
    submitBtn.disabled = true;
    
    // 发送AJAX请求
    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            password: password
        })
    })
    .then(response => {
        return response.json().then(data => {
            if (response.ok) {
                return data;
            } else {
                throw new Error(data.message || '登录失败');
            }
        });
    })
    .then(data => {
        if (data.success) {
            showNotification('登录成功！正在跳转...', 'success');
            setTimeout(() => {
                window.location.href = data.redirect;
            }, 1000);
        } else {
            showNotification(data.message || '登录失败', 'error');
        }
    })
    .catch(error => {
        console.error('Login error:', error);
        showNotification(error.message || '登录失败，请检查用户名和密码', 'error');
    })
    .finally(() => {
        // 恢复按钮状态
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

function handleRegister(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    const username = formData.get('username');
    const password = formData.get('password');
    const confirmPassword = formData.get('confirmPassword');
    const accountType = formData.get('account_type');
    
    // 验证
    if (!username || !password || !confirmPassword || !accountType) {
        showNotification('请填写所有必填字段', 'error');
        return;
    }
    
    if (password !== confirmPassword) {
        showNotification('两次输入的密码不一致', 'error');
        return;
    }
    
    if (password.length < 6) {
        showNotification('密码长度至少6位', 'error');
        return;
    }
    
    // 显示加载状态
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 注册中...';
    submitBtn.disabled = true;
    
    // 发送AJAX请求
    fetch('/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            password: password,
            account_type: accountType
        })
    })
    .then(response => {
        return response.json().then(data => {
            if (response.ok) {
                return data;
            } else {
                throw new Error(data.message || '注册失败');
            }
        });
    })
    .then(data => {
        if (data.success) {
            showNotification('注册成功！正在跳转到登录页面...', 'success');
            setTimeout(() => {
                window.location.href = data.redirect;
            }, 1500);
        } else {
            showNotification(data.message || '注册失败', 'error');
        }
    })
    .catch(error => {
        console.error('Register error:', error);
        showNotification(error.message || '注册失败，请稍后重试', 'error');
    })
    .finally(() => {
        // 恢复按钮状态
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

function showNotification(message, type = 'info') {
    // 移除现有的通知
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 创建新通知
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    // 添加样式
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1'};
        color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460'};
        border: 1px solid ${type === 'success' ? '#c3e6cb' : type === 'error' ? '#f5c6cb' : '#bee5eb'};
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideInRight 0.3s ease-out;
        min-width: 300px;
        max-width: 500px;
    `;
    
    document.body.appendChild(notification);
    
    // 自动移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, 5000);
}

function checkPasswordStrength(e) {
    const password = e.target.value;
    const strengthIndicator = document.getElementById('passwordStrength');
    
    if (!strengthIndicator) return;
    
    let strength = 0;
    let strengthText = '';
    let strengthClass = '';
    
    if (password.length >= 6) strength++;
    if (password.match(/[a-z]/)) strength++;
    if (password.match(/[A-Z]/)) strength++;
    if (password.match(/[0-9]/)) strength++;
    if (password.match(/[^a-zA-Z0-9]/)) strength++;
    
    switch (strength) {
        case 0:
        case 1:
            strengthText = '密码强度：弱';
            strengthClass = 'weak';
            break;
        case 2:
        case 3:
            strengthText = '密码强度：中';
            strengthClass = 'medium';
            break;
        case 4:
        case 5:
            strengthText = '密码强度：强';
            strengthClass = 'strong';
            break;
    }
    
    strengthIndicator.textContent = strengthText;
    strengthIndicator.className = `password-strength ${strengthClass}`;
}

function checkPasswordMatch(e) {
    const confirmPassword = e.target.value;
    const password = document.getElementById('password').value;
    const matchIndicator = document.getElementById('passwordMatch');
    
    if (!matchIndicator) return;
    
    if (confirmPassword === '') {
        matchIndicator.textContent = '';
        matchIndicator.className = 'password-match';
        return;
    }
    
    if (password === confirmPassword) {
        matchIndicator.textContent = '密码匹配';
        matchIndicator.className = 'password-match match';
    } else {
        matchIndicator.textContent = '密码不匹配';
        matchIndicator.className = 'password-match no-match';
    }
}

function addInputFocusEffects() {
    const inputs = document.querySelectorAll('input[type="text"], input[type="password"], input[type="email"], select');
    
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (this.value === '') {
                this.parentElement.classList.remove('focused');
            }
        });
        
        // 如果输入框已有值，添加focused类
        if (input.value !== '') {
            input.parentElement.classList.add('focused');
        }
    });
}

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .notification-content {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .notification-close {
        background: none;
        border: none;
        cursor: pointer;
        opacity: 0.7;
        margin-left: auto;
    }
    
    .notification-close:hover {
        opacity: 1;
    }
    
    .password-strength {
        font-size: 0.875rem;
        margin-top: 5px;
    }
    
    .password-strength.weak {
        color: #dc3545;
    }
    
    .password-strength.medium {
        color: #ffc107;
    }
    
    .password-strength.strong {
        color: #28a745;
    }
    
    .password-match {
        font-size: 0.875rem;
        margin-top: 5px;
    }
    
    .password-match.match {
        color: #28a745;
    }
    
    .password-match.no-match {
        color: #dc3545;
    }
    
    .form-group.focused label {
        color: #667eea;
        transform: translateY(-2px);
        transition: all 0.3s ease;
    }
`;
document.head.appendChild(style);