import re

def preprocess_ingredients(json_data):
    try:
        # 1) Extract the ingredients string manually
        m = re.search(
            r'"ingredients"\s*:\s*"(?P<body>(?:\\.|[^"\\])*)"',
            json_data,
            flags=re.DOTALL
        )
        if not m:
            return "Error: No ingredients field found in input"

        # this is the raw contents, still with literal \n and escapes
        raw = m.group('body')

        # 2) Turn literal \n sequences into real newlines
        body = raw.replace(r'\n', '\n')

        body = re.sub(r'^INGREDIENTS:\s*', '', body, flags=re.IGNORECASE)
        body = body.split("ALLERGEN INFORMATION:")[0]
        body = body.replace('\n', ' ').lower()
        body = re.sub(r'[()]', '', body)
        body = re.sub(r'[^a-z\s]', '', body)
        body = re.sub(r'\s+', ' ', body).strip()

        return body

    except Exception as e:
        return f"Error: {str(e)}"