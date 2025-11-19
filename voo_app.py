import pandas as pd
from statistics import mode
import yfinance as yf
import streamlit as st

# VOO実データ読み込み関数（過去30営業日）
def load_voo_data():
    ticker = yf.Ticker("VOO")
    df = ticker.history(period="2mo")
    if df.empty:
        st.error("VOOのデータが取得できませんでした。")
        st.stop()
    df = df.tail(30).reset_index()
    return df[['Date', 'High', 'Low', 'Close']]

# 最頻高値・安値を求める関数
def get_voo_high_low_modes(buy_price=None):
    df = load_voo_data()
    highs = df['High'].round(2).tolist()
    lows = df['Low'].round(2).tolist()

    try:
        high_mode = mode(highs)
    except:
        high_mode = max(set(highs), key=highs.count)

    try:
        low_mode = mode(lows)
    except:
        low_mode = max(set(lows), key=lows.count)

    width_ratio = round((high_mode - low_mode) / low_mode * 100, 2)

    df['RangeRatio'] = ((df['High'] - df['Low']) / df['Low'] * 100).round(2)
    min_row = df.loc[df['RangeRatio'].idxmin()]
    max_row = df.loc[df['RangeRatio'].idxmax()]

    current_price = df.iloc[-1]['Close']

    profit_percent = None
    tax_profit_percent = None
    if buy_price is not None:
        try:
            profit_percent = round((current_price - buy_price) / buy_price * 100, 2)
            tax_profit_percent = round(profit_percent * 0.8, 2)  # 仮に20%課税
        except ZeroDivisionError:
            st.error("買値が0のため利益計算できませんでした。")

    return {
        'most_frequent_high': high_mode,
        'most_frequent_low': low_mode,
        'width_ratio_percent': width_ratio,
        'min_range_day': min_row,
        'max_range_day': max_row,
        'current_price': current_price,
        'buy_price': buy_price,
        'profit_percent': profit_percent,
        'tax_profit_percent': tax_profit_percent,
        'df': df
    }

# Streamlit アプリ
st.title("VOO 30日分析アプリ")

buy_price_input = st.number_input("買値を入力してください", min_value=0.0, step=0.1, value=600.0)

if st.button("計算する"):
    result = get_voo_high_low_modes(buy_price=buy_price_input)

    # 最上段メトリクス（最頻高値・最頻安値・値幅割合）
    col1, col2, col3 = st.columns(3)
    col1.metric("最頻高値", result['most_frequent_high'])
    col2.metric("最頻安値", result['most_frequent_low'])
    col3.metric("値幅割合 (%)", result['width_ratio_percent'])

    # 下段メトリクス（買値・現在価格・利益率・税引後利益率）
    col4, col5, col6, col7 = st.columns(4)
    col4.metric("買値", result['buy_price'])
    col5.metric("現在価格", round(result['current_price'], 2))
    if result['profit_percent'] is not None:
        col6.metric("予想利益率 (%)", result['profit_percent'])
    if result['tax_profit_percent'] is not None:
        col7.metric("税引後利益率 (%)", result['tax_profit_percent'])

    st.subheader("📉 値幅の割合が最も小さい日")
    st.write(result['min_range_day'].to_frame().T)

    st.subheader("📈 値幅の割合が最も大きい日")
    st.write(result['max_range_day'].to_frame().T)

    st.subheader("📋 30営業日のデータ一覧")
    st.dataframe(result['df'])
