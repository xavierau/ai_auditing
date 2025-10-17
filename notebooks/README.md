# Jupyter Notebooks

Interactive notebooks for testing and demonstrating GenReport components.

## Available Notebooks

### 1. `parsing_demo.ipynb` - Excel Parsing Engine Demo

**Purpose:** Comprehensive demonstration of the two-phase LLM parsing system.

**What it demonstrates:**
- `SecureExcelParser` - Secure Excel parsing with sanitization
- `PreliminaryScanner` - Two-phase LLM analysis with DSPy
- `RelationshipMapper` - Worksheet relationship graph builder

**Features:**
- Creates realistic sample workbook with trial balance sheets
- Shows Phase 1a: Coding system discovery (1 API call)
- Shows Phase 1b: Per-worksheet analysis (N API calls)
- Builds relationship graph and prioritization
- Visualizes worksheet relationships
- Exports analysis results to JSON

**Usage:**
```bash
# Start Jupyter
jupyter notebook

# Open parsing_demo.ipynb and run all cells
```

**Requirements:**
- All Phase 2 components implemented ✅
- Optional: Configure DSPy with LLM provider for real analysis
- Default: Uses mock responses for demo (no API costs)

## Running Notebooks

### Setup

```bash
# Install Jupyter if not already installed
pip install jupyter notebook ipykernel

# Add project kernel
python -m ipykernel install --user --name=genreport

# Start Jupyter
jupyter notebook
```

### With Real LLM (Optional)

To use real LLM analysis instead of mocks:

1. Set up your LLM provider:
   ```bash
   # OpenAI
   export OPENAI_API_KEY="your-key-here"

   # Anthropic Claude
   export ANTHROPIC_API_KEY="your-key-here"
   ```

2. Uncomment the DSPy configuration in Step 3 of the notebook:
   ```python
   import dspy
   lm = dspy.OpenAI(model="gpt-4", api_key=os.getenv("OPENAI_API_KEY"))
   dspy.settings.configure(lm=lm)
   ```

3. Remove the mock patches in Step 4

## Expected Output

When running `parsing_demo.ipynb`, you should see:

### Step 1: Sample Workbook Created
- 5 sheets with realistic accounting data
- TB-01 Summary (Trial Balance)
- TB-02 Cash Details
- TB-03 AP Details
- GL-100 General Ledger
- Audit Notes

### Step 2: Secure Parsing
```
✅ Parsed 5 sheets
Sheet names:
  1. TB-01 Summary
  2. TB-02 Cash Details
  ...
```

### Step 4: Preliminary Scan
```
📊 Phase 1a: Discovering coding system (1 API call)...
✅ Coding System Discovered:
  Pattern: TB-XX format for Trial Balance sheets, GL-XXX for General Ledger
  Confidence: 95.00%

📋 Phase 1b: Analyzing 5 worksheets (5 API calls)...
✅ Worksheet Analyses:
  📊 SUMMARY     | TB-01 Summary             | Score: 0.95 → TB-02, TB-03
  📝 SUPPORTING  | TB-02 Cash Details        | Score: 0.80
  ...
```

### Step 5: Relationship Map
```
✅ Relationship Map Generated:
  Coding System: TB-XX format...
  Confidence: 88.50%

🔗 Relationships:
  TB-01 Summary             → TB-02, TB-03
  TB-02 Cash Details        → (no references)
  ...
```

## API Call Efficiency

The two-phase approach is highly efficient:

```
Two-Phase Approach: 6 API calls (1 + N)
Naive Approach (N²): 25 API calls
Efficiency Gain: 76.0% reduction
```

For a 50-sheet workbook:
- Two-Phase: 51 API calls
- Naive N²: 2,500 API calls
- **98% reduction!**

## Troubleshooting

### Import Errors
```python
# If you get import errors, ensure project root is in path:
import sys
from pathlib import Path
project_root = Path().resolve().parent
sys.path.insert(0, str(project_root))
```

### DSPy Configuration Issues
```python
# Check DSPy is installed
pip install dspy-ai

# Verify LLM provider credentials
import os
print(os.getenv("OPENAI_API_KEY"))  # Should not be None
```

### Mock Not Working
If mocks aren't working:
```python
# Ensure unittest.mock is imported
from unittest.mock import patch, MagicMock

# Check patch path is correct
with patch('genreport.core.parsing.preliminary_scanner.dspy') as mock_dspy:
    # Your code here
```

## Next Steps

After running the demo notebook:

1. **Try with real LLM**: Configure DSPy and see actual LLM analysis
2. **Customize sample data**: Modify the workbook creation to test different patterns
3. **Export analysis**: Use the JSON export for further processing
4. **Integrate with Phase 3**: Once ValidationEngine is implemented, add validation steps

## Contributing

To add new notebooks:

1. Create notebook following the existing pattern
2. Add documentation to this README
3. Include clear step-by-step explanations
4. Provide both mock and real LLM options
5. Show expected output examples

## Architecture Compliance

All notebooks should:
- ✅ Use market-agnostic core components
- ✅ Not hardcode jurisdictions (HK, SG, AU)
- ✅ Follow the hybrid architecture pattern
- ✅ Include security best practices
- ✅ Document API call efficiency
