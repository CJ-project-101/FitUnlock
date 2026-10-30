Set sh  = CreateObject("WScript.Shell")
    sh.Environment("Process")("PYTHONUTF8") = "1"
Set fso = CreateObject("Scripting.FileSystemObject")

root = fso.GetParentFolderName(WScript.ScriptFullName)
py   = """" & root & "\venv\Scripts\python.exe"""

sh.CurrentDirectory = root & "\reels\server"
sh.Run "cmd /c " & """" & py & " -m uvicorn main:app --port 8000 > server.log 2>&1""", 0, False

WScript.Sleep 3000

sh.CurrentDirectory = root & "\python_app"
sh.Run "cmd /c " & """" & py & " main.py > fitplay.log 2>&1""", 0, False

WScript.Sleep 3000

' Unity game (set the path to your build's exe, relative to this folder)
' sh.Run """" & root & "\game\YourGame.exe""", 1, False