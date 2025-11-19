import pandas as pd
from statistics import mode
from datetime import datetime
import yfinance as yf
import streamlit as st

# ---- ページ設定 & ビルド時刻を表示（反映確認用） ----
st.set_page_config(page_title="VOO 分析", layout="wide")

st.caption(f"Build: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (ローカル/Cloud反映確認用)")

# ---- 軽いCSS（買値のテキストボックスを小さく目立たせない） ----
st.markdown(
    """
    <style>
    .buy-input > div > input {max-width: 120px;}
    .small-label {font-size: 12px; color: #777; margin-bottom: 4px;}
    div[data-baseweb="input"] { margin-bottom: 4px; }

    /* === 共通：モバイル最適化（横スクロール・固定） === */
    .sticky-row { background: var(--background-color, #FFFFFF); }
    .sticky-row .scroll-x { overflow-x: auto; -webkit-overflow-scrolling: touch; }
    .sticky-row .scroll-x > div[data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: repeat(4, minmax(140px, 1fr));
        column-gap: 12px; align-items: start;
    }

    @media (max-width: 640px) {
      #sticky-head { position: sticky; top: 0; z-index: 1000; background: var(--background-color, #FFFFFF); padding: 4px 0; box-shadow: 0 1px 0 rgba(0,0,0,0.04); }
      #top-row-1 { position: sticky; top: 56px; z-index: 999; padding: 6px 0; box-shadow: 0 1px 0 rgba(0,0,0,0.03); }
      #top-row-2 { position: sticky; top: 118px; z-index: 998; padding: 6px 0; box-shadow: 0 1px 0 rgba(0,0,0,0.02); }
      .sticky-row .scroll-x > div[data-testid="stHorizontalBlock"] { min-width: 560px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---- 期間選択（プルダウン） ----
PERIOD_OPTIONS = {
    "1週間": "7d",
    "1か月": "1mo",
    "3か月": "3mo",
    "6か月": "6mo",
    "1年": "1y",
    "5年": "5y",
}

# 期間セレクタは控えめに左上に表示
sel_col1, sel_col2 = st.columns([1, 3])
with sel_col1:
    period_label = st.selectbox("期間", list(PERIOD_OPTIONS.keys()), index=1)
with sel_col2:
    st.empty()

# タイトルは選択期間に合わせて変更
# タイトルをHTMLで出してスマホ時にsticky化
st.markdown(f"<div id='sticky-head'><h1>VOO {period_label} 分析アプリ</h1></div>", unsafe_allow_html=True)

# ---- ユーティリティ ----
def _to_float_or_none(s: str):
    try:
        s = s.strip()
        if s == "":
            return None
        return float(s)
    except Exception:
        return None

# 表示用フォーマッタ
def fnum(x, digits: int = 2):
    if x is None:
        return "-"
    try:
        return f"{float(x):,.{digits}f}"
    except Exception:
        return "-"

def fpct(p, digits: int = 2):
    if p is None:
        return "-"
    try:
        return f"{float(p):.{digits}f}%"
    except Exception:
        return "-"

def fpct_delta(p, digits: int = 2):
    if p is None:
        return None
    try:
        val = float(p)
        sign = "+" if val > 0 else ""  # st.metric は符号付きが色分けされる
        return f"{sign}{val:.{digits}f}%"
    except Exception:
        return None

# ---- データ取得 ----
def load_voo_data(yf_period: str):
    ticker = yf.Ticker("VOO")
    # 期間はセレクタから渡す。日足で取得
    df = ticker.history(period=yf_period, interval="1d")
    if df.empty:
        st.error("VOOのデータが取得できませんでした。")
        st.stop()
    df = df.reset_index()
    return df[["Date", "High", "Low", "Close"]]

# ---- 集計ロジック ----
def get_voo_high_low_modes(yf_period: str, buy_price=None, manual_current_price=None):
    df = load_voo_data(yf_period)
    hs = df["High"].astype(float)
    ls = df["Low"].astype(float)

    # 箱ひげ図の太い部分(IQR)で代表値を出す
    h_q1, h_q3 = hs.quantile(0.25), hs.quantile(0.75)
    l_q1, l_q3 = ls.quantile(0.25), ls.quantile(0.75)

    high_rep = round(h_q3, 2)  # High: 箱の上端(Q3)
    low_rep  = round(l_q1, 2)  # Low : 箱の下端(Q1)

    # 万一の逆転を防止
    if low_rep > high_rep:
        mid = round((low_rep + high_rep) / 2, 2)
        low_rep, high_rep = mid, mid

    width_ratio = round((high_rep - low_rep) / low_rep * 100, 2) if low_rep != 0 else 0.0

    # 参考: 日別の値幅比で最小/最大日
    df["RangeRatio"] = ((df["High"] - df["Low"]) / df["Low"] * 100).round(2)
    min_row = df.loc[df["RangeRatio"].idxmin()]
    max_row = df.loc[df["RangeRatio"].idxmax()]

    current_price = manual_current_price if manual_current_price is not None else float(df.iloc[-1]["Close"])

    profit_percent = None
    tax_profit_percent = None
    if buy_price is not None and buy_price > 0:
        profit_percent = round((current_price - buy_price) / buy_price * 100, 2)
        tax_profit_percent = round(profit_percent * 0.79685, 2)

    return {
        "most_frequent_high": high_rep,
        "most_frequent_low": low_rep,
        "width_ratio_percent": width_ratio,
        "min_range_day": min_row,
        "max_range_day": max_row,
        "current_price": round(float(current_price), 2),
        "buy_price": None if buy_price is None else round(float(buy_price), 2),
        "profit_percent": profit_percent,
        "tax_profit_percent": tax_profit_percent,
        "df": df,
    }

# ---- 最重要の上段を先に描画（選択期間で集計） ----
yf_period = PERIOD_OPTIONS[period_label]
base_result = get_voo_high_low_modes(yf_period=yf_period, buy_price=None, manual_current_price=None)

# ---- 1行目：最重要指標（2行目と列幅を合わせて上下を揃える：4列に統一） ----
st.markdown('<div class="sticky-row" id="top-row-1"><div class="scroll-x">', unsafe_allow_html=True)
r1c1, r1c2, r1c3, r1c4 = st.columns([1, 1, 1, 1])
r1c1.metric("高値（最頻）", fnum(base_result["most_frequent_high"]))
r1c2.metric("安値（最頻）", fnum(base_result["most_frequent_low"]))
r1c3.metric("値動き（率）", fpct(base_result["width_ratio_percent"]))
# 4列目はダミー（2行目の税引後利率に列位置を合わせるためのスペーサ）
r1c4.write("")
st.markdown('</div></div>', unsafe_allow_html=True)

# ---- 2行目：試算（買値・現在値・利率・税引後利率） ----
st.markdown('<div class="sticky-row" id="top-row-2"><div class="scroll-x">', unsafe_allow_html=True)
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
    st.markdown("<div class='buy-input'></div>", unsafe_allow_html=True)

buy_price_val = _to_float_or_none(buy_price_str)

# 買値を反映して再計算（現在価格入力は撤去し、自動の終値を使用）
result = get_voo_high_low_modes(yf_period=yf_period, buy_price=buy_price_val, manual_current_price=None)

r2c1.metric("買値", fnum(result["buy_price"]))
r2c2.metric("現在価格", fnum(result["current_price"]))
r2c3.metric("利率", fpct(result["profit_percent"]), delta=fpct_delta(result["profit_percent"]))
r2c4.metric("税引後利率", fpct(result["tax_profit_percent"]), delta=fpct_delta(result["tax_profit_percent"]))

st.caption("※ 税引後利率は米国ETFを特定口座で売買した場合（概算 20.315%）で計算しています。買値を入れると自動で計算されます。")

# ---- 以下、詳細テーブル ----
st.subheader("📉 値幅の割合が最も小さい日")
st.write(result["min_range_day"].to_frame().T)

st.subheader("📈 値幅の割合が最も大きい日")
st.write(result["max_range_day"].to_frame().T)

st.subheader("📋 データ一覧（選択期間）")
st.dataframe(result["df"], use_container_width=True)
