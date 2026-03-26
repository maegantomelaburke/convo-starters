import os
import json
import time
import anthropic
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def search_organizations(query: str) -> list[dict]:
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
        messages=[
            {
                "role": "user",
                "content": f"""Search the web and find 5 real organizations that match this description: "{query}"

For each organization provide:
- name: the organization name
- description: exactly 2 sentences (first: what they do, second: why they are a fit for "{query}")
- contact: "First Last, Title" if findable from search results, otherwise null

Return ONLY a valid JSON array with no other text before or after it:
[{{"name": "...", "description": "...", "contact": "..."}}]""",
            }
        ],
    )

    # Get the last text block Claude produced
    text = next((b.text for b in reversed(response.content) if hasattr(b, "text")), "")

    # Extract JSON array if wrapped in prose or code fences
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        text = text[start : end + 1]

    return json.loads(text)[:5]


def write_email(org: dict, query: str) -> str:
    contact = org.get("contact") or ""
    contact_name = contact.split(",")[0].split()[0] if contact else ""

    time.sleep(1)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": f"""Write a short outreach email to {org['name']}.

About this organization: {org['description']}
Contact: {contact if contact else 'unknown'}
What I am looking for: {query}

Rules for the email:
- Warm, direct, and conversational. Like a smart curious person reaching out to someone she genuinely respects.
- No dashes of any kind (no em dashes, no hyphens used as punctuation).
- No corporate jargon.
- No "I help you" framing.
- Never use these words: transform, unlock, unleash, leverage, synergy, innovative, cutting-edge, game-changer, empower.
- Reference something specific about {org['name']} so it is clearly not a template.
- 3 to 4 short paragraphs.
- Include a subject line at the top.
- If a contact name is known ({contact_name if contact_name else 'unknown'}), address them by first name. Otherwise use "Hi there" or a similarly warm opener.
- Sign off as: [Your name]

Return only the email text, nothing else.""",
            }
        ],
    )

    return response.content[0].text.strip()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search():
    query = (request.json or {}).get("query", "").strip()
    if not query:
        return jsonify({"error": "No query provided"}), 400
    try:
        orgs = search_organizations(query)
        return jsonify({"organizations": orgs})
    except json.JSONDecodeError:
        return jsonify({"error": "Could not parse organization results. Try rephrasing your description."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/email", methods=["POST"])
def generate_email():
    data = request.json or {}
    query = data.get("query", "")
    org = data.get("org", {})
    if not query or not org:
        return jsonify({"error": "Missing query or org"}), 400
    try:
        email = write_email(org, query)
        return jsonify({"email": email, "org": org})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
