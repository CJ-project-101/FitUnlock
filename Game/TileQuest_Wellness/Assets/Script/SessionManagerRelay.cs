using UnityEngine;

public class SessionManagerRelay : MonoBehaviour
{
    private SessionManager GetManager()
{
    if (SessionManager.Instance != null)
        return SessionManager.Instance;

    SessionManager manager = FindFirstObjectByType<SessionManager>();

    if (manager != null)
        return manager;

    Debug.LogError(
        "[Relay] No SessionManager exists in the loaded scene."
    );

    return null;
}

    public void ToggleExitMenu()
    {
        SessionManager manager = GetManager();
        if (manager != null)
            manager.ToggleExitMenu();
    }

    public void ExitGame()
    {
        SessionManager manager = GetManager();
        if (manager != null)
            manager.ExitGame();
    }

    public void OpenFitPlay()
    {
        SessionManager manager = GetManager();
        if (manager != null)
            manager.OpenFitPlay();
    }
}