// API Configuration
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:5000/api'
    : '/api';

// Global Chart/Interval instances
let priceChart = null;
let priceInterval = null;
let perfBasePrices = {}; // שמירת מחירי בסיס לחישוב ביצועים בלייב

// --- Event Listeners and Initialization ---
document.addEventListener('DOMContentLoaded', function () {
    const stockSymbolInput = document.getElementById('stockSymbol');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loadRecommendationsBtn = document.getElementById('loadRecommendations');
    const quickBtns = document.querySelectorAll('.quick-btn');

    // Main Analyze Listeners
    analyzeBtn.addEventListener('click', analyzeStock);
    stockSymbolInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') analyzeStock();
    });

    // Market Scan Listener
    loadRecommendationsBtn.addEventListener('click', loadRecommendations);

    // Quick Symbols Listeners
    quickBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            stockSymbolInput.value = btn.dataset.symbol;
            analyzeStock();
        });
    });

    // Chart Range Selector Listener
    const rangeSelector = document.getElementById('chartRangeTabs');
    if (rangeSelector) {
        rangeSelector.addEventListener('click', (e) => {
            if (e.target.classList.contains('range-btn')) {
                const range = e.target.dataset.range;
                const symbol = document.getElementById('stockSymbolDisplay').textContent;

                // UI UI state management
                document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');

                if (symbol) updateChart(symbol, range);
            }
        });
    }
});

// --- Core API Interaction ---

/**
 * Main function to analyze a specific stock symbol
 */
