# PowerShell One-Command Test Runner for ScholarGraph
param (
    [switch]$SkipE2E = $false
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "         ScholarGraph Unified Automated Test Suite         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

python run_all_tests.py

