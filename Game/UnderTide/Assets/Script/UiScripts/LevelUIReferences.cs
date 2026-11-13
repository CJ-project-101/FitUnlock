using UnityEngine;
using TMPro;

public class LevelUIReferences : MonoBehaviour
{
    [Header("Session UI for this scene")]
    public TMP_Text timerText;
    public GameObject gamePanel;
    public GameObject lockedPanel;

    [Header("Pause / Exit Menu")]
    public GameObject menuPanel;
    public GameObject menuSelector;       // if you use SelectionArrow here too
    public GameObject firstSelectedButton; // e.g. ExitButton

    void OnEnable()
    {
        SessionManager.Instance?.RegisterSceneUI(this);
    }
}