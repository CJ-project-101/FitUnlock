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
    public static SessionManager Instance => instance;

    [Header("UI (re-bound automatically after every scene load)")]
    public TMP_Text timerText;
    public GameObject gamePanel;
    public GameObject lockedPanel;
    public GameObject exitPanel;

    [Header("Object names used to re-find the UI in each scene")]
    public string timerTextName   = "TimerText";
    public string gamePanelName   = "GamePanel";
    public string lockedPanelName = "LockedPanel";
    public string exitPanelName   = "ExitPanel";   // set this to your exit menu's name

    [Header("Player Control")]
    public MonoBehaviour playerMovementScript;

    [Header("Settings")]
    public float pollIntervalSeconds = 1.0f;
    public float freshnessWindowSeconds = 60f;

    private string sessionPath;
    private string projectRoot;
    private float timeRemaining = 0f;
    private bool gameUnlocked = false;
    private bool returnedTimeOnExit = false;
    private float pollTimer = 0f;

    // ── Lifecycle ───────────────────────────────────────────────────────────
    void Awake()
    {
        if (instance != null && instance != this)
        {
            enabled = false;            // stops Start()/Update() on the duplicate
            Destroy(gameObject);
            return;
        }

        instance = this;
        DontDestroyOnLoad(gameObject);

        sessionPath = FindSharedFile("session.json");
        SceneManager.sceneLoaded += OnSceneLoaded;
        Debug.Log("[SessionManager] Looking for session file at: " + sessionPath);
    }

    void OnDestroy()
    {
        if (instance == this)
        {
            SceneManager.sceneLoaded -= OnSceneLoaded;
            instance = null;
        }
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

        Debug.LogError("[SessionManager] Could not locate shared/ folder above: " + Application.dataPath);
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
        pollTimer += Time.unscaledDeltaTime;
        if (pollTimer >= pollIntervalSeconds)
        {
            pollTimer = 0f;
            if (!gameUnlocked) ReadSession();
        }

        if (!gameUnlocked) return;

        timeRemaining -= Time.deltaTime;
        if (timeRemaining > 0f) UpdateTimerDisplay();
        else OnTimeExpired();
    }

    // ── session.json access (with retries: Python may have the file open) ──
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
            try
            {
                File.WriteAllText(sessionPath, json);
                return true;
            }
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
        if (!TryReadSession(out SessionData data))
        {
            ShowLocked();
            return;
        }

        ActiveSession a = data.active_session;

        if (a != null && a.status == "unlocked" && a.seconds_remaining > 0
            && IsTimestampFresh(a.started_at))
        {
            UnlockGame(a.seconds_remaining);
            ClaimActiveSession(data);
        }
        else
        {
            // Time was deducted from the bank by FitPlay but never used: give it back.
            if (a != null && a.status == "unlocked" && a.seconds_remaining > 0)
                RefundStaleSession(data);

            ShowLocked();
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
        data.active_session.status = "running";    // cannot be unlocked a second time
        TryWriteSession(data);
    }

    void RefundStaleSession(SessionData data)
    {
        int cap = data.max_bank_seconds > 0 ? data.max_bank_seconds : 3600;
        data.banked_seconds = Mathf.Min(data.banked_seconds + data.active_session.seconds_remaining, cap);
        data.active_session = new ActiveSession { status = "locked", seconds_remaining = 0, started_at = "" };

        if (TryWriteSession(data))
            Debug.LogWarning("[SessionManager] Stale unlock refunded to the bank.");
    }

    void ForceLockActiveSession()
    {
        if (!TryReadSession(out SessionData data)) return;

        data.active_session = new ActiveSession { status = "locked", seconds_remaining = 0, started_at = "" };
        TryWriteSession(data);
    }

    // ── Lock / unlock state ────────────────────────────────────────────────
    void UnlockGame(int secondsRemaining)
    {
        timeRemaining = secondsRemaining;
        gameUnlocked = true;
        returnedTimeOnExit = false;

        ApplyUnlockedUI();
        RestoreUnityWindow();
        UpdateTimerDisplay();

        Debug.Log($"[SessionManager] Unlocked! {secondsRemaining} seconds of playtime.");
    }

    void ApplyUnlockedUI()
    {
        ResumeGame();
        if (gamePanel != null) gamePanel.SetActive(true);
        if (lockedPanel != null) lockedPanel.SetActive(false);
        if (playerMovementScript != null) playerMovementScript.enabled = true;
    }

    void ShowLocked()
    {
        gameUnlocked = false;
        PauseGame();

        if (gamePanel != null) gamePanel.SetActive(false);
        if (lockedPanel != null) lockedPanel.SetActive(true);
        if (playerMovementScript != null) playerMovementScript.enabled = false;
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

        float clamped = Mathf.Max(timeRemaining, 0f);
        int minutes = Mathf.FloorToInt(clamped / 60f);
        int seconds = Mathf.FloorToInt(clamped % 60f);
        timerText.text = $"{minutes:00}:{seconds:00}";
    }

    void OnTimeExpired()
    {
        Debug.Log("[SessionManager] Time's up! Locking active session, bank preserved.");

        gameUnlocked = false;
        timeRemaining = 0f;
        UpdateTimerDisplay();

        ForceLockActiveSession();
        ShowLocked();
        LaunchFitPlayApp();
    }

    // ── Scene changes ──────────────────────────────────────────────────────
    private void OnSceneLoaded(Scene scene, LoadSceneMode mode)
    {
        GameObject timer  = FindInScene(scene, timerTextName);
        GameObject game   = FindInScene(scene, gamePanelName);
        GameObject locked = FindInScene(scene, lockedPanelName);
        GameObject exit   = FindInScene(scene, exitPanelName);

        if (timer != null)  timerText   = timer.GetComponent<TMP_Text>();
        if (game != null)   gamePanel   = game;
        if (locked != null) lockedPanel = locked;
        if (exit != null)   exitPanel   = exit;

        PlayerMovement player = FindFirstObjectByType<PlayerMovement>();
        if (player != null) playerMovementScript = player;

        if (gameUnlocked)
        {
            ApplyUnlockedUI();
            UpdateTimerDisplay();
        }
        else
        {
            ShowLocked();
        }
    }

    // Finds an object by name inside one scene, including inactive objects.
    static GameObject FindInScene(Scene scene, string objectName)
    {
        if (string.IsNullOrEmpty(objectName)) return null;

        foreach (GameObject root in scene.GetRootGameObjects())
            foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
                if (t.name == objectName) return t.gameObject;

        return null;
    }

    // ── Exit handling ──────────────────────────────────────────────────────
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
        Debug.Log($"[SessionManager] Returned {secondsToReturn} seconds to the bank.");
    }

    private void OnApplicationQuit()
    {
        ReturnUnusedTimeToBank();
    }

    public void ToggleExitMenu()
    {
        if (exitPanel != null) exitPanel.SetActive(!exitPanel.activeSelf);
    }

    public void ExitGame()
    {
        ReturnUnusedTimeToBank();
        Debug.Log("[SessionManager] Player exited game.");
        Application.Quit();
    }

    // ── FitPlay launching ──────────────────────────────────────────────────
    public void OpenFitPlay()
    {
        LaunchFitPlayApp();
    }

    void LaunchFitPlayApp()
    {
        Debug.Log("[SessionManager] Launching FitPlay app...");

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
                CreateNoWindow = true          // no black console window
            };
            Process.Start(psi);
        }
        catch (Exception e)
        {
            Debug.LogError("[SessionManager] Failed to launch FitPlay: " + e.Message);
        }
    }

    // ── Windows: bring the game window to the front ───────────────────────
    void RestoreUnityWindow()
    {
#if UNITY_STANDALONE_WIN
        IntPtr hwnd = GetUnityWindow();

        if (hwnd != IntPtr.Zero)
        {
            ShowWindow(hwnd, SW_RESTORE);
            SetForegroundWindow(hwnd);
        }
#endif
    }

#if UNITY_STANDALONE_WIN
    [System.Runtime.InteropServices.DllImport("user32.dll")]
    static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    static extern bool SetForegroundWindow(IntPtr hWnd);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    static extern bool IsWindowVisible(IntPtr hWnd);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    const int SW_RESTORE = 9;

    IntPtr GetUnityWindow()
    {
        IntPtr result = IntPtr.Zero;
        uint currentProcessId = (uint)Process.GetCurrentProcess().Id;

        EnumWindows((hWnd, lParam) =>
        {
            GetWindowThreadProcessId(hWnd, out uint windowProcessId);

            if (windowProcessId == currentProcessId && IsWindowVisible(hWnd))
            {
                result = hWnd;
                return false;
            }
            return true;
        }, IntPtr.Zero);

        return result;
    }
#endif
}

[Serializable]
public class SessionData
{
    public int banked_seconds;
    public int max_bank_seconds;
    public ActiveSession active_session;
}

[Serializable]
public class ActiveSession
{
    public string status;
    public int seconds_remaining;
    public string started_at;
}