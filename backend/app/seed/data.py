"""Reference data loaded (idempotently) on every startup."""

CATEGORIES = [
    # slug, name, icon, color, is_expense
    ("food", "Food & Dining", "utensils", "#F59E0B", True),
    ("grocery", "Grocery", "shopping-basket", "#84CC16", True),
    ("fuel", "Fuel", "fuel", "#EF4444", True),
    ("medicine", "Medicine & Health", "pill", "#06B6D4", True),
    ("transport", "Transport", "car", "#8B5CF6", True),
    ("utilities", "Bills & Utilities", "receipt", "#0EA5E9", True),
    ("shopping", "Shopping & Apparel", "shopping-bag", "#EC4899", True),
    ("entertainment", "Entertainment", "film", "#F97316", True),
    ("education", "Education", "graduation-cap", "#14B8A6", True),
    ("travel", "Travel", "plane", "#6366F1", True),
    ("housing", "Rent & Housing", "home", "#A855F7", True),
    ("telecom", "Mobile & Internet", "smartphone", "#22C55E", True),
    ("charity", "Sadqah & Charity", "heart-handshake", "#10B981", True),
    ("transfer", "Transfers", "arrow-left-right", "#64748B", False),
    ("income", "Income", "wallet", "#224F10", False),
    ("misc", "Miscellaneous", "circle-ellipsis", "#94A3B8", True),
]

# name, short, kind, website, alert email domains, aliases
BANKS = [
    ("Meezan Bank", "Meezan", "islamic_bank", "https://www.meezanbank.com", ["meezanbank.com"], ["meezan", "mbl"]),
    ("Habib Bank Limited", "HBL", "bank", "https://www.hbl.com", ["hbl.com"], ["hbl", "habib bank"]),
    ("United Bank Limited", "UBL", "bank", "https://www.ubldigital.com", ["ubl.com.pk", "ubldigital.com"], ["ubl"]),
    ("MCB Bank", "MCB", "bank", "https://www.mcb.com.pk", ["mcb.com.pk"], ["mcb", "muslim commercial bank"]),
    ("Allied Bank", "ABL", "bank", "https://www.abl.com", ["abl.com"], ["abl", "allied"]),
    ("Bank Alfalah", "Alfalah", "bank", "https://www.bankalfalah.com", ["bankalfalah.com"], ["alfalah", "bafl"]),
    ("Faysal Bank", "Faysal", "islamic_bank", "https://www.faysalbank.com", ["faysalbank.com"], ["faysal", "fbl"]),
    ("Standard Chartered Pakistan", "SCB", "bank", "https://www.sc.com/pk", ["sc.com"], ["standard chartered", "scb"]),
    ("Askari Bank", "Askari", "bank", "https://askaribank.com", ["askaribank.com.pk", "askaribank.com"], ["askari"]),
    ("Bank Al Habib", "BAHL", "bank", "https://www.bankalhabib.com", ["bankalhabib.com"], ["bank al habib", "bahl"]),
    ("JS Bank", "JS", "bank", "https://jsbl.com", ["jsbl.com"], ["js bank", "jsbl"]),
    ("Habib Metropolitan Bank", "HabibMetro", "bank", "https://www.habibmetro.com", ["habibmetro.com"], ["habib metro"]),
    ("Soneri Bank", "Soneri", "bank", "https://www.soneribank.com", ["soneribank.com"], ["soneri"]),
    ("Bank of Punjab", "BOP", "bank", "https://www.bop.com.pk", ["bop.com.pk"], ["bop", "bank of punjab"]),
    ("National Bank of Pakistan", "NBP", "bank", "https://www.nbp.com.pk", ["nbp.com.pk"], ["nbp", "national bank"]),
    ("Dubai Islamic Bank Pakistan", "DIB", "islamic_bank", "https://www.dibpak.com", ["dibpak.com"], ["dib", "dubai islamic"]),
    ("BankIslami", "BankIslami", "islamic_bank", "https://bankislami.com.pk", ["bankislami.com.pk"], ["bank islami"]),
    ("Al Baraka Bank", "AlBaraka", "islamic_bank", "https://www.albaraka.com.pk", ["albaraka.com.pk"], ["al baraka"]),
    ("Silkbank", "Silk", "bank", "https://www.silkbank.com.pk", ["silkbank.com.pk"], ["silk bank"]),
    ("Easypaisa", "Easypaisa", "wallet", "https://easypaisa.com.pk", ["easypaisa.com.pk"], ["telenor microfinance"]),
    ("JazzCash", "JazzCash", "wallet", "https://www.jazzcash.com.pk", ["jazzcash.com.pk"], ["jazz cash", "mobilink"]),
    ("SadaPay", "SadaPay", "wallet", "https://sadapay.pk", ["sadapay.pk"], ["sada pay"]),
    ("NayaPay", "NayaPay", "wallet", "https://www.nayapay.com", ["nayapay.com"], ["naya pay"]),
]

