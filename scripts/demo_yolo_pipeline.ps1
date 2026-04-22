<#
.SYNOPSIS
Demo YOLO pipeline end-to-end: create signalement → trigger pipeline → poll status

.DESCRIPTION
This script demonstrates the full UrbanFix AI pipeline flow:
1. Create a new signalement with a local image
2. Trigger the async pipeline processing
3. Poll /status until completion or timeout (60s)
4. Display detection results, annotated image path, and warnings

.PARAMETER ImagePath
Path to a local image file (JPEG, PNG). Required.

.PARAMETER BaseUrl
Backend API base URL. Default: http://localhost:8000

.PARAMETER PollIntervalSeconds
Interval between status polls. Default: 2 seconds

.PARAMETER TimeoutSeconds
Max time to poll before giving up. Default: 60 seconds

.EXAMPLE
.\demo_yolo_pipeline.ps1 -ImagePath "C:\test_image.jpg"
.\demo_yolo_pipeline.ps1 -ImagePath "./test_image.jpg" -BaseUrl "http://localhost:8000"

#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ImagePath,

    [Parameter(Mandatory=$false)]
    [string]$BaseUrl = "http://localhost:8000",

    [Parameter(Mandatory=$false)]
    [int]$PollIntervalSeconds = 2,

    [Parameter(Mandatory=$false)]
    [int]$TimeoutSeconds = 60
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

function Test-ImagePath {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        Write-Error "Image file not found: $Path"
        exit 1
    }
    
    $ext = [System.IO.Path]::GetExtension($Path).ToLower()
    if ($ext -notin @(".jpg", ".jpeg", ".png", ".webp")) {
        Write-Error "Unsupported image format: $ext (supported: jpg, jpeg, png, webp)"
        exit 1
    }
}

function New-SignalementWithImage {
    param(
        [string]$ImagePath,
        [string]$BaseUrl
    )
    
    $uri = "$BaseUrl/api/v1/signalements/"
    
    Write-Host "📤 Creating signalement with image..." -ForegroundColor Cyan
    
    # Prepare multipart form data
    $fileName = [System.IO.Path]::GetFileName($ImagePath)
    $fileContent = [System.IO.File]::ReadAllBytes($ImagePath)
    
    # Build form data with boundary
    $boundary = [System.Guid]::NewGuid().ToString()
    $bodyLines = @()
    
    # Title field
    $bodyLines += "--$boundary"
    $bodyLines += 'Content-Disposition: form-data; name="title"'
    $bodyLines += ""
    $bodyLines += "Demo YOLO Pipeline Test"
    
    # Description field
    $bodyLines += "--$boundary"
    $bodyLines += 'Content-Disposition: form-data; name="description"'
    $bodyLines += ""
    $bodyLines += "Automated pipeline demo"
    
    # Latitude
    $bodyLines += "--$boundary"
    $bodyLines += 'Content-Disposition: form-data; name="latitude"'
    $bodyLines += ""
    $bodyLines += "36.8065"
    
    # Longitude
    $bodyLines += "--$boundary"
    $bodyLines += 'Content-Disposition: form-data; name="longitude"'
    $bodyLines += ""
    $bodyLines += "10.1815"
    
    # City
    $bodyLines += "--$boundary"
    $bodyLines += 'Content-Disposition: form-data; name="city"'
    $bodyLines += ""
    $bodyLines += "Tunis"
    
    # Region
    $bodyLines += "--$boundary"
    $bodyLines += 'Content-Disposition: form-data; name="region"'
    $bodyLines += ""
    $bodyLines += "Tunis"
    
    # Image file
    $bodyLines += "--$boundary"
    $bodyLines += "Content-Disposition: form-data; name=""image""; filename=""$fileName"""
    $bodyLines += "Content-Type: application/octet-stream"
    $bodyLines += ""
    
    # Convert to bytes for multipart
    $headerBytes = [System.Text.Encoding]::UTF8.GetBytes(($bodyLines -join "`r`n") + "`r`n")
    $footerBytes = [System.Text.Encoding]::UTF8.GetBytes("`r`n--$boundary--`r`n")
    
    # Combine all parts
    $body = New-Object System.Collections.Generic.List[byte]
    $body.AddRange($headerBytes)
    $body.AddRange($fileContent)
    $body.AddRange($footerBytes)
    
    try {
        $response = Invoke-WebRequest -Uri $uri `
            -Method POST `
            -ContentType "multipart/form-data; boundary=$boundary" `
            -Body $body.ToArray() `
            -ErrorAction Stop
        
        $json = $response.Content | ConvertFrom-Json
        $sigId = $json.data.id
        
        Write-Host "✅ Signalement created: ID=$sigId" -ForegroundColor Green
        return $sigId
    }
    catch {
        Write-Error "Failed to create signalement: $_"
        exit 1
    }
}

