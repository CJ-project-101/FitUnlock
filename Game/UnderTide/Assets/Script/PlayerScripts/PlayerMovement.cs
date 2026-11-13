using UnityEngine;
using UnityEngine.InputSystem;

public class PlayerMovement : MonoBehaviour
{
    [SerializeField] float runSpeed = 10f;
    [SerializeField] float jumpSpeed = 10f;
    [SerializeField] float climbSpeed = 4f;

    [SerializeField] float wallJumpCooldown = 0.3f;
    [SerializeField] float wallJumpLockDuration = 0.2f;

    float lastWallJumpTime = -10f;
    float wallJumpLockTimer = 0f;

    Vector2 moveInput;
    Rigidbody2D myRigidbody;
    Animator myAnimator;
    CapsuleCollider2D myBodyCollider;
    BoxCollider2D myFeetCollider;
    float gravityScaleAtStart;

    void Start()
    {
        myRigidbody = GetComponent<Rigidbody2D>();
        myAnimator = GetComponent<Animator>();
        myBodyCollider = GetComponent<CapsuleCollider2D>();
        myFeetCollider = GetComponent<BoxCollider2D>();
        gravityScaleAtStart = myRigidbody.gravityScale;
    }

    void Update()
    {
        if (wallJumpLockTimer > 0f)
            wallJumpLockTimer -= Time.deltaTime;
        else
            Run();

        FlipSprite();
        ClimbLadder();
    }

    void OnMove(InputValue value)
    {
        moveInput = value.Get<Vector2>();
    }

    void OnJump(InputValue value)
    {
        bool touchingWall = myBodyCollider.IsTouchingLayers(LayerMask.GetMask("Wall"));
        bool grounded = myFeetCollider.IsTouchingLayers(LayerMask.GetMask("Ground"));

        if (value.isPressed)
        {
            if (grounded)
            {
                myRigidbody.linearVelocity = new Vector2(myRigidbody.linearVelocity.x, jumpSpeed);
            }
            else if (touchingWall && Time.time > lastWallJumpTime + wallJumpCooldown)
            {
                float wallDirection = -Mathf.Sign(transform.localScale.x);
                myRigidbody.linearVelocity = new Vector2(wallDirection * runSpeed, jumpSpeed);
                wallJumpLockTimer = wallJumpLockDuration;
                lastWallJumpTime = Time.time;
            }
        }
    }

    void Run()
    {
        Vector2 playerVelocity = new Vector2(moveInput.x * runSpeed, myRigidbody.linearVelocity.y);
        myRigidbody.linearVelocity = playerVelocity;

        bool playerHasHorizontalSpeed = Mathf.Abs(myRigidbody.linearVelocity.x) > Mathf.Epsilon;
        myAnimator.SetBool("IsRunning", playerHasHorizontalSpeed);
    }

    void FlipSprite()
    {
        bool playerHasHorizontalSpeed = Mathf.Abs(myRigidbody.linearVelocity.x) > Mathf.Epsilon;
        if (playerHasHorizontalSpeed)
            transform.localScale = new Vector2(Mathf.Sign(myRigidbody.linearVelocity.x), 1f);
    }

    void ClimbLadder()
    {
        if (!myFeetCollider.IsTouchingLayers(LayerMask.GetMask("Climbing")))
        {
            myRigidbody.gravityScale = gravityScaleAtStart;
            myAnimator.SetBool("IsClimbing", false);
            return;
        }
        Vector2 climbVelocity = new Vector2(myRigidbody.linearVelocity.x, moveInput.y * climbSpeed);
        myRigidbody.linearVelocity = climbVelocity;
        myRigidbody.gravityScale = 0f;

        bool playerHasVerticalSpeed = Mathf.Abs(myRigidbody.linearVelocity.y) > Mathf.Epsilon;
        myAnimator.SetBool("IsClimbing", playerHasVerticalSpeed);
    }
}