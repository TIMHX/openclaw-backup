---
name: gatech-assignment
description: >
  Complete Georgia Tech course assignments end-to-end. Use when user says "do my GaTech assignment",
  "complete assignment", "work on project", or provides an instruction PDF for a GaTech course.
  This skill reads assignment instructions, completes the assignment step-by-step, saves analysis
  scripts for replication, and outputs results/plots. Saves tabular results to Google Sheets.
triggers:
  - "do my gatech assignment"
  - "complete assignment"
  - "work on project"
  - "finish homework"
  - "read instructions and do the assignment"
---

# GaTech Assignment Completion Skill

Complete Georgia Tech course assignments end-to-end with full documentation and reproducibility.
**All Python environments are managed by `uv`.**

## Workflow

### Step 1: Capture Assignment Context

1. **Read instruction PDF** using pdf skill if provided
2. **Read Q&A PDF** using pdf skill if provided
3. **Note dataset files** provided by user in the repo
4. **Check existing files** in the project directory

### Step 2: Analyze Instructions

Break down the assignment into:
- Required tasks/questions (answer each one)
- Required datasets (follow instructions exactly - use provided datasets or download per instructions)
- Expected outputs (plots, tables, reports)
- Python/library dependencies mentioned
- Due date (if mentioned)

### Step 3: Setup Python Environment with uv

**Always use `uv` for Python environment management:**

```bash
# Create project directory and enter it
cd assignment_work

# Create pyproject.toml with dependencies based on assignment requirements
cat > pyproject.toml << 'EOF'
[project]
name = "assignment"
version = "0.1.0"
dependencies = [
    "pandas",
    "numpy",
    "matplotlib",
    "seaborn",
    "scikit-learn",
]

[project.optional-dependencies]
dev = ["jupyter", "ipykernel"]
fairness = ["fairlearn"]
EOF

# Create virtual environment
uv venv

# Install dependencies (including optional groups as needed)
uv sync

# For Jupyter notebooks
uv add --optional dev jupyter ipykernel
uv sync
```

### Step 4: Handle Datasets

**ALWAYS follow the instructions for datasets:**
- If datasets are provided in the repo → use those
- If instructions say to download from a specific URL/source → download from there
- If instructions say to use a specific library function → use that exact function
- If no dataset instructions and user didn't provide → **ask user** where to get the data

**Do NOT assume or use alternative datasets unless explicitly instructed.**

### Step 5: Complete Assignment Step-by-Step

**Always activate the venv before running Python commands:**
```bash
# Activate venv (use the correct path)
source .venv/bin/activate  # Linux/macOS
# or
.\.venv\Scripts\Activate.ps1  # Windows

# Run scripts
python scripts/01_load_data.py
python scripts/02_analysis.py
```

For each question/task:
1. Read the question carefully
2. Implement the solution in a Python script
3. Run and verify results
4. Generate required outputs (plots, tables)
5. Document findings

### Step 6: Save Analysis Scripts

Save all analysis as reusable scripts so user can replicate:
```bash
# Save each step as a numbered script
scripts/01_load_data.py
scripts/02_preprocessing.py
scripts/03_analysis_q1.py
scripts/04_analysis_q2.py
scripts/05_generate_plots.py
scripts/06_summary.py
```

### Step 7: Output Results

Output structure:
```
assignment_work/
├── pyproject.toml     # Project dependencies (uv managed)
├── .venv/            # Virtual environment
├── data/             # Raw and processed data (if any)
├── scripts/          # All Python analysis scripts
├── output/           # Generated plots, tables, results
│   ├── plots/        # Visualization files
│   ├── tables/       # Export tables as CSV
│   └── report.md     # Summary report
└── notebooks/        # Jupyter notebooks (optional)
```

Label all plots clearly with axes, title, legend. Save all tables as CSV.

### Step 8: Save to Google Sheets (using gog)

For tabular results, create a Google Sheet:
```bash
# Create a new spreadsheet
gog sheets create "Course Assignment Results"

# Note the spreadsheet ID from output, then append data:
gog sheets append <spreadsheet-id> "Sheet1!A1" "Header1" "Header2" "Value1" "Value2"
```

## Output Format for Results

```markdown
# Assignment Results

## Course: [Course Name]
## Assignment: [Assignment Title]
## Date: [Completion Date]

## Tasks Completed
1. [Task 1 description]
2. [Task 2 description]

## Key Findings
- [Finding 1]
- [Finding 2]

## Generated Outputs
- [Plot/Table 1](./output/plots/filename.png)
- [Plot/Table 2](./output/tables/filename.csv)

## Reproduction
To reproduce this analysis:
```bash
cd assignment_work
uv venv
uv sync
source .venv/bin/activate
python scripts/01_load_data.py
python scripts/02_preprocessing.py
...
```
```

## uv Quick Reference

| Task | Command |
|------|---------|
| Create venv | `uv venv` |
| Add package | `uv add pandas` |
| Add dev package | `uv add --dev jupyter` |
| Sync dependencies | `uv sync` |
| Run script | `uv run python script.py` |
| Shell with venv | `uv run --with pandas python -c "import pandas; print(pandas.__version__)"` |
| Activate venv | `source .venv/bin/activate` |

## Notes

- Always use `uv` for Python environment management
- Create `pyproject.toml` at the start of each assignment
- Always activate venv or use `uv run` before running Python scripts
- Label all plots clearly with axes, title, legend
- Save all tables as CSV for easy import
- Use `ai-humanizer` skill for longer text summaries
- Follow dataset instructions EXACTLY - do not improvise
