document.addEventListener('DOMContentLoaded', () => {    // DOM元素引用
    const addNodeBtn = document.getElementById('add-node-btn');
    const startTrainingBtn = document.getElementById('start-training-btn');
    const stopTrainingBtn = document.getElementById('stop-training-btn');
    const resetBtn = document.getElementById('reset-btn');
    const clearLogBtn = document.getElementById('clear-log-btn');
    const nodesContainer = document.getElementById('nodes-container');
    const centralNode = document.getElementById('central-node');
    const statusDisplay = document.getElementById('status-display');
    const logContent = document.getElementById('log-content');
    const nodeTemplate = document.getElementById('node-template');
    const networkContainer = document.getElementById('network-container');
      // 弹窗相关元素
    const helpBtn = document.getElementById('help-btn');
    const helpModal = document.getElementById('help-modal');
    const helpCloseBtn = document.getElementById('help-close-btn');
    const errorModal = document.getElementById('error-modal');
    const errorCloseBtn = document.getElementById('error-close-btn');
    const errorMessage = document.getElementById('error-message');
    
    // 新增的弹窗元素
    const introBtn = document.getElementById('intro-btn');
    const introModal = document.getElementById('intro-modal');
    const introCloseBtn = document.getElementById('intro-close-btn');
    const magnifyLogBtn = document.getElementById('magnify-log-btn');
    const logModal = document.getElementById('log-modal');
    const logCloseBtn = document.getElementById('log-close-btn');
    const logModalContent = document.getElementById('log-modal-content');
    
    // 训练参数控制
    const roundNumber = document.getElementById('round-number');
    const clientNumber = document.getElementById('client-number');
    const roundPlus = document.getElementById('round-plus');
    const roundMinus = document.getElementById('round-minus');
    const clientPlus = document.getElementById('client-plus');
    const clientMinus = document.getElementById('client-minus');

    // 存储节点数据
    let nodes = [];
    let nodeIdCounter = 1;
    let isTraining = false;
    
    // 拖拽相关变量
    let isDragging = false;
    let currentDragNode = null;
    let startX = 0;
    let startY = 0;
    let nodeStartX = 0;
    let nodeStartY = 0;
    let containerRect = null;
    let nodeRect = null;
    let rafId = null;    // 添加节点 - 通过客户端ID
    addNodeBtn.addEventListener('click', () => {
        const clientIdInput = document.getElementById('client-id-input');
        const clientId = clientIdInput.value.trim();
        
        if (!clientId) {
            addLogMessage('请输入客户端ID', 'warning');
            return;
        }
        
        if (nodes.length >= 8) {
            addLogMessage('已达到最大节点数量限制 (8)', 'warning');
            return;
        }
        
        // 验证客户端ID格式
        if (!clientId.match(/^CLIENT_[A-Z0-9]{8}$/)) {
            addLogMessage('客户端ID格式无效，应为: CLIENT_XXXXXXXX', 'error');
            return;
        }
        
        // 检查是否已存在
        const existingNode = nodes.find(node => node.clientId === clientId);
        if (existingNode) {
            addLogMessage(`客户端 ${clientId} 已存在`, 'warning');
            return;
        }
        
        createNodeWithClientId(clientId);
        clientIdInput.value = ''; // 清空输入框
    });    // 创建带有客户端ID的新节点
    function createNodeWithClientId(clientId) {
        const nodeId = nodeIdCounter++;
        
        // 从模板克隆节点
        const nodeFragment = document.importNode(nodeTemplate.content, true);
        const nodeElement = nodeFragment.querySelector('.node');
        
        // 设置节点ID和标题
        nodeElement.id = `node-${nodeId}`;
        nodeElement.querySelector('.node-title').textContent = clientId;
        
        // 设置上传输入框ID
        const imageInput = nodeElement.querySelector('.image-input');
        imageInput.id = `image-input-${nodeId}`;
        nodeElement.querySelector('label').setAttribute('for', `image-input-${nodeId}`);
        
        // 定位节点 - 在圆周上均匀分布
        positionNode(nodeElement, nodeId);
        
        // 添加到DOM
        nodesContainer.appendChild(nodeElement);
        
        // 存储节点数据
        const nodeData = {
            id: nodeId,
            clientId: clientId,
            element: nodeElement,
            images: [],
            status: 'idle',  // idle, training, uploading, complete
        };
        nodes.push(nodeData);
        
        // 绑定事件
        setupNodeEvents(nodeId);
        
        // 添加日志
        addLogMessage(`客户端 ${clientId} 已添加到网络`);
        
        // 更新客户端状态面板
        updateClientStatusPanel();
        
        // 通知服务器新节点添加
        if (window.flSocket) {
            window.flSocket.emit('node_added', {
                node_id: nodeId,
                client_id: clientId
            });
        }
        
        return nodeId;
    }

    // 创建新节点 (旧版本，保持兼容性)
    function createNode() {
        const nodeId = nodeIdCounter++;
        
        // 从模板克隆节点
        const nodeFragment = document.importNode(nodeTemplate.content, true);
        const nodeElement = nodeFragment.querySelector('.node');
        
        // 设置节点ID和标题
        nodeElement.id = `node-${nodeId}`;
        nodeElement.querySelector('.node-title').textContent = `节点 ${nodeId}`;
        
        // 设置上传输入框ID
        const imageInput = nodeElement.querySelector('.image-input');
        imageInput.id = `image-input-${nodeId}`;
        nodeElement.querySelector('label').setAttribute('for', `image-input-${nodeId}`);
        
        // 定位节点 - 在圆周上均匀分布
        positionNode(nodeElement, nodeId);
        
        // 添加到DOM
        nodesContainer.appendChild(nodeElement);
        
        // 存储节点数据
        nodes.push({
            id: nodeId,
            element: nodeElement,
            images: [],
            status: 'idle',  // idle, training, uploading, complete
        });
        
        // 绑定事件
        setupNodeEvents(nodeId);
        
        // 添加日志
        addLogMessage(`节点 ${nodeId} 已添加到网络`);
        
        return nodeId;
    }

    // 定位节点到圆周位置
    function positionNode(nodeElement, id) {
        const containerWidth = networkContainer.clientWidth;
        const containerHeight = networkContainer.clientHeight;
        const radius = Math.min(containerWidth, containerHeight) * 0.35; // 圆的半径
        
        // 根据节点数量计算角度
        const angle = ((id - 1) % 8) * (Math.PI / 4);
        
        // 计算中心位置
        const centerX = containerWidth / 2;
        const centerY = containerHeight / 2;
        
        // 计算位置（像素）
        const x = centerX + radius * Math.cos(angle);
        const y = centerY + radius * Math.sin(angle);
        
        // 转换为百分比并应用
        nodeElement.style.left = `${(x / containerWidth) * 100}%`;
        nodeElement.style.top = `${(y / containerHeight) * 100}%`;
        nodeElement.style.transform = 'translate(-50%, -50%)'; // 居中节点
    }

    // 设置节点事件监听
    function setupNodeEvents(nodeId) {
        const nodeElement = document.getElementById(`node-${nodeId}`);
        const imageInput = nodeElement.querySelector('.image-input');
        const removeBtn = nodeElement.querySelector('.node-remove-btn');
        const nodeHeader = nodeElement.querySelector('.node-header');
        
        // 图片上传
        imageInput.addEventListener('change', (e) => {
            if (isTraining) return;
            
            const files = e.target.files;
            if (!files.length) return;
            
            const node = getNodeById(nodeId);
            if (!node) return;
            
            node.images = [...node.images, ...Array.from(files)];
            
            // 更新显示
            nodeElement.querySelector('.uploaded-count').textContent = node.images.length;
            
            // 添加日志
            addLogMessage(`节点 ${nodeId} 已上传 ${files.length} 张图片数据`);
        });
        
        // 删除节点
        removeBtn.addEventListener('click', () => {
            if (isTraining) return;
            
            // 从DOM移除
            nodeElement.remove();
            
            // 从数组移除
            nodes = nodes.filter(n => n.id !== nodeId);
            
            // 添加日志
            addLogMessage(`节点 ${nodeId} 已从网络中移除`);
        });
        
        // 拖拽功能 - 鼠标按下
        nodeHeader.addEventListener('mousedown', (e) => {
            // 如果正在训练，不允许拖拽
            if (isTraining) return;
            
            isDragging = true;
            currentDragNode = nodeElement;
            
            // 记录起始位置
            startX = e.clientX;
            startY = e.clientY;
            
            // 获取容器和节点位置信息
            containerRect = networkContainer.getBoundingClientRect();
            nodeRect = currentDragNode.getBoundingClientRect();
            
            // 计算节点中心相对于容器的当前位置（百分比）
            const nodeCenterX = nodeRect.left + nodeRect.width / 2 - containerRect.left;
            const nodeCenterY = nodeRect.top + nodeRect.height / 2 - containerRect.top;
            
            nodeStartX = (nodeCenterX / containerRect.width) * 100;
            nodeStartY = (nodeCenterY / containerRect.height) * 100;
            
            // 添加拖动类，以实现视觉反馈
            nodeElement.classList.add('dragging');
            
            // 阻止事件冒泡和默认行为
            e.preventDefault();
            e.stopPropagation();
        });
    }
    
    // 拖拽事件 - 鼠标移动
    document.addEventListener('mousemove', (e) => {
        if (!isDragging || !currentDragNode) return;
        
        // 取消之前的动画帧请求
        if (rafId) {
            cancelAnimationFrame(rafId);
        }
        
        // 使用requestAnimationFrame优化渲染性能
        rafId = requestAnimationFrame(() => {
            // 计算鼠标移动距离（像素）
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;
            
            // 转换为百分比移动距离
            const deltaXPercent = (deltaX / containerRect.width) * 100;
            const deltaYPercent = (deltaY / containerRect.height) * 100;
            
            // 计算新位置（百分比）
            let newXPercent = nodeStartX + deltaXPercent;
            let newYPercent = nodeStartY + deltaYPercent;
            
            // 限制节点在容器内（考虑节点大小的一半）
            const nodeSize = currentDragNode.id === 'central-node' ? 75 : 75; // 节点半径的百分比估算
            const safeMargin = (nodeSize / Math.min(containerRect.width, containerRect.height)) * 100;
            
            newXPercent = Math.max(safeMargin, Math.min(newXPercent, 100 - safeMargin));
            newYPercent = Math.max(safeMargin, Math.min(newYPercent, 100 - safeMargin));
            
            // 应用位置
            currentDragNode.style.left = `${newXPercent}%`;
            currentDragNode.style.top = `${newYPercent}%`;
            currentDragNode.style.transform = 'translate(-50%, -50%)';
        });
    });
    
    // 拖拽事件 - 鼠标释放
    document.addEventListener('mouseup', () => {
        if (!isDragging) return;
        
        // 取消任何待处理的动画帧
        if (rafId) {
            cancelAnimationFrame(rafId);
            rafId = null;
        }
        
        if (currentDragNode) {
            // 移除拖动状态
            currentDragNode.classList.remove('dragging');
            currentDragNode = null;
        }
        
        // 重置变量
        isDragging = false;
        containerRect = null;
        nodeRect = null;
    });

    // 绑定参数控制按钮事件
    roundPlus.addEventListener('click', () => {
        const currentValue = parseInt(roundNumber.value);
        if (currentValue < 10) { // 最大10轮
            roundNumber.value = currentValue + 1;
        }
    });
    
    roundMinus.addEventListener('click', () => {
        const currentValue = parseInt(roundNumber.value);
        if (currentValue > 1) { // 最少1轮
            roundNumber.value = currentValue - 1;
        }
    });
    
    clientPlus.addEventListener('click', () => {
        const currentValue = parseInt(clientNumber.value);
        if (currentValue < 8) { // 最多8个客户端
            clientNumber.value = currentValue + 1;
        }
    });
    
    clientMinus.addEventListener('click', () => {
        const currentValue = parseInt(clientNumber.value);
        if (currentValue > 0) { // 最少0个(表示全部)
            clientNumber.value = currentValue - 1;
        }
    });
    
    // 验证输入数值
    roundNumber.addEventListener('change', () => {
        let value = parseInt(roundNumber.value);
        if (isNaN(value) || value < 1) {
            value = 1;
        } else if (value > 10) {
            value = 10;
        }
        roundNumber.value = value;
    });
    
    clientNumber.addEventListener('change', () => {
        let value = parseInt(clientNumber.value);
        if (isNaN(value) || value < 0) {
            value = 0;
        } else if (value > 8) {
            value = 8;
        }
        clientNumber.value = value;
    });    // 开始训练
    startTrainingBtn.addEventListener('click', () => {
        if (isTraining) return;
        
        if (nodes.length === 0) {
            const message = '请至少添加一个训练节点才能开始训练！';
            addLogMessage(message, 'warning');
            showErrorModal(message);
            return;
        }
        
        // 检查是否所有节点都有数据
        const emptyNodes = nodes.filter(node => node.images.length === 0);
        if (emptyNodes.length > 0) {
            const nodeIds = emptyNodes.map(n => n.id).join(', ');
            const message = `节点 ${nodeIds} 没有上传图片数据，请先为所有节点上传训练数据！`;
            addLogMessage(message, 'warning');
            showErrorModal(message);
            return;
        }
        
        // 检查客户端参与数量
        const participatingClients = parseInt(clientNumber.value);
        if (participatingClients > nodes.length) {
            const message = `设置的参与客户端数(${participatingClients})大于实际节点数(${nodes.length})，请调整参数！`;
            addLogMessage(message, 'warning');
            showErrorModal(message);
            return;
        }
        
        isTraining = true;
        startTrainingBtn.disabled = true;
        stopTrainingBtn.disabled = false;  // 启用停止按钮
        addNodeBtn.disabled = true;
        
        // 获取训练参数
        const rounds = parseInt(roundNumber.value);
        const clientCount = parseInt(clientNumber.value);
        
        // 清除状态显示
        statusDisplay.innerHTML = '<p>开始联邦学习训练...</p>';
        
        // 添加日志
        addLogMessage(`联邦学习训练开始，总轮数: ${rounds}, 每轮参与客户端: ${clientCount > 0 ? clientCount : '全部'}`, 'highlight');
        
        // 通过SocketIO通知开始训练
        if (window.flSocket) {
            window.flSocket.emit('start_training', {
                rounds: rounds,
                client_count: clientCount
            });
        }
        
        // 开始模拟训练（本地可视化）
        startFederatedLearning(rounds, clientCount);
    });
    
    // 停止训练
    stopTrainingBtn.addEventListener('click', () => {
        if (!isTraining) return;
        
        // 调用联邦学习模块的停止函数
        if (window.stopFederatedLearning) {
            window.stopFederatedLearning();
            addLogMessage('正在停止训练过程...', 'warning');
            stopTrainingBtn.disabled = true;  // 防止多次点击
        }
    });

    // 重置系统 - 更新重置逻辑以包含参数重置
    resetBtn.addEventListener('click', () => {
        if (isTraining) return;
        
        // 清除所有节点
        nodesContainer.innerHTML = '';
        nodes = [];
        nodeIdCounter = 1;
        
        // 重置中心节点
        centralNode.querySelector('.node-status').textContent = '待机中';
        centralNode.classList.remove('complete', 'training', 'uploading');
        // 重置中心节点位置
        centralNode.style.left = '50%';
        centralNode.style.top = '50%';
        
        // 重置训练参数
        roundNumber.value = 3;
        clientNumber.value = 0;
        
        // 重置状态显示
        statusDisplay.innerHTML = '<p>等待开始训练...</p>';
        
        // 添加日志
        addLogMessage('系统已重置');
    });    // 清除日志
    clearLogBtn.addEventListener('click', () => {
        logContent.innerHTML = '';
    });    // 帮助按钮事件
    helpBtn.addEventListener('click', () => {
        helpModal.classList.add('show');
    });

    // 介绍按钮事件
    introBtn.addEventListener('click', () => {
        introModal.classList.add('show');
    });

    // 日志放大按钮事件
    magnifyLogBtn.addEventListener('click', () => {
        // 复制当前日志内容到放大模态框
        logModalContent.innerHTML = logContent.innerHTML;
        logModal.classList.add('show');
    });

    // 关闭帮助弹窗
    helpCloseBtn.addEventListener('click', () => {
        helpModal.classList.remove('show');
    });

    // 关闭介绍弹窗
    introCloseBtn.addEventListener('click', () => {
        introModal.classList.remove('show');
    });

    // 关闭日志放大弹窗
    logCloseBtn.addEventListener('click', () => {
        logModal.classList.remove('show');
    });

    // 关闭错误弹窗
    errorCloseBtn.addEventListener('click', () => {
        errorModal.classList.remove('show');
    });    // 点击弹窗背景关闭
    helpModal.addEventListener('click', (e) => {
        if (e.target === helpModal) {
            helpModal.classList.remove('show');
        }
    });

    introModal.addEventListener('click', (e) => {
        if (e.target === introModal) {
            introModal.classList.remove('show');
        }
    });

    logModal.addEventListener('click', (e) => {
        if (e.target === logModal) {
            logModal.classList.remove('show');
        }
    });

    errorModal.addEventListener('click', (e) => {
        if (e.target === errorModal) {
            errorModal.classList.remove('show');
        }
    });    // ESC键关闭弹窗
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            helpModal.classList.remove('show');
            introModal.classList.remove('show');
            logModal.classList.remove('show');
            errorModal.classList.remove('show');
        }
    });

    // 显示错误弹窗
    function showErrorModal(message) {
        errorMessage.textContent = message;
        errorModal.classList.add('show');
    }

    // 根据ID获取节点对象
    function getNodeById(id) {
        return nodes.find(n => n.id === id);
    }    // 添加日志消息
    function addLogMessage(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        
        const timestampSpan = document.createElement('span');
        timestampSpan.className = 'log-timestamp';
        timestampSpan.textContent = timestamp;
        
        logEntry.appendChild(timestampSpan);
        logEntry.appendChild(document.createTextNode(message));
        
        logContent.appendChild(logEntry);
        logContent.scrollTop = logContent.scrollHeight;
    }

    // 公开addLogEntry函数供外部调用
    window.addLogEntry = function(type, message) {
        addLogMessage(`[${type}] ${message}`, 'info');
    };

    // 创建默认节点
    for (let i = 0; i < 4; i++) {
        createNode();
    }

    // 为中心节点添加拖拽功能
    setupCentralNodeDrag();

    // 设置网络容器大小调整监听
    setupNetworkContainerResize();
    
    // 公开API以供federated-learning.js使用
    window.federatedUI = {
        updateNodeStatus,
        updateCentralNodeStatus,
        finishTraining,
        addLogMessage
    };    function updateNodeStatus(nodeId, status, message) {
        const node = getNodeById(nodeId);
        if (!node) return;
        
        const statusElement = node.element.querySelector('.node-status');
        
        // 强制保存当前精确位置
        const currentLeft = node.element.style.left;
        const currentTop = node.element.style.top;
        const currentTransform = node.element.style.transform || 'translate(-50%, -50%)';
        
        // 更新状态
        node.status = status;
        
        // 移除所有状态类
        node.element.classList.remove('training', 'uploading', 'complete');
        
        // 添加新状态类和文本
        if (status === 'training') {
            statusElement.textContent = '本地训练中...';
            node.element.classList.add('training');
        } else if (status === 'uploading') {
            statusElement.textContent = '上传模型参数...';
            node.element.classList.add('uploading');
        } else if (status === 'complete') {
            statusElement.textContent = '训练完成';
            node.element.classList.add('complete');
        } else if (status === 'idle') {
            statusElement.textContent = '待机中';
        }
        
        // 强制恢复并保持原始位置（同步执行，确保不被动画覆盖）
        if (currentLeft && currentTop) {
            node.element.style.left = currentLeft;
            node.element.style.top = currentTop;
            node.element.style.transform = currentTransform;
            
            // 使用 important 强制覆盖任何动画变换
            node.element.style.setProperty('transform', currentTransform, 'important');
        }
        
        // 双重保险：下一帧再次确保位置
        requestAnimationFrame(() => {
            if (currentLeft && currentTop) {
                node.element.style.left = currentLeft;
                node.element.style.top = currentTop;
                node.element.style.setProperty('transform', currentTransform, 'important');
            }
        });
        
        // 更新状态显示
        if (message) {
            const statusUpdate = document.createElement('p');
            statusUpdate.textContent = message;
            statusDisplay.appendChild(statusUpdate);
            statusDisplay.scrollTop = statusDisplay.scrollHeight;
        }
    }    function updateCentralNodeStatus(status, message) {
        const statusElement = centralNode.querySelector('.node-status');
        
        // 强制保存当前精确位置
        const currentLeft = centralNode.style.left || '50%';
        const currentTop = centralNode.style.top || '50%';
        const currentTransform = centralNode.style.transform || 'translate(-50%, -50%)';
        
        // 移除所有状态类
        centralNode.classList.remove('training', 'uploading', 'complete');
        
        // 添加新状态类和文本
        if (status === 'aggregating') {
            statusElement.textContent = '聚合模型参数...';
            centralNode.classList.add('training');
        } else if (status === 'distributing') {
            statusElement.textContent = '分发全局模型...';
            centralNode.classList.add('uploading');
        } else if (status === 'complete') {
            statusElement.textContent = '训练完成';
            centralNode.classList.add('complete');
        } else if (status === 'idle') {
            statusElement.textContent = '待机中';
        }
        
        // 强制恢复并保持原始位置
        centralNode.style.left = currentLeft;
        centralNode.style.top = currentTop;
        centralNode.style.setProperty('transform', currentTransform, 'important');
        
        // 双重保险：下一帧再次确保位置
        requestAnimationFrame(() => {
            centralNode.style.left = currentLeft;
            centralNode.style.top = currentTop;
            centralNode.style.setProperty('transform', currentTransform, 'important');
        });
        
        // 更新状态显示
        if (message) {
            const statusUpdate = document.createElement('p');
            statusUpdate.textContent = message;
            statusDisplay.appendChild(statusUpdate);
            statusDisplay.scrollTop = statusDisplay.scrollHeight;
        }
    }    function finishTraining() {
        isTraining = false;
        startTrainingBtn.disabled = false;
        stopTrainingBtn.disabled = true;  // 禁用停止按钮
        addNodeBtn.disabled = false;
        
        // 不自动添加"训练完成"日志，由调用方决定是否添加
    }

    // 更新客户端状态面板
    function updateClientStatusPanel() {
        const statusList = document.getElementById('client-status-list');
        if (!statusList) return;

        if (nodes.length === 0) {
            statusList.innerHTML = '<p class="text-muted text-center">暂无客户端连接</p>';
            return;
        }

        statusList.innerHTML = nodes.map(node => `
            <div class="client-status-item">
                <div class="client-info">
                    <div class="client-id">${node.clientId || `节点${node.id}`}</div>
                    <div class="client-data">${node.images.length} 个数据文件</div>
                </div>
                <span class="client-state ${getClientStateClass(node.status)}">
                    ${getClientStateText(node.status)}
                </span>
            </div>
        `).join('');
    }

    // 获取客户端状态样式类
    function getClientStateClass(status) {
        const stateClasses = {
            'idle': 'online',
            'training': 'training',
            'uploading': 'training',
            'complete': 'online',
            'offline': 'offline'
        };
        return stateClasses[status] || 'offline';
    }

    // 获取客户端状态文本
    function getClientStateText(status) {
        const stateTexts = {
            'idle': '在线',
            'training': '训练中',
            'uploading': '上传中',
            'complete': '完成',
            'offline': '离线'
        };
        return stateTexts[status] || '未知';
    }

    // 添加服务器日志
    function addServerLog(message, type = 'info') {
        const logsContent = document.getElementById('server-logs-content');
        if (!logsContent) return;

        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        logEntry.innerHTML = `
            <span class="log-timestamp">[${timestamp}]</span>
            <span class="log-type">[${type.toUpperCase()}]</span>
            <span class="log-message">${message}</span>
        `;

        logsContent.appendChild(logEntry);
        logsContent.scrollTop = logsContent.scrollHeight;

        // 限制日志条目数量
        const logEntries = logsContent.querySelectorAll('.log-entry');
        if (logEntries.length > 100) {
            logEntries[0].remove();
        }
    }

    // 清除服务器日志
    const clearServerLogsBtn = document.getElementById('clear-server-logs');
    if (clearServerLogsBtn) {
        clearServerLogsBtn.addEventListener('click', () => {
            const logsContent = document.getElementById('server-logs-content');
            if (logsContent) {
                logsContent.innerHTML = '';
                addServerLog('服务器日志已清除', 'info');
            }
        });
    }

    // 设置中心节点的拖拽功能
    function setupCentralNodeDrag() {
        // 如果正在训练，不添加拖拽功能
        if (isTraining) return;
        
        // 确保中心节点有正确的初始transform
        centralNode.style.transform = 'translate(-50%, -50%)';
        
        // 添加拖拽处理
        centralNode.addEventListener('mousedown', (e) => {
            // 如果正在训练，不允许拖拽
            if (isTraining) return;
            
            isDragging = true;
            currentDragNode = centralNode;
            
            // 记录起始位置
            startX = e.clientX;
            startY = e.clientY;
            
            // 获取容器和节点位置信息
            containerRect = networkContainer.getBoundingClientRect();
            nodeRect = centralNode.getBoundingClientRect();
            
            // 计算节点中心相对于容器的当前位置（百分比）
            const nodeCenterX = nodeRect.left + nodeRect.width / 2 - containerRect.left;
            const nodeCenterY = nodeRect.top + nodeRect.height / 2 - containerRect.top;
            
            nodeStartX = (nodeCenterX / containerRect.width) * 100;
            nodeStartY = (nodeCenterY / containerRect.height) * 100;
            
            // 添加拖动类
            centralNode.classList.add('dragging');
            
            // 阻止事件冒泡和默认行为
            e.preventDefault();
            e.stopPropagation();
        });
    }
    
    // 设置网络容器大小调整监听
    function setupNetworkContainerResize() {
        // 监听容器大小变化
        const resizeObserver = new ResizeObserver(entries => {
            for (let entry of entries) {
                if (entry.target === networkContainer) {
                    // 使用防抖来避免频繁调整
                    if (this.resizeTimeout) {
                        clearTimeout(this.resizeTimeout);
                    }
                    this.resizeTimeout = setTimeout(() => {
                        adjustNodesPositionOnResize();
                    }, 100);
                }
            }
        });
        
        // 观察网络容器
        resizeObserver.observe(networkContainer);
        
        // 添加双击事件重置容器大小
        networkContainer.addEventListener('dblclick', (e) => {
            // 如果点击的是调整大小的手柄区域，则不处理
            const rect = networkContainer.getBoundingClientRect();
            const handleSize = 20;
            if (e.clientX > rect.right - handleSize && e.clientY > rect.bottom - handleSize) {
                return;
            }
            
            // 重置容器大小
            networkContainer.style.width = '';
            networkContainer.style.height = '600px';
            
            // 延迟一帧后调整节点位置，确保容器大小已更新
            requestAnimationFrame(() => {
                adjustNodesPositionOnResize();
            });
        });
    }
    
    // 调整节点位置以适应容器大小变化
    function adjustNodesPositionOnResize() {
        // 如果正在训练，不调整位置
        if (isTraining) return;
        
        // 获取新的容器大小
        const containerWidth = networkContainer.clientWidth;
        const containerHeight = networkContainer.clientHeight;
        
        // 调整客户端节点位置
        nodes.forEach(node => {
            // 获取节点当前的百分比位置
            const currentLeft = parseFloat(node.element.style.left) || 50;
            const currentTop = parseFloat(node.element.style.top) || 50;
            
            // 确保节点位置在合理范围内（考虑节点自身大小）
            const nodeWidth = 150; // 节点宽度
            const nodeHeight = 200; // 节点高度（估算）
            
            // 计算安全边界（百分比）
            const maxLeft = 100 - (nodeWidth / containerWidth) * 50; // 50%是因为transform: translate(-50%, -50%)
            const maxTop = 100 - (nodeHeight / containerHeight) * 50;
            const minLeft = (nodeWidth / containerWidth) * 50;
            const minTop = (nodeHeight / containerHeight) * 50;
            
            // 限制位置在安全范围内
            const safeLeft = Math.max(minLeft, Math.min(currentLeft, maxLeft));
            const safeTop = Math.max(minTop, Math.min(currentTop, maxTop));
            
            // 应用位置
            node.element.style.left = `${safeLeft}%`;
            node.element.style.top = `${safeTop}%`;
            node.element.style.transform = 'translate(-50%, -50%)';
        });
        
        // 调整中心节点位置（确保它保持在中心附近）
        const centralLeft = parseFloat(centralNode.style.left) || 50;
        const centralTop = parseFloat(centralNode.style.top) || 50;
        
        // 中心节点的安全边界
        const centralSize = 150; // 中心节点大小
        const centralMaxLeft = 100 - (centralSize / containerWidth) * 50;
        const centralMaxTop = 100 - (centralSize / containerHeight) * 50;
        const centralMinLeft = (centralSize / containerWidth) * 50;
        const centralMinTop = (centralSize / containerHeight) * 50;
        
        const safeCentralLeft = Math.max(centralMinLeft, Math.min(centralLeft, centralMaxLeft));
        const safeCentralTop = Math.max(centralMinTop, Math.min(centralTop, centralMaxTop));
        
        centralNode.style.left = `${safeCentralLeft}%`;
        centralNode.style.top = `${safeCentralTop}%`;
        centralNode.style.transform = 'translate(-50%, -50%)';
        
        // 添加日志记录
        addLogMessage("网络显示区域大小已调整，节点位置已重新校准");
    }
    
    // 初始化Socket连接和事件监听
    function initializeSocketListeners() {
        if (!window.flSocket) return;

        // 监听客户端参数更新
        window.flSocket.on('client_parameters_updated', (data) => {
            addServerLog(`客户端 ${data.client_id} 更新了模型参数`, 'info');
            updateClientStatusPanel();
        });

        // 监听客户端数据状态更新
        window.flSocket.on('client_data_status_updated', (data) => {
            addServerLog(`客户端 ${data.client_id} 上传了 ${data.file_count} 个数据文件`, 'info');
            updateClientStatusPanel();
        });

        // 监听训练状态更新
        window.flSocket.on('training_status_updated', (data) => {
            addServerLog(data.message, 'info');
            updateClientStatusInNodes(data.client_id, data.status);
            updateClientStatusPanel();
        });

        // 监听节点状态更新
        window.flSocket.on('node_status_updated', (data) => {
            addServerLog(`节点 ${data.node_id} (${data.client_id}) 状态: ${data.status}`, 'info');
            updateClientStatusPanel();
        });

        // 定期请求状态更新
        setInterval(() => {
            window.flSocket.emit('get_client_status');
            window.flSocket.emit('get_server_logs');
        }, 10000); // 每10秒更新一次

        // 监听状态响应
        window.flSocket.on('client_status_list', (data) => {
            updateClientStatusPanelWithData(data.clients);
        });

        window.flSocket.on('server_logs_list', (data) => {
            updateServerLogsWithData(data.logs);
        });
    }

    // 更新节点中的客户端状态显示
    function updateClientStatusInNodes(clientId, status) {
        const node = nodes.find(n => n.clientId === clientId);
        if (node) {
            node.status = status;
            const statusElement = node.element.querySelector('.node-status');
            if (statusElement) {
                statusElement.textContent = getClientStateText(status);
                
                // 更新节点样式
                node.element.className = node.element.className.replace(/\b(training|uploading|complete)\b/g, '');
                if (status === 'training') {
                    node.element.classList.add('training');
                } else if (status === 'uploading') {
                    node.element.classList.add('uploading');
                } else if (status === 'complete') {
                    node.element.classList.add('complete');
                }
            }
        }
    }

    // 使用数据更新客户端状态面板
    function updateClientStatusPanelWithData(clients) {
        const statusList = document.getElementById('client-status-list');
        if (!statusList) return;

        if (clients.length === 0) {
            statusList.innerHTML = '<p class="text-muted text-center">暂无客户端连接</p>';
            return;
        }

        statusList.innerHTML = clients.map(client => `
            <div class="client-status-item">
                <div class="client-info">
                    <div class="client-id">${client.client_id}</div>
                    <div class="client-data">
                        数据: ${client.has_uploaded_data ? '已上传' : '未上传'} 
                        ${client.training_progress ? `(${client.training_progress})` : ''}
                    </div>
                </div>
                <span class="client-state ${getClientStateClass(client.status)}">
                    ${client.is_training ? '训练中' : getClientStateText(client.status)}
                </span>
            </div>
        `).join('');
    }

    // 使用数据更新服务器日志
    function updateServerLogsWithData(logs) {
        const logsContent = document.getElementById('server-logs-content');
        if (!logsContent) return;

        logsContent.innerHTML = logs.map(log => `
            <div class="log-entry">
                <span class="log-timestamp">[${new Date(log.created_at).toLocaleTimeString()}]</span>
                <span class="log-type">[${log.event_type}]</span>
                <span class="log-message">${log.message}</span>
            </div>
        `).join('');
    }

    // 页面加载时初始化
    document.addEventListener('DOMContentLoaded', () => {
        // 等待Socket连接建立
        setTimeout(() => {
            initializeSocketListeners();
            addServerLog('服务器控制台已启动', 'info');
        }, 1000);
    });
});
