/*
================================================================================
CarbonChain Explorer - Main JavaScript
================================================================================
Modern interactive features for glassmorphism UI
================================================================================
*/

// ============================================================================
// GLOBAL STATE
// ============================================================================

const CarbonChain = {
    config: {
        apiBaseUrl: '',
        refreshInterval: 30000, // 30 seconds
        animationDuration: 300,
    },
    state: {
        isLoading: false,
        lastUpdate: null,
    }
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🌿 CarbonChain Explorer initialized');
    
    // Initialize components
    initSearch();
    initTimestamps();
    initThemeToggle();
    initScrollEffects();
    initTooltips();
    
    // Start auto-refresh for real-time data
    startAutoRefresh();
});

// ============================================================================
// SEARCH FUNCTIONALITY
// ============================================================================

function initSearch() {
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('searchInput');
    
    if (!searchForm || !searchInput) return;
    
    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const query = searchInput.value.trim();
        if (!query) return;
        
        showLoading();
        
        try {
            const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.redirect) {
                window.location.href = data.redirect;
            } else if (data.error) {
                showNotification(`❌ ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Search error:', error);
            showNotification('❌ Search failed. Please try again.', 'error');
        } finally {
            hideLoading();
        }
    });
    
    // Add search suggestions (debounced)
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            const query = e.target.value.trim();
            if (query.length >= 3) {
                fetchSearchSuggestions(query);
            }
        }, 300);
    });
}

async function fetchSearchSuggestions(query) {
    // TODO: Implement search suggestions
    console.log('Fetching suggestions for:', query);
}

// ============================================================================
// TIMESTAMP FORMATTING
// ============================================================================

function initTimestamps() {
    updateAllTimestamps();
    
    // Update every second
    setInterval(updateAllTimestamps, 1000);
}

function updateAllTimestamps() {
    const timestamps = document.querySelectorAll('[data-timestamp]');
    
    timestamps.forEach(element => {
        const timestamp = parseInt(element.dataset.timestamp);
        if (isNaN(timestamp)) return;
        
        const date = new Date(timestamp * 1000);
        const formatted = formatTimeAgo(date);
        
        element.textContent = formatted;
        element.title = date.toLocaleString();
    });
}

function formatTimeAgo(date) {
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 0) return 'in the future';
    if (seconds < 60) return `${seconds}s ago`;
    
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}d ago`;
    
    const months = Math.floor(days / 30);
    if (months < 12) return `${months}mo ago`;
    
    const years = Math.floor(months / 12);
    return `${years}y ago`;
}

// ============================================================================
// THEME TOGGLE (Light/Dark Mode)
// ============================================================================

function initThemeToggle() {
    const currentTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);
    
    // Create theme toggle button if needed
    const nav = document.querySelector('.glass-nav .container');
    if (!nav) return;
    
    const themeToggle = document.createElement('button');
    themeToggle.className = 'btn-icon theme-toggle';
    themeToggle.innerHTML = currentTheme === 'dark' ? '☀️' : '🌙';
    themeToggle.title = 'Toggle theme';
    themeToggle.addEventListener('click', toggleTheme);
    
    nav.appendChild(themeToggle);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.innerHTML = newTheme === 'dark' ? '☀️' : '🌙';
    }
    
    showNotification(`Theme switched to ${newTheme} mode`, 'info');
}

// ============================================================================
// SCROLL EFFECTS
// ============================================================================

function initScrollEffects() {
    let lastScroll = 0;
    const nav = document.querySelector('.glass-nav');
    
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (nav) {
            if (currentScroll > lastScroll && currentScroll > 100) {
                // Scrolling down
                nav.style.transform = 'translateY(-100%)';
            } else {
                // Scrolling up
                nav.style.transform = 'translateY(0)';
            }
        }
        
        lastScroll = currentScroll;
        
        // Parallax effect for hero section
        const hero = document.querySelector('.hero-section');
        if (hero && currentScroll < window.innerHeight) {
            hero.style.transform = `translateY(${currentScroll * 0.5}px)`;
            hero.style.opacity = 1 - (currentScroll / window.innerHeight);
        }
    });
    
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
}

