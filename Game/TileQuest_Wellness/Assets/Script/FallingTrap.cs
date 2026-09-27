using UnityEngine;
using System.Collections;

public class FallingTrap : MonoBehaviour
{
    public SpriteRenderer triggerVisual;
    public Rigidbody2D[] fallingObjects;
    public float delayBetweenDrops = 0.15f;   // seconds between each rock releasing

    private bool triggered = false;

    private void OnTriggerEnter2D(Collider2D other)
    {
        if (triggered) return;

        if (other.CompareTag("Player"))
        {
            triggered = true;

            if (triggerVisual != null)
                triggerVisual.enabled = true;

            StartCoroutine(DropRocksSequentially());
        }
    }

    private IEnumerator DropRocksSequentially()
    {
        foreach (Rigidbody2D rock in fallingObjects)
        {
            if (rock != null)
            {
                rock.bodyType = RigidbodyType2D.Dynamic;
                rock.gravityScale = 3f;
            }

            yield return new WaitForSeconds(delayBetweenDrops);
        }
    }
}