async function analyzeStock() {
    const symbolInput = document.getElementById('stockSymbol');
    const symbol = symbolInput.value.trim().toUpperCase();

    if (!symbol) {
        showError('אנא הכנס סימול מניה');
        return;
    }

    showLoading(true);
    hideError();
    document.getElementById('dashboard').classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE_URL}/analyze/${symbol}`);
        const data = await response.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        displayStockData(data);
    } catch (error) {
        showError('שגיאה בחיבור לשרת. ודא שהשרת רץ.');
        console.error('Error:', error);
    } finally {
        showLoading(false);
    }
}

/**
 * Specifically updates the chart data for a new range without full analysis
 */
async function updateChart(symbol, range) {
    try {
        const response = await fetch(`${API_BASE_URL}/analyze/${symbol}?range=${range}`);
        const data = await response.json();
        if (data.chart_data) {
            renderChart(data.chart_data);
        }
    } catch (error) {
        console.error('Error updating chart:', error);
    }
}

// --- Dashboard Rendering ---

/**
 * Populates all UI elements with the analyzed stock data
 */
function displayStockData(data) {
    console.log('Received data:', data);

    // Reset state and show dashboard
    document.getElementById('dashboard').classList.remove('hidden');

    // Header Info
    const rec = data.recommendation;
    document.getElementById('stockName').textContent = rec.company_name;
    document.getElementById('stockSymbolDisplay').textContent = rec.symbol;

    // Detailed Textual Analysis (Expert Pros/Cons)
    const detailedAnalysisElem = document.getElementById('detailedAnalysis');
    if (detailedAnalysisElem && rec.detailed_analysis_he) {
        detailedAnalysisElem.innerHTML = rec.detailed_analysis_he
            .replace(/\n\n/g, '<br><br>') // Paragraphs
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
            .replace(/\n/g, '<br>'); // Line breaks
        detailedAnalysisElem.style.display = 'block';
    }

    // Recommendation Badges
    document.getElementById('shortTermRec').textContent = rec.short_term || 'N/A';
    document.getElementById('shortTermRec').className = `rec-badge ${getBadgeClass(rec.short_term)}`;
    document.getElementById('shortTermConf').textContent = `ביטחון: ${rec.short_term_confidence || 'N/A'}`;
    document.getElementById('longTermRec').textContent = rec.long_term || 'N/A';
    document.getElementById('longTermRec').className = `rec-badge ${getBadgeClass(rec.long_term)}`;

    // Risk Assesment
    document.getElementById('riskLevel').textContent = data.risk.level;
    document.getElementById('riskLevel').className = `risk-badge ${getRiskClass(data.risk.level)}`;
    document.getElementById('riskDetails').innerHTML = `
        <p>תנודתיות: ${data.risk.volatility}</p>
        <p>Beta: ${data.overview.beta || 'N/A'}</p>
        <p>ציון סיכון: ${data.risk.score || 'N/A'}/5</p>
    `;

    // Indicators
    document.getElementById('trend').textContent = data.technical.trend;
    document.getElementById('momentum').textContent = data.technical.momentum;
    document.getElementById('peRatio').textContent = data.fundamental.pe_rating;
    document.getElementById('marketCap').textContent = formatMarketCap(data.overview.market_cap);
    document.getElementById('beta').textContent = data.overview.beta || 'N/A';

    // Live Price Initialization
    const priceData = data.price_data;
    const currentPrice = priceData.current_price;
    const changePct = priceData.change_percent || 0;

    document.getElementById('currentPrice').textContent = formatPrice(currentPrice);
    const changeEl = document.getElementById('priceChange');
    changeEl.textContent = `${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%`;
    changeEl.className = `price-change ${changePct >= 0 ? 'positive' : 'negative'}`;

    // 52-Week High/Low (Fix: correctly mapping and parsing)
    const high52 = priceData.high_52w || (data.overview ? data.overview.high_52w : null);
    const low52 = priceData.low_52w || (data.overview ? data.overview.low_52w : null);
    if (high52 && high52 !== 'N/A') document.getElementById('high52w').textContent = formatPrice(parseFloat(high52));
    if (low52 && low52 !== 'N/A') document.getElementById('low52w').textContent = formatPrice(parseFloat(low52));

    // Secondary Metric (30D Change)
    if (data.performance && data.performance['1M']) {
        const change1m = data.performance['1M'].change * 100;
        const el30d = document.getElementById('change30d');
        el30d.textContent = `${change1m >= 0 ? '+' : ''}${change1m.toFixed(2)}%`;
        el30d.className = `metric-value ${change1m >= 0 ? 'positive' : 'negative'}`;
    }

    // Performance Horizontal Bar (1D, 5D, 1Y...)
    if (data.performance) {
        perfBasePrices = {};
        for (const [key, val] of Object.entries(data.performance)) {
            perfBasePrices[key] = val.base;
        }
        renderPerformance(data.performance);
    }

    // Investment Strategy (Real Analysis)
    if (data.investment_strategy) {
        const strat = data.investment_strategy;
        const stratEl = document.getElementById('strategyType');
        if (stratEl) {
            stratEl.textContent = strat.strategy;
            stratEl.className = `strategy-badge ${getStrategyClass(strat.strategy)}`;
        }
        const textEl = document.getElementById('strategyText');
        if (textEl) textEl.innerHTML = strat.recommendation_he.replace(/\n/g, '<br>');

        const volEl = document.getElementById('volatilityValue');
        if (volEl) volEl.textContent = `${strat.volatility}% (יומי)`;
    }

    // News Section (Fixed Timestamps)
    const newsGrid = document.getElementById('newsGrid');
    if (data.news && data.news.length > 0) {
        newsGrid.innerHTML = data.news.map(item => `
            <div class="news-item">
                <div class="news-meta">
                    <span>${item.publisher}</span> • <span>${item.published}</span>
                </div>
                <div class="news-title">${item.title}</div>
                <a href="${item.link}" target="_blank" class="news-link">קרא עוד ↗</a>
            </div>
        `).join('');
    } else {
        newsGrid.innerHTML = '<p class="no-news-msg">לא נמצאו חדשות אחרונות עבור סימול זה.</p>';
    }

    // Initialize/Reset Chart
    if (data.chart_data) {
        renderChart(data.chart_data);
    }

    // Restart Live Price Polling
    startLiveUpdates(rec.symbol);
}

// --- Modules ---

/**
 * Renders the performance comparison segments
 */
function renderPerformance(perfData) {
    const container = document.getElementById('performanceBar');
    if (!container) return;
    container.innerHTML = '';

    const labels = {
        '1D': 'יום', '5D': '5 ימים', '1M': 'חודש',
        '6M': '6 חוד', 'YTD': 'YTD', '1Y': 'שנה', '5Y': '5 שנים'
    };

    const order = ['1D', '5D', '1M', '6M', 'YTD', '1Y', '5Y'];

    order.forEach(key => {
        if (!perfData[key]) return;
        const item = perfData[key];
        const change = item.change * 100;
        const isUp = change >= 0;

        const el = document.createElement('div');
        el.className = 'perf-item';
        el.id = `perf-${key}`;
        el.innerHTML = `
            <span class="perf-label">${labels[key] || key}</span>
            <span class="perf-value ${isUp ? 'perf-up' : 'perf-down'}">${isUp ? '+' : ''}${change.toFixed(2)}%</span>
        `;
        container.appendChild(el);
    });
}

/**
 * Scans the overall market and populates the recommendations section
 */
async function loadRecommendations() {
    const btn = document.getElementById('loadRecommendations');
    const list = document.getElementById('recommendationsList');

    btn.disabled = true;
    btn.textContent = 'סורק שוק...';
    list.innerHTML = `
        <div class="scanning-message">
            <div class="spinner"></div>
            <p>מבצע סריקת שוק עמוקה וניתוח טכני/פונדמנטלי... (זה עשוי לקחת רגע)</p>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE_URL}/recommendations`);
        const data = await response.json();

        if (data.error) {
            list.innerHTML = `<p class="error-text">שגיאה: ${data.error}</p>`;
            return;
        }

        let html = `
            <div class="scan-info">
                <p>✅ נסרקו <strong>${data.market_scanned}</strong> מניות מובילות | נותחו בהצלחה <strong>${data.total_analyzed}</strong></p>
            </div>
        `;

        // Section: Short Term
        html += '<div class="term-section short-term-section">';
        html += '<h2 class="term-title">⚡ הזדמנויות לטווח קצר</h2>';

        if (data.short_term.hot_picks.length > 0) {
            html += '<div class="rec-category"><h3 class="category-title">🔥 המלצות חמות</h3><div class="rec-grid">';
            data.short_term.hot_picks.forEach(rec => html += createRecCard(rec, 'short'));
            html += '</div></div>';
        }

        if (data.short_term.safe_picks.length > 0) {
            html += '<div class="rec-category"><h3 class="category-title">🛡️ בחירות בטוחות</h3><div class="rec-grid">';
            data.short_term.safe_picks.forEach(rec => html += createRecCard(rec, 'short'));
            html += '</div></div>';
        }
        html += '</div>';

        // Section: Long Term
        html += '<div class="term-section long-term-section">';
        html += '<h2 class="term-title">🎯 השקעות לטווח ארוך</h2>';
        if (data.long_term.best_picks.length > 0) {
            html += '<div class="rec-category"><h3 class="category-title">🏆 מניות צמיחה/ערך</h3><div class="rec-grid">';
            data.long_term.best_picks.forEach(rec => html += createRecCard(rec, 'long'));
            html += '</div></div>';
        }
        html += '</div>';

        // Section: High Momentum
        if (data.high_momentum && data.high_momentum.length > 0) {
            html += '<div class="term-section momentum-section">';
            html += '<h2 class="term-title">🚀 מניות במומנטום חזק</h2><div class="rec-grid">';
            data.high_momentum.forEach(rec => html += createRecCard(rec, 'momentum'));
            html += '</div></div>';
        }

        list.innerHTML = html;
    } catch (error) {
        list.innerHTML = '<p class="error-text">שגיאה בתקשורת עם השרת בזמן סריקת שוק.</p>';
    } finally {
        btn.disabled = false;
        btn.textContent = 'רענן סריקת שוק';
    }
}

/**
 * Handles live price polling every 5 seconds
 */
function startLiveUpdates(symbol) {
    stopLiveUpdates();
    const priceElem = document.getElementById('currentPrice');
    const liveIndicator = document.getElementById('liveIndicator');

    if (liveIndicator) liveIndicator.style.display = 'inline-flex';

    priceInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/price/${symbol}`);
            const data = await response.json();
            if (data.error) return;

            const oldPrice = parseFloat(priceElem.textContent.replace('$', ''));
            const newPrice = data.price;
            priceElem.textContent = `$${newPrice.toFixed(2)}`;

            // Dynamic Performance Update
            if (perfBasePrices) {
                for (const [key, basePrice] of Object.entries(perfBasePrices)) {
                    if (!basePrice) continue;
                    const change = ((newPrice / basePrice) - 1) * 100;
                    const el = document.getElementById(`perf-${key}`);
                    if (el) {
                        const valEl = el.querySelector('.perf-value');
                        const isUp = change >= 0;
                        valEl.textContent = `${isUp ? '+' : ''}${change.toFixed(2)}%`;
                        valEl.className = `perf-value ${isUp ? 'perf-up' : 'perf-down'}`;
                    }
                }
            }

            // Visual feedback on price tick
            if (newPrice !== oldPrice) {
                const color = newPrice > oldPrice ? '#4ade80' : '#f87171';
                priceElem.style.color = color;
                priceElem.classList.add(newPrice > oldPrice ? 'price-up' : 'price-down');
                setTimeout(() => {
                    priceElem.style.color = '';
                    priceElem.classList.remove('price-up', 'price-down');
                }, 800);
            }
        } catch (e) { console.error('Live tick failed'); }
    }, 5000);
}

