import json
import pandas as pd
import yaml
import re
import os
from typing import Dict, List, Tuple


class KeywordProcessor:
    def __init__(self):
        self.config = self.load_config()
        
    def load_config(self) -> dict:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)
    
    def assign_ad_group(self, keyword: str) -> str:
        with open('config.yaml', 'r') as f:
            content = f.read()

        ad_group_map = {}
        current_ad_group = "General"

        #we extract ad groups and their keywords from the config content
        for line in content.split('\n'):
            if '# ' in line and ('Terms' in line or 'Queries' in line):
                current_ad_group = line.split('# ')[1].strip()
            elif '- "' in line:
                term = line.split('- "')[1].split('"')[0]
                ad_group_map[term] = current_ad_group
        
        keyword_lower = keyword.lower().strip()
        for term, group in ad_group_map.items():
            if term in keyword_lower:
                return group
        
        return "General Keywords"

    def determine_match_types(self, keyword: str, ad_group: str, search_volume: int) -> List[str]:
        strategy = self.config['advanced']['match_type_strategy']
        word_count = len(keyword.split())

        #a conservative way
        if strategy == "conservative":
            if "Brand" in ad_group or search_volume > 5000:
                return ["Exact"] 
            else:
                return ["Phrase"]  

        #aggressivee wayyy
        elif strategy == "aggressive":
            if search_volume > 1000:
                return ["Exact"]  
            elif word_count <= 3:
                return ["Phrase"]
            else:
                return ["Broad"]

        #intelligent way
        else:
            if "Brand" in ad_group:
                return ["Exact"]
            elif search_volume > 5000 and word_count <= 3:
                return ["Exact"]
            elif search_volume > 1000:
                return ["Phrase"]
            else:
                return ["Broad"]


    '''def determine_match_types(self, keyword: str, ad_group: str, search_volume: int) -> List[str]:
        """Determine match types based on strategy and keyword characteristics""" '''

    def calculate_cpc_recommendation(self, bid_low: float, bid_high: float, 
                                   competition: str, search_volume: int) -> Dict[str, float]:
        if bid_low == 0 and bid_high == 0:
            if search_volume > 5000:
                return {"min_cpc": 10.0, "max_cpc": 25.0, "suggested_cpc": 15.0}
            elif search_volume > 1000:
                return {"min_cpc": 5.0, "max_cpc": 15.0, "suggested_cpc": 10.0}
            else:
                return {"min_cpc": 2.0, "max_cpc": 8.0, "suggested_cpc": 5.0}
        
        multiplier = {"high": 1.2, "medium": 1.0, "low": 0.8}.get(competition.lower(), 1.0)
        
        min_cpc = max(1.0, bid_low * multiplier)
        max_cpc = bid_high * multiplier if bid_high > 0 else min_cpc * 2
        suggested_cpc = (min_cpc + max_cpc) / 2
        
        return {
            "min_cpc": round(min_cpc, 2),
            "max_cpc": round(max_cpc, 2),
            "suggested_cpc": round(suggested_cpc, 2)
        }

    def filter_keywords(self, df: pd.DataFrame) -> pd.DataFrame:
        original_count = len(df)
        
        #Min search volume filter
        df = df[df['avg_monthly_searches'] >= self.config['filters']['min_search_volume']]
        
        #mx CPC filter if specified
        if 'max_cpc_threshold' in self.config['filters']:
            df = df[df['top_page_bid_high'] <= self.config['filters']['max_cpc_threshold']]
        
        exclude_terms = self.config['advanced']['exclude_terms']
        for term in exclude_terms:
            df = df[~df['keyword'].str.lower().str.contains(term)]
        
        filtered_count = len(df)
        print(f" Filtered: {original_count} → {filtered_count} keywords")
        
        return df

    def process_keywords(self) -> pd.DataFrame:
        #loading raw data
        with open(self.config['output']['raw_data_file'], 'r') as f:
            raw_data = json.load(f)
        
        #nwo we laod all data
        all_keywords = []
        for source, keywords in raw_data.items():
            for keyword_data in keywords:
                keyword_data['source'] = source
                all_keywords.append(keyword_data)
        
        df = pd.DataFrame(all_keywords)
        
        if df.empty:
            raise ValueError("No keyword data found")
    
        df = df.drop_duplicates(subset=['keyword'], keep='first')
        df = self.filter_keywords(df)
        
        if df.empty:
            raise ValueError("No keywords remaining after filtering")
        df['ad_group'] = df['keyword'].apply(self.assign_ad_group)
        
        cpc_data = df.apply(lambda row: self.calculate_cpc_recommendation(
            row['top_page_bid_low'], row['top_page_bid_high'], 
            row['competition'], row['avg_monthly_searches']
        ), axis=1)
        
        df['suggested_cpc_min'] = [cpc['min_cpc'] for cpc in cpc_data]
        df['suggested_cpc_max'] = [cpc['max_cpc'] for cpc in cpc_data]
        df['suggested_cpc'] = [cpc['suggested_cpc'] for cpc in cpc_data]
        df['suggested_cpc_range'] = df.apply(
            lambda row: f"₹{row['suggested_cpc_min']:.2f} - ₹{row['suggested_cpc_max']:.2f}", axis=1
        )
        high_priority_terms = self.config['advanced']['high_priority_terms']
        df['high_priority'] = df['keyword'].str.lower().apply(
            lambda x: any(term in x for term in high_priority_terms)
        )
        expanded_rows = []
        for _, row in df.iterrows():
            match_types = self.determine_match_types(
                row['keyword'], row['ad_group'], row['avg_monthly_searches']
            )
            
            for match_type in match_types:
                new_row = row.copy()
                new_row['match_type'] = match_type
                expanded_rows.append(new_row)
        
        final_df = pd.DataFrame(expanded_rows)

        column_order = [
            'keyword', 'ad_group', 'match_type', 'avg_monthly_searches',
            'competition', 'suggested_cpc', 'suggested_cpc_range',
            'high_priority', 'source'
        ]
        
        return final_df[column_order]

    def save_results(self, df: pd.DataFrame):
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)

        main_file = "keyword_research_results.csv"
        main_output_path = os.path.join(output_dir, main_file)

        df.to_csv(main_output_path, index=False, encoding='utf-8-sig')
        print(f" Main results saved to {main_output_path}")

        if self.config['output']['create_individual_adgroup_files']:
            for ad_group in df['ad_group'].unique():
                ad_group_df = df[df['ad_group'] == ad_group]
                safe_name = re.sub(r'[^\w\s-]', '', ad_group).replace(' ', '_')
                filename = os.path.join(output_dir, f"adgroup_{safe_name}.csv")
                ad_group_df.to_csv(filename, index=False)
                print(f" {ad_group}: {filename}")

    def print_summary(self, df: pd.DataFrame):
        unique_keywords = df.drop_duplicates(subset=['keyword'])
        
        print("\n" + "="*60)
        print("📊 KEYWORD RESEARCH SUMMARY")
        print("="*60)
        print(f"🎯 Brand: {self.config['brand']['name']} ({self.config['brand']['url']})")
        print(f"🎯 Competitor: {self.config['competitor']['name']} ({self.config['competitor']['url']})")
        print(f"🔍 Min Search Volume: {self.config['filters']['min_search_volume']}")
        print("-" * 60)
        print(f"📈 Unique Keywords: {len(unique_keywords)}")
        print(f"📈 Total Variations: {len(df)}")
        print(f"📈 Ad Groups: {df['ad_group'].nunique()}")
        print(f"📈 Avg Search Volume: {unique_keywords['avg_monthly_searches'].mean():.0f}")
        print(f"📈 Total Search Volume: {unique_keywords['avg_monthly_searches'].sum():,}")
        print(f"💰 Avg Suggested CPC: ₹{df['suggested_cpc'].mean():.2f}")
        print(f"⭐ High Priority Keywords: {unique_keywords['high_priority'].sum()}")
        print("-" * 60)
        
        print("📋 AD GROUPS BREAKDOWN:")
        for ad_group, group_df in df.groupby('ad_group'):
            unique_count = group_df['keyword'].nunique()
            total_volume = group_df.drop_duplicates(subset=['keyword'])['avg_monthly_searches'].sum()
            print(f"  • {ad_group}: {unique_count} keywords ({total_volume:,} volume)")
        
        print("-" * 60)
        print("🎯 MATCH TYPES:")
        for match_type, count in df['match_type'].value_counts().items():
            print(f"  • {match_type}: {count}")
        print("="*60)

    def run(self):
        """Execute the complete processing pipeline"""
        print("🚀 Starting keyword processing...")
        
        df = self.process_keywords()
        self.save_results(df)
        self.print_summary(df)
        
        print(f"\n✅ Processing completed! Check {self.config['output']['main_file']}")
        return df


'''if __name__ == "__main__":
    processor = KeywordProcessor()
    processor.run()'''