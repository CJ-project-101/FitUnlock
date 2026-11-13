using UnityEngine;

public class PlayerRespawn : MonoBehaviour
{
    [SerializeField] private AudioClip checkpointSound;
    private Transform currentCheckpoint;
    private Health playerHealth;

    private void Awake()
    {
        playerHealth = GetComponent<Health>();
    }

    public void RespawnCheck()
    {
        if (currentCheckpoint == null)
        {
            UnityEngine.SceneManagement.SceneManager.LoadScene(
                UnityEngine.SceneManagement.SceneManager.GetActiveScene().name);
            return;
        }

        playerHealth.Respawn();
        transform.position = currentCheckpoint.position;
    }

    private void OnTriggerEnter2D(Collider2D collision)
    {
        if (collision.gameObject.CompareTag("Checkpoint"))
        {
            currentCheckpoint = collision.transform;

            if (SoundManager.instance != null)
                SoundManager.instance.PlaySound(checkpointSound);

            Collider2D col = collision.GetComponent<Collider2D>();
            if (col != null) col.enabled = false;

            Animator checkpointAnim = collision.GetComponent<Animator>();
            if (checkpointAnim != null) checkpointAnim.SetTrigger("appear");
        }
    }
}