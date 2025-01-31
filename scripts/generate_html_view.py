import json
import html

def create_html_content(data, level=0):
    content = ""
    if isinstance(data, dict):
        content += "<ul>"
        for key, value in data.items():
            if key == 'children':
                continue
            content += f"<li><strong>{html.escape(key)}:</strong> {html.escape(str(value))}</li>"
        if 'children' in data and data['children']:
            content += "<li><strong>Children:</strong>"
            content += create_html_content(data['children'], level + 1)
            content += "</li>"
        content += "</ul>"
    elif isinstance(data, list):
        content += "<ul>"
        for item in data:
            content += f"<li><details><summary>{html.escape(item.get('symbol', ''))} - {html.escape(item.get('title', ''))}</summary>"
            content += create_html_content(item, level + 1)
            content += "</details></li>"
        content += "</ul>"
    return content

def generate_html(input_file, output_file):
    with open(input_file, 'r') as f:
        data = json.load(f)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>G10L CPC Classification Expanded Definitions</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1 {{
                color: #2c3e50;
            }}
            ul {{
                list-style-type: none;
                padding-left: 20px;
            }}
            details {{
                margin-bottom: 10px;
            }}
            summary {{
                cursor: pointer;
                font-weight: bold;
                color: #2980b9;
            }}
            details > summary {{
                list-style: none;
            }}
            details > summary::-webkit-details-marker {{
                display: none;
            }}
            details > summary::before {{
                content: '▶';
                display: inline-block;
                width: 20px;
                color: #7f8c8d;
            }}
            details[open] > summary::before {{
                content: '▼';
            }}
        </style>
    </head>
    <body>
        <h1>G10L CPC Classification Expanded Definitions</h1>
        {create_html_content(data)}
    </body>
    </html>
    """

    with open(output_file, 'w') as f:
        f.write(html_content)

if __name__ == "__main__":
    input_file = 'g10l_hierarchy_expanded.json'
    output_file = 'g10l_expanded_definitions.html'
    generate_html(input_file, output_file)
    print(f"HTML file generated: {output_file}")