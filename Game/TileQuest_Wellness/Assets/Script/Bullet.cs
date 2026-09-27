using UnityEngine;

public class Bullet : MonoBehaviour
{
    [SerializeField] private float bulletSpeed = 20f;

    private Rigidbody2D myRigidbody;
    private SpriteRenderer spriteRenderer;

    private Vector2 direction = Vector2.right;

    private void Awake()
    {
        myRigidbody = GetComponent<Rigidbody2D>();
        spriteRenderer = GetComponent<SpriteRenderer>();
    }

    public void SetDirection(Vector2 newDirection)
    {
        direction = newDirection.normalized;

        // Your fire-spell animation is originally facing LEFT.
        // Therefore, flip the sprite when shooting RIGHT.
        if (spriteRenderer != null)
        {
            spriteRenderer.flipX = direction.x > 0;
        }
    }

    private void Update()
    {
        if (myRigidbody != null)
        {
            myRigidbody.linearVelocity = direction * bulletSpeed;
        }
    }

    private void OnTriggerEnter2D(Collider2D other)
    {
        if (other.CompareTag("Enemy"))
        {
            Destroy(other.gameObject);
        }

        Destroy(gameObject);
    }

    private void OnCollisionEnter2D(Collision2D collision)
    {
        Destroy(gameObject);
    }
}