using UnityEngine;
using System.Collections;

public class WeakPoint : MonoBehaviour
{
    [Header("Blocks - Order matters")]
    [SerializeField] private Rigidbody2D[] fallingBlocks;

    [Header("Settings")]
    [SerializeField] private float delayBetweenBlocks = 0.5f;
    [SerializeField] private float gravity = 3f;

    [Header("Optional Effect")]
    [SerializeField] private GameObject crackEffect;

    private bool triggered = false;

    private void OnTriggerEnter2D(Collider2D other)
    {
        if (triggered)
            return;

        if (other.CompareTag("Spell"))
        {
            triggered = true;

            if (crackEffect != null)
            {
                crackEffect.SetActive(true);
            }

            Destroy(other.gameObject);

            StartCoroutine(DropBlocksOneByOne());
        }
    }

    private IEnumerator DropBlocksOneByOne()
    {
        foreach (Rigidbody2D block in fallingBlocks)
        {
            if (block != null)
            {
                // Make this block fall
                block.bodyType = RigidbodyType2D.Dynamic;
                block.gravityScale = gravity;

                // Wait before releasing the next block
                yield return new WaitForSeconds(delayBetweenBlocks);
            }
        }
    }
}