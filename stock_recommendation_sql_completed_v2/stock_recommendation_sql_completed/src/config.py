
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_OUTPUT = PROJECT_ROOT / "data" / "output"
CHARTS = PROJECT_ROOT / "charts"
MODELS = PROJECT_ROOT / "models"

RAW_FILE = DATA_RAW / "vn100.csv"
CLEAN_FILE = DATA_PROCESSED / "vn100_clean.csv"
PCA_2D_FILE = DATA_PROCESSED / "vn100_pca_2d.csv"
PCA_3D_FILE = DATA_PROCESSED / "vn100_pca_3d.csv"
CLUSTER_FILE = DATA_OUTPUT / "stock_clusters_final.csv"
ML_PRED_FILE = DATA_OUTPUT / "stock_ml_predictions.csv"
RECOMMENDATION_FILE = DATA_OUTPUT / "recommendations_all_profiles.csv"
SIMILAR_RECOMMENDATION_FILE = DATA_OUTPUT / "similar_stock_recommendations_all.csv"

RANDOM_STATE = 42

# Các cột dùng cho ML/PCA/recommendation. Script sẽ tự bỏ qua cột nào không tồn tại.
FEATURE_COLUMNS = [
    "CLOSE", "RET", "AVG_VOL", "VOL", "PE", "PB", "FPE",
    "ROE", "ROA", "REV_G", "EPS_G", "GM", "PM", "OM",
    "DE", "CR", "QR", "BETA", "MCAP", "FCF", "OCF", "DY"
]

# Một số cột nên "càng thấp càng tốt" khi tính điểm.
LOW_IS_GOOD = ["VOL", "BETA", "PE", "PB", "DE"]
HIGH_IS_GOOD = ["RET", "ROE", "ROA", "REV_G", "EPS_G", "GM", "PM", "OM", "CR", "QR", "DY", "FCF", "OCF"]

SECTOR_MAP = {
    # Banking
    "ACB.VN":"Banking", "BID.VN":"Banking", "CTG.VN":"Banking", "EIB.VN":"Banking",
    "HDB.VN":"Banking", "LPB.VN":"Banking", "MBB.VN":"Banking", "MSB.VN":"Banking",
    "SHB.VN":"Banking", "SSB.VN":"Banking", "STB.VN":"Banking", "TCB.VN":"Banking",
    "TPB.VN":"Banking", "VCB.VN":"Banking", "VIB.VN":"Banking", "VPB.VN":"Banking",
    # Technology
    "FPT.VN":"Technology", "CMG.VN":"Technology", "ELC.VN":"Technology",
    # Retail
    "MWG.VN":"Retail", "FRT.VN":"Retail", "DGW.VN":"Retail", "PNJ.VN":"Retail",
    # Steel / Materials
    "HPG.VN":"Materials", "HSG.VN":"Materials", "NKG.VN":"Materials", "DGC.VN":"Materials",
    "DCM.VN":"Materials", "DPM.VN":"Materials", "GVR.VN":"Materials",
    # Energy
    "GAS.VN":"Energy", "PLX.VN":"Energy", "POW.VN":"Energy", "PVD.VN":"Energy", "PVS.VN":"Energy", "BSR.VN":"Energy",
    # Real estate
    "BCM.VN":"Real Estate", "DXG.VN":"Real Estate", "KBC.VN":"Real Estate", "KDH.VN":"Real Estate",
    "NLG.VN":"Real Estate", "PDR.VN":"Real Estate", "VHM.VN":"Real Estate", "VIC.VN":"Real Estate", "VRE.VN":"Real Estate",
    # Consumer
    "DBC.VN":"Consumer", "MSN.VN":"Consumer", "SAB.VN":"Consumer", "VNM.VN":"Consumer",
    # Aviation
    "HVN.VN":"Aviation", "VJC.VN":"Aviation",
    # Securities
    "FTS.VN":"Securities", "HCM.VN":"Securities", "SSI.VN":"Securities", "VCI.VN":"Securities",
    "VDS.VN":"Securities", "VIX.VN":"Securities", "VND.VN":"Securities",
    # Insurance
    "BMI.VN":"Insurance", "BVH.VN":"Insurance", "MIG.VN":"Insurance",
    # Logistics
    "GMD.VN":"Logistics", "HAH.VN":"Logistics", "VSC.VN":"Logistics",
    # Construction
    "CII.VN":"Construction", "CTD.VN":"Construction", "HHV.VN":"Construction", "VCG.VN":"Construction",
    # Utilities
    "BWE.VN":"Utilities", "NT2.VN":"Utilities", "REE.VN":"Utilities",
    # Textile
    "GIL.VN":"Textile", "TCM.VN":"Textile",
    # Pharma
    "DHG.VN":"Pharma", "DBD.VN":"Pharma", "IMP.VN":"Pharma", "TRA.VN":"Pharma",
    # Seafood
    "ANV.VN":"Seafood", "FMC.VN":"Seafood", "VHC.VN":"Seafood",
    # Industrial
    "BMP.VN":"Industrial", "CSV.VN":"Industrial", "NTP.VN":"Industrial",
    # Midcaps
    "ASM.VN":"Midcap", "DIG.VN":"Midcap", "HAG.VN":"Midcap", "IDI.VN":"Midcap",
    "PAN.VN":"Midcap", "PET.VN":"Midcap", "SCR.VN":"Midcap", "SJS.VN":"Midcap",
}

PROFILE_WEIGHTS = {
    # Phòng thủ: ưu tiên rủi ro thấp, cổ tức, chất lượng doanh nghiệp.
    "phong_thu": {
        "ROE_score": 0.20,
        "DY_score": 0.20,
        "low_VOL_score": 0.20,
        "low_BETA_score": 0.20,
        "low_DE_score": 0.10,
        "PM_score": 0.10,
    },
    # Tăng trưởng: ưu tiên tăng trưởng, hiệu quả, sinh lời.
    "tang_truong": {
        "RET_score": 0.20,
        "REV_G_score": 0.25,
        "EPS_G_score": 0.25,
        "ROE_score": 0.20,
        "low_PE_score": 0.10,
    },
    # Aggressive: chấp nhận rủi ro cao để tìm lợi nhuận/tăng trưởng cao.
    "aggressive": {
        "RET_score": 0.30,
        "REV_G_score": 0.20,
        "EPS_G_score": 0.20,
        "BETA_score": 0.15,
        "VOL_score": 0.15,
    },
    # Cân bằng: trộn giữa lợi nhuận, chất lượng, định giá, rủi ro, cổ tức.
    "can_bang": {
        "RET_score": 0.18,
        "ROE_score": 0.18,
        "low_VOL_score": 0.18,
        "low_PE_score": 0.15,
        "DY_score": 0.13,
        "REV_G_score": 0.10,
        "low_BETA_score": 0.08,
    },
}

PROFILE_NAMES = {
    "phong_thu": "Phòng thủ",
    "tang_truong": "Tăng trưởng",
    "aggressive": "Aggressive",
    "can_bang": "Cân bằng",
}
