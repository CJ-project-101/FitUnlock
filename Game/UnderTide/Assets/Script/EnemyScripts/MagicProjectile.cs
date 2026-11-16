using UnityEngine;

public class MagicProjectile : MonoBehaviour
{
    [SerializeField] private float speed = 8f;
    [SerializeField] private float maxRange = 10f;
    [SerializeField] private float explosionRadius = 1.5f;
    [SerializeField] private float explosionDamage = 1f;
    [SerializeField] private GameObject explosionVFXPrefab;

    private Vector3 startPos;
    private float direction;
    private bool exploded = false;

    public void Launch(float dir)
    {
        direction = dir;
        startPos = transform.position;

        float localScaleX = transform.localScale.x;
        if (Mathf.Sign(localScaleX) != dir)
            localScaleX = -localScaleX;
        transform.localScale = new Vector3(localScaleX, transform.localScale.y, transform.localScale.z);
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

        // Damage anyone caught in the blast radius, even if not the direct hit
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

        if (explosionVFXPrefab != null)
            Instantiate(explosionVFXPrefab, transform.position, Quaternion.identity);

        Destroy(gameObject);
    }

    
}