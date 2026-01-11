import sys
sys.path.append('.')

from services.thumbnail_generator import generate_malayalam_headline

# Test finance/banking topic
test_topics = [
    "2026 Banking Predictions: Interest Rates and Financial Trends",
    "Stock Market Investment Strategy",
    "Personal Finance Tips"
]

print("=" * 60)
print("TESTING MALAYALAM HEADLINE GENERATION")
print("=" * 60)

for topic in test_topics:
    print(f"\nTopic: {topic}")
    print("-" * 60)
    
    # Test shorts
    for i in range(3):
        headline = generate_malayalam_headline(topic, topic, "money", "short")
        print(f"  Short {i+1}: {headline}")
    
    # Test long
    for i in range(3):
        headline = generate_malayalam_headline(topic, topic, "money", "long")
        print(f"  Long {i+1}: {headline}")
    
    print()

print("=" * 60)
print("TEST COMPLETE - Verify all show: സമ്പത്ത് വർദ്ധിപ്പിക്കാം!")
print("=" * 60)
