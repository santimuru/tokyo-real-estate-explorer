import re

with open('utils/prefecture_data.py', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r',?\s*"price_index":\s*[\d.]+', '', content)
content = re.sub(r',?\s*"price_ppm2_\d+":\s*[\d]+', '', content)

# Also remove NATIONAL_AVG_PPM2 constant
content = re.sub(r'\nNATIONAL_AVG_PPM2\s*=\s*\{[^}]+\}\n', '\n', content)

with open('utils/prefecture_data.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
