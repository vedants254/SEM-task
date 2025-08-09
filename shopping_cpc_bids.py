import pandas as pd
import numpy as np
import yaml
import os

def calculate_shopping_cpc_bids():
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: 'config.yaml' not found.")
        return
    except ImportError:
        print("Error: pyyaml is not installed. Please install it using: pip install pyyaml")
        return

    target_cpa = config.get('campaign_settings', {}).get('target_cpa', 10)
    shopping_ads_budget = config.get('budgets', {}).get('shopping_ads', 1000)

    try:
        df = pd.read_csv('output/keyword_research_results.csv')
    except FileNotFoundError:
        print("Error: 'keyword_research_results.csv' not found. Please run the main script first.")
        return

    conversion_rate = config.get('campaign_settings', {}).get('conversion_rate', 0.02)  # 2% conversion rate
    df['base_target_cpc'] = target_cpa * conversion_rate
    competition_map = {'Low': 1.2, 'Medium': 1.0, 'High': 0.8}
    df['competition_factor'] = df['competition'].map(competition_map).fillna(1.0)

    df['volume_factor'] = np.log1p(df['avg_monthly_searches']) / np.log1p(df['avg_monthly_searches'].max())
    df['volume_factor'] = df['volume_factor'].fillna(0.5)
    df['volume_factor'] = df['volume_factor'] * 0.4 + 0.8

    df['bid_adjustment_factor'] = df['competition_factor'] * df['volume_factor']
    df['suggested_bid'] = df['base_target_cpc'] * df['bid_adjustment_factor']

    def parse_cpc_range(range_str):
        try:
            if isinstance(range_str, str) and '-' in range_str:
                low, high = range_str.replace('₹','').strip().split(' - ')
                return float(low), float(high)
        except (ValueError, TypeError):
            pass
        return np.nan, np.nan

    df[['low_bid', 'high_bid']] = df['suggested_cpc_range'].apply(parse_cpc_range).apply(pd.Series)
    df['suggested_bid'] = df.apply(
        lambda row: np.clip(row['suggested_bid'], row['low_bid'], row['high_bid']) if pd.notna(row['low_bid']) else row['suggested_bid'],
        axis=1
    )
    def assign_priority(row):
        if row['avg_monthly_searches'] > 100000 and row['competition'] in ['Low', 'Medium']:
            return 'High'
        elif row['avg_monthly_searches'] > 10000 and row['competition'] != 'High':
            return 'Medium'
        else:
            return 'Low'

    df['priority'] = df.apply(assign_priority, axis=1)
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'shopping_cpc_bids.csv')
    output_df = df[[
        'keyword', 'ad_group', 'avg_monthly_searches', 'competition', 'suggested_cpc_range',
        'base_target_cpc', 'bid_adjustment_factor', 'suggested_bid', 'priority'
    ]]
    output_df.to_csv(output_path, index=False)

    print(f"Successfully generated '{output_path}' using values from config.yaml.")

if __name__ == "__main__":
    calculate_shopping_cpc_bids()