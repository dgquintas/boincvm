Set WshShell = CreateObject("WScript.Shell")
WshShell.Run Chr(34) & WScript.Arguments.item(0) & "\VBoxHeadless.exe" & Chr(34)  & " -v off -s " & WScript.Arguments.item(1), 0
Set WshShell = Nothing

