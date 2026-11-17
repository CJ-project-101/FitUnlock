using UnityEngine;

public class MagicProjectile : MonoBehaviour
{
    [SerializeField] private float speed = 8f;
    [SerializeField] private float maxRange = 10f;
    [SerializeField] private float explosionRadius = 1.5f;
    [SerializeField] private float explosionDamage = 1f;
    [SerializeField] private GameObject explosionVFXPrefab;
    [Header("VFX")]
    [SerializeField] private float explosionYOffset = 0.3f;
    [SerializeField] private float explosionXOffset = 0.3f;

    private SpriteRenderer spriteRenderer;
    private Vector3 startPos;
    private float direction;
    private bool exploded = false;

    private void Awake()
    {
        spriteRenderer = GetComponent<SpriteRenderer>();
    }

    public void Launch(float dir)
    {
        direction = dir;
        startPos = transform.position;

        // dir > 0 means moving right, so flipX should be false (assuming sprite's
        // default unflipped art faces right). Flip when moving left.
        if (spriteRenderer != null)
            spriteRenderer.flipX = dir > 0;
    }

    private void Update()
    {
        if (exploded) return;

        transform.Translate(Vector3.right * direction * speed * Time.deltaTime, Space.World);

        if (Vector3.Distance(startPos, transform.position) >= maxRange)
            Explode(null);
    }

    private void OnTriggerEnter2D(Collider2D collision)
    {
        if (exploded) return;

        DestructibleWall wall = collision.GetComponent<DestructibleWall>();
        if (wall != null)
        {
            wall.OnMagicHit();
            Explode(collision);
            return;
        }

        if (collision.CompareTag("Player"))
        {
            Health playerHealth = collision.GetComponent<Health>();
            if (playerHealth != null)
                playerHealth.TakeDamage(explosionDamage);
            Explode(collision);
        }
    }

    private void Explode(Collider2D directHit)
    {
        exploded = true;

        Collider2D[] hits = Physics2D.OverlapCircleAll(transform.position, explosionRadius);
        foreach (Collider2D hit in hits)
        {
            if (hit.CompareTag("Player") && hit != directHit)
            {
                Health playerHealth = hit.GetComponent<Health>();
                if (playerHealth != null)
                    playerHealth.TakeDamage(explosionDamage);
            }
        }

        Vector3 explosionPos = transform.position
            + Vector3.up * explosionYOffset
            + Vector3.right * direction * explosionXOffset;

        if (explosionVFXPrefab != null)
            Instantiate(explosionVFXPrefab, explosionPos, Quaternion.identity);

        Destroy(gameObject);
    }
}