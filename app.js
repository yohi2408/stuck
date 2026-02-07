// API Configuration
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:5000/api'
    : '/api';

// Chart instance
let priceChart = null;
let priceInterval = null;
let perfBasePrices = {}; // שמירת מחירי בסיס לחישוב ביצועים בלייב

// DOM Elements - wait for DOM to load
document.addEventListener('DOMContentLoaded', function () {
    const stockSymbolInput = document.getElementById('stockSymbol');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loadRecommendationsBtn = document.getElementById('loadRecommendations');
    const quickBtns = document.querySelectorAll('.quick-btn');

    // Event Listeners
    analyzeBtn.addEventListener('click', analyzeStock);
    stockSymbolInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') analyzeStock();
    });

    loadRecommendationsBtn.addEventListener('click', loadRecommendations);

    quickBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            stockSymbolInput.value = btn.dataset.symbol;
            analyzeStock();
        });
    });
});

// Analyze Stock
async function analyzeStock() {
    const symbol = document.getElementById('stockSymbol').value.trim().toUpperCase();

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

// Display Stock Data
function displayStockData(data) {
    console.log('Received data:', data); // Debug

    // Show dashboard
    document.getElementById('dashboard').classList.remove('hidden');

    // Stock header
    document.getElementById('stockName').textContent = data.recommendation.company_name;
    document.getElementById('stockSymbolDisplay').textContent = data.recommendation.symbol;
    // המחיר יעודכן בהמשך מתוך price_data באופן בטוח

    // ניתוח מפורט בעברית
    const detailedAnalysisElem = document.getElementById('detailedAnalysis');
    if (detailedAnalysisElem && data.recommendation.detailed_analysis_he) {
        detailedAnalysisElem.innerHTML = data.recommendation.detailed_analysis_he
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
            .replace(/\n/g, '<br>'); // Line breaks
        detailedAnalysisElem.style.display = 'block';
    }

    // Recommendations
    const shortTerm = data.recommendation.short_term || 'N/A';
    const longTerm = data.recommendation.long_term || 'N/A';

    document.getElementById('shortTermRec').textContent = shortTerm;
    document.getElementById('shortTermRec').className = `rec-badge ${getBadgeClass(shortTerm)}`;
    document.getElementById('shortTermConf').textContent = `ביטחון: ${data.recommendation.short_term_confidence || 'N/A'}`;

    document.getElementById('longTermRec').textContent = longTerm;
    document.getElementById('longTermRec').className = `rec-badge ${getBadgeClass(longTerm)}`;

    // Risk
    document.getElementById('riskLevel').textContent = data.risk.level;
    document.getElementById('riskLevel').className = `risk-badge ${getRiskClass(data.risk.level)}`;
    document.getElementById('riskDetails').innerHTML = `
        <p>תנודתיות: ${data.risk.volatility}</p>
        <p>Beta: ${data.risk.beta || 'N/A'}</p>
        <p>ציון סיכון: ${data.risk.score}/5</p>
    `;

    // Technical Analysis
    document.getElementById('trend').textContent = data.technical.trend;
    document.getElementById('momentum').textContent = data.technical.momentum;

    // Fundamental Analysis
    document.getElementById('peRatio').textContent = data.fundamental.pe_rating;
    document.getElementById('marketCap').textContent = formatMarketCap(data.overview.market_cap);
    document.getElementById('beta').textContent = data.overview.beta || 'N/A';

    // Price display
    const price = data.price_data.current_price;
    const change = data.price_data.change_percent || 0; // Fix: use change_percent
    const volume = data.price_data.volume;

    document.getElementById('currentPrice').textContent = formatPrice(price);

    // Color code change
    const changeEl = document.getElementById('priceChange');
    changeEl.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
    changeEl.className = `price-change ${change >= 0 ? 'positive' : 'negative'}`;

    // Price Stats - using price_data object
    if (data.price_data) {
        const change30d = data.price_data.change_30d || 0;
        document.getElementById('change30d').textContent = `${change30d.toFixed(2)}%`;
        document.getElementById('change30d').className = `metric-value ${change30d >= 0 ? 'positive' : 'negative'}`;

        document.getElementById('high52w').textContent = `$${data.price_data.high_52w.toFixed(2)}`;
        document.getElementById('low52w').textContent = `$${data.price_data.low_52w.toFixed(2)}`;
    }

    // Explanation (Optional now)
    const explanationEl = document.getElementById('explanation');
    if (explanationEl) {
        explanationEl.textContent = data.recommendation.explanation;
    }

    // Performance Bar
    if (data.performance) {
        perfBasePrices = {}; // Reset
        // שמירת מחירי הבסיס לחישובים חיים
        for (const [key, val] of Object.entries(data.performance)) {
            perfBasePrices[key] = val.base;
        }
        renderPerformance(data.performance);
    }

    // Investment Strategy (NEW)
    if (data.investment_strategy) {
        console.log("Rendering Strategy:", data.investment_strategy);
        const strat = data.investment_strategy;

        const stratEl = document.getElementById('strategyType');
        if (stratEl) {
            stratEl.textContent = strat.strategy;
            stratEl.className = `strategy-badge ${getStrategyClass(strat.strategy)}`;
        }

        const textEl = document.getElementById('strategyText');
        if (textEl) {
            // Use innerHTML to support bold and line breaks from new python logic
            textEl.innerHTML = strat.recommendation_he.replace(/\n/g, '<br>');
        }

        const volEl = document.getElementById('volatilityValue');
        if (volEl) volEl.textContent = `${strat.volatility}% (יומי)`;
    } else {
        console.error("Missing investment_strategy in API response");
    }

    // Stock News (NEW)
    const newsGrid = document.getElementById('newsGrid');
    if (data.news && data.news.length > 0) {
        newsGrid.innerHTML = data.news.map(item => `
            <div class="news-item">
                <div class="news-meta">
                    <span>${item.publisher}</span>
                    <span>${item.published}</span>
                </div>
                <div class="news-title">${item.title}</div>
                <a href="${item.link}" target="_blank" class="news-link">קרא עוד ↗</a>
            </div>
        `).join('');
    } else {
        newsGrid.innerHTML = '<p style="color: #94a3b8; grid-column: 1/-1; text-align: center;">לא נמצאו חדשות אחרונות</p>';
    }

    // Chart - using chart_data!
    console.log('Chart data:', data.chart_data); // Debug
    renderChart(data.chart_data);

    // התחל עדכונים חיים
    startLiveUpdates(data.recommendation.symbol);
}

function getStrategyClass(strategy) {
    if (strategy.includes('DCA')) return 'badge-warning';
    if (strategy.includes('Lump Sum')) return 'badge-success';
    return 'badge-neutral';
}

function renderPerformance(perfData) {
    const container = document.getElementById('performanceBar');
    if (!container) return;

    container.innerHTML = ''; // Clear

    const labels = {
        '1D': 'יום',
        '5D': '5 ימים',
        '1M': 'חודש',
        '6M': '6 חוד',
        'YTD': 'YTD',
        '1Y': 'שנה',
        '5Y': '5 שנים'
    };

    // סדר תצוגה
    const order = ['1D', '5D', '1M', '6M', 'YTD', '1Y', '5Y'];

    order.forEach(key => {
        if (!perfData[key]) return;

        const item = perfData[key];
        const change = item.change * 100;
        const isUp = change >= 0;
        const colorClass = isUp ? 'perf-up' : 'perf-down';
        const sign = isUp ? '+' : '';

        const el = document.createElement('div');
        el.className = 'perf-item';
        el.id = `perf-${key}`; // ID לעדכון
        el.innerHTML = `
            <span class="perf-label">${labels[key] || key}</span>
            <span class="perf-value ${colorClass}">${sign}${change.toFixed(2)}%</span>
        `;
        container.appendChild(el);
    });
}

// Load Top Recommendations
async function loadRecommendations() {
    const btn = document.getElementById('loadRecommendations');
    const list = document.getElementById('recommendationsList');

    btn.disabled = true;
    btn.textContent = 'סורק שוק...';
    list.innerHTML = '<div class="scanning-message"><div class="spinner"></div><p>סורק את השוק ומנתח מניות... זה יקח 2-3 דקות</p></div>';

    try {
        const response = await fetch(`${API_BASE_URL}/recommendations`);
        const data = await response.json();

        if (data.error) {
            list.innerHTML = `<p class="error-text">שגיאה: ${data.error}</p>`;
            return;
        }

        let html = `
            <div class="scan-info">
                <p>✅ נסרקו <strong>${data.market_scanned}</strong> מניות מ-S&P 500 | נותחו בהצלחה <strong>${data.total_analyzed}</strong> מניות</p>
            </div>
        `;

        // טווח קצר
        html += '<div class="term-section short-term-section">';
        html += '<h2 class="term-title">⚡ טווח קצר (1-3 חודשים)</h2>';

        // המלצות חמות
        if (data.short_term.hot_picks.length > 0) {
            html += '<div class="rec-category">';
            html += '<h3 class="category-title">🔥 המלצות חמות - הזדמנויות קנייה</h3>';
            html += '<div class="rec-grid">';
            data.short_term.hot_picks.forEach(rec => {
                html += createRecCard(rec, 'short');
            });
            html += '</div></div>';
        }

        // בטוחות לטווח קצר
        if (data.short_term.safe_picks.length > 0) {
            html += '<div class="rec-category">';
            html += '<h3 class="category-title">🛡️ בטוחות לטווח קצר (סיכון נמוך)</h3>';
            html += '<div class="rec-grid">';
            data.short_term.safe_picks.forEach(rec => {
                html += createRecCard(rec, 'short');
            });
            html += '</div></div>';
        }

        html += '</div>'; // End short-term section

        // טווח ארוך
        html += '<div class="term-section long-term-section">';
        html += '<h2 class="term-title">🎯 טווח ארוך (6-12 חודשים)</h2>';

        // המלצות מובילות
        if (data.long_term.best_picks.length > 0) {
            html += '<div class="rec-category">';
            html += '<h3 class="category-title">🏆 המלצות מובילות - להשקעה ארוכת טווח</h3>';
            html += '<div class="rec-grid">';
            data.long_term.best_picks.forEach(rec => {
                html += createRecCard(rec, 'long');
            });
            html += '</div></div>';
        }

        // יציבות לטווח ארוך
        if (data.long_term.stable_picks.length > 0) {
            html += '<div class="rec-category">';
            html += '<h3 class="category-title">💎 יציבות ארוכת טווח (סיכון נמוך)</h3>';
            html += '<div class="rec-grid">';
            data.long_term.stable_picks.forEach(rec => {
                html += createRecCard(rec, 'long');
            });
            html += '</div></div>';
        }

        html += '</div>'; // End long-term section

        // מומנטום גבוה
        if (data.high_momentum && data.high_momentum.length > 0) {
            html += '<div class="term-section momentum-section">';
            html += '<h2 class="term-title">🚀 פוטנציאל גבוה (מומנטום חזק)</h2>';
            html += '<div class="rec-grid">';
            data.high_momentum.forEach(rec => {
                html += createRecCard(rec, 'momentum');
            });
            html += '</div></div>';
        }

        list.innerHTML = html;
    } catch (error) {
        list.innerHTML = '<p class="error-text">שגיאה בטעינת המלצות. ודא שהשרת רץ.</p>';
        console.error('Error:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = 'רענן סריקת שוק';
    }
}

// עצירת עדכונים חיים
function stopLiveUpdates() {
    if (priceInterval) {
        clearInterval(priceInterval);
        priceInterval = null;
    }
    if (liveIndicator) {
        liveIndicator.style.display = 'none';
    }
}

// Start Live Updates
function startLiveUpdates(symbol) {
    stopLiveUpdates(); // Clear existing

    const priceElem = document.getElementById('currentPrice');
    const liveIndicator = document.getElementById('liveIndicator');

    // Show indicator
    if (liveIndicator) liveIndicator.style.display = 'inline-flex';

    priceInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/price/${symbol}`);
            const data = await response.json();

            if (data.error) return;

            // עדכון מחיר
            const oldPrice = parseFloat(priceElem.textContent.replace('$', ''));
            const newPrice = data.price;

            priceElem.textContent = `$${newPrice.toFixed(2)}`;

            // עדכון סרגל הביצועים בזמן אמת
            if (perfBasePrices && Object.keys(perfBasePrices).length > 0) {
                for (const [key, basePrice] of Object.entries(perfBasePrices)) {
                    if (!basePrice) continue;

                    const change = ((newPrice / basePrice) - 1) * 100;
                    const el = document.getElementById(`perf-${key}`);
                    if (el) {
                        const valEl = el.querySelector('.perf-value');
                        const isUp = change >= 0;
                        const sign = isUp ? '+' : '';

                        valEl.textContent = `${sign}${change.toFixed(2)}%`;
                        valEl.className = `perf-value ${isUp ? 'perf-up' : 'perf-down'}`;
                    }
                }
            }

            // אפקט הבהוב בעדכון מחיר
            if (newPrice > oldPrice) {
                priceElem.style.color = '#4ade80'; // ירוק
                priceElem.classList.add('price-up');
            } else if (newPrice < oldPrice) {
                priceElem.style.color = '#f87171'; // אדום
                priceElem.classList.add('price-down');
            }

            setTimeout(() => {
                priceElem.style.color = '';
                priceElem.classList.remove('price-up', 'price-down');
            }, 1000); // הסר אפקט אחרי שנייה

        } catch (error) {
            console.error('Live update failed:', error);
        }
    }, 5000); // עדכון כל 5 שניות
}

// הוסף אינדיקטור LIVE
const liveIndicator = document.getElementById('liveIndicator');
if (liveIndicator) {
    liveIndicator.style.display = 'inline-flex';
    console.log('Live indicator visible'); // Debug
}

// פונקציית העדכון סריקת שוק
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
            <div class="rec-meta">
                <span class="rec-trend">${rec.trend}</span>
                <span class="rec-risk ${getRiskClass(rec.risk)}">${rec.risk}</span>
            </div>
            <div class="rec-score-bar">
                <div class="score-fill" style="width: ${Math.min(100, (rec.score + 5) * 10)}%"></div>
                <span class="score-text">ציון: ${rec.score.toFixed(1)}</span>
            </div>
        </div>
    `;
}

// Render Chart - FIXED VERSION!
function renderChart(chartData) {
    console.log('renderChart called with:', chartData);

    if (!chartData || !chartData.dates || chartData.dates.length === 0) {
        console.error("No chart data available");
        return;
    }

    const ctx = document.getElementById('priceChart');
    if (!ctx) {
        console.error("Chart canvas not found");
        return;
    }

    // Use the data directly from chart_data
    const labels = chartData.dates.map(d => new Date(d).toLocaleDateString('he-IL'));
    const prices = chartData.prices;
    const sma20 = chartData.sma_20;
    const sma50 = chartData.sma_50;

    console.log('Chart labels:', labels.length);
    console.log('Chart prices:', prices.length);

    if (priceChart) {
        priceChart.destroy();
    }

    priceChart = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'מחיר',
                    data: prices,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'SMA 20',
                    data: sma20,
                    borderColor: '#10b981',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'SMA 50',
                    data: sma50,
                    borderColor: '#f59e0b',
                    borderWidth: 2,
                    borderDash: [10, 5],
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: '#e0e7ff',
                        font: { size: 12 }
                    }
                }
            },
            scales: {
                y: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                x: {
                    ticks: { color: '#94a3b8', maxRotation: 45 },
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                }
            }
        }
    });

    console.log('Chart created successfully');
}

