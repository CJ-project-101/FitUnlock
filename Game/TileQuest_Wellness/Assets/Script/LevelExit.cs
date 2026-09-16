using UnityEngine;
using System.Collections;
using UnityEngine.SceneManagement;

public class LevelExit : MonoBehaviour
{
    [SerializeField] float levelLoadDelay = 1f;

    void OnTriggerEnter2D(Collider2D other)
    {
        // Only player should trigger
        if (other.CompareTag("Player"))
        {
            StartCoroutine(LoadNextLevel());
        }
    }

    IEnumerator LoadNextLevel()
    {
        yield return new WaitForSecondsRealtime(levelLoadDelay);

        int currentSceneIndex = SceneManager.GetActiveScene().buildIndex;
        int nextSceneIndex = currentSceneIndex + 1;

        // ✅ If we're at the last scene, loop back to first
        if (nextSceneIndex >= SceneManager.sceneCountInBuildSettings)
        {
            nextSceneIndex = 0;
        }

        // ✅ Load next level
        SceneManager.LoadScene(nextSceneIndex);
    }
}
