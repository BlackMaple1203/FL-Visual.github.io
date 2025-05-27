document.addEventListener('DOMContentLoaded', () => {
    // DOM元素引用
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
    let rafId = null;

    // 添加节点
    addNodeBtn.addEventListener('click', () => {
        if (nodes.length >= 8) {
            addLogMessage('已达到最大节点数量限制 (8)', 'warning');
            return;
        }
        
        createNode();
    });

    // 创建新节点
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
            
            // 获取容器和节点位置信息（只获取一次以提高性能）
            containerRect = networkContainer.getBoundingClientRect();
            nodeRect = currentDragNode.getBoundingClientRect();
            
            // 计算节点相对于容器的起始位置
            nodeStartX = nodeRect.left - containerRect.left;
            nodeStartY = nodeRect.top - containerRect.top;
            
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
            // 计算移动距离
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;
            
            // 计算新位置（相对于容器）
            let newX = nodeStartX + deltaX;
            let newY = nodeStartY + deltaY;
            
            // 限制节点在容器内
            const maxX = containerRect.width;
            const maxY = containerRect.height;
            
            // 转换为百分比位置
            const xPercent = (newX / containerRect.width) * 100;
            const yPercent = (newY / containerRect.height) * 100;
            
            // 判断是否为中心节点
            if (currentDragNode.id === 'central-node') {
                // 中心节点使用百分比定位
                currentDragNode.style.left = `${xPercent}%`;
                currentDragNode.style.top = `${yPercent}%`;
            } else {
                // 客户端节点使用百分比定位
                const nodeWidth = nodeRect.width;
                const nodeHeight = nodeRect.height;
                
                // 将位置从像素转换为百分比
                const widthPercent = (nodeWidth / containerRect.width) * 100;
                const heightPercent = (nodeHeight / containerRect.height) * 100;
                
                // 限制不超出边界
                const limitedXPercent = Math.max(0, Math.min(xPercent, 100 - widthPercent/2));
                const limitedYPercent = Math.max(0, Math.min(yPercent, 100 - heightPercent/2));
                
                currentDragNode.style.left = `${limitedXPercent}%`;
                currentDragNode.style.top = `${limitedYPercent}%`;
                currentDragNode.style.transform = 'translate(-50%, -50%)';
            }
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
            // 不再需要转换，保持百分比定位
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
    });

    // 开始训练
    startTrainingBtn.addEventListener('click', () => {
        if (isTraining) return;
        
        if (nodes.length === 0) {
            addLogMessage('请至少添加一个训练节点', 'warning');
            return;
        }
        
        // 检查是否所有节点都有数据
        const emptyNodes = nodes.filter(node => node.images.length === 0);
        if (emptyNodes.length > 0) {
            const nodeIds = emptyNodes.map(n => n.id).join(', ');
            addLogMessage(`节点 ${nodeIds} 没有上传图片数据`, 'warning');
            return;
        }
        
        // 检查客户端参与数量
        const participatingClients = parseInt(clientNumber.value);
        if (participatingClients > nodes.length) {
            addLogMessage(`设置的参与客户端数(${participatingClients})大于实际节点数(${nodes.length})`, 'warning');
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
        
        // 开始模拟训练
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
    });

    // 清除日志
    clearLogBtn.addEventListener('click', () => {
        logContent.innerHTML = '';
    });

    // 根据ID获取节点对象
    function getNodeById(id) {
        return nodes.find(n => n.id === id);
    }

    // 添加日志消息
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
    };

    function updateNodeStatus(nodeId, status, message) {
        const node = getNodeById(nodeId);
        if (!node) return;
        
        const statusElement = node.element.querySelector('.node-status');
        
        // 更新状态
        node.status = status;
        
        // 移除所有状态类
        node.element.classList.remove('training', 'uploading', 'complete');
        
        // 添加新状态类
        if (status === 'training') {
            statusElement.textContent = '本地训练中...';
            node.element.classList.add('training');
        } else if (status === 'uploading') {
            statusElement.textContent = '上传模型参数...';
            node.element.classList.add('uploading');
        } else if (status === 'complete') {
            statusElement.textContent = '训练完成';
            node.element.classList.add('complete');
        }
        
        // 更新状态显示
        if (message) {
            const statusUpdate = document.createElement('p');
            statusUpdate.textContent = message;
            statusDisplay.appendChild(statusUpdate);
            statusDisplay.scrollTop = statusDisplay.scrollHeight;
        }
    }

    function updateCentralNodeStatus(status, message) {
        const statusElement = centralNode.querySelector('.node-status');
        
        // 保存当前位置
        const currentLeft = centralNode.style.left;
        const currentTop = centralNode.style.top;
        
        // 移除所有状态类
        centralNode.classList.remove('training', 'uploading', 'complete');
        
        // 添加新状态类
        if (status === 'aggregating') {
            statusElement.textContent = '聚合模型参数...';
            centralNode.classList.add('training');
        } else if (status === 'distributing') {
            statusElement.textContent = '分发全局模型...';
            centralNode.classList.add('uploading');
        } else if (status === 'complete') {
            statusElement.textContent = '训练完成';
            centralNode.classList.add('complete');
        }
        
        // 确保位置不变
        if (currentLeft && currentTop) {
            // 设置一个短暂延迟，确保在状态类应用后恢复位置
            setTimeout(() => {
                centralNode.style.left = currentLeft;
                centralNode.style.top = currentTop;
                centralNode.style.transform = 'translate(-50%, -50%)';
            }, 5);
        }
        
        // 更新状态显示
        if (message) {
            const statusUpdate = document.createElement('p');
            statusUpdate.textContent = message;
            statusDisplay.appendChild(statusUpdate);
            statusDisplay.scrollTop = statusDisplay.scrollHeight;
        }
    }

    function finishTraining() {
        isTraining = false;
        startTrainingBtn.disabled = false;
        stopTrainingBtn.disabled = true;  // 禁用停止按钮
        addNodeBtn.disabled = false;
        
        // 添加最终日志
        addLogMessage('联邦学习训练完成 ✅', 'highlight');
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
            
            // 计算节点相对于容器的起始位置
            // 注意：中心节点使用transform:translate(-50%, -50%)进行居中，所以需要特殊处理
            nodeStartX = nodeRect.left - containerRect.left + nodeRect.width / 2;
            nodeStartY = nodeRect.top - containerRect.top + nodeRect.height / 2;
            
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
                    // 容器大小变化时，调整节点位置
                    adjustNodesPositionOnResize();
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
            
            // 通知容器大小变化
            adjustNodesPositionOnResize();
        });
    }
    
    // 调整节点位置以适应容器大小变化
    function adjustNodesPositionOnResize() {
        // 如果正在训练，不调整位置
        if (isTraining) return;
        
        // 获取新的容器大小
        const containerWidth = networkContainer.clientWidth;
        const containerHeight = networkContainer.clientHeight;
        
        // 调整节点位置
        nodes.forEach(node => {
            // 获取节点当前位置（相对于容器的百分比）
            const nodeRect = node.element.getBoundingClientRect();
            const containerRect = networkContainer.getBoundingClientRect();
            
            // 计算节点左上角相对于容器的位置（像素）
            const leftPx = nodeRect.left - containerRect.left;
            const topPx = nodeRect.top - containerRect.top;
            
            // 将位置转换为相对于容器的百分比
            const leftPercent = (leftPx / containerRect.width) * 100;
            const topPercent = (topPx / containerRect.height) * 100;
            
            // 应用新位置（使用百分比以适应容器大小变化）
            node.element.style.left = `${leftPercent}%`;
            node.element.style.top = `${topPercent}%`;
        });
        
        // 添加日志记录
        addLogMessage("网络显示区域大小已调整");
    }
});
