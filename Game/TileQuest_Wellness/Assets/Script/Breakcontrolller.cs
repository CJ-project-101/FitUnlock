using UnityEngine;
using UnityEngine.SceneManagement;
using TMPro;

public class BreakController : MonoBehaviour
{
    public TMP_Text messageText;
    private GameManager gameManager;

    void Start()
    {
        // Find GameManager in the main scene
        gameManager = Object.FindFirstObjectByType<GameManager>();
        // For older Unity versions: gameManager = FindObjectOfType<GameManager>();

        if (messageText)
            messageText.text = "🌿 Take a short wellness break!";
    }

    // Called by Resume Button or AI verification
    public void ResumeGame()
    {
        if (messageText)
            messageText.text = "✨ Welcome back! Resuming...";

        // Unload BreakScene
        SceneManager.UnloadSceneAsync("BreakScene");

        // Tell GameManager to resume
        if (gameManager != null)
            gameManager.EndBreakAndResume();
    }
}
