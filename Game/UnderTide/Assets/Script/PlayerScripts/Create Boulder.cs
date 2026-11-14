using UnityEngine;
using System.Collections;

public class Boulder : MonoBehaviour
{
    [Header("Damage")]
    [SerializeField] private float damage = 2f;
    [SerializeField] private float throwSpeed = 12f;

    [Header("Break Effect")]
    [SerializeField] private float breakAnimDuration = 0.4f;

    private Rigidbody2D rb;
    private CapsuleCollider2D col;
    private Animator anim;
    private bool isHeld = false;
    private bool isThrown = false;
    private bool isBreaking = false;

    private void Awake()
    {
        rb = GetComponent<Rigidbody2D>();
        col = GetComponent<CapsuleCollider2D>();
        anim = GetComponent<Animator>();
    }

    public void PickUp(Transform holdPoint)
    {
        isHeld = true;
        isThrown = false;
        rb.bodyType = RigidbodyType2D.Kinematic;
        col.enabled = false;
        transform.SetParent(holdPoint);
        transform.localPosition = Vector3.zero;
    }

    public void Throw(float direction)
    {
        isHeld = false;
        isThrown = true;
        transform.SetParent(null);
        rb.bodyType = RigidbodyType2D.Dynamic;
        col.enabled = true;
        rb.linearVelocity = new Vector2(direction * throwSpeed, 0f);
    }

    public void Drop()
    {
        isHeld = false;
        isThrown = false;
        transform.SetParent(null);
        rb.bodyType = RigidbodyType2D.Dynamic;
        col.enabled = true;
    }

    public bool IsHeld => isHeld;

    private void OnCollisionEnter2D(Collision2D collision)
    {
        if (isBreaking) return;

        AurethBoss boss = collision.gameObject.GetComponent<AurethBoss>();
        if (boss != null && isThrown)
        {
            boss.ReceiveBoulderHit(damage);
            StartBreak();
            return;
        }

        // Ground contact while thrown — just stop being "in flight" and rest. No break.
        if (((1 << collision.gameObject.layer) & LayerMask.GetMask("Ground")) != 0)
        {
            isThrown = false;
        }
    }

    private void StartBreak()
    {
        isBreaking = true;
        rb.linearVelocity = Vector2.zero;
        rb.bodyType = RigidbodyType2D.Kinematic;
        col.enabled = false;

        if (anim != null)
            anim.SetTrigger("break");

        StartCoroutine(DestroyAfterAnim());
    }

    private IEnumerator DestroyAfterAnim()
    {
        yield return new WaitForSeconds(breakAnimDuration);
        Destroy(gameObject);
    }
}