import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.compressor import PromptCompressor

def test():
    compressor = PromptCompressor(enabled=True)
    
    # Sample verbose search result
    raw_text = """
    Please be advised that we have found that NVIDIA is the leader in AI chips. 
    It is important to note that Rishi Sunak, the Prime Minister, has met there. 
    In order to understand the market, we must look at the data. 
    I would appreciate it if you could consider these results. 
    Thank you for your patience and if you have any questions, let us know.
    """
    
    compressed = compressor.compress(raw_text)
    savings, pct = compressor.get_savings(raw_text, compressed)
    
    print("-" * 50)
    print("ORIGINAL:")
    print(raw_text)
    print("-" * 50)
    print("COMPRESSED:")
    print(compressed)
    print("-" * 50)
    print(f"Savings: {savings} chars ({pct:.1f}%)")
    print("-" * 50)

if __name__ == "__main__":
    test()
