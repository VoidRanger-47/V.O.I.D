import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from skills.coding_engine import coding_engine
from skills.coding import handle_coding_query

def main():
    print("==================================================")
    print("V.O.I.D. 100% Offline Coding Intelligence Demo")
    print("==================================================\n")

    print("--- 1. Testing Workspace Symbol Search ---")
    query1 = "find class CodingAgent"
    print(f"Query: '{query1}'")
    res1 = handle_coding_query(query1)
    print("Response:")
    print(res1["response"])
    print("\n" + "="*50 + "\n")

    print("--- 2. Testing Algorithmic Pattern Retrieval ---")
    query2 = "write a binary search function"
    print(f"Query: '{query2}'")
    res2 = handle_coding_query(query2)
    print("Response:")
    print(res2["response"])
    print("\n" + "="*50 + "\n")

    print("--- 3. Testing Self-Healing Execution Loop ---")
    broken_code = """
def calculate_ratio(a, b)
    return a / b

print('Result:', calculate_ratio(100, 0))
"""
    print("Input Code (Contains syntax error & division by zero):")
    print(broken_code)
    print("\nExecuting in Sandboxed Self-Healing Loop...")
    
    res3 = coding_engine.healer.execute_and_heal(broken_code)
    
    print(f"\nSuccess: {res3['success']}")
    print("Repairs applied:")
    for repair in res3['repairs']:
        print(f" - {repair}")
    print("\nOutput:")
    print(res3['output'])
    print("==================================================")

if __name__ == "__main__":
    main()