function Invoke-PipelineTrigger {
    param(
        [int]$SignalementId,
        [string]$BaseUrl
    )
    
    $uri = "$BaseUrl/api/v1/process/$SignalementId"
    
    Write-Host "🚀 Triggering pipeline..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-WebRequest -Uri $uri `
            -Method POST `
            -ContentType "application/json" `
            -Body "{}" `
            -ErrorAction Stop
        
        $json = $response.Content | ConvertFrom-Json
        $status = $json.data.status
        
        Write-Host "✅ Pipeline triggered: status=$status" -ForegroundColor Green
    }
    catch {
        Write-Error "Failed to trigger pipeline: $_"
        exit 1
    }
}

function Poll-ProcessStatus {
    param(
        [int]$SignalementId,
        [string]$BaseUrl,
        [int]$PollIntervalSeconds,
        [int]$TimeoutSeconds
    )
    
    $uri = "$BaseUrl/api/v1/process/$SignalementId/status"
    $startTime = Get-Date
    $pollCount = 0
    
    Write-Host "⏳ Polling status (timeout: ${TimeoutSeconds}s, interval: ${PollIntervalSeconds}s)..." -ForegroundColor Cyan
    
    while ($true) {
        $elapsed = (Get-Date) - $startTime
        
        if ($elapsed.TotalSeconds -gt $TimeoutSeconds) {
            Write-Error "❌ Timeout: pipeline did not complete within ${TimeoutSeconds}s"
            exit 1
        }
        
        try {
            $response = Invoke-WebRequest -Uri $uri `
                -Method GET `
                -ErrorAction Stop
            
            $json = $response.Content | ConvertFrom-Json
            $polyStatus = $json.data.status
            $progress = $json.data.progress
            $pollCount++
            
            Write-Host "  [$([math]::Round($elapsed.TotalSeconds, 1))s] Status: $polyStatus | Progress: $progress% | Poll #$pollCount"
            
            if ($polyStatus -eq "completed") {
                Write-Host "✅ Pipeline completed!" -ForegroundColor Green
                return $json.data
            }
            elseif ($polyStatus -eq "failed") {
                Write-Host "❌ Pipeline failed!" -ForegroundColor Red
                $lastError = $json.data.last_error
                if ($lastError) {
                    Write-Host "Error details: $($lastError | ConvertTo-Json -Depth 3)"
                }
                exit 1
            }
            
            Start-Sleep -Seconds $PollIntervalSeconds
        }
        catch {
            Write-Error "Failed to poll status: $_"
            exit 1
        }
    }
}

function Display-Results {
    param(
        [object]$StatusData
    )
    
    Write-Host ""
    Write-Host "📊 Pipeline Results" -ForegroundColor Cyan
    Write-Host "─" * 60
    
    # Detections summary
    $detections = $statusData.detections
    if ($detections) {
        $boxCount = ($detections.boxes | Measure-Object).Count
        Write-Host "🔍 Detections:"
        Write-Host "   • Boxes count: $boxCount"
        
        if ($detections.warnings -and $detections.warnings.Count -gt 0) {
            Write-Host "   • Warnings:"
            foreach ($warning in $detections.warnings) {
                Write-Host "     - $warning" -ForegroundColor Yellow
            }
        }
        else {
            Write-Host "   • Warnings: none" -ForegroundColor Green
        }
    }
    
    # Annotated image path
    $outputs = $statusData.outputs
    if ($outputs.annotated_image_path) {
        Write-Host ""
        Write-Host "🖼️  Annotated Image:"
        Write-Host "   • Path: $($outputs.annotated_image_path)"
    }
    
    # Detection result alias
    $detectionResult = $statusData.detection_result
    if ($detectionResult) {
        Write-Host ""
        Write-Host "🎯 Detection Result (alias field):"
        Write-Host "   • Model: $($detectionResult.model_name)"
        Write-Host "   • Version: $($detectionResult.model_version)"
        Write-Host "   • Image dims: $($detectionResult.image_width)x$($detectionResult.image_height)"
        Write-Host "   • Boxes: $($detectionResult.boxes.Count)"
    }
    
    # Summary
    Write-Host ""
    Write-Host "─" * 60
    Write-Host "✅ Demo completed successfully!" -ForegroundColor Green
}

# ─────────────────────────────────────────────────────────────────────────────
# Main execution
# ─────────────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "🎯 UrbanFix AI - YOLO Pipeline Demo" -ForegroundColor Magenta
Write-Host "Backend: $BaseUrl" -ForegroundColor Magenta
Write-Host "Image: $ImagePath" -ForegroundColor Magenta
Write-Host ""

# Validate inputs
Test-ImagePath $ImagePath

# Execute pipeline
$sigId = New-SignalementWithImage -ImagePath $ImagePath -BaseUrl $BaseUrl
Invoke-PipelineTrigger -SignalementId $sigId -BaseUrl $BaseUrl
$statusData = Poll-ProcessStatus -SignalementId $sigId -BaseUrl $BaseUrl `
    -PollIntervalSeconds $PollIntervalSeconds -TimeoutSeconds $TimeoutSeconds

# Display results
Display-Results -StatusData $statusData

Write-Host ""
