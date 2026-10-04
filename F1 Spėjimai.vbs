' F1 spejimu programa - dukart spustelekite sita faila.
' Pirma karta automatiskai idiegia viska, ko reikia (programa\idiegti.bat), veliau
' paleidzia programa fone (be juodo lango) ir atidaro ja atskirame lange.

Option Explicit
Dim fso, sh, root, prog, py, url, i, edge, candidates, c

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
prog = root & "\programa"
py = prog & "\.venv\Scripts\python.exe"
url = "http://localhost:8501"

If Not fso.FileExists(py) Or Not fso.FileExists(prog & "\.venv\Scripts\streamlit.exe") Then
  MsgBox "Pirmas paleidimas: dabar bus idiegta tai, ko reikia programai (2-5 min., reikia interneto)." & vbCrLf & _
         "Atsidarys juodas langas - palaukite, kol jis uzsidarys.", vbInformation, "F1 spejimai"
  sh.Run "cmd /c """"" & prog & "\idiegti.bat"" auto""", 1, True
  If Not fso.FileExists(py) Then
    MsgBox "Diegimas nepavyko. Paleiskite programa\idiegti.bat ir perskaitykite klaidos pranesima.", _
           vbCritical, "F1 spejimai"
    WScript.Quit 1
  End If
End If

Function IsRunning()
  Dim http, ok
  ok = False
  On Error Resume Next
  Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
  http.setTimeouts 1000, 1000, 1000, 1000
  http.Open "GET", url & "/_stcore/health", False
  http.Send
  If Err.Number = 0 Then
    If http.Status = 200 Then ok = True
  End If
  Err.Clear
  On Error GoTo 0
  IsRunning = ok
End Function

If Not IsRunning() Then
  sh.CurrentDirectory = prog
  sh.Run """" & py & """ -m streamlit run ui.py --server.headless true --server.port 8501 " & _
         "--browser.gatherUsageStats false", 0, False
  For i = 1 To 120
    WScript.Sleep 500
    If IsRunning() Then Exit For
  Next
End If

' Atidarome kaip atskira programos langa (Edge), jei nera - numatytoje narsykleje
candidates = Array(sh.ExpandEnvironmentStrings("%ProgramFiles(x86)%") & "\Microsoft\Edge\Application\msedge.exe", _
                   sh.ExpandEnvironmentStrings("%ProgramFiles%") & "\Microsoft\Edge\Application\msedge.exe")
edge = ""
For Each c In candidates
  If edge = "" And fso.FileExists(c) Then edge = c
Next
If edge <> "" Then
  sh.Run """" & edge & """ --app=" & url & " --window-size=1400,900", 1, False
Else
  sh.Run url, 1, False
End If
