// 全局JavaScript文件

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 为主页科目按钮添加动画效果
    const subjectButtons = document.querySelectorAll('.subject-button');
    subjectButtons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // 为表单添加提交处理
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // 添加加载状态
            const submitButtons = form.querySelectorAll('button[type="submit"]');
            submitButtons.forEach(button => {
                button.disabled = true;
                button.textContent = '处理中...';
            });
        });
    });
});

// 图片查看器功能
function initImageViewer() {
    const imageContainer = document.getElementById('image-container');
    const reviewImage = document.getElementById('review-image');
    
    if (!imageContainer || !reviewImage) return;
    
    let scale = 1;
    let posX = 0;
    let posY = 0;
    let isDragging = false;
    let startX, startY, startPosX, startPosY;
    
    // 鼠标滚轮缩放
    imageContainer.addEventListener('wheel', function(e) {
        e.preventDefault();
        
        const rect = reviewImage.getBoundingClientRect();
        const offsetX = e.clientX - rect.left;
        const offsetY = e.clientY - rect.top;
        
        const zoomIntensity = 0.1;
        const oldScale = scale;
        
        if (e.deltaY < 0) {
            scale *= (1 + zoomIntensity);
        } else {
            scale /= (1 + zoomIntensity);
        }
        
        // 限制缩放范围
        scale = Math.max(0.5, Math.min(scale, 5));
        
        // 调整位置以围绕鼠标点缩放
        const deltaScale = scale - oldScale;
        posX -= offsetX * deltaScale;
        posY -= offsetY * deltaScale;
        
        applyTransform();
    });
    
    // 鼠标拖拽移动
    reviewImage.addEventListener('mousedown', function(e) {
        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;
        startPosX = posX;
        startPosY = posY;
        reviewImage.style.cursor = 'grabbing';
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        
        posX = startPosX + dx;
        posY = startPosY + dy;
        
        applyTransform();
    });
    
    document.addEventListener('mouseup', function() {
        isDragging = false;
        reviewImage.style.cursor = 'grab';
    });
    
    // 触摸缩放和移动
    let touchStartDistance = 0;
    let touchStartScale = 1;
    
    reviewImage.addEventListener('touchstart', function(e) {
        if (e.touches.length === 2) {
            // 双指触摸开始
            const touch1 = e.touches[0];
            const touch2 = e.touches[1];
            touchStartDistance = Math.sqrt(
                Math.pow(touch2.clientX - touch1.clientX, 2) +
                Math.pow(touch2.clientY - touch1.clientY, 2)
            );
            touchStartScale = scale;
        } else if (e.touches.length === 1) {
            // 单指触摸开始
            isDragging = true;
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            startPosX = posX;
            startPosY = posY;
        }
    });
    
    reviewImage.addEventListener('touchmove', function(e) {
        if (e.touches.length === 2) {
            // 双指触摸移动 - 缩放
            const touch1 = e.touches[0];
            const touch2 = e.touches[1];
            const distance = Math.sqrt(
                Math.pow(touch2.clientX - touch1.clientX, 2) +
                Math.pow(touch2.clientY - touch1.clientY, 2)
            );
            
            scale = touchStartScale * (distance / touchStartDistance);
            scale = Math.max(0.5, Math.min(scale, 5));
            
            applyTransform();
            e.preventDefault();
        } else if (e.touches.length === 1 && isDragging) {
            // 单指触摸移动 - 平移
            const dx = e.touches[0].clientX - startX;
            const dy = e.touches[0].clientY - startY;
            
            posX = startPosX + dx;
            posY = startPosY + dy;
            
            applyTransform();
            e.preventDefault();
        }
    });
    
    reviewImage.addEventListener('touchend', function() {
        isDragging = false;
    });
    
    // 应用变换
    function applyTransform() {
        reviewImage.style.transform = `translate(${posX}px, ${posY}px) scale(${scale})`;
    }
    
    // 重置视图
    function resetView() {
        scale = 1;
        posX = 0;
        posY = 0;
        applyTransform();
    }
    
    // 双击重置视图
    reviewImage.addEventListener('dblclick', resetView);
}

// 初始化图片查看器
document.addEventListener('DOMContentLoaded', initImageViewer);

// AJAX请求辅助函数
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        },
    };
    
    try {
        const response = await fetch(url, finalOptions);
        const data = await response.json();
        return { success: response.ok, data };
    } catch (error) {
        console.error('API请求错误:', error);
        return { success: false, error: error.message };
    }
}