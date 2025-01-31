import json
import anthropic
import time

# Set up your Anthropic API key
client = anthropic.Anthropic(api_key="your-anthropic-api-key-here")

def get_expanded_definition(symbol, title, parent_title=""):
    prompt = f"""Human: Provide a concise definition for the CPC category {symbol}: '{title}'. """
    if parent_title:
        prompt += f"This is a subgroup of '{parent_title}'. "
    prompt += "Focus only on what this specific category covers, without repeating information from higher levels."
    prompt += "\n\nAssistant: Here's a concise definition for the CPC category:"

    try:
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=300,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        definition = response.content[0].text.strip()
        return definition
    except Exception as e:
        print(f"Error generating definition for {symbol}: {e}")
        return ""

def process_hierarchy(data, parent_title=""):
    if isinstance(data, dict):
        if 'symbol' in data and 'title' in data:
            data['expanded_definition'] = get_expanded_definition(data['symbol'], data['title'], parent_title)
            print(f"Processed: {data['symbol']}")
        
        if 'children' in data and isinstance(data['children'], list):
            for child in data['children']:
                process_hierarchy(child, data.get('title', ''))
    elif isinstance(data, list):
        for item in data:
            process_hierarchy(item, parent_title)

def expand_definitions(input_file, output_file):
    # Load the JSON file
    with open(input_file, 'r') as f:
        data = json.load(f)

    # Process the entire hierarchy
    process_hierarchy(data)

    # Save the updated JSON file
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    input_file = 'g10l_hierarchy.json'
    output_file = 'g10l_hierarchy_expanded.json'
    
    expand_definitions(input_file, output_file)
    print(f"Processing complete. Updated JSON saved as '{output_file}'.")