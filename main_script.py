
"""Now we process scraped keywords using custom KeywordProcessor which weh hve defined earlier"""
print("\n Processing keywords...")

from keyword_processing import KeywordProcessor
    

if __name__ == "__main__":
    processor = KeywordProcessor()
    processor.run() 