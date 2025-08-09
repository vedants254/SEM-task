import pandas as pd
import json
import yaml
from collections import defaultdict
import os

def generate_performance_max_themes():
    """
    Generates Performance Max themes dynamically based on keyword research results and config settings.
    Themes are categorized based on ad groups, category terms, and service locations.
    The output is a JSON file named 'performance_max_themes.json'.
    """
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: 'config.yaml' not found.")
        return
    except ImportError:
        print("Error: pyyaml is not installed. Please install it using: pip install pyyaml")
        return

    try:
        df = pd.read_csv('output/keyword_research_results.csv')
    except FileNotFoundError:
        print("Error: 'keyword_research_results.csv' not found. Please run the main script first.")
        return

    category_terms = config.get('category_terms', [])
    service_locations = config.get('service_locations', [])
    brand_name = config.get('brand', {}).get('name', 'brand')
    competitor_name = config.get('competitor', {}).get('name', 'competitor')

    themes = defaultdict(list)

    ad_groups = df['ad_group'].unique()

    for group in ad_groups:
        group_lower = group.lower()
        
        if brand_name.lower() in group_lower:
            themes["Brand Themes"].append(group)
        elif competitor_name.lower() in group_lower:
            themes["Competitor Themes"].append(group)

        for term in category_terms:
            if term.lower() in group_lower:
                themes[f"Category - {term.title()}"].append(group)

        for location in service_locations:
            if location.lower() in group_lower:
                themes[f"Location - {location.title()}"].append(group)
        
        if not any(term.lower() in group_lower for term in category_terms + service_locations + [brand_name.lower(), competitor_name.lower()]):
             themes["General Themes"].append(group)

    for theme, adgroups in themes.items():
        themes[theme] = sorted(list(set(adgroups)))
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'performance_max_themes.json')

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(themes, f, indent=4, ensure_ascii=False)

    print(f"Successfully generated '{output_path}' with dynamic themes.")

if __name__ == "__main__":
    generate_performance_max_themes()