# SEM Keyword research tool

## NOTE : You need to manually solve captcha in browser as its protected with reCaptcha. Scrapping will be automatically done within couple of seconds according to used WordStream's page structure. For additional help, I have attached a video run of this task. Check it out here: 
## Quick Start

1. **Install Dependencies**
   ```bash
   npm install
   pip install -r requirements.txt
   ```

2. **Configure**
   Edit `config.yaml` with your brand and competitor URLs

3. **Run**
   ```bash
   python main_script.py
   ```

4. **Manual Step**
   Solve CAPTCHAs in browser windows when they appear

## Features

**Automated Scraping** - Extracting keywords using puppeteer 
**Match Type Logic** - You could use either Conservative/Intelligent/Aggressive strategies  
**CPC Recommendations** - Data-driven bid suggestions  
**Advanced Filtering** - Volume, competition, exclusion filters  
**Export Ready** - CSV files for campaign import  

## Configuration Options

### Brand & Competitor
```yaml
brand:
  url: "your-brand.com"
  name: "Your Brand"

competitor:
  url: "competitor.com"
  name: "Competitor"
```

### Filtering
```yaml
filters:
  min_search_volume: 500
  max_cpc_threshold: 50

advanced:
  exclude_terms: ["job", "career", "franchise"]
  match_type_strategy: "intelligent"  #you could also use conservative, intelligent, aggressive
```

### Output Control
```yaml
output:
  main_file: "keyword_research_results.csv"
  create_individual_adgroup_files: true
  save_raw_data: true
```

## Output Files

- **`keyword_research_results.csv`** - Main keyword list with all data
- **`adgroup_*.csv`** - Individual files per ad group
- **`raw_keywords_data.json`** - Raw scraped data for backup
- **`performance_max_themes.json`** - JSON file containing dynamically generated Performance Max themes
- **`shopping_cpc_bids.csv`** - CSV file with calculated CPC bids for manual shopping campaigns

## Ad Group Categories 
###These ad Groups are ideated and given based on the brand and its goals. 

| Category | Description | Keywords Example |
|----------|-------------|------------------|
| **Brand Terms** | Your brand keywords | "dominos pizza", "dominos menu" |
| **Competitor Terms** | Competitor keywords | "pizza hut vs", "pizza hut alternative" |
| **Category Terms** | Product categories | "pizza delivery", "garlic bread order" |
| **Location Terms** | City-based queries | "pizza Mumbai", "delivery Delhi" |
| **Long-Tail Informational** | Question keywords | "how to order pizza online" |
| **Offers & Deals** | Promotional terms | "pizza discount", "free delivery" |
| **Local & Delivery** | Proximity searches | "pizza near me", "delivery nearby" |
| **General Keywords** | Other relevant terms | Generic product keywords |

## Match Type Strategies  
### Matching priorities: Exact > Phrase >Broad 

### Conservative
- Brand terms: Exact + Phrase
- High volume: Exact + Phrase  
- Others: Exact only

### Intelligent (default coded)
- Brand terms: Exact + Phrase
- High volume short: Exact + Phrase + Broad
- Medium volume: Exact + Phrase
- Long-tail: Phrase + Broad
- Low volume: Exact

### Aggressive  
- High volume: All match types
- Others: Phrase + Broad

## Campaign Insights Generated

- **Budget Allocation** by ad group based on search volume
- **High-Opportunity Keywords** (high volume + low CPC)
- **CPC Recommendations** with min/max ranges
- **Volume Distribution** across ad groups
- **Priority Keywords** flagging based on terms



## Additional Tools

This task includes additional scripts for specific tasks related to keyword research and campaign management. Kindl ceh

### Performance Max Theme Generator (`performance_max_themes.py`)

This script generates dynamic Performance Max themes based on the `keyword_research_results.csv` and settings in `config.yaml`. It categorizes ad groups into themes like Brand, Competitor, Category and Location, which can be used for structuring Performance Max campaigns.

To run this script:
```bash
python performance_max_themes.py
```
**Input:** `output/keyword_research_results.csv`, `config.yaml`
**Output:** `output/performance_max_themes.json`

### Shopping CPC Bid Calculator (`shopping_cpc_bids.py`)

This script calculates suggested CPC bids for manual shopping campaigns. It uses a sophisticated logic based on `keyword_research_results.csv` and campaign settings in `config.yaml` (e.g., `target_cpa`, `conversion_rate`).

To run this script:
```bash
python shopping_cpc_bids.py
```
**Input:** `output/keyword_research_results.csv`, `config.yaml`
**Output:** `output/shopping_cpc_bids.csv`

## Troubleshooting

### Common Issues

**"Node.js not found"**
- Install from https://nodejs.org/

**"No keywords found"** 
- Check internet connection
- Verify URLs in config.yaml
- Ensure CAPTCHAs are solved

**"Processing failed"**
- Check if raw_keywords_data.json exists
- Lower min_search_volume in config

**CAPTCHAs appearing**
- This is normal - solve them manually
- Browser window will pause until solved

### Performance Tips

- Use `headless: false` for debugging
- Increase `retry_attempts` for unstable connections  
- Adjust `delay_between_requests` if getting rate limited
- Set realistic `min_search_volume` (don't go too low)

## File Structure

```
├── config.yaml              # Main configuration
├── main.py                   # Main runner script  
├── wordstream_scraper.js     # Node.js scraper
├── keyword_processor.py      # Python processing engine
├── package.json              # Node.js dependencies
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Workflow

1. **Load Config** → Read settings from config.yaml
2. **Check Dependencies** → Verify Node.js and packages
3. **Scrape WordStream** → Extract keywords from both URLs
4. **Process Data** → Categorize, filter, and enhance keywords  
5. **Generate Insights** → Calculate budgets and recommendations
6. **Export Results** → Create CSV files for campaign import

## System Requirements

- **Node.js** 14+ (for Puppeteer)
- **Python** 3.7+ (for processing)
- **Memory**: 2GB+ recommended
- **Network**: Stable internet for scraping

## Example Output

```csv
keyword,ad_group,match_type,avg_monthly_searches,competition,suggested_cpc,suggested_cpc_range,high_priority,source
pizza delivery,Pizza - Category,Exact,12000,Medium,15.50,"₹12.00 - ₹19.00",true,brand
order pizza online,General Keywords,Phrase,8500,High,18.25,"₹15.00 - ₹21.50",true,brand
dominos menu,Dominos - Brand,Exact,15000,Low,12.00,"₹10.00 - ₹14.00",false,brand
```

