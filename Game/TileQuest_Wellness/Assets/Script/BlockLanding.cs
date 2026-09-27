using UnityEngine;

public class BlockLanding : MonoBehaviour
{
    public LayerMask groundOrLavaLayer;
    public Rigidbody2D nextBlockInChain;   // drag the NEXT block here, or leave empty if this is the last one
    public float chainDelay = 0.3f;        // small delay before next block falls, for visual pacing

    private bool hasLanded = false;

    private void OnCollisionEnter2D(Collision2D collision)
    {
        if (hasLanded) return;

        if (((1 << collision.gameObject.layer) & groundOrLavaLayer) != 0)
        {
            hasLanded = true;

            // Lock this block in place
            Rigidbody2D rb = GetComponent<Rigidbody2D>();
            if (rb != null)
            {
                rb.linearVelocity = Vector2.zero;
                rb.bodyType = RigidbodyType2D.Kinematic;
            }

            // Destroy the lava tile/object it landed on
            
            // Trigger the next block in the chain, if one is assigned
            if (nextBlockInChain != null)
            {
                Invoke(nameof(TriggerNextBlock), chainDelay);
            }
        }
    }

    private void TriggerNextBlock()
    {
        nextBlockInChain.bodyType = RigidbodyType2D.Dynamic;
        nextBlockInChain.gravityScale = 3f;
    }
}