import re
import json

def preprocess_ingredients(json_data):
    try:
        
        # 1) Decode bytes to string
        content_str = json_data.body.decode('utf-8')

        # 2) Parse JSON to dict
        content_dict = json.loads(content_str)
        
        # 3) Get the ingredients field
        raw = content_dict.get("ingredients", "")
        if not raw:
            return "Error: No ingredients field found in input"

        # 4) Process the text
        body = raw.replace(r'\n', '\n')
        body = re.sub(r'^INGREDIENTS:\s*', '', body, flags=re.IGNORECASE)
        body = body.split("ALLERGEN INFORMATION:")[0]
        body = body.replace('\n', ' ').lower()
        body = re.sub(r'[()]', '', body)
        body = re.sub(r'[^a-z\s]', '', body)
        body = re.sub(r'\s+', ' ', body).strip()

        print("debug :", body)
        return body

    except Exception as e:
        return f"Error: {str(e)}"