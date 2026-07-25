"""
Fetches real GitHub stats for a user via the GitHub GraphQL + REST APIs and
writes them to stats_data.json. This file is the single source of truth that
render_svgs.py reads from - keeping "fetch data" and "draw SVGs" as two
separate, independently-testable steps.

Requires a token with at least `read:user` scope in the GH_STATS_TOKEN repo
secret. The default GITHUB_TOKEN Actions provides is scoped to the
*workflow run* (and authenticates as github-actions[bot]), not to your
personal account's contribution history - that's why a PAT is required here,
the same way github-readme-stats and similar tools require one. See the
comment at the bottom of github-stats-sync.yml for setup steps.
"""
import os
import sys
import json
import datetime
import urllib.request
import urllib.error

GITHUB_USERNAME = os.environ.get("GITHUB_STATS_USERNAME", "PranavThorat1432")
TOKEN = os.environ.get("GH_STATS_TOKEN") or os.environ.get("GITHUB_TOKEN")

if not TOKEN:
    print("ERROR: no GH_STATS_TOKEN (or GITHUB_TOKEN) available in the environment.", file=sys.stderr)
    sys.exit(1)

API_URL = "https://api.github.com/graphql"

LANGUAGE_COLORS = {
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Python": "#3572A5",
    "Java": "#b07219", "C++": "#f34b7d", "C": "#555555", "HTML": "#e34c26",
    "CSS": "#563d7c", "Shell": "#89e051", "EJS": "#a91e50", "Dockerfile": "#384d54",
    "Arduino": "#bd79d1", "Jupyter Notebook": "#DA5B0B",
}


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        API_URL, data=body,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "github-stats-sync-script",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print("GraphQL request failed:", e.read().decode(), file=sys.stderr)
        raise
    if "errors" in data:
        print("GraphQL returned errors:", data["errors"], file=sys.stderr)
    return data.get("data", {})


PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    login
    createdAt
    followers { totalCount }
    pullRequests(states: [OPEN, CLOSED, MERGED]) { totalCount }
    issues { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        name
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

CONTRIB_YEAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
  }
}
"""


def fetch_profile():
    data = gql(PROFILE_QUERY, {"login": GITHUB_USERNAME})
    user = data.get("user")
    if not user:
        print(f"ERROR: could not find GitHub user '{GITHUB_USERNAME}'.", file=sys.stderr)
        sys.exit(1)
    return user


def fetch_total_commits(created_at_iso):
    """GraphQL's contributionsCollection is capped at a 1-year window per call,
    so we loop year-by-year from account creation to now and sum."""
    created = datetime.datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
    now = datetime.datetime.now(datetime.timezone.utc)
    total_commits = 0
    total_contribs = 0
    year_start = created
    while year_start < now:
        year_end = min(year_start + datetime.timedelta(days=365), now)
        data = gql(CONTRIB_YEAR_QUERY, {
            "login": GITHUB_USERNAME,
            "from": year_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": year_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        cc = data.get("user", {}).get("contributionsCollection", {})
        total_commits += cc.get("totalCommitContributions", 0)
        total_commits += cc.get("restrictedContributionsCount", 0)
        total_contribs += cc.get("contributionCalendar", {}).get("totalContributions", 0)
        year_start = year_end
    return total_commits, total_contribs


def compute_languages(repos):
    totals = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]
    grand_total = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:6]
    return [
        {
            "name": name,
            "pct": round(size / grand_total * 100, 1),
            "color": LANGUAGE_COLORS.get(name, "#9b4bff"),
        }
        for name, size in ranked
    ]


def compute_rank(stars, commits, prs, issues, followers, repos):
    """A simplified, transparent point-scoring heuristic (NOT a reproduction of
    any third-party service's proprietary formula) used only to pick a
    display letter grade for the rank ring. Weights are deliberately simple
    and easy to tune by hand."""
    score = (
        min(stars, 500) * 0.4 +
        min(commits, 3000) * 0.05 +
        min(prs, 200) * 0.6 +
        min(issues, 200) * 0.3 +
        min(followers, 300) * 0.6 +
        min(repos, 100) * 0.8
    )
    max_score = 500 * 0.4 + 3000 * 0.05 + 200 * 0.6 + 200 * 0.3 + 300 * 0.6 + 100 * 0.8
    pct = score / max_score
    if pct > 0.85: letter = "S"
    elif pct > 0.65: letter = "A+"
    elif pct > 0.45: letter = "A"
    elif pct > 0.25: letter = "B+"
    else: letter = "B"
    return letter, round(pct, 3)


def main():
    user = fetch_profile()
    repos = user["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)
    repo_count = user["repositories"]["totalCount"]
    followers = user["followers"]["totalCount"]
    prs = user["pullRequests"]["totalCount"]
    issues = user["issues"]["totalCount"]

    commits, contributions = fetch_total_commits(user["createdAt"])
    languages = compute_languages(repos)
    rank_letter, rank_pct = compute_rank(stars, commits, prs, issues, followers, repo_count)

    out = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "username": user["login"],
        "name": user["name"] or user["login"],
        "repos": repo_count,
        "stars": stars,
        "followers": followers,
        "commits": commits,
        "contributions": contributions,
        "prs": prs,
        "issues": issues,
        "languages": languages,
        "rank_letter": rank_letter,
        "rank_pct": rank_pct,
    }
    with open("stats_data.json", "w") as f:
        json.dump(out, f, indent=2)
    print("Wrote stats_data.json:", json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
