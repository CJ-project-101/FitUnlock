using UnityEngine;
using System.Collections;

public class AurethBoss : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private Animator anim;
    [SerializeField] private Health health;

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

    private bool isChasing = false;

    public bool IsDizzy => isDizzy;
    public float CurrentStamina => currentStamina;
    public float MaxStamina => maxStamina;

    private void Awake()
    {
        if (anim == null) anim = GetComponent<Animator>();
        if (health == null) health = GetComponent<Health>();
        currentStamina = maxStamina;
    }

    private void Update()
    {
        if (isChasing && !isDizzy)
            DrainStamina(chaseStaminaDrainPerSecond * Time.deltaTime);
    }

    public void SetChasing(bool chasing)
    {
        isChasing = chasing;
    }

    public void OnHeavyAttackPerformed()
    {
        DrainStamina(heavyAttackStaminaCost);
    }

    public void OnMagicCastPerformed()
    {
        DrainStamina(magicCastStaminaCost);
    }

    // Called by Boulder.cs when a thrown boulder hits Aureth
    public void ReceiveBoulderHit(float damage)
    {
        if (isDizzy)
        {
            // Guaranteed hit during dizzy window
            health.TakeDamage(damage);
            return;
        }

        if (Random.value <= blockChance)
        {
            // Successful block
            DrainStamina(blockStaminaCost);
            if (anim != null) anim.SetTrigger("block");
        }
        else
        {
            // Failed block — boulder connects directly
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
        isChasing = false;

        if (anim != null) anim.SetTrigger("dizzy");

        yield return new WaitForSeconds(dizzyDuration);

        isDizzy = false;
        currentStamina = maxStamina; // refill after recovering, so he isn't instantly dizzy again
    }

    // Public reset for use later in Phase 8 (teleport)
    public void ResetStamina()
    {
        currentStamina = maxStamina;
    }
}