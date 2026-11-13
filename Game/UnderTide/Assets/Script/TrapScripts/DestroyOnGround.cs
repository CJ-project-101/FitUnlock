using UnityEngine;
using System.Collections;

public class DestroyOnGround : MonoBehaviour
{
    [Header("Optional: what happens if it hits the player")]
    public int damageToPlayer = 1;

    [Header("Shatter animation")]
    public Animator animator;
    public float shatterDuration = 0.4f;

    private bool isBreaking = false;

    private void OnCollisionEnter2D(Collision2D collision)
    {
        Debug.Log($"[Falling_rock] Collided with: {collision.gameObject.name} | Layer: {LayerMask.LayerToName(collision.gameObject.layer)} | Tag: {collision.gameObject.tag}");

        if (isBreaking) return;

        if (collision.gameObject.layer == LayerMask.NameToLayer("Ground"))
        {
            Break();
        }
        else if (collision.gameObject.CompareTag("Player"))
        {
            Break();
        }
    }

    private void Break()
    {
        isBreaking = true;

        Rigidbody2D rb = GetComponent<Rigidbody2D>();
        if (rb != null)
        {
            rb.linearVelocity = Vector2.zero;
            rb.bodyType = RigidbodyType2D.Kinematic;
        }

        Collider2D col = GetComponent<Collider2D>();
        if (col != null) col.enabled = false;

        if (animator != null)
        {
            animator.SetTrigger("Break");
        }

        StartCoroutine(DestroyAfterAnimation());
    }

    private IEnumerator DestroyAfterAnimation()
    {
        yield return new WaitForSeconds(shatterDuration);
        Destroy(gameObject);
    }
}