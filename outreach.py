#!/usr/bin/env python3
"""
Convo Starters: An interactive lead generation and outreach tool.
"""

import os
import sys
import json
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def print_divider():
    print("\n" + "─" * 60 + "\n")


def search_organizations(query: str) -> list[dict]:
    """Use web search + Claude to find 5 relevant organizations."""
    print("\nSearching for organizations...\n")

    # Build search queries to get comprehensive results
    search_queries = [
        query,
        f"{query} contact email",
        f"{query} program director OR executive director",
    ]

    # Collect search results
    all_results = []
    for sq in search_queries[:2]:  # Two searches to stay efficient
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2000,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            messages=[
                {
                    "role": "user",
                    "content": f'Search for: {sq}. Return the raw search results.',
                }
            ],
        )
        for block in response.content:
            if hasattr(block, "text"):
                all_results.append(block.text)

    combined_results = "\n\n".join(all_results)

    # Now ask Claude to synthesize 5 organizations from the search results
    synthesis_response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=3000,
        messages=[
            {
                "role": "user",
                "content": f"""Based on these web search results, identify 5 real organizations that match this description: "{query}"

Search results:
{combined_results}

For each organization, provide:
1. Organization name (real, verifiable)
2. A 2-sentence description: what they do and why they're a fit for "{query}"
3. A contact person name and title if findable from the results (otherwise write "Contact not found")

Be specific and accurate. Only include organizations that genuinely match. Format your response as a JSON array like this:
[
  {{
    "name": "Organization Name",
    "description": "What they do. Why they're a fit.",
    "contact": "Jane Smith, Program Director"
  }},
  ...
]

Return only the JSON array, nothing else.""",
            }
        ],
    )

    text = synthesis_response.content[0].text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    organizations = json.loads(text)
    return organizations[:5]


def present_organizations(orgs: list[dict]) -> None:
    """Display the 5 organizations to the user."""
    print_divider()
    print("Here are 5 organizations that match your description:\n")

    for i, org in enumerate(orgs, 1):
        print(f"{i}. {org['name']}")
        print(f"   {org['description']}")
        contact = org.get("contact", "Contact not found")
        if contact and contact != "Contact not found":
            print(f"   Contact: {contact}")
        print()


def get_user_picks(orgs: list[dict]) -> list[dict]:
    """Ask user to pick their top 3."""
    print("Which 3 would you like to reach out to? Enter 3 numbers separated by spaces (e.g. 1 3 5):")
    print()

    while True:
        raw = input("> ").strip()
        parts = raw.split()

        if len(parts) != 3:
            print("Please enter exactly 3 numbers.")
            continue

        try:
            picks = [int(p) for p in parts]
        except ValueError:
            print("Please enter valid numbers.")
            continue

        valid = all(1 <= p <= len(orgs) for p in picks)
        if not valid:
            print(f"Please enter numbers between 1 and {len(orgs)}.")
            continue

        if len(set(picks)) != 3:
            print("Please enter 3 different numbers.")
            continue

        return [orgs[p - 1] for p in picks]


def write_outreach_email(org: dict, user_query: str) -> str:
    """Generate a warm, specific outreach email for one organization."""
    contact = org.get("contact", "")
    contact_name = ""
    if contact and contact != "Contact not found":
        # Extract just the first name
        contact_name = contact.split(",")[0].split()[0]

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": f"""Write a short outreach email to {org['name']}.

Context about this organization: {org['description']}
Contact: {contact if contact else 'unknown'}
What I'm looking for: {user_query}

Rules for the email:
- Warm, direct, and conversational. Like a smart, curious person reaching out to someone she genuinely respects.
- No dashes of any kind (not em dashes, not hyphens used as punctuation).
- No corporate jargon.
- No "I help you" framing.
- Do not use the words: transform, unlock, unleash, leverage, synergy, innovative, cutting-edge, game-changer, empower.
- Reference something specific about {org['name']} so it's clearly not a template.
- Keep it short: 3 to 4 short paragraphs max.
- Subject line included.
- If a contact name is known ({contact_name if contact_name else 'unknown'}), address them by first name. Otherwise use a general greeting.
- Sign off as just: [Your name]

Return only the email text, nothing else.""",
            }
        ],
    )

    return response.content[0].text.strip()


def main():
    print()
    print("Convo Starters")
    print("An outreach tool for finding the right people and saying the right thing.")
    print_divider()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable is not set.")
        sys.exit(1)

    print("What are you looking for? Describe the type of organization or opportunity:")
    print()
    user_query = input("> ").strip()

    if not user_query:
        print("No input provided. Exiting.")
        sys.exit(0)

    # Step 1: Find organizations
    try:
        orgs = search_organizations(user_query)
    except json.JSONDecodeError:
        print("\nHad trouble parsing search results. Please try again with a different description.")
        sys.exit(1)
    except Exception as e:
        print(f"\nSomething went wrong during search: {e}")
        sys.exit(1)

    if len(orgs) < 3:
        print("\nCouldn't find enough matching organizations. Try a broader description.")
        sys.exit(1)

    # Step 2: Present and pick
    present_organizations(orgs)
    picks = get_user_picks(orgs)

    # Step 3: Write emails
    print_divider()
    print("Writing your outreach emails...\n")

    for i, org in enumerate(picks, 1):
        print(f"Email {i} of 3: {org['name']}")
        email = write_outreach_email(org, user_query)
        print_divider()
        print(f"TO: {org['name']}")
        if org.get("contact") and org["contact"] != "Contact not found":
            print(f"CONTACT: {org['contact']}")
        print()
        print(email)
        print()

    print_divider()
    print("Good luck with your outreach.")
    print()


if __name__ == "__main__":
    main()