// ============================================================================
// TOOLTIPS
// ============================================================================

function initTooltips() {
    const elementsWithTitle = document.querySelectorAll('[title]');
    
    elementsWithTitle.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    const element = e.currentTarget;
    const title = element.getAttribute('title');
    if (!title) return;
    
    // Remove title to prevent default tooltip
    element.setAttribute('data-original-title', title);
    element.removeAttribute('title');
    
    // Create custom tooltip
    const tooltip = document.createElement('div');
    tooltip.className = 'custom-tooltip glass-card';
    tooltip.textContent = title;
    document.body.appendChild(tooltip);
    
    // Position tooltip
    const rect = element.getBoundingClientRect();
    tooltip.style.position = 'fixed';
    tooltip.style.top = `${rect.top - tooltip.offsetHeight - 10}px`;
    tooltip.style.left = `${rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)}px`;
    tooltip.style.zIndex = '10000';
    tooltip.style.pointerEvents = 'none';
    
    // Animate in
    setTimeout(() => tooltip.classList.add('show'), 10);
}

function hideTooltip(e) {
    const element = e.currentTarget;
    const originalTitle = element.getAttribute('data-original-title');
    
    if (originalTitle) {
        element.setAttribute('title', originalTitle);
        element.removeAttribute('data-original-title');
    }
    
    const tooltip = document.querySelector('.custom-tooltip');
    if (tooltip) {
        tooltip.classList.remove('show');
        setTimeout(() => tooltip.remove(), 300);
    }
}

// ============================================================================
// NOTIFICATIONS
// ============================================================================

