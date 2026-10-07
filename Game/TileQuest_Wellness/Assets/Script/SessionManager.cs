using System;
using System.IO;
using Process = System.Diagnostics.Process;
using ProcessStartInfo = System.Diagnostics.ProcessStartInfo;
using UnityEngine;
using TMPro;
using UnityEngine.SceneManagement;

public class SessionManager : MonoBehaviour
{
    private static SessionManager instance;
    
    [Header("UI References — drag these in from your scene")]
    public TMP_Text timerText;
    public GameObject gamePanel;
    public GameObject lockedPanel;

    [Header("Player Control")]
    public MonoBehaviour playerMovementScript;  // drag your PlayerMovement component here

    [Header("Settings")]
    public float pollIntervalSeconds = 1.0f;
    public float freshnessWindowSeconds = 60f;

    private string sessionPath;
    private string projectRoot;
    private float timeRemaining = 0f;
    private bool gameUnlocked = false;
    private float pollTimer = 0f;

    void Awake()
    {
        if (instance != null)
        {
            Destroy(gameObject);
            return;
        }
        instance= this;
        DontDestroyOnLoad(gameObject);
        sessionPath = FindSharedFile("session.json");
        SceneManager.sceneLoaded += OnSceneLoaded;
        Debug.Log("[SessionManager] Looking for session file at: " + sessionPath);
    }

    string FindSharedFile(string filename)
    {
        string current = Path.GetDirectoryName(Application.dataPath);

        for (int i = 0; i < 6; i++)
        {
            string sharedCandidate = Path.Combine(current, "shared");
            if (Directory.Exists(sharedCandidate))
            {
                projectRoot = current;
                return Path.GetFullPath(Path.Combine(sharedCandidate, filename));
            }

            DirectoryInfo parent = Directory.GetParent(current);
            if (parent == null) break;
            current = parent.FullName;
        }

        Debug.LogError("[SessionManager] Could not locate shared/ folder anywhere above: " + Application.dataPath);
        projectRoot = Path.GetDirectoryName(Application.dataPath);
        return Path.GetFullPath(Path.Combine(projectRoot, "shared", filename));
    }

    void Start()
    {
        ReadSession();
    }

    void Update()
    {
        pollTimer += Time.unscaledDeltaTime;
        if (pollTimer >= pollIntervalSeconds)
        {
            pollTimer = 0f;
            if (!gameUnlocked)
            {
                ReadSession();
            }
        }

        if (gameUnlocked && timeRemaining > 0)
        {
            timeRemaining -= Time.deltaTime;
            UpdateTimerDisplay();
        }
        else if (gameUnlocked && timeRemaining <= 0)
        {
            OnTimeExpired();
        }
    }

    void ReadSession()
    {
        if (!File.Exists(sessionPath))
        {
            Debug.LogWarning("[SessionManager] session.json not found — showing locked screen.");
            ShowLocked();
            return;
        }

        try
        {
            string json = File.ReadAllText(sessionPath);
            SessionData data = JsonUtility.FromJson<SessionData>(json);

            if (data != null && data.status == "unlocked" && data.minutes_earned > 0
                && IsTimestampFresh(data.timestamp))
            {
                UnlockGame(data.minutes_earned);
                ConsumeSession();
            }
            else
            {
                if (data != null && data.status == "unlocked" && !IsTimestampFresh(data.timestamp))
                {
                    Debug.LogWarning("[SessionManager] Stale unlock detected — ignoring and re-locking.");
                    ForceLockSession();
                }
                ShowLocked();
            }
        }
        catch (Exception e)
        {
            Debug.LogError("[SessionManager] Failed to read session.json: " + e.Message);
            ShowLocked();
        }
    }

    bool IsTimestampFresh(string timestampStr)
    {
        if (string.IsNullOrEmpty(timestampStr)) return false;

        DateTime writtenTime;
        bool parsed = DateTime.TryParse(timestampStr, out writtenTime);
        if (!parsed) return false;

        double secondsSinceWrite = (DateTime.Now - writtenTime).TotalSeconds;
        return secondsSinceWrite <= freshnessWindowSeconds;
    }

    void UnlockGame(int minutesEarned)
    {
        timeRemaining = minutesEarned * 60f;
        gameUnlocked = true;

        ResumeGame();
        RestoreUnityWindow();

        if (gamePanel != null)   gamePanel.SetActive(true);
        if (lockedPanel != null) lockedPanel.SetActive(false);
        if (playerMovementScript != null) playerMovementScript.enabled = true;

        Debug.Log($"[SessionManager] Unlocked! {minutesEarned} minutes of playtime.");
    }

    void ShowLocked()
    {
        gameUnlocked = false;

        PauseGame();

        if (gamePanel != null)   gamePanel.SetActive(false);
        if (lockedPanel != null) lockedPanel.SetActive(true);
        if (playerMovementScript != null) playerMovementScript.enabled = false;
    }

    void ConsumeSession()
    {
        ForceLockSession();
    }

