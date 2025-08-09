const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const yaml = require('js-yaml');

puppeteer.use(StealthPlugin());

class WordStreamScraper {
    constructor() {
        this.config = this.loadConfig();
        this.browser = null;
        this.page = null;
    }

    loadConfig() {
        try {
            const fileContents = fs.readFileSync('config.yaml', 'utf8');
            return yaml.load(fileContents);
        } catch (error) {
            console.log('⚠️  Config file not found, using defaults');
            return {
                scraping: { headless: false, timeout: 60000, retry_attempts: 3, delay_between_requests: 6000 },
                output: { raw_data_file: 'raw_keywords_data.json' },
                brand: { url: 'https://dominos.co.in' },
                competitor: { url: 'https://pizzahut.co.in' }
            };
        }
    }

    async initialize() {
        this.browser = await puppeteer.launch({
            headless: this.config.scraping.headless,
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
        });
        this.page = await this.browser.newPage();
        await this.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
        await this.page.setViewport({ width: 1366, height: 768 });
    }

    async scrapeKeywords(websiteUrl) {
        const targetUrl = `https://tools.wordstream.com/fkt?website=${encodeURIComponent(websiteUrl)}&cid=&camplink=&campname=&geoflow=0`;

        for (let attempt = 1; attempt <= this.config.scraping.retry_attempts; attempt++) {
            console.log(`Scraping ${websiteUrl} (Attempt ${attempt})`);

            await this.page.goto(targetUrl, { waitUntil: 'networkidle2', timeout: this.config.scraping.timeout });

            // Press submit if needed
            const submitSelectors = ['button[type="submit"]', 'input[type="submit"]', '.btn-primary'];
            for (const selector of submitSelectors) {
                try {
                    const button = await this.page.$(selector);
                    if (button) {
                        await button.click();
                        break;
                    }
                } catch (e) { /* ignore */ }
            }

            // Wait for the table to render
            await this.page.waitForSelector('table, .keyword-table', { timeout: this.config.scraping.timeout });
            await new Promise(resolve => setTimeout(resolve, 5000));

            // Extraction with robust mapping + heuristics
            const keywords = await this.page.evaluate(() => {
                const tables = document.querySelectorAll('table');
                let targetTable = null;

                // choose table by header hint
                for (const table of tables) {
                    const headers = Array.from(table.querySelectorAll('th, thead td'));
                    const headerText = headers.map(h => h.textContent.toLowerCase()).join(' ');
                    if (headerText.includes('keyword') || headerText.includes('search')) {
                        targetTable = table;
                        break;
                    }
                }
                if (!targetTable && tables.length > 0) targetTable = tables[0];
                if (!targetTable) return [];

                // normalize header cells
                const headerCells = Array.from(targetTable.querySelectorAll('thead th')).map(h =>
                    h.textContent.replace(/\s+/g, ' ').trim().toLowerCase()
                );

                // helper to get index with fallback to common pattern 0..4
                const getIndex = (name, fallback) => {
                    const idx = headerCells.findIndex(h => h.includes(name));
                    return idx >= 0 ? idx : fallback;
                };

                // default expected pattern:
                // 0: keyword (often a <th> in tbody)
                // 1: search volume
                // 2: top page bid (low)
                // 3: top page bid (high)
                // 4: competition
                const idxKeyword = getIndex('keyword', 0);
                const idxSearchVol = getIndex('search volume', 1);
                const idxLowBid = getIndex('low range', 2);
                const idxHighBid = getIndex('high range', 3);
                const idxCompetition = getIndex('competition', 4);

                console.log('Detected header cells:', headerCells);
                console.log('Initial index mapping:', { idxKeyword, idxSearchVol, idxLowBid, idxHighBid, idxCompetition });

                const rows = Array.from(targetTable.querySelectorAll('tbody tr'));

                const parseNumber = (text) => {
                    if (!text) return 0;
                    // remove currency symbols and spaces, keep digits, dot and minus
                    const cleaned = (text + '').replace(/\s+/g, '').replace(/[^\d\.\-\,]/g, '');
                    if (!cleaned) return 0;
                    const normalized = cleaned.replace(/,/g, '');
                    const m = normalized.match(/-?\d+(\.\d+)?/);
                    return m ? parseFloat(m[0]) : 0;
                };

                const looksLikeText = (s) => /[A-Za-z\u00C0-\u017F]/.test(s); // contains letters

                return rows.map(row => {
                    // include both th and td so we keep the keyword cell if it's a th
                    const cells = Array.from(row.querySelectorAll('th, td'));

                    if (!cells || cells.length === 0) return null;

                    // Start with the header-based/fallback indexes
                    let kIdx = idxKeyword;
                    let sIdx = idxSearchVol;
                    let lowIdx = idxLowBid;
                    let highIdx = idxHighBid;
                    let compIdx = idxCompetition;

                    // If the supposed keyword cell is missing or looks numeric, attempt heuristic:
                    const rawKeywordCellText = (cells[kIdx]?.textContent || '').trim();
                    if (!rawKeywordCellText || !looksLikeText(rawKeywordCellText)) {
                        // find the first cell that contains letters (likely the real keyword)
                        let found = -1;
                        for (let i = 0; i < cells.length; i++) {
                            const txt = (cells[i]?.textContent || '').trim();
                            if (txt && looksLikeText(txt)) { found = i; break; }
                        }
                        if (found >= 0) {
                            kIdx = found;
                            sIdx = kIdx + 1;
                            lowIdx = kIdx + 2;
                            highIdx = kIdx + 3;
                            compIdx = kIdx + 4;
                        }
                    }

                    // safe fetch values
                    const getCellText = (i) => (cells[i] && cells[i].textContent) ? cells[i].textContent.trim() : '';

                    const keyword = getCellText(kIdx) || '';
                    const avg_monthly_searches = parseNumber(getCellText(sIdx));
                    const top_page_bid_low = parseNumber(getCellText(lowIdx));
                    const top_page_bid_high = parseNumber(getCellText(highIdx));
                    const competition = getCellText(compIdx) || 'Unknown';

                    // If keyword still looks numeric (fail-safe), bail out this row
                    if (!keyword || !looksLikeText(keyword)) return null;

                    // Return normalized entry
                    return {
                        keyword,
                        avg_monthly_searches,
                        top_page_bid_low,
                        top_page_bid_high,
                        competition
                    };
                }).filter(item => item !== null);
            });

            if (keywords && keywords.length > 0) {
                console.log(`✅ Found ${keywords.length} keywords for ${websiteUrl}`);
                return keywords;
            }

            if (attempt < this.config.scraping.retry_attempts) {
                console.log('Retrying...');
                await new Promise(resolve => setTimeout(resolve, 5000));
            }
        }

        console.log(`❌ No keywords found for ${websiteUrl}`);
        return [];
    }

    async run() {
        await this.initialize();

        const results = {};

        // Scrape brand keywords
        results.brand = await this.scrapeKeywords(this.config.brand.url);
        await new Promise(resolve => setTimeout(resolve, this.config.scraping.delay_between_requests));

        // Scrape competitor keywords
        results.competitor = await this.scrapeKeywords(this.config.competitor.url);

        // Save raw data
        fs.writeFileSync(this.config.output.raw_data_file, JSON.stringify(results, null, 2));
        console.log(`📁 Raw data saved to ${this.config.output.raw_data_file}`);

        await this.browser.close();
        return results;
    }
}

// Run directly if called as main
if (require.main === module) {
    (async () => {
        const scraper = new WordStreamScraper();
        await scraper.run();
    })();
}

module.exports = WordStreamScraper;
