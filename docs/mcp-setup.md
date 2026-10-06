# MCP Setup: GitHub, Atlassian, and Claude Design

How to wire up the three MCP servers this kit uses so `/plan`, `/implement`, and
`/create-pr` can talk to your real Jira board and GitHub repo.

---

## 1. Atlassian (Jira + Confluence)

The kit talks to Jira through Atlassian's official hosted MCP endpoint.

### Steps

1. **Get an Atlassian API token**
   - Go to <https://id.atlassian.com/manage-profile/security/api-tokens>
   - Click **Create API token**, give it a name (e.g. `claude-code`), copy the value.

2. **Find your Atlassian site URL**
   - Your Jira URL looks like `https://yourorg.atlassian.net`.
   - You need the base domain: `yourorg.atlassian.net`.

3. **Configure `.mcp.json`**
   The kit already has this entry — just confirm it is present:
   ```json
   {
     "mcpServers": {
       "atlassian": {
         "type": "http",
         "url": "https://mcp.atlassian.com/v1/mcp/authv2"
       }
     }
   }
   ```

4. **Authenticate at session start**
   The first time Claude calls an Atlassian tool, it will open an OAuth
   browser window. Log in with your Atlassian account. The token is stored
   in your local Claude keychain — you won't be asked again.

   If you're in a headless/CI environment, use a Personal Access Token instead:
   ```json
   "atlassian": {
     "type": "http",
     "url": "https://mcp.atlassian.com/v1/mcp/authv2",
     "headers": {
       "Authorization": "Bearer YOUR_PAT_HERE"
     }
   }
   ```

### Verify
Run `/status` on any ticket key. If it prints the ticket title, Atlassian is connected.

---

## 2. GitHub

Claude Code has built-in GitHub awareness (via `gh` CLI and the GitHub MCP
server), but for this kit's hooks to push branches and open PRs you need the
`gh` CLI authenticated.

### Steps

1. **Install the GitHub CLI**
   ```
   winget install --id GitHub.cli   # Windows
   brew install gh                  # macOS
   ```

2. **Authenticate**
   ```
   gh auth login
   ```
   Choose **GitHub.com** → **HTTPS** → **Login with a browser**. Follow the prompt.

3. **Add the GitHub MCP server** (optional — adds richer Jira↔PR cross-linking)
   ```json
   {
     "mcpServers": {
       "github": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-github"],
         "env": {
           "GITHUB_TOKEN": "YOUR_FINE_GRAINED_PAT"
         }
       }
     }
   }
   ```
   Create the PAT at <https://github.com/settings/tokens> with scopes:
   `repo`, `pull_requests`, `issues`.

### Verify
```
gh auth status
```
Should print `Logged in to github.com as <your-handle>`.

---

## 3. Claude Design MCP (Anthropic Artifacts / claude.ai)

The design MCP lets agents read and write Artifacts published on claude.ai —
useful for design specs, diagrams, and review documents that live outside the
repo.

### Steps

1. **This MCP is built into Claude Code** — no extra install needed. The
   `Artifact` tool is available in every session.

2. **To reference a design doc from a ticket**, paste the artifact URL
   (`https://claude.ai/artifact/<id>`) into the Jira ticket description or
   a comment. The `jira-ticket-intake` skill will surface it as an attachment.

3. **To create a new design doc during planning**, use:
   ```
   /explore <area>   # then "create an artifact with the diagram"
   ```
   or ask Claude directly to publish a design as an Artifact. It will give you
   a private URL you can paste back into Jira.

4. **Granting edit access to a teammate**: open the Artifact, click **Share**,
   add their email. They can comment or edit; Claude will see those comments
   via `ArtifactComments`.

### Verify
Ask Claude: "list my recent artifacts". It should return your claude.ai gallery.

---

## Quick reference — `.mcp.json` with all three

```json
{
  "mcpServers": {
    "atlassian": {
      "type": "http",
      "url": "https://mcp.atlassian.com/v1/mcp/authv2"
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_YOUR_TOKEN_HERE"
      }
    },
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    }
  }
}
```

Replace `ghp_YOUR_TOKEN_HERE` with your real PAT. Atlassian uses OAuth so no
token needed there. Claude Design lives inside Claude Code — no entry required.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `getJiraIssue` returns 401 | Re-run the OAuth flow: close the session, reopen, call any Atlassian tool |
| `gh pr create` fails with "not authenticated" | `gh auth login` again |
| Artifact tool not found | Make sure you're in a Claude Code session (not the API) — the Artifact tool is Code-only |
| Jira ticket not found | Check the site URL — your `.mcp.json` must point at the right Atlassian subdomain |
