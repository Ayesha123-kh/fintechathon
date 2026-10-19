"""Catalog of card products issued by the supported banks and wallets (global reference data).

Compiled from the banks' own websites and schedules of charges on VERIFIED_ON. Banks rename and retire
cards often, so every row says how sure we are:

- official: the product is named on a bank page that was read in full (network/tier as that page states them).
- bank_site: seen in search results for the bank's own pages or fee schedules, not read in full.
- weak: sources disagree, are old, or are third-party only. Treat as a hint, not a fact.

`network` is None when the bank's page does not say which scheme the card runs on; a person who owns such a
card is asked which one it is. Business, corporate, prepaid and student cards are left out on purpose.
Loaded (idempotently, by bank + name) at startup by app.seed.loader.
"""

from datetime import date

VERIFIED_ON = date(2026, 10, 18)

# bank short_name, product name, network, tier, type, islamic, confidence, source url
CARD_PRODUCTS: list[tuple[str, str, str | None, str | None, str, bool, str, str]] = [
    # ---------------------------------------------------------------- Meezan (Islamic; debit only, no credit card found)
    ("Meezan", "Meezan Visa Classic Debit Card", "visa", "classic", "debit", True, "bank_site", "https://www.meezanbank.com/visa-debit-card/"),
    ("Meezan", "Meezan Visa Gold Debit Card", "visa", "gold", "debit", True, "bank_site", "https://www.meezanbank.com/visa-debit-card/"),
    ("Meezan", "Meezan Visa Platinum Debit Card", "visa", "platinum", "debit", True, "bank_site", "https://www.meezanbank.com/visa-platinum-debit-card/"),
    ("Meezan", "Meezan Visa Infinite Debit Card", "visa", "infinite", "debit", True, "bank_site", "https://www.meezanbank.com/wp-content/themes/mbl/downloads/home-downloads/SOC-ENG-Jul-Dec-2025.pdf"),
    ("Meezan", "Meezan Kids & Teens Visa Debit Card", "visa", "kids", "debit", True, "bank_site", "https://www.meezanbank.com/wp-content/themes/mbl/downloads/home-downloads/SOC-ENG-Jul-Dec-2025.pdf"),
    ("Meezan", "Meezan Mastercard Classic Debit Card", "mastercard", "classic", "debit", True, "bank_site", "https://www.meezanbank.com/wp-content/themes/mbl/downloads/home-downloads/SOC-ENG-Jul-Dec-2025.pdf"),
    ("Meezan", "Meezan Mastercard Titanium Debit Card", "mastercard", "titanium", "debit", True, "bank_site", "https://www.meezanbank.com/titanium-debit-card/"),
    ("Meezan", "Meezan World Debit Card", "mastercard", "world", "debit", True, "bank_site", "https://www.meezanbank.com/world-debit-card/"),
    ("Meezan", "Meezan PayPak Debit Card", "paypak", "basic", "debit", True, "bank_site", "https://www.meezanbank.com/wp-content/themes/mbl/downloads/home-downloads/SOC-ENG-Jul-Dec-2025.pdf"),

    # ---------------------------------------------------------------- HBL (network often not stated on the page)
    ("HBL", "HBL Classic DebitCard (Visa)", "visa", "classic", "debit", False, "official", "https://hbl.com/personal/cards/debit-cards/debit-cards-overview"),
    ("HBL", "HBL Classic DebitCard (Mastercard)", "mastercard", "classic", "debit", False, "official", "https://hbl.com/personal/cards/debit-cards/debit-cards-overview"),
    ("HBL", "HBL Classic DebitCard (UnionPay)", "unionpay", "classic", "debit", False, "official", "https://hbl.com/personal/cards/debit-cards/debit-cards-overview"),
    ("HBL", "HBL Gold DebitCard", None, "gold", "debit", False, "official", "https://hbl.com/personal/cards/debit-cards/debit-cards-overview"),
    ("HBL", "HBL UPI Gold DebitCard", "unionpay", "gold", "debit", False, "official", "https://hbl.com/personal/cards/debit-cards/debit-cards-overview"),
    ("HBL", "HBL World DebitCard", None, "world", "debit", False, "official", "https://hbl.com/personal/cards/debit-cards/debit-cards-overview"),
    ("HBL", "HBL UnionPay PayPak Co-Badge DebitCard", "unionpay", None, "debit", False, "official", "https://hbl.com/personal/cards/debit-cards/debit-cards-overview"),
    ("HBL", "HBL PayPak DebitCard", "paypak", "basic", "debit", False, "official", "https://www.hbl.com/personal/cards/debit-cards/hbl-paypak-debit-card"),
    ("HBL", "HBL Platinum CreditCard", None, "platinum", "credit", False, "official", "https://www.hbl.com/personal/cards/credit-cards/credit-cards-overview"),
    ("HBL", "HBL Gold CreditCard", None, "gold", "credit", False, "official", "https://www.hbl.com/personal/cards/credit-cards/credit-cards-overview"),
    ("HBL", "HBL Green CreditCard", None, "green", "credit", False, "official", "https://www.hbl.com/personal/cards/credit-cards/credit-cards-overview"),
    ("HBL", "HBL FuelSaver CreditCard", None, None, "credit", False, "official", "https://www.hbl.com/personal/cards/credit-cards/credit-cards-overview"),

    # ---------------------------------------------------------------- UBL
    ("UBL", "UBL Visa Classic Credit Card", "visa", "classic", "credit", False, "bank_site", "https://ubldigital.com/Loans/Cards-Products/UBL-Credit-Card/UBL-Credit-Card-Product"),
    ("UBL", "UBL Visa Gold Credit Card", "visa", "gold", "credit", False, "bank_site", "https://ubldigital.com/Loans/Cards-Products/UBL-Credit-Card/UBL-Credit-Card-Product"),
    ("UBL", "UBL Visa Platinum Credit Card", "visa", "platinum", "credit", False, "bank_site", "https://www.ubldigital.com/Loans/Cards-Products/UBL-Credit-Card"),
    ("UBL", "UBL Premium Visa Debit Card", "visa", "premium", "debit", False, "bank_site", "https://ubldigital.com/Loans/Cards-Products/UBL-Premium-Visa-Debit-Card"),
    ("UBL", "UBL Visa Infinite Debit Card", "visa", "infinite", "debit", False, "bank_site", "https://ubldigital.com/Loans/Cards-Products/UBL-Debit-Card"),
    ("UBL", "UBL Mastercard Signature Debit Card", "mastercard", "signature", "debit", False, "bank_site", "https://www.ubldigital.com/Loans/Cards-Products/UBL-Signature-Debit-MasterCard"),
    ("UBL", "UBL Premium Debit Mastercard", "mastercard", "premium", "debit", False, "bank_site", "https://ubldigital.com/Loans/Cards-Products/UBL-Debit-Card"),
    ("UBL", "UBL Ameen Visa Classic Debit Card", "visa", "classic", "debit", True, "bank_site", "https://ubldigital.com/Banking/UBLAmeen/SelfServiceBanking/AmeenVisaDebitCard"),

    # ---------------------------------------------------------------- MCB
    ("MCB", "MCB Visa Debit Card", "visa", None, "debit", False, "official", "https://www.mcb.com.pk/personal/roshan-digital-account/mcb-visa-debit-card"),
    ("MCB", "MCB Visa Credit Card", "visa", None, "credit", False, "official", "https://www.mcb.com.pk/personal/cards/credit-cards/mcb-visa-credit-card"),
    ("MCB", "MCB Classic/Gold Credit Card", None, "gold", "credit", False, "official", "https://www.mcb.com.pk/personal/cards/credit-cards/classic-gold-credit-card"),
    ("MCB", "MCB Platinum Credit Card", None, "platinum", "credit", False, "official", "https://www.mcb.com.pk/personal/cards/credit-cards/platinum-credit-card"),

    # ---------------------------------------------------------------- Allied Bank
    ("ABL", "Allied Visa Infinite Debit Card", "visa", "infinite", "debit", False, "official", "https://www.abl.com/allied-bank-cards/"),
    ("ABL", "Allied Visa Premium Debit Card", "visa", "premium", "debit", False, "official", "https://www.abl.com/allied-bank-cards/"),
    ("ABL", "Allied Visa Platinum Debit Card", "visa", "platinum", "debit", False, "official", "https://www.abl.com/allied-bank-cards/"),
    ("ABL", "Allied Visa Classic Debit Card", "visa", "classic", "debit", False, "official", "https://www.abl.com/allied-bank-cards/"),
    ("ABL", "Allied UnionPay PayPak Gold Debit Card", "unionpay", "gold", "debit", False, "official", "https://www.abl.com/allied-bank-cards/"),
    ("ABL", "Allied UnionPay PayPak Classic Debit Card", "unionpay", "classic", "debit", False, "official", "https://www.abl.com/allied-bank-cards/"),
    ("ABL", "Allied Basic Debit Card (PayPak)", "paypak", "basic", "debit", False, "official", "https://www.abl.com/allied-bank-cards/"),
    ("ABL", "Allied Visa Gold Credit Card", "visa", "gold", "credit", False, "official", "https://www.abl.com/allied-bank-cards/"),
    ("ABL", "Allied Visa Platinum Credit Card", "visa", "platinum", "credit", False, "official", "https://www.abl.com/allied-bank-cards/"),

    # ---------------------------------------------------------------- Bank Alfalah
    ("Alfalah", "Bank Alfalah Visa Platinum Credit Card", "visa", "platinum", "credit", False, "official", "https://www.bankalfalah.com/personal-banking/credit-cards/visa-platinum-credit-card"),
    ("Alfalah", "Bank Alfalah Visa Gold Credit Card", "visa", "gold", "credit", False, "official", "https://www.bankalfalah.com/personal-banking/credit-cards/visa-gold-credit-card"),
    ("Alfalah", "Bank Alfalah Visa Classic Credit Card", "visa", "classic", "credit", False, "official", "https://www.bankalfalah.com/personal-banking/credit-cards/visa-classic-credit-card"),
    ("Alfalah", "Bank Alfalah Visa Ultra Cashback Card", "visa", None, "credit", False, "official", "https://www.bankalfalah.com/personal-banking/credit-cards/visa-ultra-cashback-card"),
    ("Alfalah", "Bank Alfalah American Express Gold Credit Card", "amex", "gold", "credit", False, "official", "https://www.bankalfalah.com/personal-banking/credit-cards/american-express-gold-credit-card"),
    ("Alfalah", "Bank Alfalah Mastercard Optimus Credit Card", "mastercard", None, "credit", False, "official", "https://www.bankalfalah.com/personal-banking/credit-cards/mastercard-optimus-credit-card"),
    ("Alfalah", "Bank Alfalah Visa Signature Debit Card", "visa", "signature", "debit", False, "official", "https://www.bankalfalah.com/personal-banking/cards/debit-cards"),
    ("Alfalah", "Bank Alfalah Visa Platinum Debit Card", "visa", "platinum", "debit", False, "official", "https://www.bankalfalah.com/personal-banking/cards/debit-cards"),
    ("Alfalah", "Bank Alfalah Visa Gold Debit Card", "visa", "gold", "debit", False, "official", "https://www.bankalfalah.com/personal-banking/cards/debit-cards"),
    ("Alfalah", "Bank Alfalah Visa Classic Debit Card", "visa", "classic", "debit", False, "official", "https://www.bankalfalah.com/personal-banking/cards/debit-cards"),
    ("Alfalah", "Bank Alfalah PayPak Classic Debit Card", "paypak", "classic", "debit", False, "official", "https://www.bankalfalah.com/personal-banking/cards/debit-cards"),
    ("Alfalah", "Bank Alfalah UnionPay PayPak Classic Debit Card", "unionpay", "classic", "debit", False, "official", "https://www.bankalfalah.com/personal-banking/cards/debit-cards"),
    ("Alfalah", "Bank Alfalah UnionPay PayPak Gold Debit Card", "unionpay", "gold", "debit", False, "official", "https://www.bankalfalah.com/personal-banking/cards/debit-cards"),
    ("Alfalah", "Bank Alfalah UnionPay PayPak Platinum Debit Card", "unionpay", "platinum", "debit", False, "official", "https://www.bankalfalah.com/personal-banking/cards/debit-cards"),

    # ---------------------------------------------------------------- Faysal (Noor = Islamic credit cards)
    ("Faysal", "Faysal Islami Noor World Mastercard Credit Card", "mastercard", "world", "credit", True, "bank_site", "https://www.faysalbank.com/cards"),
    ("Faysal", "Faysal Islami Noor Platinum Credit Card", "mastercard", "platinum", "credit", True, "bank_site", "https://www.faysalbank.com/cards"),
    ("Faysal", "Faysal Islami Noor Titanium Credit Card", "mastercard", "titanium", "credit", True, "bank_site", "https://www.faysalbank.com/cards"),
    ("Faysal", "Faysal Islami Noor Gold Credit Card", "mastercard", "gold", "credit", True, "bank_site", "https://www.faysalbank.com/cards"),
    ("Faysal", "Faysal Islami PayPak Debit Card", "paypak", "basic", "debit", True, "bank_site", "https://www.faysalbank.com/debit-cards/paypak-debit-card"),
    ("Faysal", "Faysal Islami Debit Card Co-Badged PayPak Mastercard", "mastercard", None, "debit", True, "bank_site", "https://www.faysalbank.com/debit-cards/faysal-islami-debit-card-co-badged-paypak-mastercard"),
    ("Faysal", "Faysal Islami Classic Debit Card", None, "classic", "debit", True, "bank_site", "https://www.faysalbank.com/debit-cards"),
    ("Faysal", "Faysal Islami Gold Debit Card", None, "gold", "debit", True, "bank_site", "https://www.faysalbank.com/debit-cards"),

    # ---------------------------------------------------------------- Standard Chartered (Saadiq = Islamic)
    ("SCB", "Standard Chartered Mastercard Platinum Credit Card", "mastercard", "platinum", "credit", False, "official", "https://www.sc.com/pk/credit-cards/"),
    ("SCB", "Standard Chartered Mastercard World Credit Card", "mastercard", "world", "credit", False, "official", "https://www.sc.com/pk/credit-cards/"),
    ("SCB", "Standard Chartered Mastercard Titanium Credit Card", "mastercard", "titanium", "credit", False, "official", "https://www.sc.com/pk/credit-cards/mastercard-titanium.html"),
    ("SCB", "Standard Chartered Mastercard Cashback Credit Card", "mastercard", None, "credit", False, "official", "https://www.sc.com/pk/credit-cards/"),
    ("SCB", "Saadiq Mastercard Platinum Credit Card", "mastercard", "platinum", "credit", True, "official", "https://www.sc.com/pk/credit-cards/"),
    ("SCB", "Standard Chartered Pay PAK Debit Card", "paypak", "basic", "debit", False, "official", "https://www.sc.com/pk/debit-cards/pay-pak-debit-card/"),
    ("SCB", "Standard Chartered Classic Debit Card", None, "classic", "debit", False, "official", "https://www.sc.com/pk/debit-cards/classic-debit-card/"),
    ("SCB", "Standard Chartered Titanium Debit Card", None, "titanium", "debit", False, "official", "https://www.sc.com/pk/debit-cards/titanium-debit-card/"),
    ("SCB", "Standard Chartered Priority Platinum Debit Card", None, "platinum", "debit", False, "official", "https://www.sc.com/pk/debit-cards/priority-platinum-debit-card/"),

    # ---------------------------------------------------------------- Askari
    ("Askari", "Askari Mastercard Classic Credit Card", "mastercard", "classic", "credit", False, "bank_site", "https://askaribank.com/personal/cards/mastercard-credit-cards"),
    ("Askari", "Askari Mastercard Gold Credit Card", "mastercard", "gold", "credit", False, "bank_site", "https://askaribank.com/personal/cards/mastercard-credit-cards"),
    ("Askari", "Askari Mastercard Platinum Credit Card", "mastercard", "platinum", "credit", False, "bank_site", "https://askaribank.com/personal/cards/mastercard-credit-cards"),
    ("Askari", "Askari World Mastercard Credit Card", "mastercard", "world", "credit", False, "bank_site", "https://askaribank.com/personal/cards/askari-world-mastercard-credit-card"),
    ("Askari", "Askari Visa Classic Debit Card", "visa", "classic", "debit", False, "bank_site", "https://askaribank.com/personal/cards/askari-visa-debit-card"),
    ("Askari", "Askari Visa Gold Debit Card", "visa", "gold", "debit", False, "bank_site", "https://askaribank.com/personal/cards/askari-visa-debit-card"),
    ("Askari", "Askari Visa Platinum Debit Card", "visa", "platinum", "debit", False, "bank_site", "https://askaribank.com/personal/cards/askari-visa-debit-card"),
    ("Askari", "Askari Visa Signature Debit Card", "visa", "signature", "debit", False, "bank_site", "https://askaribank.com/personal/cards/askari-visa-debit-card"),
    ("Askari", "Askari PayPak Classic Debit Card", "paypak", "classic", "debit", False, "bank_site", "https://askaribank.com/personal"),
    ("Askari", "Askari PayPak Gold Debit Card", "paypak", "gold", "debit", False, "bank_site", "https://askaribank.com/personal"),

    # ---------------------------------------------------------------- Bank AL Habib (credit tier list differs between its pages)
    ("BAHL", "Bank AL Habib Mastercard Platinum Credit Card", "mastercard", "platinum", "credit", False, "weak", "https://www.bankalhabib.com/credit-cards"),
    ("BAHL", "Bank AL Habib Mastercard Gold Credit Card", "mastercard", "gold", "credit", False, "weak", "https://www.bankalhabib.com/credit-cards"),
    ("BAHL", "Bank AL Habib Mastercard Green Credit Card", "mastercard", "green", "credit", False, "weak", "https://www.bankalhabib.com/credit-cards"),
    ("BAHL", "Bank AL Habib Visa Signature Debit Card", "visa", "signature", "debit", False, "bank_site", "https://www.bankalhabib.com/debit-cards"),
    ("BAHL", "Bank AL Habib Visa Platinum Debit Card", "visa", "platinum", "debit", False, "bank_site", "https://www.bankalhabib.com/debit-cards"),
    ("BAHL", "Bank AL Habib Visa Gold Debit Card", "visa", "gold", "debit", False, "bank_site", "https://www.bankalhabib.com/debit-cards"),
    ("BAHL", "Bank AL Habib Visa Silver Debit Card", "visa", "silver", "debit", False, "bank_site", "https://www.bankalhabib.com/debit-cards"),
    ("BAHL", "Bank AL Habib PayPak Debit Card", "paypak", "basic", "debit", False, "bank_site", "https://www.bankalhabib.com/debit-cards"),
    ("BAHL", "Bank AL Habib UnionPay Debit Card", "unionpay", None, "debit", False, "bank_site", "https://www.bankalhabib.com/debit-cards"),

    # ---------------------------------------------------------------- JS Bank
    ("JS", "JS Bank Visa Classic Credit Card", "visa", "classic", "credit", False, "bank_site", "https://www.jsbl.com/js-credit-card/"),
    ("JS", "JS Bank Visa Gold Credit Card", "visa", "gold", "credit", False, "bank_site", "https://www.jsbl.com/js-credit-card/"),
    ("JS", "JS Bank Visa Platinum Credit Card", "visa", "platinum", "credit", False, "bank_site", "https://www.jsbl.com/js-credit-card/"),
    ("JS", "JS Bank Visa Signature Credit Card", "visa", "signature", "credit", False, "bank_site", "https://www.jsbl.com/js-credit-card/"),
    ("JS", "JS Bank Visa Debit Card", "visa", None, "debit", False, "bank_site", "https://www.jsbl.com/personal/debit-card/"),
    ("JS", "JS Bank Mastercard Gold Debit Card", "mastercard", "gold", "debit", False, "bank_site", "https://www.jsbl.com/personal/debit-card/"),
    ("JS", "JS Bank Mastercard Titanium Debit Card", "mastercard", "titanium", "debit", False, "bank_site", "https://www.jsbl.com/personal/debit-card/"),
    ("JS", "JS Bank Mastercard Platinum Debit Card", "mastercard", "platinum", "debit", False, "bank_site", "https://www.jsbl.com/personal/debit-card/"),
    ("JS", "JS Bank Mastercard World Debit Card", "mastercard", "world", "debit", False, "bank_site", "https://www.jsbl.com/personal/debit-card/"),
    ("JS", "JS Bank PayPak Classic Debit Card", "paypak", "classic", "debit", False, "bank_site", "https://www.jsbl.com/personal/debit-card/"),

    # ---------------------------------------------------------------- Habib Metropolitan (no credit card found)
    ("HabibMetro", "HabibMetro Visa Platinum Debit Card", "visa", "platinum", "debit", False, "bank_site", "https://www.habibmetro.com/visa-debit-card-2/"),
    ("HabibMetro", "HabibMetro Visa Gold Debit Card", "visa", "gold", "debit", False, "bank_site", "https://www.habibmetro.com/visa-debit-card-2/"),
    ("HabibMetro", "HabibMetro Visa Premium Debit Card", "visa", "premium", "debit", False, "bank_site", "https://www.habibmetro.com/visa-debit-card-2/"),
    ("HabibMetro", "HabibMetro PayPak Debit Card", "paypak", "basic", "debit", False, "bank_site", "https://www.habibmetro.com/wp-content/uploads/2021/06/SOC_07_2021_Eng.pdf"),

    # ---------------------------------------------------------------- Soneri
    ("Soneri", "Soneri Visa Infinite Credit Card", "visa", "infinite", "credit", False, "bank_site", "https://soneribank.com/infinite-credit-card"),
    ("Soneri", "Soneri Visa Platinum Credit Card", "visa", "platinum", "credit", False, "bank_site", "https://soneribank.com/all-credit-cards"),
    ("Soneri", "Soneri Visa Gold Credit Card", "visa", "gold", "credit", False, "bank_site", "https://soneribank.com/all-credit-cards"),
    ("Soneri", "Soneri Visa Classic Credit Card", "visa", "classic", "credit", False, "bank_site", "https://soneribank.com/all-credit-cards"),
    ("Soneri", "Soneri Mastercard Platinum Debit Card", "mastercard", "platinum", "debit", False, "bank_site", "https://soneribank.com/debit-cards"),
    ("Soneri", "Soneri Mastercard Gold Debit Card", "mastercard", "gold", "debit", False, "bank_site", "https://soneribank.com/debit-cards"),
    ("Soneri", "Soneri Mastercard Standard Debit Card", "mastercard", "standard", "debit", False, "bank_site", "https://soneribank.com/debit-cards"),
    ("Soneri", "Soneri PayPak Debit Card", "paypak", "basic", "debit", False, "bank_site", "https://soneribank.com/personal/soneri-cards/paypak-2"),

    # ---------------------------------------------------------------- Bank of Punjab (Taqwa = its Islamic window)
    ("BOP", "BOP Mastercard Gold Credit Card", "mastercard", "gold", "credit", False, "bank_site", "https://www.bop.com.pk/view.aspx?id=3374"),
    ("BOP", "BOP Mastercard Platinum Credit Card", "mastercard", "platinum", "credit", False, "bank_site", "https://www.bop.com.pk/view.aspx?id=3374"),
    ("BOP", "BOP Mastercard World Credit Card", "mastercard", "world", "credit", False, "bank_site", "https://www.bop.com.pk/view.aspx?id=3374"),
    ("BOP", "BOP Green Credit Card", "mastercard", "green", "credit", False, "bank_site", "https://www.bop.com.pk/view.aspx?id=3374"),
    ("BOP", "BOP Mastercard Classic Debit Card", "mastercard", "classic", "debit", False, "bank_site", "https://www.bop.com.pk/Documents/Debit%20Cards%20User%20Guide.pdf"),
    ("BOP", "BOP Mastercard Gold Debit Card", "mastercard", "gold", "debit", False, "bank_site", "https://www.bop.com.pk/Documents/Resource_Center/TIB%20SOBC-English%20Jan-June%202026.pdf"),
    ("BOP", "BOP Mastercard Platinum Debit Card", "mastercard", "platinum", "debit", False, "bank_site", "https://www.bop.com.pk/Documents/Resource_Center/TIB%20SOBC-English%20Jan-June%202026.pdf"),
    ("BOP", "BOP PayPak Debit Card", "paypak", "basic", "debit", False, "bank_site", "https://www.bop.com.pk/Documents/Resource_Center/TIB%20SOBC-English%20Jan-June%202026.pdf"),

    # ---------------------------------------------------------------- NBP (no credit card found)
    ("NBP", "NBP PayPak EMV Debit Card", "paypak", "classic", "debit", False, "bank_site", "https://www.nbp.com.pk/EMV-Debit-Card/index.aspx"),
    ("NBP", "NBP UnionPay (UPI) EMV Debit Card", "unionpay", None, "debit", False, "bank_site", "https://www.nbp.com.pk/EMV-Debit-Card/index.aspx"),
    ("NBP", "NBP PayPak Edge Mastercard Co-Badge Debit Card", "mastercard", None, "debit", False, "bank_site", "https://www.nbp.com.pk/EMV-Debit-Card/index.aspx"),

    # ---------------------------------------------------------------- Dubai Islamic Bank (Islamic; debit only)
    ("DIB", "DIB Visa Infinite Debit Card", "visa", "infinite", "debit", True, "bank_site", "https://www.dibpak.com/index.php/infinite-debit-card/"),
    ("DIB", "DIB Visa Signature Debit Card", "visa", "signature", "debit", True, "bank_site", "https://www.dibpak.com/index.php/signature-debit-card/"),
    ("DIB", "DIB Visa Aayan Metal Debit Card", "visa", "metal", "debit", True, "bank_site", "https://www.dibpak.com/index.php/debit-cards/"),
    ("DIB", "DIB UnionPay Asia Prestige Debit Card", "unionpay", "prestige", "debit", True, "bank_site", "https://www.dibpak.com/index.php/debit-cards/"),
    ("DIB", "DIB UnionPay Gold Debit Card", "unionpay", "gold", "debit", True, "bank_site", "https://www.dibpak.com/index.php/debit-cards/"),
    ("DIB", "DIB UnionPay Silver Debit Card", "unionpay", "silver", "debit", True, "bank_site", "https://www.dibpak.com/index.php/debit-cards/"),
    ("DIB", "DIB PayPak Debit Card", "paypak", "classic", "debit", True, "bank_site", "https://www.dibpak.com/index.php/paypak-debit-card/"),

    # ---------------------------------------------------------------- BankIslami (Islamic; debit only)
    ("BankIslami", "BankIslami Titanium Debit Mastercard", "mastercard", "titanium", "debit", True, "bank_site", "https://bankislami.com.pk/digital-channel/debitcards/titanium-debit-mastercard/"),
    ("BankIslami", "BankIslami Classic Debit Mastercard", "mastercard", "classic", "debit", True, "bank_site", "https://bankislami.com.pk/digital-channel/debitcards/classic-debit-mastercard/"),
    ("BankIslami", "BankIslami PayPak Debit Card", "paypak", "basic", "debit", True, "bank_site", "https://bankislami.com.pk/digital-channel/debitcards/"),

    # ---------------------------------------------------------------- Al Baraka (Islamic; debit only; tier names differ between its documents)
    ("AlBaraka", "Al Baraka Mastercard Classic Debit Card", "mastercard", "classic", "debit", True, "bank_site", "https://www.albaraka.com.pk/page/al-baraka-unionpay-debit-card/"),
    ("AlBaraka", "Al Baraka Mastercard Gold Debit Card", "mastercard", "gold", "debit", True, "bank_site", "https://www.albaraka.com.pk/page/al-baraka-unionpay-debit-card/"),
    ("AlBaraka", "Al Baraka Mastercard Titanium Debit Card", "mastercard", "titanium", "debit", True, "weak", "https://www.albaraka.com.pk/uploads/Key-Fact-Statement-Saving-Accounts-June-2025.pdf"),
    ("AlBaraka", "Al Baraka Mastercard Platinum Debit Card", "mastercard", "platinum", "debit", True, "bank_site", "https://www.albaraka.com.pk/uploads/Key-Fact-Statement-Saving-Accounts-June-2025.pdf"),
    ("AlBaraka", "Al Baraka PayPak Debit Card", "paypak", "basic", "debit", True, "bank_site", "https://www.albaraka.com.pk/uploads/Key-Fact-Statement-Saving-Accounts-June-2025.pdf"),
    ("AlBaraka", "Al Baraka UnionPay Debit Card", "unionpay", None, "debit", True, "bank_site", "https://www.albaraka.com.pk/page/al-baraka-unionpay-debit-card/"),

    # ---------------------------------------------------------------- Silkbank
    ("Silk", "Silkbank Visa Signature Credit Card", "visa", "signature", "credit", False, "bank_site", "https://www.silkbank.com.pk/cards/credit-cards/visa-signature/1"),
    ("Silk", "Silkbank Visa Platinum Credit Card", "visa", "platinum", "credit", False, "bank_site", "https://silkbank.com.pk/cards"),
    ("Silk", "Silkbank Visa Gold Credit Card", "visa", "gold", "credit", False, "bank_site", "https://silkbank.com.pk/cards"),
    ("Silk", "Silkbank Visa Classic Credit Card", "visa", "classic", "credit", False, "bank_site", "https://silkbank.com.pk/cards"),
    ("Silk", "Silkbank Mastercard Platinum Credit Card", "mastercard", "platinum", "credit", False, "bank_site", "https://silkbank.com.pk/cards"),
    ("Silk", "Silkbank Mastercard Titanium Credit Card", "mastercard", "titanium", "credit", False, "bank_site", "https://silkbank.com.pk/cards"),
    ("Silk", "Silkbank Mastercard Gold Credit Card", "mastercard", "gold", "credit", False, "bank_site", "https://www.silkbank.com.pk/cards/credit-card/mastercard-gold-credit-card/7"),
    ("Silk", "Silkbank Mastercard Standard Credit Card", "mastercard", "standard", "credit", False, "bank_site", "https://www.silkbank.com.pk/cards/credit-card/mastercard-standard-credit-card/8"),
    ("Silk", "Silkbank Visa Platinum Debit Card", "visa", "platinum", "debit", False, "bank_site", "https://www.silkbank.com.pk/pages/debit-cards/"),
    ("Silk", "Silkbank Visa Gold Debit Card", "visa", "gold", "debit", False, "bank_site", "https://www.silkbank.com.pk/pages/debit-cards/"),
    ("Silk", "Silkbank Visa Classic Debit Card", "visa", "classic", "debit", False, "bank_site", "https://www.silkbank.com.pk/pages/debit-cards/"),
    ("Silk", "Silkbank PayPak Debit Card", "paypak", "basic", "debit", False, "bank_site", "https://www.silkbank.com.pk/pages/debit-cards/"),

    # ---------------------------------------------------------------- Wallets (debit-style cards linked to the wallet)
    ("Easypaisa", "Easypaisa Visa Debit Card", "visa", None, "debit", False, "weak", "https://mediamatters.com.pk/easypaisa-launches-visa-debit-card-to-facilitate-millions-of-customers-across-pakistan/"),
    ("Easypaisa", "Easypaisa Visa Online (Virtual) Debit Card", "visa", "virtual", "debit", False, "weak", "https://propakistani.pk/how-to/how-to-get-easypaisa-debit-card/"),
    ("Easypaisa", "Easypaisa PayPak Debit Card", "paypak", "basic", "debit", False, "weak", "https://easypaisa.com.pk/?p=19769"),
    ("JazzCash", "JazzCash Mastercard Debit Card", "mastercard", None, "debit", False, "weak", "https://www.mastercard.com/news/eemea/en/newsroom/press-releases/en/2021/october/jazzcash-and-mastercard-introduce-new-solutions-to-transform-pakistan-s-digital-payment-ecosystem"),
    ("JazzCash", "JazzCash Mastercard Virtual Card", "mastercard", "virtual", "debit", False, "weak", "https://www.mastercard.com/news/eemea/en/newsroom/press-releases/en/2021/october/jazzcash-and-mastercard-introduce-new-solutions-to-transform-pakistan-s-digital-payment-ecosystem"),
    ("SadaPay", "SadaPay Mastercard Debit Card", "mastercard", None, "debit", False, "weak", "https://newsroom.mastercard.com/news/eemea/en/newsroom/press-releases/en/2021/february/mastercard-launches-the-mea-region-s-first-numberless-card-in-pakistan-with-sadapay"),
    ("SadaPay", "SadaPay Mastercard Virtual Debit Card", "mastercard", "virtual", "debit", False, "weak", "https://sadapay.pk/blogs/sada-spotlight-your-virtual-debit-card"),
    ("NayaPay", "NayaPay Visa Debit Card", "visa", None, "debit", False, "weak", "https://nayapay.com/"),
    ("NayaPay", "NayaPay Visa Virtual Debit Card", "visa", "virtual", "debit", False, "weak", "https://help.nayapay.com/article/96-whats-a-visa-virtual-debit-card"),
    ("NayaPay", "NayaPay PayPak Debit Card", "paypak", "basic", "debit", False, "weak", "https://help.nayapay.com/category/102-paypak-debit-card"),
]
