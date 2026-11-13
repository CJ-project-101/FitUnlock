using UnityEngine;

public class HazardDamage : MonoBehaviour
{
    [SerializeField] float damageAmount = 1f;

    private void OnTriggerEnter2D(Collider2D collision)
    {
        if (((1 << collision.gameObject.layer) & LayerMask.GetMask("Enemies", "Hazards")) != 0)
        {
            Health health = GetComponent<Health>();
            if (health != null)
                health.TakeDamage(damageAmount);
        }
    }
}