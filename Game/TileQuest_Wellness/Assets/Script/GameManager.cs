using UnityEngine;
using UnityEngine.SceneManagement;
using TMPro;
using UnityEngine.UI;

public class GameManager : MonoBehaviour
{
    [Header("Play & Rest Timing (seconds)")]
    public float startPlayTime = 900f;      // 15 minutes
    public float maxPlayTime = 3600f;       // 60 minutes
    public float resetPlayTime = 3120f;     // 52 minutes
    public float startRestTime = 300f;      // 5 minutes
    public float maxRestTime = 900f;        // 15 minutes
    public float growthStep = 600f;         // +10 minutes each cycle

    [Header("UI Display (Optional)")]
    public TMP_Text infoText;
    public Image timerBar;

    private float currentPlayTime;
    private float currentRestTime;
    private float timer = 0f;
    private bool inRest = false;
    private int cycleCount = 0;

    void Start()
    {
        currentPlayTime = startPlayTime;
        currentRestTime = startRestTime;
        timer = 0f;
        UpdateInfo();
    }

    void Update()
    {
        timer += Time.unscaledDeltaTime;

        float remaining = inRest ? currentRestTime - timer : currentPlayTime - timer;
        float total = inRest ? currentRestTime : currentPlayTime;

        if (timerBar)
        {
            timerBar.fillAmount = Mathf.Clamp01(remaining / total);
            timerBar.color = inRest ? Color.cyan : Color.green;
        }

        if (infoText)
        {
            string mode = inRest ? "REST" : "PLAY";
            infoText.text = $"{mode} MODE\nRemaining: {(remaining / 60f):F1} min";
        }

        if (!inRest && timer >= currentPlayTime)
            StartRest();
        else if (inRest && timer >= currentRestTime)
            EndRest();
    }

    void StartRest()
    {
        inRest = true;
        timer = 0f;

        // Disable player controls
        var player = Object.FindFirstObjectByType<PlayerMovement>();
        if (player) player.enabled = false;

        Debug.Log($"🔵 REST started for {currentRestTime / 60f:F1} min.");

        // Load BreakScene overlay
        if (!SceneManager.GetSceneByName("BreakScene").isLoaded)
        {
            SceneManager.LoadScene("BreakScene", LoadSceneMode.Additive);
            Debug.Log("🌿 BreakScene loaded additively.");
        }

        UpdateInfo();
    }

    void EndRest()
    {
        inRest = false;
        timer = 0f;
        cycleCount++;

        Debug.Log("🟢 Rest timer finished — auto-resuming...");

        // Automatically trigger BreakController.ResumeGame() if active
        var breakController = Object.FindFirstObjectByType<BreakController>();
        if (breakController != null)
        {
            breakController.ResumeGame();
            return;
        }

        // Safety: unload BreakScene if still loaded
        if (SceneManager.GetSceneByName("BreakScene").isLoaded)
        {
            SceneManager.UnloadSceneAsync("BreakScene");
            Debug.Log("BreakScene unloaded manually.");
        }

        // Resume player movement
        var player = Object.FindFirstObjectByType<PlayerMovement>();
        if (player) player.enabled = true;

        Time.timeScale = 1f;

        // Adaptive cycle progression
        if (currentPlayTime < maxPlayTime)
        {
            currentPlayTime = Mathf.Min(currentPlayTime + growthStep, maxPlayTime);
            currentRestTime = Mathf.Min(currentRestTime + growthStep / 4f, maxRestTime);
        }
        else
        {
            currentPlayTime = resetPlayTime;
            currentRestTime = maxRestTime;
            Debug.Log("♻️ Cycle reset: play = 52 min, rest = 15 min");
        }

        Debug.Log($"✅ Auto-resume complete. Next: Play = {currentPlayTime / 60f:F1} min | Rest = {currentRestTime / 60f:F1} min");
        UpdateInfo();
    }

    public void EndBreakAndResume()
    {
        inRest = false;
        timer = 0f;
        Time.timeScale = 1f;
        Debug.Log("✅ Game resumed after wellness break!");

        if (SceneManager.GetSceneByName("BreakScene").isLoaded)
        {
            SceneManager.UnloadSceneAsync("BreakScene");
            Debug.Log("🟢 BreakScene unloaded.");
        }

        var player = Object.FindFirstObjectByType<PlayerMovement>();
        if (player) player.enabled = true;
    }

    public float GetCurrentRestTime()
    {
        return currentRestTime;
    }

    void UpdateInfo()
    {
        if (infoText)
        {
            string mode = inRest ? "REST" : "PLAY";
            float remaining = inRest ? currentRestTime - timer : currentPlayTime - timer;
            infoText.text = $"{mode} MODE\nNext switch in {(remaining / 60f):F1} min";
        }
    }
}