ASSET_CLASSES = [
    ("gold_silver", "Gold & Silver", "Bullion: international spot and Pakistani sarafa (per tola) rates."),
    ("psx", "Pakistani Stocks", "Equities listed on the Pakistan Stock Exchange."),
    ("foreign_stocks", "Foreign Stocks", "US and global equities and ETFs."),
    ("crypto", "Crypto Currencies", "Digital assets. Highly volatile; note SBP's regulatory stance."),
    ("pk_real_estate", "Pakistani Real Estate", "Residential and commercial property in major Pakistani cities."),
]

# asset_class, slug, name, description, symbols
WATCH_CLUSTERS = [
    ("gold_silver", "bullion-gold", "Gold", "International gold spot and Pakistani per-tola rate.", ["XAU", "GOLD_TOLA_PK"]),
    ("gold_silver", "bullion-silver", "Silver", "International silver spot and Pakistani per-tola rate.",
     ["XAG", "SILVER_TOLA_PK"]),
    ("psx", "psx-oil-gas", "PSX Oil & Gas", "Exploration, production and oil marketing companies.",
     ["OGDC", "PPL", "MARI", "POL", "PSO", "APL"]),
    ("psx", "psx-banks", "PSX Banks", "Commercial and Islamic banks.", ["MEBL", "HBL", "UBL", "MCB", "BAFL", "BAHL"]),
    ("psx", "psx-cement", "PSX Cement", "Cement manufacturers.", ["LUCK", "DGKC", "MLCF", "FCCL", "CHCC"]),
    ("psx", "psx-fertilizer", "PSX Fertilizer", "Fertilizer producers.", ["ENGRO", "FFC", "EFERT", "FATIMA"]),
    ("psx", "psx-tech", "PSX Technology", "Technology and telecom.", ["SYS", "TRG", "AVN", "NETSOL"]),
    ("psx", "psx-power", "PSX Power", "Independent power producers.", ["HUBC", "KAPCO", "NPL"]),
    ("foreign_stocks", "us-megacap-tech", "US Mega-cap Tech", "Largest US technology companies.",
     ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META"]),
    ("foreign_stocks", "global-etfs", "Broad Market ETFs", "Index funds for diversified exposure.",
     ["SPY", "QQQ", "VT", "VWO"]),
    ("foreign_stocks", "semiconductors", "Semiconductors", "Chip designers and manufacturers.",
     ["TSM", "AMD", "AVGO", "ASML"]),
    ("crypto", "crypto-majors", "Crypto Majors", "Bitcoin and Ethereum.", ["BTC", "ETH"]),
    ("crypto", "crypto-large-caps", "Crypto Large Caps", "Other large market-cap coins.",
     ["SOL", "BNB", "XRP", "ADA"]),
    ("pk_real_estate", "re-karachi", "Karachi Real Estate", "DHA, Clifton, Bahria Town Karachi, Gulshan.",
     ["DHA_KHI", "CLIFTON", "BAHRIA_KHI", "GULSHAN"]),
    ("pk_real_estate", "re-lahore", "Lahore Real Estate", "DHA Lahore, Bahria Town Lahore, Gulberg, Johar Town.",
     ["DHA_LHR", "BAHRIA_LHR", "GULBERG_LHR", "JOHAR_TOWN"]),
    ("pk_real_estate", "re-islamabad", "Islamabad/Rawalpindi Real Estate", "DHA, Bahria Town, B-17, Gulberg Greens.",
     ["DHA_ISB", "BAHRIA_ISB", "B17", "GULBERG_GREENS"]),
]

# Merchants the deal team starts from (expanded automatically from users' spending).
SEED_MERCHANTS = [
    ("KFC Pakistan", "food", "fast food restaurant"),
    ("McDonald's Pakistan", "food", "fast food restaurant"),
    ("Pizza Hut Pakistan", "food", "fast food restaurant"),
    ("Hardee's Pakistan", "food", "fast food restaurant"),
    ("Imtiaz Super Market", "grocery", "supermarket"),
    ("Carrefour Pakistan", "grocery", "supermarket"),
    ("Naheed Supermarket", "grocery", "supermarket"),
    ("Khaadi", "shopping", "women's apparel"),
    ("Sapphire", "shopping", "women's apparel"),
    ("Outfitters", "shopping", "men's and women's apparel"),
    ("Bata Pakistan", "shopping", "footwear"),
    ("Servis", "shopping", "men's footwear"),
    ("Daraz", "shopping", "online marketplace"),
    ("Foodpanda", "food", "food delivery"),
    ("Shell Pakistan", "fuel", "fuel station"),
    ("PSO", "fuel", "fuel station"),
    ("D. Watson", "medicine", "pharmacy"),
    ("Servaid Pharmacy", "medicine", "pharmacy"),
]

PLANS = [
    ("free", "Free", 0, {"advisors": ["assistant", "savings", "deals"], "investment_board": False}),
    ("plus", "Plus", 999, {"advisors": ["assistant", "savings", "deals", "investment"], "investment_board": True}),
]
