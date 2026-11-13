using System.Collections;
using UnityEngine;

public class EnemyPoisonAttack : MonoBehaviour
{
    [Header("Detection")]
    [SerializeField] private float detectionRange = 2.5f;
    [SerializeField] private LayerMask playerLayer;

    [Header("Attack")]
    [SerializeField] private float warningTime = 0.5f;
    [SerializeField] private float smokeDuration = 1.2f;
    [SerializeField] private float attackCooldown = 2f;

    [Header("Visual")]
    [SerializeField] private GameObject poisonSmoke;

    private SpriteRenderer spriteRenderer;

    private Color normalColor;

    private bool attacking = false;
    private bool canAttack = true;

    private void Start()
    {
        spriteRenderer = GetComponent<SpriteRenderer>();

        if (spriteRenderer != null)
        {
            normalColor = spriteRenderer.color;
        }

        if (poisonSmoke != null)
        {
            poisonSmoke.SetActive(false);
        }
    }

    private void Update()
    {
        if (attacking || !canAttack)
            return;

        Collider2D player = Physics2D.OverlapCircle(
            transform.position,
            detectionRange,
            playerLayer
        );

        if (player != null)
        {
            StartCoroutine(PoisonAttack());
        }
    }

    private IEnumerator PoisonAttack()
    {
        attacking = true;

        // WARNING
        StartCoroutine(WarningFlash());

        yield return new WaitForSeconds(warningTime);

        // SMOKE
        if (poisonSmoke != null)
        {
            poisonSmoke.SetActive(true);

            Animator smokeAnimator =
                poisonSmoke.GetComponent<Animator>();

            if (smokeAnimator != null)
            {
                smokeAnimator.Play(
                    "PoisonSmoke",
                    0,
                    0f
                );
            }
        }

        yield return new WaitForSeconds(smokeDuration);

        // TURN SMOKE OFF
        if (poisonSmoke != null)
        {
            poisonSmoke.SetActive(false);
        }

        // NORMAL COLOR
        if (spriteRenderer != null)
        {
            spriteRenderer.color = normalColor;
        }

        attacking = false;

        // COOLDOWN
        canAttack = false;

        yield return new WaitForSeconds(attackCooldown);

        canAttack = true;
    }

    private IEnumerator WarningFlash()
    {
        float elapsed = 0f;

        while (elapsed < warningTime)
        {
            if (spriteRenderer != null)
            {
                spriteRenderer.color = Color.red;
            }

            yield return new WaitForSeconds(0.1f);

            if (spriteRenderer != null)
            {
                spriteRenderer.color = normalColor;
            }

            yield return new WaitForSeconds(0.1f);

            elapsed += 0.2f;
        }

        if (spriteRenderer != null)
        {
            spriteRenderer.color = Color.red;
        }
    }

    private void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.red;

        Gizmos.DrawWireSphere(
            transform.position,
            detectionRange
        );
    }
}