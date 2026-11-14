using UnityEngine;
using UnityEngine.InputSystem;

public class BoulderCarrier : MonoBehaviour
{
    [SerializeField] private Transform holdPoint;
    [SerializeField] private float carrySpeedMultiplier = 0.6f;
    [SerializeField] private float pickupRange = 1f;
    [SerializeField] private LayerMask boulderLayer;

    private Boulder heldBoulder;
    private PlayerMovement playerMovement;

    public bool IsCarrying => heldBoulder != null;
    public float CarrySpeedMultiplier => carrySpeedMultiplier;

    private void Awake()
    {
        playerMovement = GetComponent<PlayerMovement>();
    }

    public void OnInteract(InputValue value)
    {
        if (!value.isPressed) return;

        if (heldBoulder == null)
            TryPickUp();
        else
            Throw();
    }

    private void TryPickUp()
    {
        Collider2D hit = Physics2D.OverlapCircle(transform.position, pickupRange, boulderLayer);
        if (hit != null)
        {
            Boulder boulder = hit.GetComponent<Boulder>();
            if (boulder != null && !boulder.IsHeld)
            {
                heldBoulder = boulder;
                heldBoulder.PickUp(holdPoint);
            }
        }
    }

    private void Throw()
    {
        if (heldBoulder == null) return;
        float direction = Mathf.Sign(transform.localScale.x);
        heldBoulder.Throw(direction);
        heldBoulder = null;
    }
}