// Helper Functions
function formatPrice(price) {
    if (price === undefined || price === null) return 'N/A';
    return `$${price.toFixed(2)}`;
}

function getBadgeClass(recommendation) {
    if (!recommendation) return 'badge-neutral'; // Added null check
    if (recommendation.includes('Strong Buy')) return 'badge-strong-buy'; // Changed to specific class
    if (recommendation.includes('Buy')) return 'badge-buy'; // Changed to specific class
    if (recommendation.includes('Hold')) return 'badge-warning';
    if (recommendation.includes('Sell') || recommendation.includes('Avoid')) return 'badge-danger';
    return 'badge-neutral';
}

function getRiskClass(risk) {
    if (risk.includes('Low')) return 'low';
    if (risk.includes('Moderate')) return 'moderate';
    return 'high';
}

function formatMarketCap(cap) {
    if (cap === 'N/A' || !cap) return 'N/A';
    const num = parseFloat(cap);
    if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    return `$${num.toFixed(2)}`;
}

function showLoading(show) {
    document.getElementById('loading').classList.toggle('hidden', !show);
}

function showError(message) {
    const errorMsg = document.getElementById('errorMsg');
    errorMsg.textContent = message;
    errorMsg.classList.remove('hidden');
}

function hideError() {
    document.getElementById('errorMsg').classList.add('hidden');
}
