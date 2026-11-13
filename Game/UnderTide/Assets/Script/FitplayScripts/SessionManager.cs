using System;
using System.IO;
using Process = System.Diagnostics.Process;
using ProcessStartInfo = System.Diagnostics.ProcessStartInfo;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.InputSystem;

public class SessionManager : MonoBehaviour
{
    private static SessionManager instance;
    public static SessionManager Instance => instance;

    [Header("Player Control")]
    public MonoBehaviour playerMovementScript;

    [Header("Settings")]
    public float pollIntervalSeconds = 1.0f;
    public float freshnessWindowSeconds = 60f;

    public bool IsUnlocked => gameUnlocked;
    public bool IsExitMenuOpen => menuOpen;

    // ── Events other scripts subscribe to — no more direct UI references here ──
    public event Action<bool> OnLockStateChanged;   // true = unlocked
    public event Action<float> OnTimeUpdated;        // seconds remaining
    public event Action<bool> OnMenuToggled;          // true = menu open

    private string sessionPath;
    private string projectRoot;
    private float timeRemaining = 0f;
    private bool gameUnlocked = false;
    private bool returnedTimeOnExit = false;
    private float pollTimer = 0f;
    private bool menuOpen = false;

    
    private LevelUIReferences currentUI;

    void Awake()
    {
        if (instance != null && instance != this)
        {
            Destroy(gameObject);
            return;
        }

        instance = this;
        DontDestroyOnLoad(gameObject);

        sessionPath = FindSharedFile("session.json");
        SceneManager.sceneLoaded += OnSceneLoaded;
    }

    void OnDestroy()
    {
        if (instance == this)
        {
            SceneManager.sceneLoaded -= OnSceneLoaded;
            instance = null;
        }
    }

    // Called by LevelUIReferences.OnEnable() in each scene
    public void RegisterSceneUI(LevelUIReferences ui)
    {
        currentUI = ui;
        // Re-apply current state to the newly registered UI
        OnLockStateChanged?.Invoke(gameUnlocked);
        OnTimeUpdated?.Invoke(timeRemaining);
        OnMenuToggled?.Invoke(menuOpen);
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
        projectRoot = Path.GetDirectoryName(Application.dataPath);
        return Path.GetFullPath(Path.Combine(projectRoot, "shared", filename));
    }

    void Start()
    {
        ReadSession();
#if !UNITY_EDITOR
        if (!gameUnlocked) LaunchFitPlayApp();
#endif
    }

    void Update()
    {
        HandleMenuHotkeys();

        pollTimer += Time.unscaledDeltaTime;
        if (pollTimer >= pollIntervalSeconds)
        {
            pollTimer = 0f;
            if (!gameUnlocked) ReadSession();
        }

        if (!gameUnlocked) return;

        timeRemaining -= Time.deltaTime;
        if (timeRemaining > 0f)
            OnTimeUpdated?.Invoke(timeRemaining);
        else
            OnTimeExpired();
    }

    bool TryReadSession(out SessionData data)
    {
        data = null;
        for (int i = 0; i < 5; i++)
        {
            try
            {
                if (!File.Exists(sessionPath)) return false;
                data = JsonUtility.FromJson<SessionData>(File.ReadAllText(sessionPath));
                return data != null;
            }
            catch (Exception e)
            {
                if (i == 4) Debug.LogWarning("[SessionManager] Read failed: " + e.Message);
                else System.Threading.Thread.Sleep(40);
            }
        }
        return false;
    }

    bool TryWriteSession(SessionData data)
    {
        string json = JsonUtility.ToJson(data, true);
        for (int i = 0; i < 5; i++)
        {
            try { File.WriteAllText(sessionPath, json); return true; }
            catch (Exception e)
            {
                if (i == 4) Debug.LogError("[SessionManager] Write failed: " + e.Message);
                else System.Threading.Thread.Sleep(40);
            }
        }
        return false;
    }

    void ReadSession()
    {
        if (!TryReadSession(out SessionData data)) { SetLocked(); return; }

        ActiveSession a = data.active_session;
        if (a != null && a.status == "unlocked" && a.seconds_remaining > 0 && IsTimestampFresh(a.started_at))
        {
            UnlockGame(a.seconds_remaining);
            ClaimActiveSession(data);
        }
        else
        {
            if (a != null && a.status == "unlocked" && a.seconds_remaining > 0)
                RefundStaleSession(data);
            SetLocked();
        }
    }

    bool IsTimestampFresh(string timestampStr)
    {
        if (string.IsNullOrEmpty(timestampStr)) return false;
        if (!DateTime.TryParse(timestampStr, out DateTime writtenTime)) return false;
        return (DateTime.Now - writtenTime).TotalSeconds <= freshnessWindowSeconds;
    }

    void ClaimActiveSession(SessionData data)
    {
        data.active_session.status = "running";
        TryWriteSession(data);
    }

    void RefundStaleSession(SessionData data)
    {
        int cap = data.max_bank_seconds > 0 ? data.max_bank_seconds : 3600;
        data.banked_seconds = Mathf.Min(data.banked_seconds + data.active_session.seconds_remaining, cap);
        data.active_session = new ActiveSession { status = "locked", seconds_remaining = 0, started_at = "" };
        TryWriteSession(data);
    }

