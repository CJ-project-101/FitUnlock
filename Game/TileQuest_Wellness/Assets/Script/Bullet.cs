using UnityEngine;

public class Bullet : MonoBehaviour
{
    [Header("Bullet")]
    [SerializeField] private float bulletSpeed = 20f;

    [Header("Enemy Damage")]
    [SerializeField] private float enemyDamageRange = 7f;
    [SerializeField] private int enemyDamage = 1;

    private Rigidbody2D myRigidbody;
    private SpriteRenderer spriteRenderer;

    private Vector2 direction = Vector2.right;

    // Position of the player when the spell was fired
    private Vector2 playerFirePosition;

    private void Awake()
    {
        myRigidbody = GetComponent<Rigidbody2D>();
        spriteRenderer = GetComponent<SpriteRenderer>();

        // Default position in case FireSpell doesn't set it
        playerFirePosition = transform.position;
    }

    public void SetDirection(Vector2 newDirection)
    {
        direction = newDirection.normalized;

        // Your fire-spell animation originally faces LEFT.
        // Flip when shooting RIGHT.
        if (spriteRenderer != null)
        {
            spriteRenderer.flipX = direction.x > 0;
        }
    }

    public void SetPlayerFirePosition(Vector2 position)
    {
        playerFirePosition = position;
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
    Debug.Log("🔥 BULLET COLLIDED WITH: " + other.gameObject.name);

    if (other.CompareTag("Enemy"))
    {
        Debug.Log("🔥 ENEMY TAG FOUND!");

        EnemyHealth enemyHealth =
            other.GetComponentInParent<EnemyHealth>();

        if (enemyHealth != null)
        {
            Debug.Log("🔥 ENEMY HEALTH FOUND! DEALING DAMAGE!");

            enemyHealth.TakeDamage(1);
        }
        else
        {
            Debug.LogError("❌ EnemyHealth NOT FOUND!");
        }

        Destroy(gameObject);
        return;
    }

    Debug.Log("Bullet hit something that is NOT Enemy.");
    Destroy(gameObject);
}

    private void OnCollisionEnter2D(Collision2D collision)
    {
        Destroy(gameObject);
    }
}