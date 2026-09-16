using UnityEngine;

public class Bullet : MonoBehaviour
{
    [SerializeField] float bulletSpeed = 20f;
    Rigidbody2D myRigidbody;
    PlayerMovement player;
    float xSpeed;

    void Start()
    {
        myRigidbody = GetComponent<Rigidbody2D>();

        // ✅ Updated for Unity 6 (FindFirstObjectByType replaces FindObjectOfType)
        player = Object.FindFirstObjectByType<PlayerMovement>();

        // Safety check in case player isn’t found
        if (player != null)
            xSpeed = player.transform.localScale.x * bulletSpeed;
        else
            Debug.LogWarning("⚠️ PlayerMovement not found! Bullet may not move correctly.");
    }

    void Update()
    {
        // Use velocity (not linearVelocity) — “linearVelocity” is an internal alias and may cause issues
        myRigidbody.linearVelocity = new Vector2(xSpeed, 0f);
    }

    void OnTriggerEnter2D(Collider2D other)
    {
        if (other.CompareTag("Enemy"))
        {
            Destroy(other.gameObject);
        }

        Destroy(gameObject);
    }

    void OnCollisionEnter2D(Collision2D other)
    {
        Destroy(gameObject);
    }
}
