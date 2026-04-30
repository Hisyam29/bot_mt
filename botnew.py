import yfinance as yf
import pandas as pd
import requests

# =========================
# CONFIG
# =========================
TOKEN = "8265694791:AAHElCfxfPoB40pZe5yv9tvVcQEIFIAQUAw"
CHAT_IDS = [
    "1280847575",
]

PERIOD = "90d"

ATR_PERIOD = 2
MULTIPLIER = 1

# =========================
# TELEGRAM
# =========================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    for chat_id in CHAT_IDS:
        data = {
            "chat_id": chat_id,
            "text": message
        }
        try:
            res = requests.post(url, data=data)
            print(f"Telegram ke {chat_id}:", res.text)
        except:
            print(f"Gagal kirim ke {chat_id}")

# =========================
# LOAD SAHAM
# =========================
def load_symbols():
    df = pd.read_excel(r"C:\Users\Hisyam\OneDrive\Documents\Coding\saham.xlsx")

    print("KOLOM TERDETEKSI:", df.columns)

    # ambil kolom "Kode"
    symbols = df["Kode"].tolist()

    # bersihkan
    symbols = [str(s).strip().upper() for s in symbols if str(s) != 'nan']

    # tambah .JK
    symbols = [s + ".JK" for s in symbols]

    print("TOTAL SAHAM:", len(symbols))
    print(symbols[:10])

    return symbols

# =========================
# GET DATA
# =========================
def get_data(symbol, interval):
    df = yf.download(symbol, period=PERIOD, interval=interval, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.dropna(inplace=True)
    return df

# =========================
# SUPER TREND
# =========================
def compute_supertrend(df):
    df = df.copy()

    df['H-L'] = df['High'] - df['Low']
    df['H-C'] = (df['High'] - df['Close'].shift()).abs()
    df['L-C'] = (df['Low'] - df['Close'].shift()).abs()

    df['TR'] = df[['H-L','H-C','L-C']].max(axis=1)
    df['ATR'] = df['TR'].rolling(ATR_PERIOD).mean()

    hl2 = (df['High'] + df['Low']) / 2

    df['upperband'] = hl2 + MULTIPLIER * df['ATR']
    df['lowerband'] = hl2 - MULTIPLIER * df['ATR']

    df['in_uptrend'] = True

    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['upperband'].iloc[i-1]:
            df.loc[df.index[i], 'in_uptrend'] = True
        elif df['Close'].iloc[i] < df['lowerband'].iloc[i-1]:
            df.loc[df.index[i], 'in_uptrend'] = False
        else:
            df.loc[df.index[i], 'in_uptrend'] = df['in_uptrend'].iloc[i-1]

    return df

# =========================
# MAIN
# =========================
def run_bot():
    symbols = load_symbols()

    print("Scanning Multi TF + MA20...")

    results = []

    for symbol in symbols:
        try:
            # =========================
            # H4 DATA
            # =========================
            df_h4 = get_data(symbol, "4h")
            if len(df_h4) < 20:
                continue

            df_h4 = compute_supertrend(df_h4)

            current = df_h4['in_uptrend'].iloc[-1]
            previous = df_h4['in_uptrend'].iloc[-2]

            volume_now = df_h4['Volume'].iloc[-1]
            volume_avg = df_h4['Volume'].rolling(20).mean().iloc[-1]

            # =========================
            # DAILY DATA
            # =========================
            df_d1 = get_data(symbol, "1d")
            if len(df_d1) < 20:
                continue

            df_d1 = compute_supertrend(df_d1)

            daily_trend = df_d1['in_uptrend'].iloc[-1]

            # MA20 DAILY
            df_d1['MA20'] = df_d1['Close'].rolling(20).mean()
            daily_close = df_d1['Close'].iloc[-1]
            ma20 = df_d1['MA20'].iloc[-1]

            # =========================
            # FILTER FINAL
            # =========================
            is_reversal = (previous == False and current == True)
            is_volume = (volume_now > volume_avg)
            is_daily_up = (daily_trend == True)
            is_above_ma20 = (daily_close > ma20)

            if is_reversal and is_volume and is_daily_up and is_above_ma20:
                price = df_h4['Close'].iloc[-1]
                results.append((symbol, price))

                print("VALID:", symbol)

        except Exception as e:
            print("Error:", symbol, e)

    # =========================
    # OUTPUT
    # =========================
    if results:
        message = "🚀 H4 REVERSAL + DAILY TREND + MA20\n\n"

        for r in results:
            message += f"{r[0]} | {int(r[1])}\n"

        send_telegram(message)
        print(message)

    else:
        print("Tidak ada sinyal valid")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    run_bot()