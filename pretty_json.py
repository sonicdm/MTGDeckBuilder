import json
import re

input_json = r"Z:\Scripts\MTGDecks\reference\AllPrintings.json"
output_json = r"Z:\Scripts\MTGDecks\reference\AllPrintings_pretty.json"

# Open with UTF-8 encoding
print("Opening JSON file...")
print(f"Original JSON file: {input_json}")
with open(input_json, "r", encoding="utf-8") as f:
    data = json.load(f)

print("JSON file loaded successfully.")

# with open(output_json, "w", encoding="utf-8") as f:
#     print("Saving pretty JSON...")
#     json.dump(data, f, indent=2)
#
#
# print(f"Pretty JSON saved to: {output_json}")

import re


def inspect_structure(data: dict) -> dict:
    """
    Recursively inspect the structure of the JSON data and return a mapping of the structure.
    Include the type of each key and value in the structure.
    - Stops at "cards": dict[str, int] without further inspecting its contents.
    - Skips UUID-like keys.
    """
    structure = {}

    for key, value in data.items():
        # Skip UUID-based keys (cards dictionary contents)
        if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", key):
            continue

        if isinstance(value, dict):
            # Special case: Stop recursion when encountering a "cards" dictionary
            if key == "cards":
                structure[key] = "dict[str, int]"
            else:
                structure[key] = inspect_structure(value)  # Recursively process structure
        else:
            # Store the type of the value
            structure[key] = type(value).__name__

    return structure


# Recursively inspect the structure of the JSON
print("Inspecting JSON structure...")
import json

# output structure to a schema file
schema_file = r"reference\10E.json"
# structure = inspect_structure(data)


# Write the structure to a schema file
# export data['data']["10E"] to json strict quoting and utf-8 encoding
with open(schema_file, "w", encoding="utf-8") as f:
    print("Saving schema output...")
    tenE = data['data']["10E"]
    output_dict = {}
    output_dict['data'] = {}
    output_dict['data']['10E'] = tenE

    json.dump(output_dict, f, indent=2)

print(f"Schema output saved to: {schema_file}")
print("Done.")
