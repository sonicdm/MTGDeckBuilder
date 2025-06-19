import json
import random
import os

with open(r"data\mtgjson\AllPrintings.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Convert keys to list before sampling
set_codes = random.sample(list(data['data'].keys()), 1)
sample_sets = {k: data['data'][k] for k in set_codes}
sample_dict = {}
sample_dict['data'] = sample_sets
sample_dict['meta'] = data['meta']

# Create a test data directory if it doesn't exist
test_data_dir = "tests\\sample_data"
os.makedirs(test_data_dir, exist_ok=True)

# Save the sample data as a properly formatted JSON file
output_file = os.path.join(test_data_dir, "sample_allprintings.json")
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(sample_dict, f, indent=2)

print(f"Sample data has been saved to: {output_file}")
print(f"Number of sets sampled: {len(sample_sets)}")
print("Sample set codes:", ", ".join(set_codes))
