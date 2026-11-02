Option Explicit
Dim WshShell, fso, scriptDir

Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = scriptDir

WshShell.Run "pythonw.exe """ & scriptDir & "\app.py""", 0, False
