using UnityEngine;
using System.Collections;

public class Health : MonoBehaviour
{
    [Header("Health")]
    [SerializeField] private float startingHealth = 10f;
    public float currentHealth { get; private set; }
    public float MaxHealth => startingHealth;

    private Animator anim;
    private bool dead;

    [Header("iFrames")]
    [SerializeField] private float iFramesDuration = 1f;
    [SerializeField] private int numberOfFlashes = 3;
    private SpriteRenderer spriteRend;

    [Header("Components to disable on death")]
    [SerializeField] private Behaviour[] components;
    private bool invulnerable;

    [Header("Sounds")]
    [SerializeField] private AudioClip deathSound;
    [SerializeField] private AudioClip hurtSound;

    private void Awake()
    {
        currentHealth = startingHealth;
        anim = GetComponent<Animator>();
        spriteRend = GetComponent<SpriteRenderer>();
    }

    public void TakeDamage(float _damage)
    {
        if (invulnerable || dead) return;

        currentHealth = Mathf.Clamp(currentHealth - _damage, 0, startingHealth);

        if (currentHealth > 0)
        {
           

            if (SoundManager.instance != null)
                SoundManager.instance.PlaySound(hurtSound);
        }
        else
        {
            if (!dead)
            {
                foreach (Behaviour component in components)
                    component.enabled = false;

                if (anim != null) anim.SetTrigger("Dying");

                dead = true;

                if (SoundManager.instance != null)
                    SoundManager.instance.PlaySound(deathSound);

                StartCoroutine(RespawnAfterDelay());
            }
        }
    }

    public void AddHealth(float _value)
    {
        currentHealth = Mathf.Clamp(currentHealth + _value, 0, startingHealth);
    }

    private IEnumerator Invulnerability()
    {
        invulnerable = true;
        for (int i = 0; i < numberOfFlashes; i++)
        {
            if (spriteRend != null) spriteRend.color = new Color(1, 0, 0, 0.5f);
            yield return new WaitForSeconds(iFramesDuration / (numberOfFlashes * 2));
            if (spriteRend != null) spriteRend.color = Color.white;
            yield return new WaitForSeconds(iFramesDuration / (numberOfFlashes * 2));
        }
        invulnerable = false;
    }

    private IEnumerator RespawnAfterDelay()
    {
        yield return new WaitForSeconds(1.2f);
        PlayerRespawn respawn = GetComponent<PlayerRespawn>();
        if (respawn != null)
            respawn.RespawnCheck();
    }

    public void Respawn()
    {
        AddHealth(startingHealth);
        if (anim != null)
        {
            anim.ResetTrigger("die");
            anim.Play("Idle");
        }
        StartCoroutine(Invulnerability());
        dead = false;

        foreach (Behaviour component in components)
            component.enabled = true;
    }
}