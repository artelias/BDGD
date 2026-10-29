param([ValidateSet('start','status','stop','resume')][string]$Action='status',[string]$Config="$PSScriptRoot\pilot.json")
$ErrorActionPreference='Stop'
$cfg=Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$out=[System.IO.Path]::GetFullPath($cfg.output)
if (-not $out.StartsWith('D:\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Output must be on D:' }
$python='D:\NUCLEO_BDGD_2025\motor_v2\.venv\Scripts\python.exe'
$root=Split-Path $PSScriptRoot -Parent
New-Item -ItemType Directory -Force $out | Out-Null
if($Action -eq 'status'){if(Test-Path "$out\status.json"){Get-Content "$out\status.json"};exit}
if($Action -eq 'stop'){Set-Content -LiteralPath "$out\STOP" -Value 'requested';exit}
if(Test-Path "$out\executor.lock"){
 $owner=Get-Content "$out\executor.lock" -Raw | ConvertFrom-Json
 if(Get-Process -Id $owner.pid -ErrorAction SilentlyContinue){throw 'Executor may already be active. Inspect status before starting.'}
}
if(Test-Path "$out\STOP"){Remove-Item -LiteralPath "$out\STOP"}
$env:OMP_NUM_THREADS='2';$env:MKL_NUM_THREADS='2';$env:OPENBLAS_NUM_THREADS='2'
$env:TEMP="$out\tmp";$env:TMP=$env:TEMP
New-Item -ItemType Directory -Force $env:TEMP | Out-Null
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
Start-Process -FilePath $python -ArgumentList @('-u','-m','motor_v2.runner','--config',('"'+[System.IO.Path]::GetFullPath($Config)+'"')) -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput "$out\run-$stamp.log" -RedirectStandardError "$out\run-$stamp.err" -PassThru | Select-Object Id
