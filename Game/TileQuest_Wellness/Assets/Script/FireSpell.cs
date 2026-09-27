using UnityEngine;
using UnityEngine.InputSystem;

public class FireSpell : MonoBehaviour
{
    [Header("Spell Prefabs")]
    public GameObject fireSpellPrefab;
    public GameObject fireSpellUpPrefab;

    [Header("Spawn Point")]
    public Transform firePoint;

    [Header("Settings")]
    public float spellSpeed = 15f;

    private bool fireHeld = false;
    private bool fireUpHeld = false;

    public void OnFire(InputValue value)
    {
        fireHeld = value.isPressed;
        TryFire();
    }

    public void OnFireUp(InputValue value)
    {
        fireUpHeld = value.isPressed;
        TryFire();
    }

    private void TryFire()
    {
        if (fireHeld && fireUpHeld)
        {
            SpawnSpell(fireSpellUpPrefab, Vector2.up);
        }
        else if (fireHeld)
        {
            float facingDirection = Mathf.Sign(transform.localScale.x);
            SpawnSpell(fireSpellPrefab, new Vector2(facingDirection, 0f));
        }
    }

    private void SpawnSpell(GameObject prefab, Vector2 direction)
    {
        if (prefab == null || firePoint == null) return;

        GameObject spell = Instantiate(prefab, firePoint.position, Quaternion.identity);
        Rigidbody2D rb = spell.GetComponent<Rigidbody2D>();
        if (rb != null)
        {
            rb.linearVelocity = direction.normalized * spellSpeed;
        }
    }
}