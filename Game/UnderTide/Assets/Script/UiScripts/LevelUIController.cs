using UnityEngine;
using UnityEngine.EventSystems;

public class LevelUIController : MonoBehaviour
{
    [SerializeField] LevelUIReferences ui;

    void OnEnable()
    {
        SessionManager mgr = SessionManager.Instance;
        if (mgr == null) return;

        mgr.OnLockStateChanged += HandleLockState;
        mgr.OnTimeUpdated += HandleTimeUpdated;
        mgr.OnMenuToggled += HandleMenuToggled;
    }

    void OnDisable()
    {
        SessionManager mgr = SessionManager.Instance;
        if (mgr == null) return;

        mgr.OnLockStateChanged -= HandleLockState;
        mgr.OnTimeUpdated -= HandleTimeUpdated;
        mgr.OnMenuToggled -= HandleMenuToggled;
    }

    void HandleLockState(bool unlocked)
    {
        if (ui.gamePanel != null) ui.gamePanel.SetActive(unlocked);
        if (ui.lockedPanel != null) ui.lockedPanel.SetActive(!unlocked);
    }

    void HandleTimeUpdated(float secondsRemaining)
    {
        if (ui.timerText == null) return;
        float clamped = Mathf.Max(secondsRemaining, 0f);
        int minutes = Mathf.FloorToInt(clamped / 60f);
        int seconds = Mathf.FloorToInt(clamped % 60f);
        ui.timerText.text = $"{minutes:00}:{seconds:00}";
    }

    void HandleMenuToggled(bool open)
    {
        if (ui.menuPanel != null) ui.menuPanel.SetActive(open);
        if (ui.menuSelector != null) ui.menuSelector.SetActive(open);

        if (open && EventSystem.current != null && ui.firstSelectedButton != null)
            EventSystem.current.SetSelectedGameObject(ui.firstSelectedButton);
    }
}