function stopLiveUpdates() {
    if (priceInterval) { clearInterval(priceInterval); priceInterval = null; }
    const liveIndicator = document.getElementById('liveIndicator');
    if (liveIndicator) liveIndicator.style.display = 'none';
}

/**
 * Renders the Chart.js line chart
 */
function renderChart(chartData) {
    const ctx = document.getElementById('priceChart');
    if (!ctx || !chartData || !chartData.dates) return;

    const labels = chartData.dates.map(d => new Date(d).toLocaleDateString('he-IL'));

    if (priceChart) priceChart.destroy();

    priceChart = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'מחיר',
                    data: chartData.prices,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 1
                },
                {
                    label: 'SMA 50',
                    data: chartData.sma_50,
                    borderColor: '#f59e0b',
                    borderWidth: 1.5,
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#e0e7ff', font: { size: 11 } } },
                tooltip: { mode: 'index', intersect: false }
            },
            scales: {
                y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
                x: { ticks: { color: '#94a3b8', maxRotation: 45, autoSkip: true, maxTicksLimit: 12 }, grid: { display: false } }
            }
        }
    });
}

// --- Helpers ---

function createRecCard(rec, type) {
    const recommendation = type === 'short' ? rec.short_term : rec.long_term;
    const badgeClass = getBadgeClass(recommendation);

    return `
        <div class="stock-rec-card ${type}-card" onclick="document.getElementById('stockSymbol').value='${rec.symbol}'; analyzeStock();">
            <div class="rec-card-header">
                <span class="rec-symbol">${rec.symbol}</span>
                <span class="rec-badge ${badgeClass}">${recommendation}</span>
            </div>
            <div class="rec-name">${rec.name}</div>
            <div class="rec-price">$${rec.price.toFixed(2)}</div>
            <div class="rec-stats-deep">
                <span>P/E: ${rec.pe !== 'N/A' ? Number(rec.pe).toFixed(1) : 'N/A'}</span>
                <span>RSI: ${Math.round(rec.rsi)}</span>
                ${rec.yield > 0 ? `<span>דיב': ${rec.yield.toFixed(1)}%</span>` : ''}
            </div>
            <div class="rec-meta">
                <span class="rec-trend">${rec.trend}</span>
                <span class="rec-risk ${getRiskClass(rec.risk)}">${rec.risk}</span>
            </div>
            <div class="rec-score-bar">
                <div class="score-fill" style="width: ${Math.min(100, (rec.score + 5) * 10)}%"></div>
                <span class="score-text">ציון עומק: ${rec.score.toFixed(1)}</span>
            </div>
        </div>
    `;
}

function getBadgeClass(rec) {
    if (!rec) return 'badge-neutral';
    const r = rec.toLowerCase();
    if (r.includes('strong buy')) return 'strong-buy';
    if (r.includes('buy')) return 'buy';
    if (r.includes('strong sell')) return 'strong-sell';
    if (r.includes('sell')) return 'sell';
    return 'hold';
}

function getRiskClass(risk) {
    if (!risk) return 'moderate';
    if (risk.includes('Low')) return 'low';
    if (risk.includes('High')) return 'high';
    return 'moderate';
}

function getStrategyClass(strategy) {
    if (!strategy) return 'badge-neutral';
    if (strategy.includes('DCA')) return 'badge-warning';
    if (strategy.includes('Lump Sum')) return 'badge-success';
    return 'badge-neutral';
}

function formatPrice(p) { return (p === undefined || p === null) ? 'N/A' : `$${p.toFixed(2)}`; }

function formatMarketCap(cap) {
    if (cap === 'N/A' || !cap) return 'N/A';
    const num = parseFloat(cap);
    if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    return `$${num.toFixed(2)}`;
}

function showLoading(s) { document.getElementById('loading').classList.toggle('hidden', !s); }
function showError(m) { const e = document.getElementById('errorMsg'); e.textContent = m; e.classList.remove('hidden'); }
function hideError() { document.getElementById('errorMsg').classList.add('hidden'); }
