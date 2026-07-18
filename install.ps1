if (!$LLAMA_BUCKET) { $LLAMA_BUCKET = $env:LLAMA_BUCKET }
if (!$LLAMA_BUCKET) { $LLAMA_BUCKET = "ggml-org/install.sh" }
$REPO = "https://huggingface.co/buckets/$LLAMA_BUCKET/resolve"
$WebParams = @{}

$CudaDlls = "cublas64_12.dll","cublasLt64_12.dll"

if ($env:HF_TOKEN) {
    $WebParams["Headers"] = @{ "Authorization" = "Bearer $env:HF_TOKEN" }
}

function Die {
    param([string[]]$Messages)
    $Messages | % { [Console]::Error.WriteLine($_) }
    exit 111
}

function Download {
    param($FILE, [string[]]$URL)
    if (Test-Path "$DIR\$FILE") {
        return
    }
    "Downloading $FILE..."
    foreach ($U in $URL) {
        try {
            if ($U -like "*.zst") {
                Download "unzstd.exe" "$ARCH/windows/unzstd.exe"
                Invoke-RestMethod "$REPO/$LLAMA_VERSION/$U" -OutFile "$DIR\tmp.zst" @WebParams
                Start-Process -FilePath "$DIR\unzstd.exe" -RedirectStandardInput "$DIR\tmp.zst" -RedirectStandardOutput "$DIR\$FILE" -NoNewWindow -Wait
                Remove-Item "$DIR\tmp.zst"
            } else {
                Invoke-RestMethod "$REPO/$LLAMA_VERSION/$U" -OutFile "$DIR\$FILE" @WebParams
            }
            return
        } catch {
            if ($U -eq $URL[-1]) { Die "Failed to download" }
        }
    }
}

function DownloadCudaDeps {
    param([string]$CODE)
    $Cached = (Test-Path $CudaSentinel) -and ((Get-Content $CudaSentinel -Raw).Trim() -eq $CODE)
    foreach ($d in $CudaDlls) { if (-not (Test-Path "$INSTALL_DIR\$d")) { $Cached = $false } }
    if ($Cached) {
        "CUDA runtime already cached (code $CODE), reusing"
        foreach ($d in $CudaDlls) { Copy-Item "$INSTALL_DIR\$d" "$DIR\$d" -Force }
    } else {
        "Downloading CUDA runtime (code $CODE)..."
        foreach ($d in $CudaDlls) { Download "$d" "$ARCH/windows/cuda/deps/$CODE/$d.zst" }
    }
    $script:CudaCode = $CODE
}

function PersistCuda {
    if (-not $script:CudaCode) { return }
    foreach ($d in $CudaDlls) {
        if (Test-Path "$DIR\$d") { Move-Item "$DIR\$d" "$INSTALL_DIR\$d" -Force }
    }
    Set-Content -Path $CudaSentinel -Value $script:CudaCode -NoNewline
}

function ProbeCUDA {
    if ($env:SKIP_CUDA) { return }
    "Probing CUDA..."
    Download "cuda-probe.exe" @("$ARCH/windows/cuda/probe/probe.exe.zst", "$ARCH/windows/cuda/probe/probe.zst")
    $CONFIG = & "$DIR\cuda-probe.exe" 2>$null
    if ($LASTEXITCODE) { return }
    "Found: $CONFIG"
    $parts  = -split $CONFIG
    $CONFIG = $parts[0]
    $SDK    = $parts[1]
    Download "llama.exe" @("$ARCH/windows/cuda/$CONFIG/llama-app.exe.zst", "$ARCH/windows/cuda/$CONFIG/llama-app.zst")
    if ($SDK) { DownloadCudaDeps $SDK }
}

function ProbeVulkan {
    if ($env:SKIP_VULKAN) { return }
    "Probing Vulkan..."
    Download "vulkan-probe.exe" @("$ARCH/windows/vulkan/probe/probe.exe.zst", "$ARCH/windows/vulkan/probe/probe.zst")
    Download "featcode.exe" "$ARCH/windows/featcode.exe"
    & "$DIR\vulkan-probe.exe" 2>$null
    if ($LASTEXITCODE) { return }
    $CONFIG = & "$DIR\featcode.exe" 2>$null
    & "$DIR\featcode.exe" $CONFIG 2>$null | % { "Found: $_" }
    Download "llama.exe" @("$ARCH/windows/vulkan/$CONFIG/llama-app.exe.zst", "$ARCH/windows/vulkan/$CONFIG/llama-app.zst")
}

function ProbeCPU {
    "Probing CPU..."
    Download "featcode.exe" "$ARCH/windows/featcode.exe"
    $CONFIG = & "$DIR\featcode.exe" 2>$null
    & "$DIR\featcode.exe" $CONFIG 2>$null | % { "Found: $_" }
    Download "llama.exe" @("$ARCH/windows/cpu/$CONFIG/llama-app.exe.zst", "$ARCH/windows/cpu/$CONFIG/llama-app.zst")
}

function Main {
    switch ($env:PROCESSOR_ARCHITECTURE) {
        "ARM64" { $ARCH = "aarch64" }
        "AMD64" { $ARCH = "x86_64"  }
        default { Die "Arch not supported" }
    }

    if (!$LLAMA_VERSION) { $LLAMA_VERSION = $env:LLAMA_VERSION }
    if (!$LLAMA_VERSION) { $LLAMA_VERSION = Invoke-RestMethod "$REPO/latest" @WebParams }
    if (!$LLAMA_VERSION) { Die "No version found" }
    "Version: $LLAMA_VERSION"

    $INSTALL_DIR = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
    $DIR = Join-Path $env:LOCALAPPDATA "llama-app"
    $CudaSentinel = Join-Path $INSTALL_DIR "cuda-code"
    Remove-Item $DIR -Recurse -Force 2>$null
    New-Item -Path $DIR -Force -ItemType "Directory" | Out-Null

    if (!(Test-Path "$DIR\llama.exe")) { ProbeCUDA   }
    if (!(Test-Path "$DIR\llama.exe")) { ProbeVulkan }
    if (!(Test-Path "$DIR\llama.exe")) { ProbeCPU    }
    if (!(Test-Path "$DIR\llama.exe")) {
        Die "No prebuilt llama binary is available for your system." `
            "Please compile llama.cpp from source instead."
    }
    if ($env:SKIP_INSTALL) {
        "Installation skipped, SKIP_INSTALL is set"
        return
    }
    $Version = & "$DIR\llama.exe" version 2>$null

    if ($LASTEXITCODE) {
        Die "Downloaded llama binary failed to run"
    }
    if ("$Version" -notlike "$LLAMA_VERSION-*") {
        Die "Version mismatch: expected $LLAMA_VERSION, got $Version"
    }
    if (Test-Path "$INSTALL_DIR\llama.exe") {
        Move-Item "$INSTALL_DIR\llama.exe" "$DIR\llama.exe.old" -Force
    }
    Move-Item "$DIR\llama.exe" "$INSTALL_DIR\llama.exe" -Force
    PersistCuda
    Remove-Item $DIR -Recurse -Force 2>$null

    "Installation completed successfully"
    ""
    "Please run the following command to start it:"
    ""
    "  llama.exe serve"
    ""
}

Main @args
