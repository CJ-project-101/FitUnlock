using System.Collections;
using UnityEngine;

public class PoisonDamage : MonoBehaviour
{
    [SerializeField] private int damage = 1;
    [SerializeField] private float damageCooldown = 0.5f;

    private bool canDamage = true;

    private void OnTriggerStay2D(Collider2D other)
    {
        if (!canDamage)
            return;

        if (other.CompareTag("Player"))
        {
            other.SendMessage(
                "TakeDamage",
                damage,
                SendMessageOptions.DontRequireReceiver
            );

            StartCoroutine(DamageCooldown());
        }
    }

    private IEnumerator DamageCooldown()
    {
        canDamage = false;

        yield return new WaitForSeconds(damageCooldown);

        canDamage = true;
    }
}