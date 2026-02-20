import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page config
st.set_page_config(
    page_title="AI Stock Analyzer",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    }
    
    .main {
        background: linear-gradient(135deg, #306998 0%, #FFD43B 100%);
    }
    .stApp {
        background: linear-gradient(135deg, #306998 0%, #FFD43B 100%);
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 1rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
        font-family: 'JetBrains Mono', monospace;
    }
    .user-message {
        background-color: #306998;
        color: white;
        margin-left: 20%;
    }
    .assistant-message {
        background-color: white;
        color: #1f2937;
        margin-right: 20%;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stTextInput input {
        border-radius: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
    }
    .stButton button {
        border-radius: 0.75rem;
        background-color: #306998;
        color: white;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
    .stButton button:hover {
        background-color: #FFD43B;
        color: #306998;
    }
    .stats-container {
        background: white;
        border-radius: 1rem;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stat-box {
        background: linear-gradient(135deg, #306998 0%, #4B8BBE 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        margin: 0.5rem;
    }
    .stat-label {
        font-size: 0.75rem;
        opacity: 0.9;
        margin-bottom: 0.25rem;
    }
    .stat-value {
        font-size: 1.25rem;
        font-weight: 700;
    }
    .upgrade-banner {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.75rem;
        text-align: center;
        margin: 1rem 0;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "👋 Hi! I'm your AI stock analyzer.\n\n**Try asking me:**\n• Specific tickers: \"AAPL\", \"TSLA\", \"NVDA\"\n• General recommendations: \"What stocks should I buy today?\"\n• Market queries: \"What should I sell?\", \"Best stocks to hold?\"\n\nI'll analyze price trends, technical indicators, and provide clear buy/hold/sell recommendations!"
        }
    ]

if 'total_analyses' not in st.session_state:
    st.session_state.total_analyses = 0

if 'buy_count' not in st.session_state:
    st.session_state.buy_count = 0

if 'hold_count' not in st.session_state:
    st.session_state.hold_count = 0

if 'sell_count' not in st.session_state:
    st.session_state.sell_count = 0

if 'last_ticker' not in st.session_state:
    st.session_state.last_ticker = "N/A"

if 'current_stock_data' not in st.session_state:
    st.session_state.current_stock_data = None

if 'current_recommendation' not in st.session_state:
    st.session_state.current_recommendation = None

if 'email_captured' not in st.session_state:
    st.session_state.email_captured = False

if 'free_analyses_used' not in st.session_state:
    st.session_state.free_analyses_used = 0

# ====== SUBSCRIPTION TIER SYSTEM ======
if 'subscription_tier' not in st.session_state:
    # Check URL parameters for subscription info
    query_params = st.query_params
    if 'subscription' in query_params and query_params['subscription'] == 'success':
        plan = query_params.get('plan', 'free')
        st.session_state.subscription_tier = plan
    else:
        st.session_state.subscription_tier = 'free'

if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# Subscription tier limits
TIER_LIMITS = {
    'free': {
        'daily_analyses': 5,
        'charts': False,
        'alerts': False,
        'portfolio': False,
        'advanced_indicators': False,
        'general_recommendations': False,
    },
    'pro': {
        'daily_analyses': float('inf'),
        'charts': True,
        'alerts': True,
        'portfolio': True,
        'advanced_indicators': True,
        'general_recommendations': True,
    },
    'premium': {
        'daily_analyses': float('inf'),
        'charts': True,
        'alerts': True,
        'portfolio': True,
        'advanced_indicators': True,
        'general_recommendations': True,
        'predictions': True,
        'backtesting': True,
        'api_access': True,
    }
}

def check_feature_access(feature):
    """Check if user has access to a feature based on their tier"""
    tier = st.session_state.subscription_tier
    return TIER_LIMITS[tier].get(feature, False)

def check_analysis_limit():
    """Check if user has remaining analyses for the day"""
    tier = st.session_state.subscription_tier
    limit = TIER_LIMITS[tier]['daily_analyses']
    
    if limit == float('inf'):
        return True
    
    return st.session_state.free_analyses_used < limit

def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index"""
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def create_stock_chart(stock_data):
    """Create interactive candlestick chart with volume"""
    hist = stock_data['hist_dataframe']
    
    # Create subplots: 2 rows - price chart and volume chart
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f'{stock_data["ticker"]} Price Chart', 'Volume'),
        row_heights=[0.7, 0.3]
    )
    
    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            name='Price',
            increasing_line_color='#10b981',
            decreasing_line_color='#ef4444'
        ),
        row=1, col=1
    )
    
    # Add 20-day SMA
    sma_20_series = hist['Close'].rolling(window=20).mean()
    fig.add_trace(
        go.Scatter(
            x=hist.index,
            y=sma_20_series,
            name='20-day SMA',
            line=dict(color='#3b82f6', width=2)
        ),
        row=1, col=1
    )
    
    # Add 50-day SMA
    sma_50_series = hist['Close'].rolling(window=50).mean()
    fig.add_trace(
        go.Scatter(
            x=hist.index,
            y=sma_50_series,
            name='50-day SMA',
            line=dict(color='#f59e0b', width=2)
        ),
        row=1, col=1
    )
    
    # Volume bars
    colors = ['#10b981' if hist['Close'].iloc[i] >= hist['Open'].iloc[i] else '#ef4444' 
              for i in range(len(hist))]
    
    fig.add_trace(
        go.Bar(
            x=hist.index,
            y=hist['Volume'],
            name='Volume',
            marker_color=colors,
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        title=f'{stock_data["ticker"]} - 3 Month Chart',
        yaxis_title='Price ($)',
        yaxis2_title='Volume',
        xaxis_rangeslider_visible=False,
        height=700,
        template='plotly_white',
        hovermode='x unified',
        font=dict(family='JetBrains Mono, monospace')
    )
    
    # Update y-axes
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    return fig

def get_stock_data(ticker):
    """Fetch stock data using yfinance library"""
    try:
        import yfinance as yf
        
        # Get stock data
        stock = yf.Ticker(ticker)
        
        # Get historical data (3 months)
        hist = stock.history(period="3mo")
        
        if hist.empty:
            raise ValueError("Invalid ticker or no data available")
        
        # Get current info
        info = stock.info
        
        # Extract price data
        close_prices = hist['Close'].tolist()
        volumes = hist['Volume'].tolist()
        
        current_price = close_prices[-1]
        previous_close = close_prices[-2] if len(close_prices) > 1 else current_price
        change_percent = ((current_price - previous_close) / previous_close * 100)
        
        # Calculate technical indicators
        sma_20 = sum(close_prices[-20:]) / 20 if len(close_prices) >= 20 else sum(close_prices) / len(close_prices)
        sma_50 = sum(close_prices[-50:]) / 50 if len(close_prices) >= 50 else sum(close_prices) / len(close_prices)
        rsi = calculate_rsi(close_prices)
        
        # Volume analysis
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        current_volume = volumes[-1]
        volume_trend = ((current_volume - avg_volume) / avg_volume * 100)
        
        return {
            'ticker': ticker.upper(),
            'current_price': round(current_price, 2),
            'change_percent': round(change_percent, 2),
            'volume': int(current_volume),
            'avg_volume': int(avg_volume),
            'volume_trend': round(volume_trend, 2),
            'sma_20': round(sma_20, 2),
            'sma_50': round(sma_50, 2),
            'rsi': round(rsi, 2),
            'high_52week': round(info.get('fiftyTwoWeekHigh', 0), 2) if info.get('fiftyTwoWeekHigh') else 0,
            'low_52week': round(info.get('fiftyTwoWeekLow', 0), 2) if info.get('fiftyTwoWeekLow') else 0,
            'market_cap': round(info.get('marketCap', 0) / 1e9, 2) if info.get('marketCap') else 0,
            'price_history': [round(p, 2) for p in close_prices[-30:]],
            'hist_dataframe': hist  # Full dataframe for charts
        }
    except ImportError:
        raise Exception("Please install yfinance: pip install yfinance")
    except Exception as e:
        raise Exception(f"Error fetching data for {ticker.upper()}: {str(e)}")

def analyze_with_ai(stock_data):
    """Analyze stock data with rule-based technical analysis"""
    # Technical analysis signals
    signals = []
    score = 0
    
    # RSI Analysis
    if stock_data['rsi'] < 30:
        signals.append("🟢 RSI ({:.1f}) indicates oversold conditions - potential buying opportunity".format(stock_data['rsi']))
        score += 2
    elif stock_data['rsi'] > 70:
        signals.append("🔴 RSI ({:.1f}) indicates overbought conditions - consider taking profits".format(stock_data['rsi']))
        score -= 2
    else:
        signals.append("🟡 RSI ({:.1f}) is in neutral territory".format(stock_data['rsi']))
    
    # Moving Average Analysis
    if stock_data['current_price'] > stock_data['sma_20'] > stock_data['sma_50']:
        signals.append("🟢 Price (${:.2f}) is above both 20-day SMA (${:.2f}) and 50-day SMA (${:.2f}) - strong uptrend".format(
            stock_data['current_price'], stock_data['sma_20'], stock_data['sma_50']))
        score += 2
    elif stock_data['current_price'] < stock_data['sma_20'] < stock_data['sma_50']:
        signals.append("🔴 Price (${:.2f}) is below both moving averages - downtrend".format(stock_data['current_price']))
        score -= 2
    else:
        signals.append("🟡 Price is in a consolidation phase relative to moving averages")
    
    # Volume Analysis
    if stock_data['volume_trend'] > 20:
        signals.append("🟢 Volume is {:.1f}% above average - strong interest".format(stock_data['volume_trend']))
        score += 1
    elif stock_data['volume_trend'] < -20:
        signals.append("🔴 Volume is {:.1f}% below average - weak participation".format(abs(stock_data['volume_trend'])))
        score -= 1
    
    # Price momentum
    if stock_data['change_percent'] > 2:
        signals.append("🟢 Strong positive momentum today (+{:.2f}%)".format(stock_data['change_percent']))
        score += 1
    elif stock_data['change_percent'] < -2:
        signals.append("🔴 Negative momentum today ({:.2f}%)".format(stock_data['change_percent']))
        score -= 1
    
    # 52-week range position
    if stock_data['high_52week'] > 0:
        range_position = ((stock_data['current_price'] - stock_data['low_52week']) / 
                         (stock_data['high_52week'] - stock_data['low_52week']) * 100)
        if range_position > 80:
            signals.append("⚠️ Trading near 52-week high ({:.0f}% of range) - watch for resistance".format(range_position))
        elif range_position < 20:
            signals.append("🟢 Trading near 52-week low ({:.0f}% of range) - potential value".format(range_position))
    
    # Determine recommendation
    if score >= 3:
        recommendation = "**RECOMMENDATION: BUY** ✅"
        summary = "Multiple bullish signals align. Good entry opportunity for risk-tolerant investors."
    elif score <= -3:
        recommendation = "**RECOMMENDATION: SELL** ❌"
        summary = "Multiple bearish signals present. Consider reducing exposure or waiting for better entry."
    else:
        recommendation = "**RECOMMENDATION: HOLD** ⏸️"
        summary = "Mixed signals. Current position holders should maintain, new investors should wait for clearer direction."
    
    # Build analysis
    analysis = f"""**{stock_data['ticker']} Analysis**

{recommendation}

**Current Price:** ${stock_data['current_price']} ({stock_data['change_percent']:+.2f}% today)
**Market Cap:** ${stock_data['market_cap']}B

**Technical Signals:**
{chr(10).join('• ' + s for s in signals)}

**Summary:** {summary}

**Risk Factors:**
• Past performance doesn't guarantee future results
• Technical analysis should be combined with fundamental research
• Consider your risk tolerance and investment timeframe

**Disclaimer:** This is automated technical analysis, not financial advice. Always do your own research."""

    return analysis

def extract_ticker(text):
    """Extract stock ticker from user input"""
    import re
    # Look for common stock symbols (1-5 uppercase letters)
    match = re.search(r'\b[A-Z]{1,5}\b', text.upper())
    if match:
        return match.group(0)
    # If no match, try to clean the input
    cleaned = re.sub(r'[^A-Z]', '', text.upper())
    return cleaned if len(cleaned) <= 5 else None

# Header
st.title("📈 AI Stock Analyzer")
st.markdown("Real-time analysis with buy/hold/sell recommendations")

# Show subscription tier badge
tier = st.session_state.subscription_tier
tier_colors = {
    'free': '#6b7280',
    'pro': '#3b82f6',
    'premium': '#8b5cf6'
}
tier_display = tier.upper()
st.markdown(f'<div style="background: {tier_colors[tier]}; color: white; padding: 0.5rem 1rem; border-radius: 0.5rem; display: inline-block; font-weight: 600; margin-bottom: 1rem;">🎯 {tier_display} PLAN</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("📊 Stock Info")
    st.markdown("---")
    
    # If we have analyzed a stock, show its details
    if 'current_stock_data' in st.session_state and st.session_state.current_stock_data:
        data = st.session_state.current_stock_data
        
        st.markdown(f"### {data['ticker']}")
        
        # Recommendation section
        if 'current_recommendation' in st.session_state and st.session_state.current_recommendation:
            rec = st.session_state.current_recommendation
            st.markdown("#### 🎯 Recommendation")
            
            if rec == "BUY":
                st.markdown("""
                <div style='background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                            color: white; padding: 1.5rem; border-radius: 0.75rem; text-align: center;'>
                    <h1 style='margin: 0; font-size: 2.5rem;'>✅ BUY</h1>
                    <p style='margin: 0.5rem 0 0 0; opacity: 0.9;'>Strong bullish signals</p>
                </div>
                """, unsafe_allow_html=True)
            elif rec == "SELL":
                st.markdown("""
                <div style='background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); 
                            color: white; padding: 1.5rem; border-radius: 0.75rem; text-align: center;'>
                    <h1 style='margin: 0; font-size: 2.5rem;'>❌ SELL</h1>
                    <p style='margin: 0.5rem 0 0 0; opacity: 0.9;'>Bearish signals present</p>
                </div>
                """, unsafe_allow_html=True)
            else:  # HOLD
                st.markdown("""
                <div style='background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
                            color: white; padding: 1.5rem; border-radius: 0.75rem; text-align: center;'>
                    <h1 style='margin: 0; font-size: 2.5rem;'>⏸️ HOLD</h1>
                    <p style='margin: 0.5rem 0 0 0; opacity: 0.9;'>Mixed signals - wait</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
        
        # Interactive Chart (PRO+ only)
        if check_feature_access('charts'):
            st.markdown("#### 📊 Price Chart")
            chart = create_stock_chart(data)
            st.plotly_chart(chart, use_container_width=True)
            st.markdown("---")
        else:
            st.info("📊 **Interactive charts** available on Pro plan")
            st.markdown("---")
        
        # Price section
        st.markdown("#### 💰 Price")
        price_color = "green" if data['change_percent'] > 0 else "red"
        st.markdown(f"<h2 style='color: {price_color}; margin: 0;'>${data['current_price']}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {price_color}; margin: 0;'>{data['change_percent']:+.2f}% today</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Technical Indicators
        st.markdown("#### 📈 Technical Indicators")
        st.metric("RSI (14)", f"{data['rsi']:.2f}", 
                 delta="Oversold" if data['rsi'] < 30 else "Overbought" if data['rsi'] > 70 else "Neutral",
                 delta_color="normal")
        st.metric("20-Day SMA", f"${data['sma_20']:.2f}")
        st.metric("50-Day SMA", f"${data['sma_50']:.2f}")
        
        st.markdown("---")
        
        # Volume
        st.markdown("#### 📊 Volume")
        st.metric("Current Volume", f"{data['volume']:,}")
        st.metric("Avg Volume (20d)", f"{data['avg_volume']:,}")
        vol_color = "normal" if data['volume_trend'] > 0 else "inverse"
        st.metric("Volume Trend", f"{data['volume_trend']:+.1f}%", delta_color=vol_color)
        
        st.markdown("---")
        
        # 52-Week Range
        st.markdown("#### 📉 52-Week Range")
        if data['high_52week'] > 0:
            range_position = ((data['current_price'] - data['low_52week']) / 
                            (data['high_52week'] - data['low_52week']) * 100)
            st.progress(range_position / 100)
            st.markdown(f"**Low:** ${data['low_52week']:.2f}")
            st.markdown(f"**High:** ${data['high_52week']:.2f}")
            st.markdown(f"**Position:** {range_position:.1f}%")
        
        st.markdown("---")
        
        # Market Cap
        st.markdown("#### 💼 Market Cap")
        st.markdown(f"### ${data['market_cap']:.2f}B")
        
    else:
        st.info("👈 Analyze a stock to see detailed stats here!")
        
        st.markdown("---")
        st.markdown("#### 🔥 Popular Tickers")
        popular = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "AMD"]
        for ticker in popular:
            st.markdown(f"• {ticker}")
    
    st.markdown("---")
    
    # Upgrade CTA for free users
    if tier == 'free':
        st.markdown("#### 🚀 Upgrade to Pro")
        st.markdown("Unlock:")
        st.markdown("• ∞ Unlimited analyses")
        st.markdown("• 📊 Interactive charts")
        st.markdown("• 🔔 Price alerts")
        st.markdown("• 💼 Portfolio tracking")
        if st.button("Upgrade Now - 50% OFF!"):
            st.markdown("[Click here to upgrade](http://localhost:8000/landing.html#pricing)")
    
    st.markdown("---")
    st.markdown("#### ℹ️ About")
    st.markdown("This analyzer uses real-time market data and technical analysis to provide buy/hold/sell recommendations.")
    st.markdown("**Not financial advice.**")

# Quick Stats Display
st.markdown("""
<div class="stats-container">
    <div style="display: flex; justify-content: space-around; flex-wrap: wrap;">
        <div class="stat-box">
            <div class="stat-label">TOTAL ANALYSES</div>
            <div class="stat-value">{}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">BUY SIGNALS</div>
            <div class="stat-value">🟢 {}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">HOLD SIGNALS</div>
            <div class="stat-value">🟡 {}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">SELL SIGNALS</div>
            <div class="stat-value">🔴 {}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">LAST ANALYZED</div>
            <div class="stat-value">{}</div>
        </div>
    </div>
</div>
""".format(
    st.session_state.total_analyses,
    st.session_state.buy_count,
    st.session_state.hold_count,
    st.session_state.sell_count,
    st.session_state.last_ticker
), unsafe_allow_html=True)

st.markdown("---")

# Display chat messages
for message in st.session_state.messages:
    css_class = "user-message" if message["role"] == "user" else "assistant-message"
    st.markdown(
        f'<div class="chat-message {css_class}">{message["content"]}</div>',
        unsafe_allow_html=True
    )

# Email capture after first analysis
if not st.session_state.email_captured and st.session_state.free_analyses_used == 1:
    st.info("📧 **Enjoying the analyzer?** Enter your email to save your analysis history and get stock alerts!")
    with st.form("email_form"):
        email = st.text_input("Email address")
        submit = st.form_submit_button("Continue")
        if submit and email:
            st.session_state.email_captured = True
            st.session_state.user_email = email
            st.success("✅ Thanks! You're all set.")
            st.rerun()

# Upgrade prompt for free tier
if tier == 'free' and st.session_state.free_analyses_used >= 3:
    st.markdown("""
    <div class="upgrade-banner">
        ⚠️ You've used {}/{} free analyses today. Upgrade to Pro for unlimited analyses, charts, and more!
    </div>
    """.format(st.session_state.free_analyses_used, TIER_LIMITS['free']['daily_analyses']), unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Upgrade to Pro - 50% OFF", use_container_width=True):
            st.markdown("[Redirecting to checkout...](http://localhost:8000/checkout.html?plan=pro)")

# Chat input
with st.container():
    col1, col2 = st.columns([5, 1])
    
    with col1:
        user_input = st.text_input(
            "Enter stock ticker",
            placeholder="e.g., AAPL, TSLA, NVDA...",
            key="user_input",
            label_visibility="collapsed"
        )
    
    with col2:
        analyze_button = st.button("Analyze", use_container_width=True)

# Check if Enter was pressed (input changed and not empty)
if 'last_input' not in st.session_state:
    st.session_state.last_input = ""

enter_pressed = user_input and user_input != st.session_state.last_input

# Process user input
if (analyze_button or enter_pressed) and user_input:
    # Check analysis limit for free tier
    if not check_analysis_limit():
        st.error(f"⚠️ You've reached your daily limit of {TIER_LIMITS['free']['daily_analyses']} analyses. Upgrade to Pro for unlimited access!")
        st.markdown("[Upgrade Now](http://localhost:8000/checkout.html?plan=pro)")
        st.stop()
    
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Update last input to prevent re-running
    st.session_state.last_input = user_input
    
    # Check if user is asking for general recommendations
    user_lower = user_input.lower()
    
    is_general_query = (
        "what" in user_lower and ("buy" in user_lower or "sell" in user_lower or "hold" in user_lower or "invest" in user_lower) or
        "recommend" in user_lower or
        "best stocks" in user_lower or
        "top stocks" in user_lower or
        "good stocks" in user_lower or
        "stocks to" in user_lower
    )
    
    if is_general_query:
        # Check if feature is available for user's tier
        if not check_feature_access('general_recommendations'):
            st.session_state.messages.append({
                "role": "assistant",
                "content": "🔒 **General stock recommendations** are a Pro feature!\n\nUpgrade to get AI-powered recommendations for the best stocks to buy, sell, or hold.\n\n[Upgrade to Pro →](http://localhost:8000/checkout.html?plan=pro)"
            })
            st.rerun()
        
        # Provide general recommendations based on query type
        with st.spinner("Analyzing top stocks and generating recommendations..."):
            try:
                # Determine recommendation type
                if "sell" in user_input.lower():
                    rec_type = "sell"
                    stocks_to_analyze = ["META", "TSLA", "NFLX", "COIN"]
                    intro = "Based on current market conditions, here are stocks showing bearish signals:"
                elif "hold" in user_input.lower():
                    rec_type = "hold"
                    stocks_to_analyze = ["MSFT", "GOOGL", "AMZN"]
                    intro = "Here are stocks in consolidation that may be good to hold:"
                else:  # buy or general
                    rec_type = "buy"
                    stocks_to_analyze = ["NVDA", "AAPL", "AMD", "MSFT"]
                    intro = "Based on current market analysis, here are stocks with bullish signals:"
                
                recommendations = []
                
                for ticker in stocks_to_analyze[:3]:  # Analyze top 3
                    try:
                        stock_data = get_stock_data(ticker)
                        analysis = analyze_with_ai(stock_data)
                        
                        # Extract recommendation
                        if "RECOMMENDATION: BUY" in analysis and rec_type == "buy":
                            recommendations.append(f"**{ticker}**: Buy signal - ${stock_data['current_price']} ({stock_data['change_percent']:+.2f}%)")
                        elif "RECOMMENDATION: SELL" in analysis and rec_type == "sell":
                            recommendations.append(f"**{ticker}**: Sell signal - ${stock_data['current_price']} ({stock_data['change_percent']:+.2f}%)")
                        elif "RECOMMENDATION: HOLD" in analysis and rec_type == "hold":
                            recommendations.append(f"**{ticker}**: Hold signal - ${stock_data['current_price']} ({stock_data['change_percent']:+.2f}%)")
                        
                        if len(recommendations) >= 3:
                            break
                            
                    except:
                        continue
                
                if recommendations:
                    response = f"{intro}\n\n" + "\n".join(recommendations)
                    response += "\n\n💡 *Type any ticker symbol to see detailed analysis with charts and full reasoning.*"
                else:
                    response = "I analyzed several stocks but couldn't find strong signals matching your criteria right now. Try asking for a specific stock ticker for detailed analysis!"
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })
                
            except Exception as e:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"⚠️ Unable to generate recommendations at this time. Try analyzing specific stock tickers instead!"
                })
        
        st.rerun()
    
    # Only extract ticker if NOT a general query
    else:
        # Extract ticker
        ticker = extract_ticker(user_input)
        
        if not ticker or len(ticker) > 5:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "⚠️ Please provide a valid stock ticker (e.g., AAPL, TSLA, MSFT) or ask for general recommendations like 'what stocks should I buy?'"
            })
            st.rerun()
        
        # Show loading message
        with st.spinner(f"Analyzing {ticker}... Fetching market data and generating recommendation..."):
            try:
                # Get stock data
                stock_data = get_stock_data(ticker)
                
                # Store in session state for sidebar
                st.session_state.current_stock_data = stock_data
                
                # Analyze with AI
                analysis = analyze_with_ai(stock_data)
                
                # Extract recommendation
                if "RECOMMENDATION: BUY" in analysis:
                    st.session_state.current_recommendation = "BUY"
                elif "RECOMMENDATION: SELL" in analysis:
                    st.session_state.current_recommendation = "SELL"
                elif "RECOMMENDATION: HOLD" in analysis:
                    st.session_state.current_recommendation = "HOLD"
                else:
                    st.session_state.current_recommendation = None
                
                # Update stats
                st.session_state.total_analyses += 1
                st.session_state.last_ticker = ticker.upper()
                st.session_state.free_analyses_used += 1
                
                # Count recommendation type
                if "BUY" in analysis and "RECOMMENDATION: BUY" in analysis:
                    st.session_state.buy_count += 1
                elif "SELL" in analysis and "RECOMMENDATION: SELL" in analysis:
                    st.session_state.sell_count += 1
                elif "HOLD" in analysis and "RECOMMENDATION: HOLD" in analysis:
                    st.session_state.hold_count += 1
                
                # Add assistant response
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": analysis
                })
                
            except Exception as e:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"⚠️ {str(e)}"
                })
        
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align: center; color: white; font-size: 0.8rem;">Powered by AI • Real-time market data • Not financial advice</p>',
    unsafe_allow_html=True
)