using UnityEngine;
using System.Collections;

public class AurethBoss : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private Animator anim;
    [SerializeField] private Health health;
    [SerializeField] private Rigidbody2D rb;
    [SerializeField] private Transform player;

    [Header("Patrol Edges")]
    [SerializeField] private Transform leftEdge;
    [SerializeField] private Transform rightEdge;

    [Header("Patrol Movement")]
    [SerializeField] private float patrolSpeed = 1.5f;
    [SerializeField] private float patrolIdleDuration = 1f;
    private bool movingLeft;
    private float idleTimer;
    private Vector3 initScale;

    [Header("Chase Movement")]
    [SerializeField] private float moveSpeed = 3f;
    [SerializeField] private float attackRange = 1.5f;   // melee range (light/heavy)
    [SerializeField] private float magicRange = 5f;       // magic range (ranged)

    [Header("Attack Timing")]
    [SerializeField] private float decisionCooldown = 1.2f;
    [SerializeField] private float lightAttackDuration = 0.5f;
    [SerializeField] private float heavyAttackDuration = 0.9f;
    [SerializeField] private float castDuration = 0.6f;

    [Header("Magic")]
    [SerializeField] private Transform castPoint;
    [SerializeField] private GameObject heavyMagicPrefab;
    [SerializeField] private GameObject lightMagicPrefab;
    private bool pendingHeavyMagic;

    [Header("Wall Check (for heavy attack miss)")]
    [SerializeField] private float wallCheckRadius = 1f;
    [SerializeField] private LayerMask wallLayer;

    [Header("Stamina")]
    [SerializeField] private float maxStamina = 100f;
    private float currentStamina;

    [Header("Stamina Costs")]
    [SerializeField] private float heavyAttackStaminaCost = 20f;
    [SerializeField] private float magicCastStaminaCost = 15f;
    [SerializeField] private float chaseStaminaDrainPerSecond = 5f;
    [SerializeField] private float blockStaminaCost = 15f;

    [Header("Block")]
    [Range(0f, 1f)]
    [SerializeField] private float blockChance = 0.5f;

    [Header("Dizzy")]
    [SerializeField] private float dizzyDuration = 3f;
    private bool isDizzy = false;

    private bool busy = false;
    private float decisionTimer = 0f;

    public bool IsDizzy => isDizzy;
    public float CurrentStamina => currentStamina;
    public float MaxStamina => maxStamina;

    private void Awake()
    {
        if (anim == null) anim = GetComponent<Animator>();
        if (health == null) health = GetComponent<Health>();
        if (rb == null) rb = GetComponent<Rigidbody2D>();
        currentStamina = maxStamina;
        initScale = transform.localScale;
    }

    private void Update()
    {
        if (isDizzy || busy) return;

        bool playerInZone = IsPlayerBetweenEdges();

        if (!playerInZone)
        {
            Patrol();
            return;
        }

        DrainStamina(chaseStaminaDrainPerSecond * Time.deltaTime);

        float distance = Vector2.Distance(transform.position, player.position);
        FaceTarget();
        decisionTimer -= Time.deltaTime;

        bool inMeleeRange = distance <= attackRange;
        bool inMagicRange = distance <= magicRange;

        if (!inMeleeRange && !inMagicRange)
        {
            // Too far for anything — close the distance
            anim.SetBool("isWalking", true);
            float dir = Mathf.Sign(player.position.x - transform.position.x);
            rb.linearVelocity = new Vector2(dir * moveSpeed, rb.linearVelocity.y);
        }
        else
        {
            anim.SetBool("isWalking", false);
            rb.linearVelocity = new Vector2(0f, rb.linearVelocity.y);

            if (decisionTimer <= 0f)
            {
                decisionTimer = decisionCooldown;
                ChooseAttack(inMeleeRange, inMagicRange);
            }
        }
    }

    private void Patrol()
    {
        if (leftEdge == null || rightEdge == null) return;

        if (movingLeft)
        {
            if (transform.position.x >= leftEdge.position.x)
                MoveInDirection(-1);
            else
                PatrolDirectionChange();
        }
        else
        {
            if (transform.position.x <= rightEdge.position.x)
                MoveInDirection(1);
            else
                PatrolDirectionChange();
        }
    }

    private void PatrolDirectionChange()
    {
        anim.SetBool("isWalking", false);
        rb.linearVelocity = new Vector2(0f, rb.linearVelocity.y);
        idleTimer += Time.deltaTime;

        if (idleTimer > patrolIdleDuration)
            movingLeft = !movingLeft;
    }

    private void MoveInDirection(int _direction)
    {
        idleTimer = 0;
        anim.SetBool("isWalking", true);

        transform.localScale = new Vector3(Mathf.Abs(initScale.x) * _direction,
            initScale.y, initScale.z);

        rb.linearVelocity = new Vector2(_direction * patrolSpeed, rb.linearVelocity.y);
    }

    private bool IsPlayerBetweenEdges()
    {
        if (leftEdge == null || rightEdge == null) return true;
        return player.position.x >= leftEdge.position.x && player.position.x <= rightEdge.position.x;
    }

    private void FaceTarget()
    {
        float dir = Mathf.Sign(player.position.x - transform.position.x);
        transform.localScale = new Vector3(Mathf.Abs(initScale.x) * dir,
            initScale.y, initScale.z);
    }

    private void ChooseAttack(bool inMeleeRange, bool inMagicRange)
    {
        if (inMeleeRange)
        {
            // Melee range takes priority — light or heavy only
            int choice = Random.Range(0, 2);
            if (choice == 0) StartCoroutine(DoLightAttack());
            else StartCoroutine(DoHeavyAttack());
        }
        else if (inMagicRange)
        {
            // Out of melee reach but within magic range — cast only
            StartCoroutine(DoMagicCast());
        }
    }

    private IEnumerator DoLightAttack()
    {
        busy = true;
        anim.SetTrigger("attack");
        yield return new WaitForSeconds(lightAttackDuration);
        busy = false;
    }

    private IEnumerator DoHeavyAttack()
    {
        busy = true;
        anim.SetTrigger("strike");
        OnHeavyAttackPerformed();

        yield return new WaitForSeconds(heavyAttackDuration);

        float facingDir = Mathf.Sign(transform.localScale.x);
        Vector2 checkPos = (Vector2)transform.position + new Vector2(facingDir * wallCheckRadius, 0f);
        Collider2D hit = Physics2D.OverlapCircle(checkPos, wallCheckRadius, wallLayer);
        if (hit != null)
        {
            DestructibleWall wall = hit.GetComponent<DestructibleWall>();
            if (wall != null)
                wall.OnHeavyAttackHit();
        }

        busy = false;
    }

    private IEnumerator DoMagicCast()
    {
        busy = true;
        pendingHeavyMagic = Random.value < 0.5f;

        anim.SetTrigger("cast");
        OnMagicCastPerformed();

        yield return new WaitForSeconds(castDuration);
        busy = false;
    }

    public void OnHeavyAttackPerformed() => DrainStamina(heavyAttackStaminaCost);
    public void OnMagicCastPerformed() => DrainStamina(magicCastStaminaCost);

    public void ReceiveBoulderHit(float damage)
    {
        if (isDizzy)
        {
            health.TakeDamage(damage);
            return;
        }

        if (Random.value <= blockChance)
        {
            DrainStamina(blockStaminaCost);
            if (anim != null) anim.SetTrigger("block");
        }
        else
        {
            health.TakeDamage(damage);
        }
    }

    private void DrainStamina(float amount)
    {
        if (isDizzy) return;
        currentStamina = Mathf.Max(0f, currentStamina - amount);
        if (currentStamina <= 0f)
            StartCoroutine(EnterDizzy());
    }

    private IEnumerator EnterDizzy()
    {
        isDizzy = true;
        busy = false;
        rb.linearVelocity = new Vector2(0f, rb.linearVelocity.y);

        if (anim != null) anim.SetTrigger("dizzy");

        yield return new WaitForSeconds(dizzyDuration);

        isDizzy = false;
        currentStamina = maxStamina;
    }

    public void SpawnMagicProjectile()
    {
        GameObject prefabToUse = pendingHeavyMagic ? heavyMagicPrefab : lightMagicPrefab;

        if (prefabToUse != null && castPoint != null)
        {
            GameObject proj = Instantiate(prefabToUse, castPoint.position, Quaternion.identity);
            float dir = Mathf.Sign(transform.localScale.x);
            proj.GetComponent<MagicProjectile>()?.Launch(dir);
        }
    }

    public void ResetStamina() => currentStamina = maxStamina;
}