using System;
using System.IO;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;
using TMPro;

public class SessionManager : MonoBehaviour
{
    [Header("UI References — drag these in from your scene")]
    public TMP_Text timerText;          // shows countdown e.g. "14:59"
    public GameObject gamePanel;    // your actual game / main menu UI
    public GameObject lockedPanel;  // "Go exercise to unlock!" screen

    [Header("Settings")]
    public float pollIntervalSeconds = 1.0f;  // how often to re-check the file

    private string sessionPath;
    private float timeRemaining = 0f;
    private bool gameUnlocked = false;
    private float pollTimer = 0f;

    void Awake()
    {
        // shared/session.json sits ONE FOLDER UP from where the .exe lives,
        // so this path works identically on Windows, Mac, and Linux builds.
        string exeDir = Path.GetDirectoryName(Application.dataPath);
        sessionPath = Path.Combine(exeDir, "..", "shared", "session.json");
        sessionPath = Path.GetFullPath(sessionPath);

        Debug.Log("[SessionManager] Looking for session file at: " + sessionPath);
    }

    void Start()
    {
        ReadSession();
    }

    void Update()
    {
        // Re-check the file periodically in case Python writes to it
        // while the game is already running (e.g. paused mid-play)
        pollTimer += Time.deltaTime;
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

            if (data != null && data.status == "unlocked" && data.minutes_earned > 0)
            {
                UnlockGame(data.minutes_earned);
                ConsumeSession(); // prevent reusing the same unlock twice
            }
            else
            {
                ShowLocked();
            }
        }
        catch (Exception e)
        {
            Debug.LogError("[SessionManager] Failed to read session.json: " + e.Message);
            ShowLocked();
        }
    }

    void UnlockGame(int minutesEarned)
    {
        timeRemaining = minutesEarned * 60f;
        gameUnlocked = true;

        if (gamePanel != null)   gamePanel.SetActive(true);
        if (lockedPanel != null) lockedPanel.SetActive(false);

        Debug.Log($"[SessionManager] Unlocked! {minutesEarned} minutes of playtime.");
    }

    void ShowLocked()
    {
        gameUnlocked = false;

        if (gamePanel != null)   gamePanel.SetActive(false);
        if (lockedPanel != null) lockedPanel.SetActive(true);
    }

    void ConsumeSession()
    {
        // Immediately re-lock session.json so the SAME unlock
        // can't be read again if the game restarts.
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

    void UpdateTimerDisplay()
    {
        if (timerText == null) return;

        int minutes = Mathf.FloorToInt(timeRemaining / 60f);
        int seconds = Mathf.FloorToInt(timeRemaining % 60f);
        timerText.text = $"{minutes:00}:{seconds:00}";
    }

    void OnTimeExpired()
    {
        Debug.Log("[SessionManager] Time's up! Locking game.");
        gameUnlocked = false;
        ShowLocked();

        // Optional: quit the whole app instead of just showing the locked panel
        // Application.Quit();
    }
}

[Serializable]
public class SessionData
{
    public string status;
    public int minutes_earned;
    public string activity_done;
    public string timestamp;
}