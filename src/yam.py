# -*- coding: utf-8 -*-
import yaml
import io
import json

# Define data
with open("dandere2x_linux.json", "r") as f:
    data = json.load(f)

# Write YAML file
with io.open('data.yaml', 'w', encoding='utf8') as outfile:
    yaml.dump(data, outfile, default_flow_style=False, allow_unicode=True, indent=4)

# Read YAML file
with open("data.yaml", 'r') as stream:
    datayml = yaml.safe_load(stream)


with open ("reverted.json", "w") as f:
    json.dump(datayml, f, indent=4)

with open("reverted.json", "r") as f:
    datarev = json.load(f)

print(datarev == datayml)