using UnityEngine;
using System.Collections;

public class AurethBoss : MonoBehaviour
{
    [Header("References")]
    [SerializeField] Animator anim;
    [SerializeField] Transform player;
    [SerializeField] Health bossHealth;

    [Header("Movement")]
    [SerializeField] float moveSpeed = 3f;
    [SerializeField] float chaseRange = 8f;
    [SerializeField] float attackRange = 1.5f;

    [Header("Attack Prefabs / Points")]
    [SerializeField] Transform castPoint;
    [SerializeField] GameObject fireballPrefab;
    [SerializeField] GameObject dashWindVFX;
    [SerializeField] GameObject explosionVFX;

    [Header("Timing")]
    [SerializeField] float decisionCooldown = 1.5f;
    [SerializeField] float dashSpeed = 12f;
    [SerializeField] float dizzyDuration = 2f;

    int phase = 0;
    bool busy = false;      // true while performing an attack animation
    bool phaseLocked = false;
    float decisionTimer = 0f;

    Rigidbody2D rb;

    void Awake()
    {
        rb = GetComponent<Rigidbody2D>();
    }

    void Update()
    {
        if (busy || phaseLocked) return;

        CheckPhaseTransition();

        float distance = Vector2.Distance(transform.position, player.position);
        FaceTarget();

        decisionTimer -= Time.deltaTime;

        if (distance > chaseRange)
        {
            anim.SetBool("isWalking", false);
            return; // out of range, idle
        }

        if (distance > attackRange)
        {
            // Chase
            anim.SetBool("isWalking", true);
            Vector2 dir = (player.position - transform.position).normalized;
            rb.linearVelocity = new Vector2(dir.x * moveSpeed, rb.linearVelocity.y);
        }
        else
        {
            anim.SetBool("isWalking", false);
            rb.linearVelocity = Vector2.zero;

            if (decisionTimer <= 0f)
            {
                decisionTimer = decisionCooldown;
                ChooseAttack(distance);
            }
        }
    }

    void FaceTarget()
    {
        float dir = Mathf.Sign(player.position.x - transform.position.x);
        transform.localScale = new Vector3(Mathf.Abs(transform.localScale.x) * dir,
            transform.localScale.y, transform.localScale.z);
    }

    void ChooseAttack(float distance)
    {
        int choice;

        if (phase == 0)
            choice = Random.Range(0, 2); // Attack, Strike
        else if (phase == 1)
            choice = Random.Range(0, 4); // + Cast, Dash
        else
            choice = Random.Range(0, 5); // + JumpAttack

        switch (choice)
        {
            case 0: StartCoroutine(DoAttack()); break;
            case 1: StartCoroutine(DoStrike()); break;
            case 2: StartCoroutine(DoCast()); break;
            case 3: StartCoroutine(DoDash()); break;
            case 4: StartCoroutine(DoJumpAttack()); break;
        }
    }

    IEnumerator DoAttack()
    {
        busy = true;
        anim.SetTrigger("attack");
        yield return new WaitForSeconds(0.6f); // match animation length
        busy = false;
    }

    IEnumerator DoStrike()
    {
        busy = true;
        anim.SetTrigger("strike");
        yield return new WaitForSeconds(0.9f); // slower, heavier telegraph
        busy = false;
    }

    IEnumerator DoCast()
    {
        busy = true;
        anim.SetTrigger("cast");
        yield return new WaitForSeconds(0.5f); // windup before firing
        FireProjectile();
        yield return new WaitForSeconds(0.4f);
        busy = false;
    }

    void FireProjectile()
    {
        if (fireballPrefab == null || castPoint == null) return;
        GameObject fb = Instantiate(fireballPrefab, castPoint.position, Quaternion.identity);
        float dir = Mathf.Sign(transform.localScale.x);
        //fb.GetComponent<Projectile>()?.SetDirection(dir);
    }

    IEnumerator DoDash()
    {
        busy = true;
        anim.SetTrigger("dash");
        if (dashWindVFX != null) Instantiate(dashWindVFX, transform.position, Quaternion.identity);

        float dir = Mathf.Sign(player.position.x - transform.position.x);
        float timer = 0f;
        while (timer < 0.4f)
        {
            rb.linearVelocity = new Vector2(dir * dashSpeed, rb.linearVelocity.y);
            timer += Time.deltaTime;
            yield return null;
        }
        rb.linearVelocity = Vector2.zero;
        yield return new WaitForSeconds(0.3f);
        busy = false;
    }

    IEnumerator DoJumpAttack()
    {
        busy = true;
        anim.SetTrigger("jumpAttack");
        yield return new WaitForSeconds(0.5f); // airtime before slam
        if (explosionVFX != null) Instantiate(explosionVFX, transform.position, Quaternion.identity);
        // TODO: trigger a shockwave hitbox here that the player must jump over
        yield return new WaitForSeconds(0.5f);
        busy = false;
    }

    void CheckPhaseTransition()
    {
        float healthPercent = bossHealth.currentHealth / bossHealth.MaxHealth;

        if (phase == 0 && healthPercent <= 0.66f)
            StartCoroutine(PhaseTransition(1));
        else if (phase == 1 && healthPercent <= 0.33f)
            StartCoroutine(PhaseTransition(2));
    }

    IEnumerator PhaseTransition(int newPhase)
    {
        phaseLocked = true;
        busy = true;
        rb.linearVelocity = Vector2.zero;
        anim.SetTrigger("dizzy"); // exposed window — player gets a free punish

        yield return new WaitForSeconds(dizzyDuration);

        phase = newPhase;
        decisionCooldown = Mathf.Max(0.8f, decisionCooldown - 0.3f); // ramps up aggression each phase
        busy = false;
        phaseLocked = false;
    }

    // Called by an Animation Event on the Hurt clip, or externally
    public void OnHit()
    {
        anim.SetTrigger("hurt");
    }
}