function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `notification glass-card notification-${type}`;
    
    // Add icon based on type
    const icons = {
        info: 'ℹ️',
        success: '✅',
        error: '❌',
        warning: '⚠️'
    };
    
    notification.innerHTML = `
        <span class="notification-icon">${icons[type] || icons.info}</span>
        <span class="notification-message">${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);
    
    // Auto remove
    setTimeout(() => {
        notification.classList.remove('show');
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 300);
    }, duration);
    
    // Click to dismiss
    notification.addEventListener('click', () => {
        notification.classList.remove('show');
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 300);
    });
}

window.showNotification = showNotification;

// ============================================================================
// LOADING INDICATOR
// ============================================================================

function showLoading() {
    if (CarbonChain.state.isLoading) return;
    
    CarbonChain.state.isLoading = true;
    
    const loader = document.createElement('div');
    loader.className = 'loading-overlay';
    loader.innerHTML = `
        <div class="loading-spinner glass-card">
            <div class="spinner"></div>
            <p>Loading...</p>
        </div>
    `;
    
    document.body.appendChild(loader);
    setTimeout(() => loader.classList.add('show'), 10);
}

function hideLoading() {
    CarbonChain.state.isLoading = false;
    
    const loader = document.querySelector('.loading-overlay');
    if (loader) {
        loader.classList.remove('show');
        setTimeout(() => loader.remove(), 300);
    }
}

// ============================================================================
// AUTO REFRESH
// ============================================================================

function startAutoRefresh() {
    // Refresh stats periodically
    setInterval(async () => {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            
            updateStats(data);
            CarbonChain.state.lastUpdate = new Date();
            
        } catch (error) {
            console.error('Auto refresh error:', error);
        }
    }, CarbonChain.config.refreshInterval);
}

function updateStats(data) {
    // Update stat values if elements exist
    const elements = {
        height: document.querySelector('#blockHeight'),
        supply: document.querySelector('#totalSupply'),
        certs: document.querySelector('#certCount'),
        nodes: document.querySelector('#nodeCount'),
    };
    
    if (elements.height && data.height !== undefined) {
        animateValue(elements.height, data.height);
    }
    
    if (elements.supply && data.total_supply_cco2 !== undefined) {
        animateValue(elements.supply, data.total_supply_cco2);
    }
    
    if (elements.certs && data.certificate_count !== undefined) {
        animateValue(elements.certs, data.certificate_count);
    }
    
    if (elements.nodes && data.node_count !== undefined) {
        animateValue(elements.nodes, data.node_count);
    }
}

function animateValue(element, endValue) {
    const startValue = parseInt(element.textContent) || 0;
    const duration = 1000;
    const startTime = Date.now();
    
    function update() {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const currentValue = Math.floor(startValue + (endValue - startValue) * progress);
        element.textContent = currentValue.toLocaleString();
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// ============================================================================
// CLIPBOARD FUNCTIONALITY
// ============================================================================

function copyToClipboard(text) {
    if (!navigator.clipboard) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        
        showNotification('✅ Copied to clipboard!', 'success');
        return;
    }
    
    navigator.clipboard.writeText(text)
        .then(() => {
            showNotification('✅ Copied to clipboard!', 'success');
        })
        .catch(err => {
            console.error('Copy failed:', err);
            showNotification('❌ Failed to copy', 'error');
        });
}

window.copyToClipboard = copyToClipboard;

// ============================================================================
// MODAL MANAGEMENT
// ============================================================================

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    
    // Close on overlay click
    const overlay = modal.querySelector('.modal-overlay');
    if (overlay) {
        overlay.addEventListener('click', () => closeModal(modalId));
    }
    
    // Close on Escape key
    const escapeHandler = (e) => {
        if (e.key === 'Escape') {
            closeModal(modalId);
            document.removeEventListener('keydown', escapeHandler);
        }
    };
    document.addEventListener('keydown', escapeHandler);
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    
    modal.classList.remove('show');
    document.body.style.overflow = '';
}

window.openModal = openModal;
window.closeModal = closeModal;

// ============================================================================
// TAB MANAGEMENT
// ============================================================================

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const tabContainer = tab.closest('.tabs-container');
        if (!tabContainer) return;
        
        // Remove active from all tabs and panes
        tabContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tabContainer.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        
        // Add active to clicked tab
        tab.classList.add('active');
        
        // Show corresponding pane
        const paneId = tab.dataset.tab;
        const pane = document.getElementById(paneId);
        if (pane) {
            pane.classList.add('active');
        }
    });
});

// ============================================================================
// INTERSECTION OBSERVER (Lazy Loading)
// ============================================================================

const observerOptions = {
    root: null,
    rootMargin: '50px',
    threshold: 0.1
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Observe all cards for fade-in animation
document.querySelectorAll('.glass-card').forEach(card => {
    observer.observe(card);
});

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

function formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num);
}

function formatCurrency(amount, decimals = 8) {
    return amount.toFixed(decimals);
}

// ============================================================================
// API HELPERS
// ============================================================================

async function apiRequest(endpoint, options = {}) {
    const url = `${CarbonChain.config.apiBaseUrl}${endpoint}`;
    
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// ============================================================================
// WEBSOCKET CONNECTION (for real-time updates)
// ============================================================================

function initWebSocket() {
    // TODO: Implement WebSocket connection for real-time blockchain updates
    console.log('WebSocket initialization placeholder');
}

// ============================================================================
// EXPORT FUNCTIONS
// ============================================================================

window.CarbonChain = {
    ...CarbonChain,
    copyToClipboard,
    showNotification,
    openModal,
    closeModal,
    formatNumber,
    formatCurrency,
    apiRequest,
};

// ============================================================================
// CONSOLE BRANDING
// ============================================================================

console.log('%c🌿 CarbonChain Explorer', 'font-size: 24px; font-weight: bold; color: #00d4aa;');
console.log('%cBlockchain for CO₂ Certification', 'font-size: 14px; color: #667eea;');
console.log('%cVersion 1.0.0', 'font-size: 12px; color: #999;');
console.log('');
console.log('Explore our API: /api/stats');
console.log('GitHub: https://github.com/carbonchain');
