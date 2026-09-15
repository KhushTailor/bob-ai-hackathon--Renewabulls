# Hackathon Repository Template Guide

This guide describes the standard hackathon repository structure, required submission artifacts, and automated verification checks enforced for the **IBM BOB AI Innovation Hackathon**.

---

## 1. Submission Structure & Requirements

The repository follows the official hackathon submission template:

```
├── submission.yaml             # Core submission metadata & feature manifest
├── README.md                   # Project overview, problem, solution, setup, demo
├── CONTRIBUTING.md             # Submission guidelines for participants
├── .gitignore                  # Exclusion rules for secrets, dependencies, and builds
├── .github/workflows/
│   └── validate.yml            # Automated CI submission completeness check
├── src/                        # Complete project source code
│   ├── backend/                # FastAPI backend service & API routers
│   ├── frontend/               # React / Vite operator dashboard
│   ├── mcp-server/             # Model Context Protocol (MCP) tool integration layer
│   ├── data/                   # Microgrid dataset (grid_data.csv) & generator
│   └── tests/                  # Automated unit, integration, and API test suites
├── docs/                       # Technical and domain documentation
│   ├── problem-statement.md    # Detailed domain problem analysis
│   ├── solution-overview.md    # Architectural solution description
│   ├── architecture.md         # Component diagrams & data flow
│   ├── setup-guide.md          # Local developer setup & execution instructions
│   ├── template-guide.md       # This template compliance guide
│   └── ibm-bob-integration.md  # Detailed IBM Bob & MCP layer documentation
├── demo/                       # Demonstration artifacts
│   ├── demo-video-link.txt     # Link to hosted 3-5 minute demo video
│   ├── live-demo-url.txt       # Deployed application URL or 'NOT DEPLOYED'
│   └── screenshots/            # Sequenced application screenshots (PNG/JPG)
├── presentation/               # Slide deck & presentation materials
│   ├── README.md               # Presentation instructions & slide structure
│   ├── slides.md               # Markdown slide deck
│   └── slides.pdf              # Compiled submission slide deck
└── .bob/skills/gridpulse/      # IBM Bob domain skill (SKILL.md)
```

---

## 2. Automated Validation Workflow (`validate.yml`)

Every push to the repository runs the `.github/workflows/validate.yml` GitHub Action. The workflow executes seven verification checks:

1. **Required Files Check**:
   Verifies existence of:
   - `README.md`
   - `submission.yaml`
   - `docs/problem-statement.md`
   - `docs/solution-overview.md`
   - `docs/architecture.md`
   - `docs/setup-guide.md`
   - `demo/demo-video-link.txt`

2. **YAML Syntax Validation**:
   Parses `submission.yaml` with `yq` to guarantee valid syntax.

3. **Required Metadata Fields**:
   Ensures non-empty values for:
   - `.team.name`
   - `.team.track` (`AI`, `DevOps`, `Sustainability`, or `Open`)
   - `.team.lead.name`
   - `.team.lead.email`
   - `.submission.title`
   - `.submission.problem_statement`
   - `.submission.solution_summary`
   - `.submission.key_features` (minimum 1 entry)

4. **Source Code Check**:
   Verifies that `src/` contains active implementation code files (excluding placeholder READMEs).

5. **Demo Video Check**:
   Ensures `demo/demo-video-link.txt` does not contain unreplaced generic video placeholders.

6. **README Placeholders Check**:
   Ensures `README.md` does not contain unreplaced default template tokens.

---

## 3. Local Verification Commands

To run all submission verifications locally prior to submission:

```bash
# 1. Verify backend test suite (165 passing tests)
cd src
pytest tests -v

# 2. Verify frontend production build
cd frontend
npm run build

# 3. Verify MCP server integration (32 passing checks)
cd ../mcp-server
npm test

# 4. Verify submission YAML validity
cd ../..
python -c "import yaml; yaml.safe_load(open('submission.yaml'))"
```

---

## 4. Key Submission Rules & Boundaries

- **No Secrets in Repo**: All API keys and credentials must be kept in `.env` (enforced by `.gitignore`).
- **No Fabricated Capabilities**: System documentation honestly distinguishes between active offline deterministic physics and optional cloud foundation model integrations.
- **Architectural Honesty**: Model Context Protocol (MCP) is documented as an open tool interface layer, distinct from application runtime and development assistance.