    void ForceLockSession()
    {
        SessionData locked = new SessionData
        {
            status = "locked",
            minutes_earned = 0,
            activity_done = "",
            timestamp = ""
        };

        try
        {
            File.WriteAllText(sessionPath, JsonUtility.ToJson(locked, true));
        }
        catch (Exception e)
        {
            Debug.LogError("[SessionManager] Failed to reset session.json: " + e.Message);
        }
    }

    void PauseGame()
    {
        Time.timeScale = 0f;
        AudioListener.pause = true;
    }

    void ResumeGame()
    {
        Time.timeScale = 1f;
        AudioListener.pause = false;
    }

    void UpdateTimerDisplay()
{
    if (timerText == null) return;

    float clamped = Mathf.Max(timeRemaining, 0f);   // never show negative time
    int minutes = Mathf.FloorToInt(clamped / 60f);
    int seconds = Mathf.FloorToInt(clamped % 60f);
    timerText.text = $"{minutes:00}:{seconds:00}";
}

    void OnTimeExpired()
    {
        Debug.Log("[SessionManager] Time's up! Pausing game and re-locking session.");
        gameUnlocked = false;

        ForceLockSession();
        ShowLocked();
        LaunchFitPlayApp();
    }

    void LaunchFitPlayApp()
    {
        string fitplayDir = Path.Combine(projectRoot, "python_app");

        Debug.Log("[SessionManager] Launching FitPlay app...");

        try
        {
#if UNITY_STANDALONE_WIN
            string pythonExe = Path.GetFullPath(Path.Combine(projectRoot, "venv", "Scripts", "python.exe"));
            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = "\"" + Path.Combine(fitplayDir, "main.py") + "\" --resume-existing",
                UseShellExecute = false
            };
            Process.Start(psi);
#elif UNITY_STANDALONE_OSX || UNITY_STANDALONE_LINUX
            string pythonExe = Path.GetFullPath(Path.Combine(projectRoot, "venv", "bin", "python3"));
            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = "\"" + Path.Combine(fitplayDir, "main.py") + "\" --resume-existing",
                UseShellExecute = false
            };
            Process.Start(psi);
#endif
            MinimizeGameWindow();
        }
        catch (Exception e)
        {
            Debug.LogError("[SessionManager] Failed to launch FitPlay: " + e.Message);
        }
    }

    void MinimizeGameWindow()
    {
#if UNITY_STANDALONE_WIN
        var windowPtr = GetActiveWindow();
        ShowWindow(windowPtr, SW_MINIMIZE);
#endif
    }

    void RestoreUnityWindow()
{
#if UNITY_STANDALONE_WIN

    IntPtr hwnd = GetUnityWindow();

    if (hwnd != IntPtr.Zero)
    {
        ShowWindow(hwnd, SW_RESTORE);
        SetForegroundWindow(hwnd);

        Debug.Log("[SessionManager] Unity window restored and brought to front.");
    }
    else
    {
        Debug.LogWarning("[SessionManager] Could not find Unity window.");
    }

#endif
}

private void OnSceneLoaded(Scene scene, LoadSceneMode mode)
{
    GameObject canvas = GameObject.Find("Canvas");

    GameObject timer = GameObject.Find("TimerText");
    GameObject gamePanelObject = GameObject.Find("GamePanel");
    Transform locked = canvas.transform.Find("LockedPanel");

    if (timer != null)
        timerText = timer.GetComponent<TMP_Text>();

    if (gamePanelObject != null)
        gamePanel = gamePanelObject;

    if (locked != null)
        lockedPanel = locked.gameObject;
}


#if UNITY_STANDALONE_WIN 
    [System.Runtime.InteropServices.DllImport("user32.dll")] 
    static extern IntPtr GetActiveWindow(); 

    [System.Runtime.InteropServices.DllImport("user32.dll")] 
    static extern bool ShowWindow(IntPtr hWnd, int nCmdShow); 

    const int SW_MINIMIZE = 6;

    // ADD THESE
    [System.Runtime.InteropServices.DllImport("user32.dll")]
    static extern bool SetForegroundWindow(IntPtr hWnd);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    static extern bool IsWindowVisible(IntPtr hWnd);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    static extern uint GetWindowThreadProcessId(
        IntPtr hWnd,
        out uint processId
    );

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    static extern bool EnumWindows(
        EnumWindowsProc lpEnumFunc,
        IntPtr lParam
    );

    delegate bool EnumWindowsProc(
        IntPtr hWnd,
        IntPtr lParam
    );

    const int SW_RESTORE = 9;

    // ADD THIS
    IntPtr GetUnityWindow()
    {
        IntPtr result = IntPtr.Zero;

        uint currentProcessId =
            (uint)Process.GetCurrentProcess().Id;

        EnumWindows(
            (hWnd, lParam) =>
            {
                uint windowProcessId;

                GetWindowThreadProcessId(
                    hWnd,
                    out windowProcessId
                );

                if (
                    windowProcessId == currentProcessId &&
                    IsWindowVisible(hWnd)
                )
                {
                    result = hWnd;
                    return false;
                }

                return true;
            },
            IntPtr.Zero
        );

        return result;
    }
#endif
}




[Serializable]
public class SessionData
{
    public string status;
    public int minutes_earned;
    public string activity_done;
    public string timestamp;
}