using UnityEngine;

public class RockCoverTrap : MonoBehaviour
{
    public Animator rockCoverAnimator;
    public GameObject rockCoverObject;   // the RockCover GameObject itself
    public float crumbleDuration = 0.5f; // match your RockCrumble.anim length

    private bool triggered = false;

    private void OnTriggerEnter2D(Collider2D other)
    {
        if (triggered) return;

        if (other.CompareTag("Player"))
        {
            triggered = true;
            rockCoverAnimator.SetTrigger("Crumble");
            Invoke(nameof(RemoveCover), crumbleDuration);
        }
    }

    private void RemoveCover()
    {
        if (rockCoverObject != null)
            rockCoverObject.SetActive(false);   // reveals the spikes permanently
    }
}