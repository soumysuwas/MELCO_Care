# MELCO-Care Ollama Setup Script
# Run this script to download and configure required models

Write-Host "=== MELCO-Care Ollama Model Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check if Ollama is installed
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue

if (-not $ollamaPath) {
    Write-Host "❌ Ollama is not installed!" -ForegroundColor Red
    Write-Host "Please install Ollama from: https://ollama.ai" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Installation steps:" -ForegroundColor Yellow
    Write-Host "1. Download from https://ollama.ai/download" -ForegroundColor White
    Write-Host "2. Run the installer" -ForegroundColor White
    Write-Host "3. Restart this script" -ForegroundColor White
    exit 1
}

Write-Host "✅ Ollama found at: $($ollamaPath.Source)" -ForegroundColor Green
Write-Host ""

# Models to download
$models = @(
    @{name="qwen3:4b"; description="Qwen3 4B - Primary model for text and vision"},
    @{name="gemma3:4b"; description="Gemma3 4B - Fallback model"},
    @{name="mistral:7b"; description="Mistral 7B - Alternative model (optional)"}
)

Write-Host "📦 Models to download:" -ForegroundColor Cyan
foreach ($model in $models) {
    Write-Host "   - $($model.name): $($model.description)" -ForegroundColor White
}
Write-Host ""

# Download models
foreach ($model in $models) {
    Write-Host "⬇️  Downloading $($model.name)..." -ForegroundColor Yellow
    
    try {
        ollama pull $model.name
        Write-Host "✅ $($model.name) downloaded successfully!" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️  Error downloading $($model.name): $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# Verify models
Write-Host "=== Verifying Installation ===" -ForegroundColor Cyan
ollama list

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host "You can now start MELCO-Care!" -ForegroundColor White
Write-Host ""
Write-Host "Quick Start:" -ForegroundColor Cyan
Write-Host "  1. Start backend:  .\venv\Scripts\python.exe -m uvicorn backend.main:app --reload" -ForegroundColor White
Write-Host "  2. Start frontend: .\venv\Scripts\streamlit.exe run frontend/app.py" -ForegroundColor White
