using UnityEngine;
using UnityEngine.InputSystem;

public class FireSpell : MonoBehaviour
{
    [Header("Spell Prefabs")]
    [SerializeField] private GameObject fireSpellPrefab;
    [SerializeField] private GameObject fireSpellUpPrefab;

    [Header("Spawn Points")]
    [SerializeField] private Transform firePoint;
    [SerializeField] private Transform firePointUp;

    public void OnFire(InputValue value)
    {
        if (!value.isPressed)
            return;

        FireHorizontal();
    }

    public void OnFireUp(InputValue value)
    {
        if (!value.isPressed)
            return;

        FireUp();
    }

    private void FireHorizontal()
    {
        if (fireSpellPrefab == null || firePoint == null)
        {
            Debug.LogWarning("FireSpell: Horizontal prefab or FirePoint is missing!");
            return;
        }

        float direction = Mathf.Sign(transform.root.localScale.x);

        GameObject spell = Instantiate(
            fireSpellPrefab,
            firePoint.position,
            Quaternion.identity
        );

        Bullet bullet = spell.GetComponent<Bullet>();

        if (bullet != null)
        {
            bullet.SetDirection(new Vector2(direction, 0f));

            bullet.SetPlayerFirePosition(transform.root.position);
        }
    }

    private void FireUp()
    {
        if (fireSpellUpPrefab == null || firePointUp == null)
        {
            Debug.LogWarning("FireSpell: Up prefab or FirePointUp is missing!");
            return;
        }

        // Spawn from the TOP of the player's head
        GameObject spell = Instantiate(
            fireSpellUpPrefab,
            firePointUp.position,
            Quaternion.Euler(0f, 0f, -90f)
        );

        Bullet bullet = spell.GetComponent<Bullet>();

        if (bullet != null)
        {
            bullet.SetDirection(Vector2.up);

            bullet.SetPlayerFirePosition(transform.root.position);
        }
    }
}