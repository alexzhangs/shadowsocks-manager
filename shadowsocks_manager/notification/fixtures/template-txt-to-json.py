"""
Description:
    This script converts the contents of a template.txt file into a JSON string and prints it.

    The template.txt file is read and its contents are stored in the 'content' variable.
    Newline characters in the content are replaced with '\r\n'.
    A dictionary is created to represent the JSON data, with the template details and other fields.
    The dictionary is converted to a JSON string using the json.dumps() function.
    The JSON string is printed to the console.

    Each carriage return and the position of the template tags in the template.txt file matter.

Usage:
    python template-txt-to-json.py > template.json
"""

import json

# Read the contents of template.py
with open('template.txt', 'r') as file:
    content = file.read()

# Replace newline characters with \n
content = content.replace('\n', '\r\n')

# Create a dictionary for the JSON data
data = {
    "model": "notification.template",
    "pk": 1,
    "fields": {
        "type": "account_created",
        "content": content,
        "is_active": True,
        "dt_created": "2019-05-12T15:37:42.356Z",
        "dt_updated": "2019-06-18T20:21:16.078Z"
    }
}

# Convert the dictionary to a JSON string
json_data = json.dumps(data, indent=4)

# Print the JSON string
print("\n".join(["[", json_data, "]"]))