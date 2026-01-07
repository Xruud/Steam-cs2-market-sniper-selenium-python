# Steam Market Automation Scripts

> ⚠️ **WARNING & DISCLAIMER**: These scripts automate interactions with the Steam Community Market. Using them may violate Steam's Terms of Service and could result in your account being suspended, trade-banned, or permanently banned. The author provides this code for **educational and research purposes only** and assumes no responsibility for its use.

## 📋 Overview

A collection of Python scripts demonstrating browser automation techniques for monitoring Steam Community Market listings. 

### Scripts Included:

1. **`Steamscriptwithoutapirandom`** - Not using any api requests whatsoever, only opening and sniping for skins at random intervals
2. **`Steamsniperusingurlapi`** - Using a Chrome Window which is always open from where script exctact sell order count through the itemorderhistogram. When sell orders change a window opens using a random chromeprofile (the ones you create at start) and search and snipe skins.
3. **`Steamsniperusingregapi`** - Using requests from python to exctract sell orders. When sell orders change a window opens using a random chromeprofile (the ones you create at start) and search and snipe skins (IMPORTANT:also modify https://steamcommunity.com/market/itemordershistogram?country=UK&language=english&currency=3&item_nameid={item_nameid} on config through Ctrl+F to correct currency and country type)
Currency Code	Currency	Symbol	Country/Region

1	USD ($)
2	GBP (£)
3	EUR (€)
4	CHF (Fr.)
5	RUB (₽)
6	PLN (zł)
7	BRL (R$)
8	JPY (¥)
9	NOK (kr)
10	IDR (Rp)
11	MYR (RM)
12	PHP (₱)
13	SGD (S$)
14	THB (฿)
15	VND (₫)
16	KRW (₩)
17	TRY (₺)
18	UAH (₴)
19	MXN ($)
20	CAD (C$)
21	AUD (A$)
22	NZD (NZ$)
23	CNY (¥)
24	INR (₹)
25	CLP ($)
26	PEN (S/)
27	COP ($)
28	SAR (ر.س)
29	AED (د.إ)
30	ILS (₪)
31	KZT (₸)


## THIS IS A PROJECT MADE BY AI
- AI wrote all of the scripts
- **It will have a lot of spaghetti and jargon code**
- **Some functions of it may not work**/ or work only with some timing settings (I can't figure code out) (for example pages_to_check is weird and doesnt work mostoften)
- **I can't figure out how .gitignore works so AI also made that for me**
- **Any upgrades to the are welcome**, since I have abandoned this project (hence why I'm uploading it) 

## ⚙️ Prerequisites

- **Python 3.8+**
- **Google Chrome** (latest version)

## 📦 Installation
```bash git clone https://github.com/Xruud/Steam-cs2-market-sniper-selenium-python```
```cd Steam-cs2-market-sniper-selenium-python```

## Dependencies
Selenium, PyYAML, Requests, chromedriver-autoinstaller, webdriver-manager, pyyaml, html5lib, beautifulsoup4, fake-useragent, fake-headers

```
pip install -r /path/to/requirements.txt
```
***

## First Run
- Run Chromeprofilecreation.py, sign in to steam and download both Csfloat and Steam Invetntory Helper extensions on all 5 profiles
 On Steam Invetntory Helper set the settings to 100 listings per page and enable the quick buy button on all 5 profiles
- Afterwards run any of the 3 scripts