    void ForceLockActiveSession()
    {
        if (!TryReadSession(out SessionData data)) return;
        data.active_session = new ActiveSession { status = "locked", seconds_remaining = 0, started_at = "" };
        TryWriteSession(data);
    }

    void UnlockGame(int secondsRemaining)
    {
        timeRemaining = secondsRemaining;
        gameUnlocked = true;
        returnedTimeOnExit = false;

        Time.timeScale = 1f;
        AudioListener.pause = false;
        if (playerMovementScript != null) playerMovementScript.enabled = true;

        OnLockStateChanged?.Invoke(true);
        OnTimeUpdated?.Invoke(timeRemaining);
        RestoreUnityWindow();
    }

    void SetLocked()
    {
        gameUnlocked = false;
        Time.timeScale = 0f;
        AudioListener.pause = true;
        if (playerMovementScript != null) playerMovementScript.enabled = false;

        OnLockStateChanged?.Invoke(false);
    }

    void OnTimeExpired()
    {
        gameUnlocked = false;
        timeRemaining = 0f;
        OnTimeUpdated?.Invoke(0f);

        ForceLockActiveSession();
        SetLocked();
        LaunchFitPlayApp();
    }

    private void OnSceneLoaded(Scene scene, LoadSceneMode mode)
    {
        currentUI = null; // old scene's UI is gone; new scene's LevelUIReferences will re-register itself

        PlayerMovement player = FindFirstObjectByType<PlayerMovement>();
        if (player != null) playerMovementScript = player;
    }

    private void ReturnUnusedTimeToBank()
    {
        if (returnedTimeOnExit || !gameUnlocked) return;
        int secondsToReturn = Mathf.FloorToInt(timeRemaining);
        if (secondsToReturn <= 0) return;

        if (!TryReadSession(out SessionData data)) return;
        int cap = data.max_bank_seconds > 0 ? data.max_bank_seconds : 3600;
        data.banked_seconds = Mathf.Min(data.banked_seconds + secondsToReturn, cap);
        data.active_session = new ActiveSession { status = "locked", seconds_remaining = 0, started_at = "" };

        if (!TryWriteSession(data)) return;
        returnedTimeOnExit = true;
        gameUnlocked = false;
    }

    private void OnApplicationQuit() => ReturnUnusedTimeToBank();

    public void ToggleExitMenu()
    {
        menuOpen = !menuOpen;
        OnMenuToggled?.Invoke(menuOpen);

        if (gameUnlocked)
        {
            Time.timeScale = menuOpen ? 0f : 1f;
            //AudioListener.pause = menuOpen;
        }
    }

    public void CloseExitMenu()
    {
        if (!menuOpen) return;
        menuOpen = false;
        OnMenuToggled?.Invoke(false);
        if (gameUnlocked) { Time.timeScale = 1f;  }
    }

    public void ExitGame()
    {
        ReturnUnusedTimeToBank();
        Application.Quit();
    }

    void HandleMenuHotkeys()
    {
        bool escape = Keyboard.current != null && Keyboard.current.escapeKey.wasPressedThisFrame;
        bool start = Gamepad.current != null && Gamepad.current.startButton.wasPressedThisFrame;
        if (escape || start) ToggleExitMenu();
    }

    public void OpenFitPlay() => LaunchFitPlayApp();

    void LaunchFitPlayApp()
    {
        try
        {
            string fitplayDir = Path.Combine(projectRoot, "python_app");
            string mainPy = Path.Combine(fitplayDir, "main.py");
#if UNITY_STANDALONE_WIN
            string pythonExe = Path.GetFullPath(Path.Combine(projectRoot, "venv", "Scripts", "python.exe"));
#else
            string pythonExe = Path.GetFullPath(Path.Combine(projectRoot, "venv", "bin", "python3"));
#endif
            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = "\"" + mainPy + "\" --resume-existing",
                WorkingDirectory = fitplayDir,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            Process.Start(psi);
        }
        catch (Exception e)
        {
            Debug.LogError("[SessionManager] Failed to launch FitPlay: " + e.Message);
        }
    }

    void RestoreUnityWindow()
    {
#if UNITY_STANDALONE_WIN
        IntPtr hwnd = GetUnityWindow();
        if (hwnd != IntPtr.Zero) { ShowWindow(hwnd, SW_RESTORE); SetForegroundWindow(hwnd); }
#endif
    }

#if UNITY_STANDALONE_WIN
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr hWnd);
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr hWnd);
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
    [System.Runtime.InteropServices.DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    const int SW_RESTORE = 9;

    IntPtr GetUnityWindow()
    {
        IntPtr result = IntPtr.Zero;
        uint currentProcessId = (uint)Process.GetCurrentProcess().Id;
        EnumWindows((hWnd, lParam) =>
        {
            GetWindowThreadProcessId(hWnd, out uint windowProcessId);
            if (windowProcessId == currentProcessId && IsWindowVisible(hWnd)) { result = hWnd; return false; }
            return true;
        }, IntPtr.Zero);
        return result;
    }
#endif
}

[Serializable]
public class SessionData { public int banked_seconds; public int max_bank_seconds; public ActiveSession active_session; }

[Serializable]
public class ActiveSession { public string status; public int seconds_remaining; public string started_at; }