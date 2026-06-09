if (!$LLAMA_BUCKET) { $LLAMA_BUCKET = $env:LLAMA_BUCKET }
if (!$LLAMA_BUCKET) { $LLAMA_BUCKET = "ggml-org/install.sh" }
$REPO = "https://huggingface.co/buckets/$LLAMA_BUCKET/resolve"

function Die {
    param([string[]]$Messages)
    $Messages | % { [Console]::Error.WriteLine($_) }
    exit 111
}

function Download {
    param($FILE, $URL)
    if (Test-Path "$DIR\$FILE") {
        return
    }
    "Downloading $FILE..."
    try {
        if ($URL -like "*.zst") {
            Download "unzstd.exe" "$ARCH/windows/unzstd.exe"
            Invoke-RestMethod "$REPO/$LLAMA_VERSION/$URL" -OutFile "$DIR\tmp.zst"
            Start-Process -FilePath "$DIR\unzstd.exe" -RedirectStandardInput "$DIR\tmp.zst" -RedirectStandardOutput "$DIR\$FILE" -NoNewWindow -Wait
            Remove-Item "$DIR\tmp.zst"
        } else {
            Invoke-RestMethod "$REPO/$LLAMA_VERSION/$URL" -OutFile "$DIR\$FILE"
        }
    } catch {
        Die "Failed to download"
    }
}

function ProbeVulkan {
    if ($env:SKIP_VULKAN) { return }
    "Probing Vulkan..."
    Download "vulkan-probe.exe" "$ARCH/windows/vulkan/probe/probe.zst"
    Download "featcode.exe" "$ARCH/windows/featcode.exe"
    & "$DIR\vulkan-probe.exe" 2>$null
    if ($LASTEXITCODE) { return }
    $CONFIG = & "$DIR\featcode.exe" 2>$null
    & "$DIR\featcode.exe" $CONFIG 2>$null | % { "Found: $_" }
    Download "llama.exe" "$ARCH/windows/vulkan/$CONFIG/llama-app.zst"
}

function ProbeCPU {
    "Probing CPU..."
    Download "featcode.exe" "$ARCH/windows/featcode.exe"
    $CONFIG = & "$DIR\featcode.exe" 2>$null
    & "$DIR\featcode.exe" $CONFIG 2>$null | % { "Found: $_" }
    Download "llama.exe" "$ARCH/windows/cpu/$CONFIG/llama-app.zst"
}

function Main {
    switch ($env:PROCESSOR_ARCHITECTURE) {
        "ARM64" { $ARCH = "aarch64" }
        "AMD64" { $ARCH = "x86_64"  }
        default { Die "Arch not supported" }
    }

    if (!$LLAMA_VERSION) { $LLAMA_VERSION = $env:LLAMA_VERSION }
    if (!$LLAMA_VERSION) { $LLAMA_VERSION = Invoke-RestMethod "$REPO/latest" }
    if (!$LLAMA_VERSION) { Die "No version found" }
    "Version: $LLAMA_VERSION"

    $INSTALL_DIR = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
    $DIR = Join-Path $env:LOCALAPPDATA "llama-app"
    Remove-Item $DIR -Recurse -Force 2>$null
    New-Item -Path $DIR -Force -ItemType "Directory" | Out-Null

    if (!(Test-Path "$DIR\llama.exe")) { ProbeVulkan }
    if (!(Test-Path "$DIR\llama.exe")) { ProbeCPU    }
    if (!(Test-Path "$DIR\llama.exe")) {
        Die "No prebuilt llama binary is available for your system." `
            "Please compile llama.cpp from source instead."
    }

    if (Test-Path "$INSTALL_DIR\llama.exe") {
        Move-Item "$INSTALL_DIR\llama.exe" "$DIR\llama.exe.old" -Force
    }
    Move-Item "$DIR\llama.exe" "$INSTALL_DIR\llama.exe" -Force
    Remove-Item $DIR -Recurse -Force 2>$null

    if ($args.Length -gt 0) {
        & llama.exe @args
        exit $LASTEXITCODE
    }
    "Installation completed successfully"
    ""
    "Please run the following command to start it:"
    ""
    "  llama.exe serve"
    ""
}

Main @args
