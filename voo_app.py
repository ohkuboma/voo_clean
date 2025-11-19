import pandas as pd
from statistics import mode
from datetime import datetime
import yfinance as yf
import streamlit as st

# ---- ページ設定 & ビルド時刻を表示（反映確認用） ----
st.set_page_config(page_title="VOO 30日分析", layout="wide")
st.title("VOO 30日分析アプリ")
st.caption(f"Build: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (ローカル/Cloud反映確認用)")

# ---- 軽いCSS（買値のテキストボックスを小さく目立たせない） ----
st.markdown(
    """
    <style>
    .buy-input > div > input {max-width: 120px;}
    .small-label {font-size: 12px; color: #777; margin-bottom: 4px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---- ユーティリティ ----
def _to_float_or_none(s: str):
    try:
        s = s.strip()
        if s == "":
            return None
        return float(s)
    except Exception:
        return None

# ---- データ取得 ----
def load_voo_data():
    ticker = yf.Ticker("VOO")
    df = ticker.history(period="2mo")
    if df.empty:
        st.error("VOOのデータが取得できませんでした。")
        st.stop()
    df = df.tail(30).reset_index()
    return df[["Date", "High", "Low", "Close"]]

# ---- 集計ロジック ----
def get_voo_high_low_modes(buy_price=None, manual_current_price=None):
    df = load_voo_data()
    highs = df["High"].round(2).tolist()
    lows = df["Low"].round(2).tolist()

    try:
        high_mode = mode(highs)
    except Exception:
        high_mode = max(set(highs), key=highs.count)

    try:
        low_mode = mode(lows)
    except Exception:
        low_mode = max(set(lows), key=lows.count)

    width_ratio = round((high_mode - low_mode) / low_mode * 100, 2)

    df["RangeRatio"] = ((df["High"] - df["Low"]) / df["Low"] * 100).round(2)
    min_row = df.loc[df["RangeRatio"].idxmin()]
    max_row = df.loc[df["RangeRatio"].idxmax()]

    current_price = manual_current_price if manual_current_price is not None else df.iloc[-1]["Close"]

    profit_percent = None
    tax_profit_percent = None
    if buy_price is not None and buy_price > 0:
        profit_percent = round((current_price - buy_price) / buy_price * 100, 2)
        # 日本の特定口座で米国ETF譲渡益課税（概ね 20.315%）→ 手取りは約 79.685%
        tax_profit_percent = round(profit_percent * 0.79685, 2)

    return {
        "most_frequent_high": round(high_mode, 2),
        "most_frequent_low": round(low_mode, 2),
        "width_ratio_percent": width_ratio,
        "min_range_day": min_row,
        "max_range_day": max_row,
        "current_price": round(float(current_price), 2),
        "buy_price": None if buy_price is None else round(float(buy_price), 2),
        "profit_percent": profit_percent,
        "tax_profit_percent": tax_profit_percent,
        "df": df,
    }

# ---- まず集計（最重要の上段を先に描画） ----
# 買値入力はこの後で反映させる（上段の邪魔をしない）
base_result = get_voo_high_low_modes(buy_price=None, manual_current_price=None)

# ---- 1行目：最重要指標（赤枠の位置） ----
r1c1, r1c2, r1c3 = st.columns(3)
r1c1.metric("高値（最頻）", base_result["most_frequent_high"])
r1c2.metric("安値（最頻）", base_result["most_frequent_low"])
r1c3.metric("値動き（率 %）", base_result["width_ratio_percent"])

# ---- 2行目：試算（買値・現在値・利率・税引後利率） ----
r2c1, r2c2, r2c3, r2c4 = st.columns(4)
with r2c1:
    st.markdown('<div class="small-label">買値</div>', unsafe_allow_html=True)
    buy_price_str = st.text_input(
        label="買値入力",
        value="",
        placeholder="例: 600",
        label_visibility="collapsed",
        key="buy_input",
    )
    # CSSで幅を絞る
    st.markdown("<div class='buy-input'></div>", unsafe_allow_html=True)

buy_price_val = _to_float_or_none(buy_price_str)

# 買値を反映して再計算（現在価格入力は撤去し、自動の終値を使用）
result = get_voo_high_low_modes(buy_price=buy_price_val, manual_current_price=None)

r2c1.metric("買値", "-" if result["buy_price"] is None else result["buy_price"])
r2c2.metric("現在価格", result["current_price"])
r2c3.metric("利率 (%)", "-" if result["profit_percent"] is None else result["profit_percent"])
r2c4.metric("税引後利率 (%)", "-" if result["tax_profit_percent"] is None else result["tax_profit_percent"])

st.caption("※ 税引後利率は米国ETFを特定口座で売買した場合（概算 20.315%）で計算しています。買値を入れると自動で計算されます。")

# ---- 以下、詳細テーブル ----
st.subheader("📉 値幅の割合が最も小さい日")
st.write(result["min_range_day"].to_frame().T)

st.subheader("📈 値幅の割合が最も大きい日")
st.write(result["max_range_day"].to_frame().T)

st.subheader("📋 30営業日のデータ一覧")
st.dataframe(result["df"], use_container_width=True)
