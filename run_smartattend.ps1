$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = "python"

& $python -c "import pymupdf, google.genai; print('PDF and Gemini runtime ready')"
if ($LASTEXITCODE -ne 0) {
    throw "Install dependencies with: $python -m pip install -r requirements.txt"
}

& $python -m streamlit run app.py --server.headless=true
