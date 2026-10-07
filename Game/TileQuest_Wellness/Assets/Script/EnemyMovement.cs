using UnityEngine;

public class EnemyMovement : MonoBehaviour
{
    [Header("Patrol")]
    [SerializeField] private float moveSpeed = 1f;

    [Header("Chase")]
    [SerializeField] private float chaseRange = 4f;
    [SerializeField] private LayerMask playerLayer;

    private Rigidbody2D rb;

    private Transform player;

    private bool canMove = true;
    private bool chasingPlayer = false;

    private void Start()
    {
        rb = GetComponent<Rigidbody2D>();
    }

    private void Update()
    {
        if (!canMove)
        {
            rb.linearVelocity = new Vector2(
                0f,
                rb.linearVelocity.y
            );

            return;
        }

        FindPlayer();

        if (chasingPlayer && player != null)
        {
            ChasePlayer();
        }
        else
        {
            Patrol();
        }
    }

    private void FindPlayer()
    {
        Collider2D playerCollider = Physics2D.OverlapCircle(
            transform.position,
            chaseRange,
            playerLayer
        );

        if (playerCollider != null)
        {
            player = playerCollider.transform;
            chasingPlayer = true;
        }
        else
        {
            player = null;
            chasingPlayer = false;
        }
    }

    private void Patrol()
    {
        rb.linearVelocity = new Vector2(
            moveSpeed,
            rb.linearVelocity.y
        );

        FlipPatrolDirection();
    }

    private void ChasePlayer()
    {
        float distanceX =
            player.position.x - transform.position.x;

        if (Mathf.Abs(distanceX) > 0.05f)
        {
            float direction = Mathf.Sign(distanceX);

            rb.linearVelocity = new Vector2(
                direction * moveSpeed,
                rb.linearVelocity.y
            );

            FlipEnemy(direction);
        }
        else
        {
            rb.linearVelocity = new Vector2(
                0f,
                rb.linearVelocity.y
            );
        }
    }

    private void FlipPatrolDirection()
    {
        if (moveSpeed > 0)
        {
            transform.localScale = new Vector3(1f, 1f, 1f);
        }
        else
        {
            transform.localScale = new Vector3(-1f, 1f, 1f);
        }
    }

    private void FlipEnemy(float direction)
    {
        if (direction > 0)
        {
            transform.localScale =
                new Vector3(1f, 1f, 1f);
        }
        else
        {
            transform.localScale =
                new Vector3(-1f, 1f, 1f);
        }
    }

    private void OnTriggerExit2D(Collider2D other)
    {
        if (!chasingPlayer)
        {
            moveSpeed = -moveSpeed;
        }
    }

    public void StopMovement()
    {
        canMove = false;

        rb.linearVelocity = new Vector2(
            0f,
            rb.linearVelocity.y
        );
    }

    public void ResumeMovement()
    {
        canMove = true;
    }

    public float GetMoveDirection()
    {
        return Mathf.Sign(moveSpeed);
    }

    private void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.yellow;

        Gizmos.DrawWireSphere(
            transform.position,
            chaseRange
        );
    }
}