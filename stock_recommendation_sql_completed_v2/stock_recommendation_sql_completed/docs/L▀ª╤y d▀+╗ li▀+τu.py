import yfinance as yf
import pandas as pd
import numpy as np
import time

# =====================================================
# DANH SÁCH VN100
# =====================================================

VN100_STOCKS = [

    # =========================
    # BANKING
    # =========================

    "ACB.VN",
    "BID.VN",
    "CTG.VN",
    "EIB.VN",
    "HDB.VN",
    "LPB.VN",
    "MBB.VN",
    "MSB.VN",
    "SHB.VN",
    "SSB.VN",
    "STB.VN",
    "TCB.VN",
    "TPB.VN",
    "VCB.VN",
    "VIB.VN",
    "VPB.VN",

    # =========================
    # TECHNOLOGY
    # =========================

    "FPT.VN",
    "CMG.VN",
    "ELC.VN",

    # =========================
    # RETAIL
    # =========================

    "MWG.VN",
    "FRT.VN",
    "DGW.VN",
    "PNJ.VN",

    # =========================
    # STEEL / MATERIALS
    # =========================

    "HPG.VN",
    "HSG.VN",
    "NKG.VN",
    "DGC.VN",
    "DCM.VN",
    "DPM.VN",
    "GVR.VN",

    # =========================
    # ENERGY / OIL
    # =========================

    "GAS.VN",
    "PLX.VN",
    "POW.VN",
    "PVD.VN",
    "PVS.VN",
    "BSR.VN",

    # =========================
    # REAL ESTATE
    # =========================

    "BCM.VN",
    "DXG.VN",
    "KBC.VN",
    "KDH.VN",
    "NLG.VN",
    "PDR.VN",
    "VHM.VN",
    "VIC.VN",
    "VRE.VN",

    # =========================
    # FOOD & CONSUMER
    # =========================

    "DBC.VN",
    "MSN.VN",
    "SAB.VN",
    "VNM.VN",

    # =========================
    # AVIATION
    # =========================

    "HVN.VN",
    "VJC.VN",

    # =========================
    # SECURITIES
    # =========================

    "FTS.VN",
    "HCM.VN",
    "SSI.VN",
    "VCI.VN",
    "VDS.VN",
    "VIX.VN",
    "VND.VN",

    # =========================
    # INSURANCE
    # =========================

    "BMI.VN",
    "BVH.VN",
    "MIG.VN",

    # =========================
    # LOGISTICS / PORT
    # =========================

    "GMD.VN",
    "HAH.VN",
    "VSC.VN",

    # =========================
    # CONSTRUCTION
    # =========================

    "CII.VN",
    "CTD.VN",
    "HHV.VN",
    "VCG.VN",

    # =========================
    # UTILITIES
    # =========================

    "BWE.VN",
    "NT2.VN",
    "REE.VN",

    # =========================
    # TEXTILE
    # =========================

    "GIL.VN",
    "TCM.VN",

    # =========================
    # PHARMA
    # =========================

    "DHG.VN",
    "DBD.VN",
    "IMP.VN",
    "TRA.VN",

    # =========================
    # SEAFOOD
    # =========================

    "ANV.VN",
    "FMC.VN",
    "VHC.VN",

    # =========================
    # INDUSTRIAL
    # =========================

    "BMP.VN",
    "CSV.VN",
    "NTP.VN",

    # =========================
    # MIDCAPS
    # =========================

    "ASM.VN",
    "DIG.VN",
    "HAG.VN",
    "IDI.VN",
    "PAN.VN",
    "PET.VN",
    "SCR.VN",
    "SJS.VN",

]

# =====================================================
# DATASET
# =====================================================

all_data = []

# =====================================================
# LOOP QUA TỪNG CỔ PHIẾU
# =====================================================

for ticker in VN100_STOCKS:

    try:

        print(f"\nDownloading {ticker} ...")

        stock = yf.Ticker(ticker)

        # =================================================
        # LẤY DỮ LIỆU GIÁ 2025
        # =================================================

        hist = stock.history(
            start="2025-01-01",
            end="2025-12-31"
        )

        # =================================================
        # CHECK EMPTY
        # =================================================

        if hist.empty:
            print(f"No data for {ticker}")
            continue

        # =================================================
        # FUNDAMENTAL DATA
        # =================================================

        info = stock.info

        # =================================================
        # TÍNH TOÁN PRICE FEATURES
        # =================================================

        yearly_return = (
            hist["Close"].iloc[-1] /
            hist["Close"].iloc[0]
        ) - 1

        avg_volume = hist["Volume"].mean()

        volatility = (
            hist["Close"]
            .pct_change()
            .std()
        )

        # =================================================
        # FEATURE ROW
        # =================================================

        row = {

            # =============================================
            # BASIC
            # =============================================

            "Stock": ticker,

            # =============================================
            # PRICE FEATURES
            # =============================================

            "CLOSE":
                hist["Close"].iloc[-1],

            "RET":
                yearly_return,

            "AVG_VOL":
                avg_volume,

            "VOL":
                volatility,

            # =============================================
            # VALUATION
            # =============================================

            "PE":
                info.get("trailingPE"),

            "PB":
                info.get("priceToBook"),

            "FPE":
                info.get("forwardPE"),

            # =============================================
            # QUALITY
            # =============================================

            "ROE":
                info.get("returnOnEquity"),

            "ROA":
                info.get("returnOnAssets"),

            # =============================================
            # GROWTH
            # =============================================

            "REV_G":
                info.get("revenueGrowth"),

            "EPS_G":
                info.get("earningsGrowth"),

            # =============================================
            # MARGINS
            # =============================================

            "GM":
                info.get("grossMargins"),

            "PM":
                info.get("profitMargins"),

            "OM":
                info.get("operatingMargins"),

            # =============================================
            # FINANCIAL HEALTH
            # =============================================

            "DE":
                info.get("debtToEquity"),

            "CR":
                info.get("currentRatio"),

            "QR":
                info.get("quickRatio"),

            # =============================================
            # RISK
            # =============================================

            "BETA":
                info.get("beta"),

            "MCAP":
                info.get("marketCap"),

            # =============================================
            # CASH FLOW
            # =============================================

            "FCF":
                info.get("freeCashflow"),

            "OCF":
                info.get("operatingCashflow"),

            # =============================================
            # DIVIDEND
            # =============================================

            "DY":
                info.get("dividendYield"),
        }

        # add row
        all_data.append(row)

        print(f"Done {ticker}")

        # tránh spam request
        time.sleep(1)

    except Exception as e:

        print(f"ERROR {ticker}: {e}")

# =====================================================
# TẠO DATAFRAME
# =====================================================

df = pd.DataFrame(all_data)

# =====================================================
# CLEAN DATA
# =====================================================

# thay inf thành NaN
df = df.replace([np.inf, -np.inf], np.nan)

# lấy numeric columns
numeric_cols = df.select_dtypes(include=np.number).columns

# fill missing bằng median
df[numeric_cols] = df[numeric_cols].fillna(
    df[numeric_cols].median()
)

# =====================================================
# HIỂN THỊ DATASET
# =====================================================

print("\n================ DATASET ================\n")

print(df.head())

print("\nShape:")
print(df.shape)

# =====================================================
# SAVE CSV
# =====================================================

df.to_csv(
    "vn100_fundamental_2025.csv",
    index=False
)

print("\nCSV SAVED")